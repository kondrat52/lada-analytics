"""The arena scoreboard in the wide cut (rink.py `scoreboard` box): period clock, score, shots, and the penalty panels
(player number and time left). Its LEDs flicker, so most single frames show it dark: keep the brightest of each
second's frames.

  scoreboard.py W                 one pass over the video -> W/scoreboard.npy (~5 min; fetch does this)
  scoreboard.py W OUT.jpg t1 t2 …  the board at those seconds of video as a sheet, 2.5x (scans first if needed;
                                   an archived folder's scoreboard_jpg.npz serves too)
"""
import os, subprocess, sys, threading, time
import numpy as np, cv2, imageio_ffmpeg
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rink import rink

STALL = 120   # s without a frame: the pass is wedged (a stuck NVDEC, say) and is killed


def _cpu_forced():
    return os.environ.get("SCOREBOARD_CPU", "") not in ("", "0")


def _decode(vid, box, gpu, threads, seek=None, dur=None):
    """ffmpeg reading the board's box of every frame as BGR (from `seek` s, for `dur` s). gpu: NVDEC decodes
    (-hwaccel cuda: ffmpeg's own VP9 parser driving NVDEC, which gave the software decode's bytes on every frame of an
    8-minute slice; the vp9_cuvid decoder's own -crop drifted by up to 28 levels within a GOP) and the box is cut out
    on the GPU, so only it comes back: this ffmpeg has no crop for CUDA frames (`crop` passes them whole), so the frame
    is laid onto a box-sized one with overlay_cuda at minus the box's corner. Through yuv420p, so the conversion to BGR
    is the software path's (NV12 to BGR rounds differently). An odd side or corner comes out otherwise than crop's
    (which evens them): gpu_ok then says no."""
    x, y, w, h = box
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-loglevel", "error"]
    cmd += (["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"] if gpu else ["-threads", str(threads)])
    cmd += (["-ss", str(seek)] if seek else []) + ["-i", vid] + (["-t", str(dur)] if dur else [])
    if gpu:
        cmd += ["-filter_complex", f"[0:v]split[a][b];[a]scale_cuda={w}:{h}[m];[m][b]overlay_cuda=x={-x}:y={-y},"
                                   "hwdownload,format=nv12,format=yuv420p"]
    else:
        cmd += ["-vf", f"crop={w}:{h}:{x}:{y}"]
    return cmd + ["-f", "rawvideo", "-pix_fmt", "bgr24", "-"], (w, h)


def gpu_ok(vid, box, duration):
    """Whether the GPU path gives the software path's bytes for the video's first second and one in the middle (no
    NVDEC, no CUDA filters, another ffmpeg, an odd box: it doesn't, and the scan decodes on the CPU). About 2 s.
    SCOREBOARD_CPU=1 skips it; so does the Mac, which has no NVDEC, and a video whose container gives no duration
    (there's no middle second to check, and no length to tell a short pass by)."""
    if _cpu_forced() or sys.platform == "darwin" or not duration:
        return False
    for seek in [None] + ([int(duration / 2)] if duration > 10 else []):
        try:
            outs = [subprocess.run(_decode(vid, box, gpu, 0, seek, 1)[0], capture_output=True, timeout=120).stdout
                    for gpu in (True, False)]
        except Exception:
            return False
        if not outs[0] or outs[0] != outs[1]:
            return False
    return True


def _pass(vid, box, gpu, low_priority, fps):
    """One decode of the whole video -> (the brightest frame of each second, frames read, ffmpeg's exit code, whether
    it stalled). A watchdog kills an ffmpeg that sends no frame for STALL s; whatever happens, ffmpeg doesn't outlive
    the pass (on the GPU path it would hold its CUDA context)."""
    cmd, (w, h) = _decode(vid, box, gpu, 4 if low_priority else 0)
    low = low_priority and not gpu
    nice = dict(creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS) if low and sys.platform == "win32" else {}
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=w * h * 3 * 64, **nice)
    last, stalled, done = [time.time()], threading.Event(), threading.Event()

    def watch():
        while not done.wait(min(5.0, STALL / 4)):
            if time.time() - last[0] > STALL:
                stalled.set(); p.kill(); return
    threading.Thread(target=watch, daemon=True).start()
    best, lit, n = [], [], 0
    try:
        if low and sys.platform != "win32":
            os.setpriority(os.PRIO_PROCESS, p.pid, 10)
        while len(buf := p.stdout.read(w * h * 3)) == w * h * 3:
            last[0] = time.time()
            f = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            s, v = int(n / fps), int((f[..., 2].astype(np.int16) - f[..., 1] > 60).sum())   # lit red LEDs
            if s == len(best):
                best.append(f.copy()); lit.append(v)
            elif v > lit[s]:
                best[s], lit[s] = f.copy(), v
            n += 1
        rc = p.wait()
    finally:
        done.set()
        if p.poll() is None:
            p.kill(); p.wait()
    return best, n, rc, stalled.is_set()


