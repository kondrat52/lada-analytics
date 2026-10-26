"""The arena scoreboard in the wide cut (rink.py `scoreboard` box): period clock, score, shots, and the penalty panels
(player number and time left). Its LEDs flicker, so most single frames show it dark: keep the brightest of each
second's frames.

  scoreboard.py W                 one pass over the video -> W/scoreboard.npy (~5 min; fetch does this)
  scoreboard.py W OUT.jpg t1 t2 …  the board at those seconds of video as a sheet, 2.5x (scans first if needed;
                                   an archived folder's scoreboard_jpg.npz serves too)
"""
import os, subprocess, sys
import numpy as np, cv2, imageio_ffmpeg
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rink import rink


def scan(W, out=None, low_priority=False):
    """low_priority: fetch runs this alongside detection, so the decode gets 4 threads at below-normal priority.
    On a 4-minute slice of the Oct 25 video that slowed detection by 16%, all threads by 31%."""
    out = out or f"{W}/scoreboard.npy"
    x, y, w, h = rink(f"{W}/full").scoreboard
    nice = dict(creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS) if low_priority and sys.platform == "win32" else {}
    p = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-loglevel", "error",
                          "-threads", "4" if low_priority else "0",
                          "-i", f"{W}/video.webm", "-vf", f"crop={w}:{h}:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "bgr24",
                          "-"], stdout=subprocess.PIPE, bufsize=w * h * 3 * 64, **nice)
    if low_priority and sys.platform != "win32":
        os.setpriority(os.PRIO_PROCESS, p.pid, 10)
    fps = next(imageio_ffmpeg.read_frames(f"{W}/video.webm"))["fps"]   # 24 at first, 30 since Oct 2026
    best, lit, n = [], [], 0
    while len(buf := p.stdout.read(w * h * 3)) == w * h * 3:
        f = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        s, v = int(n / fps), int((f[..., 2].astype(np.int16) - f[..., 1] > 60).sum())   # lit red LEDs
        if s == len(best):
            best.append(f.copy()); lit.append(v)
        elif v > lit[s]:
            best[s], lit[s] = f.copy(), v
        n += 1
    p.wait()
    np.save(out[:-4] + ".tmp.npy", np.array(best))   # a scan cut short leaves no scoreboard.npy for load() to trust
    os.replace(out[:-4] + ".tmp.npy", out)
    print(f"{out}: {len(best)} s")


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
