"""4K crops of players in our jersey, for OCR and the visual review. process.py saves them while detecting.

Usage: crops.py VIDEO OUTDIR FPS : cut the crops process.py would have saved for OUTDIR/dets.csv with the jersey
now in OUTDIR/rink.json, without detecting again (for when the jersey was set after detection). Crops that exist
are kept; frame numbers match process.py's (the same fps filter from t=0).
       crops.py VIDEO OUTDIR FPS --hue : add the bhue column to a dets.csv made before process.py wrote it.
"""
import os, sys, threading, queue, subprocess, time
import numpy as np, cv2

COLORS = ["blue", "white", "purple", "red", "dark", "lblue", "bhue"]   # color_stats order, as in dets.csv


def torso(img, b):
    """The part of box b that process.py takes colours from: the middle 60% across, 15-50% of the way down."""
    x1, y1, x2, y2 = b
    w, h = x2 - x1, y2 - y1
    tx1, tx2 = int(x1 + 0.2 * w), int(x2 - 0.2 * w)
    ty1, ty2 = int(y1 + 0.15 * h), int(y1 + 0.5 * h)
    return img[max(ty1, 0):max(ty2, ty1 + 1), max(tx1, 0):max(tx2, tx1 + 1)]


def blue_hue(Hh, Ss, Vv):
    """Median hue (OpenCV's 0-180) of the torso's blue pixels, 0 if fewer than 20: what tells our blue jersey from
    another team's lighter one (at Kirkland ours ~113, Teamy McTeamface's sky blue ~107)."""
    b = (Hh >= 90) & (Hh <= 125) & (Ss >= 70) & (Vv >= 70)
    return float(np.median(Hh[b])) if b.sum() >= 20 else 0.0


def wants_crop(test, cs, h, n):
    """test: the jersey's crop test (rink.JERSEYS); cs: color_stats list; small (far) players every third frame."""
    return bool(test(dict(zip(COLORS, cs)))) and (h >= 100 or n % 3 == 0)


def save_crop(img, bi, path):
    """bi: box in img's pixels (img = the detection band of the frame)."""
    h = bi[3] - bi[1]
    pw, ph = int(0.1 * (bi[2] - bi[0])), int(0.05 * h)
    crop = img[max(bi[1] - ph, 0):bi[3] + ph, max(bi[0] - pw, 0):bi[2] + pw]
    cv2.imwrite(path, crop, [cv2.IMWRITE_JPEG_QUALITY, 88])


def recrop(vid, out, fps):
    import imageio_ffmpeg, pandas as pd
    from rink import rink, jersey
    FF = imageio_ffmpeg.get_ffmpeg_exe()
    test = jersey(out)["crop"]
    d = pd.read_csv(f"{out}/dets.csv", header=None, names=["frame", "t", "x1", "y1", "x2", "y2", "conf"] + COLORS)
    d["i"] = d.groupby("frame").cumcount()
    have = set(os.listdir(f"{out}/crops"))
    d["fn"] = [f"f{f:06d}_{i:02d}.jpg" for f, i in zip(d.frame, d.i)]
    keep = [wants_crop(test, cs, y2 - y1, f) and fn not in have
            for cs, y1, y2, f, fn in zip(d[COLORS].values, d.y1, d.y2, d.frame, d.fn)]
    d = d[keep]
    print(f"{len(d)} crops to cut", flush=True)
    if d.empty:
        return
    W, FULL_H = next(imageio_ffmpeg.read_frames(vid))["size"]
    Y0 = int(round(rink(out).crop_top * FULL_H)); H = FULL_H - Y0
    todo = {f: g[["x1", "y1", "x2", "y2", "fn"]].values for f, g in d.groupby("frame")}
    last = max(todo)
    proc = subprocess.Popen([FF, "-loglevel", "error", "-threads", "0", "-i", vid, "-vf",
                             f"fps={fps},crop={W}:{H}:0:{Y0}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                            stdout=subprocess.PIPE, bufsize=W * H * 3 * 4)
    q = queue.Queue(maxsize=32)

    def reader():
        n = 0
        while n <= last:
            buf = proc.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break
            if n in todo:
                q.put((n, np.frombuffer(buf, np.uint8).reshape(H, W, 3)))
            n += 1
        q.put(None)
    threading.Thread(target=reader, daemon=True).start()
    t0, done, shown = time.time(), 0, 0
    while (item := q.get()) is not None:
        n, img = item
        for x1, y1, x2, y2, fn in todo[n]:
            save_crop(img, (x1, y1 - Y0, x2, y2 - Y0), f"{out}/crops/{fn}")
            done += 1
        if time.time() - shown > 60:
            shown = time.time()
            print(f"frame {n} t={n / fps:.0f}s crops={done} elapsed={time.time() - t0:.0f}s", flush=True)
    proc.kill()
    print(f"cut {done} crops in {time.time() - t0:.0f}s", flush=True)


def add_hue(vid, out, fps):
    """Append bhue to every row of out/dets.csv (one pass over the video, the same frames process.py read)."""
    import imageio_ffmpeg
    from rink import rink
    lines = open(f"{out}/dets.csv").read().splitlines()
    if lines and lines[0].count(",") >= 7 + len(COLORS) - 1:
        print("dets.csv has bhue already"); return
    rows = {}
    for k, l in enumerate(lines):
        p = l.split(",")
        rows.setdefault(int(p[0]), []).append((k, *map(int, p[2:6])))
    W, FULL_H = next(imageio_ffmpeg.read_frames(vid))["size"]
    Y0 = int(round(rink(out).crop_top * FULL_H)); H = FULL_H - Y0
    proc = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-threads", "0", "-i", vid, "-vf",
                             f"fps={fps},crop={W}:{H}:0:{Y0}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                            stdout=subprocess.PIPE, bufsize=0)
    hue = [None] * len(lines); last = max(rows); n = 0; t0 = shown = time.time()
    buf = bytearray(W * H * 3); mv = memoryview(buf)
    while n <= last:
        got = 0
        while got < len(buf) and (k := proc.stdout.readinto(mv[got:])):
            got += k
        if got < len(buf):
            break
        img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        for k, x1, y1, x2, y2 in rows.get(n, ()):
            hsv = cv2.cvtColor(torso(img, (x1, y1 - Y0, x2, y2 - Y0)), cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(np.int16)
            hue[k] = blue_hue(*hsv.T)
        n += 1
        if time.time() - shown > 60:
            shown = time.time(); print(f"frame {n} of {last + 1}, {time.time() - t0:.0f}s", flush=True)
    proc.kill()
    if any(h is None for h in hue):
        sys.exit(f"the video ended at frame {n}, before dets.csv's last frame {last}")
    open(f"{out}/dets.tmp", "w").write("".join(f"{l},{h:.3f}\n" for l, h in zip(lines, hue)))
    os.replace(f"{out}/dets.tmp", f"{out}/dets.csv")
    print(f"bhue for {len(lines)} detections in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    (add_hue if "--hue" in sys.argv else recrop)(sys.argv[1], sys.argv[2], float(sys.argv[3]))