def scan(W, out=None, low_priority=False):
    """low_priority: fetch runs this alongside detection. A CPU decode then gets 4 threads at below-normal priority:
    on a 4-minute slice of the Oct 25 video that slowed detection by 16%, all threads by 31%. Where the GPU path passes
    gpu_ok the decode is on NVDEC and costs about a tenth of the CPU (2.5 CPU-s per minute of 4K VP9 against 23.5 for
    the CPU decode at 4 threads, Nov 18, 2026), and it keeps normal priority: below normal, the little CPU it needs
    came too late, and alongside detection and 4 OCR workers it took 2.7-2.9 minutes for an 8-minute slice, ending
    50-60 s after detection; at normal priority 0.8-0.9 minutes, ending 60-80 s before it, detection no slower.
    Returns "GPU" or "CPU". A GPU pass that fails, stalls (no frame for STALL s) or comes up short (over 1 s under the
    video's length; the board's seconds matched the duration within 0 to +1 on 32 archived games) is redone on the CPU
    from the start; a CPU pass that stalls raises, so no truncated scoreboard.npy is saved."""
    out = out or f"{W}/scoreboard.npy"
    vid = f"{W}/video.webm"
    box = rink(f"{W}/full").scoreboard
    meta = next(imageio_ffmpeg.read_frames(vid))
    fps, dur = meta["fps"], meta.get("duration") or 0   # fps 24 at first, 30 since Oct 2026
    for gpu in ((True, False) if gpu_ok(vid, box, dur) else (False,)):
        best, n, rc, stalled = _pass(vid, box, gpu, low_priority, fps)
        if not gpu:
            if stalled:
                raise RuntimeError(f"scoreboard: the CPU decode stalled (no frame for {STALL} s) after {n} frames")
            break
        if rc == 0 and not stalled and len(best) >= dur - 1:
            break
        why = "stalled" if stalled else f"failed ({rc})" if rc else "came up short"
        print(f"scoreboard: the GPU decode {why} after {n} frames ({len(best)} s); again on the CPU", flush=True)
    np.save(out[:-4] + ".tmp.npy", np.array(best))   # a scan cut short leaves no scoreboard.npy for load() to trust
    os.replace(out[:-4] + ".tmp.npy", out)
    print(f"{out}: {len(best)} s")
    return "GPU" if gpu else "CPU"


def compress(W):
    """scoreboard.npy -> scoreboard_jpg.npz, the same frames as JPEGs (~20 MB instead of ~150-400): what archive keeps."""
    a = np.load(f"{W}/scoreboard.npy", mmap_mode="r")
    jpgs = [cv2.imencode(".jpg", np.asarray(f), [cv2.IMWRITE_JPEG_QUALITY, 90])[1].tobytes() for f in a]
    np.savez(f"{W}/scoreboard_jpg.npz", data=np.frombuffer(b"".join(jpgs), np.uint8),
             ends=np.cumsum([len(j) for j in jpgs]), shape=np.array(a.shape[1:3]))
    print(f"{W}/scoreboard_jpg.npz: {len(jpgs)} s")


def load(W):
    """The board per second: scoreboard.npy, else the JPEGs an archive keeps, else a scan of the video."""
    if os.path.exists(f"{W}/scoreboard.npy"):
        return np.load(f"{W}/scoreboard.npy")
    if os.path.exists(f"{W}/scoreboard_jpg.npz"):
        z = np.load(f"{W}/scoreboard_jpg.npz")
        data, ends = z["data"], z["ends"]
        starts = np.r_[0, ends[:-1]]
        return np.array([cv2.imdecode(data[s:e], cv2.IMREAD_COLOR) for s, e in zip(starts, ends)])
    if not os.path.exists(f"{W}/video.webm"):
        raise SystemExit(f"{W}: no scoreboard.npy, scoreboard_jpg.npz or video.webm to read the board from")
    scan(W)
    return np.load(f"{W}/scoreboard.npy")


def sheet(W, out, ts, cols=6):
    a = load(W)
    h, w = a.shape[1:3]
    tw = 325; th = int(tw * h / w)
    tiles = []
    for t in ts:
        im = cv2.resize(a[min(int(t), len(a) - 1)], (tw, th), interpolation=cv2.INTER_CUBIC)
        cv2.putText(im, f"{int(t) // 60}:{int(t) % 60:02d} ({int(t)})", (4, th - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 255, 255), 1)
        tiles.append(im)
    blank = np.zeros_like(tiles[0])
    rows = [np.hstack(tiles[i:i + cols] + [blank] * (cols - len(tiles[i:i + cols]))) for i in range(0, len(tiles), cols)]
    cv2.imwrite(out, np.vstack(rows))
    print(out)


if __name__ == "__main__":
    W = os.path.abspath(sys.argv[1])
    if len(sys.argv) == 2:
        scan(W)
    else:
        sheet(W, sys.argv[2], [float(t) for t in sys.argv[3:]])
