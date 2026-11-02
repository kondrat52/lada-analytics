"""Detect all people on the rink, record jersey color stats, save 4K crops of players in our jersey (rink.jersey).

Usage: process.py VIDEO OUTDIR FPS [START_SEC DUR_SEC]
  (restart after a crash with START_SEC = last t in dets.csv; frame numbers stay global)
Outputs:
  OUTDIR/dets.csv    frame,t,x1,y1,x2,y2,conf,blue,white,purple,red,dark,lblue,bhue (bhue from Oct 2026)
  OUTDIR/crops/      f{frame:06d}_{i:02d}.jpg  (candidates in our jersey, not those seated deep in our bench)
  OUTDIR/ov/         ov_{sec:05d}.jpg overview frames every 10 s

Three processes over one ring of frames in shared memory (SLOTS of them): a reader that fills slots from ffmpeg's
pipe, this one running the model on batches of 8, and a post-processor doing the colour statistics, the crop JPEGs,
the CSV lines and the overview frames in frame order, then freeing the slots. Measured on a 4-minute slice of
3840x1536 video (RTX 5090, Nov 2, 2026): 34 s against 53 s with everything in one process (ffmpeg alone 21 s,
the model alone about 36 s), the same detections and crops; a thread instead of a process for the post-processing
gained nothing, since that work holds the GIL. On a kill of this process the children notice within 5 s and exit."""
import os, sys, time, subprocess, multiprocessing as mp
from multiprocessing import shared_memory
import numpy as np

SLOTS = int(os.environ.get("SLOTS", "48"))


def reader_proc(cmd, shm_name, W, H, slots, free_q, full_q):
    """ffmpeg -> shared-memory slots. Puts (slot, n) on full_q, None at the end; takes free slots from free_q."""
    shm = shared_memory.SharedMemory(name=shm_name)
    size = W * H * 3
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=0)
    n = 0
    parent = mp.parent_process()
    while True:
        while True:
            try:
                slot = free_q.get(timeout=5); break
            except Exception:
                if not parent.is_alive():
                    proc.kill(); shm.close(); return
        mv = memoryview(shm.buf)[slot * size:(slot + 1) * size]; got = 0
        while got < size:
            k = proc.stdout.readinto(mv[got:])
            if not k:
                break
            got += k
        if got < size:
            full_q.put(None); break
        full_q.put((slot, n)); n += 1
    proc.wait(); shm.close()


def post_proc(OUT, shm_name, W, H, Y0, FPS, START, post_q, free_q):
    """Colour stats, crops, CSV lines and overview frames for each batch, in frame order; frees the slots."""
    import cv2
    from rink import rink, jersey
    from crops import wants_crop, save_crop, torso, blue_hue, deep_in_bench
    R = rink(OUT); crop_test = jersey(OUT)["crop"]
    shm = shared_memory.SharedMemory(name=shm_name)
    frames = np.ndarray((SLOTS, H, W, 3), np.uint8, buffer=shm.buf)

    def color_stats(img, b):
        t = torso(img, b)
        if t.size == 0:
            return [0] * 7
        hsv = cv2.cvtColor(t, cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(np.int16)
        Hh, Ss, Vv = hsv[:, 0], hsv[:, 1], hsv[:, 2]
        n = len(hsv)
        blue = ((Hh >= 90) & (Hh <= 125) & (Ss >= R.blue_s) & (Vv >= 70)).sum() / n
        lblue = ((Hh >= 90) & (Hh <= 118) & (Ss >= 50) & (Ss < 200) & (Vv >= 130)).sum() / n
        white = ((Ss < 45) & (Vv >= R.white_v)).sum() / n
        purple = ((Hh >= 125) & (Hh <= 165) & (Ss >= 60) & (Vv >= 50)).sum() / n
        red = (((Hh <= 8) | (Hh >= 170)) & (Ss >= 100) & (Vv >= 70)).sum() / n
        dark = (Vv < R.dark_v).sum() / n
        return [blue, white, purple, red, dark, lblue, blue_hue(Hh, Ss, Vv)]

    fcsv = open(f"{OUT}/dets.csv", "a")
    parent = mp.parent_process()
    while True:
        try:
            item = post_q.get(timeout=5)
        except Exception:
            if not parent.is_alive():
                return
            continue
        if item is None:
            break
        for slot, n, boxes, confs in item:
            img = frames[slot]
            t = START + n / FPS
            n = n + int(round(START * FPS))
            sec = int(round(t))
            if abs(t - sec) < 0.5 / FPS and sec % 10 == 0:
                cv2.imwrite(f"{OUT}/ov/ov_{sec:05d}.jpg", cv2.resize(img, (1280, 381)), [cv2.IMWRITE_JPEG_QUALITY, 80])
            deep = deep_in_bench(R, boxes, Y0)
            for i, (b, c) in enumerate(zip(boxes, confs)):
                bi = b.astype(int)
                cs = color_stats(img, bi)
                fcsv.write(f"{n},{t:.3f},{bi[0]},{bi[1]+Y0},{bi[2]},{bi[3]+Y0},{c:.3f}," +
                           ",".join(f"{v:.3f}" for v in cs) + "\n")
                if not deep[i] and wants_crop(crop_test, cs, bi[3] - bi[1], n):
                    save_crop(img, bi, f"{OUT}/crops/f{n:06d}_{i:02d}.jpg")
            free_q.put(slot)
        fcsv.flush()
    fcsv.close(); shm.close()


def main():
    import imageio_ffmpeg
    from rink import rink
    FF = imageio_ffmpeg.get_ffmpeg_exe()
    VID, OUT, FPS = sys.argv[1], sys.argv[2], float(sys.argv[3])
    START = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
    DUR = float(sys.argv[5]) if len(sys.argv) > 5 else None
    _meta = next(imageio_ffmpeg.read_frames(VID))
    W, FULL_H = _meta["size"]
    R = rink(OUT)
    Y0, Y1 = int(round(R.crop_top * FULL_H)), FULL_H
    H = Y1 - Y0
    os.makedirs(f"{OUT}/crops", exist_ok=True); os.makedirs(f"{OUT}/ov", exist_ok=True)

    cmd = [FF, "-loglevel", "error", "-threads", "0"]
    if START: cmd += ["-ss", str(START)]
    cmd += ["-i", VID]
    if DUR: cmd += ["-t", str(DUR)]
    cmd += ["-vf", f"fps={FPS},crop={W}:{H}:0:{Y0}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]

    size = W * H * 3
    shm = shared_memory.SharedMemory(create=True, size=SLOTS * size)
    frames = np.ndarray((SLOTS, H, W, 3), np.uint8, buffer=shm.buf)
    free_q, full_q, post_q = mp.Queue(), mp.Queue(), mp.Queue(maxsize=4)
    for s in range(SLOTS):
        free_q.put(s)
    rp = mp.Process(target=reader_proc, args=(cmd, shm.name, W, H, SLOTS, free_q, full_q), daemon=True); rp.start()
    SKIP_POST = bool(os.environ.get("SKIP_POST"))
    pp = None
    if not SKIP_POST:
        pp = mp.Process(target=post_proc, args=(OUT, shm.name, W, H, Y0, FPS, START, post_q, free_q), daemon=True); pp.start()

    from ultralytics import YOLO
    import torch
    model = YOLO(os.environ.get("YOLO_MODEL", "yolo11m.pt"))
    DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

    t0 = time.time(); done = False; BATCH = 8
    while not done:
        batch = []
        while len(batch) < BATCH:
            item = full_q.get()
            if item is None:
                done = True; break
            batch.append(item)
        if not batch:
            break
        res = model.predict([frames[s] for s, _ in batch], imgsz=1920, classes=[0], conf=0.15,
                            device=DEVICE, verbose=False)
        if SKIP_POST:
            for s, _ in batch:
                free_q.put(s)
        else:
            post_q.put([(s, n, r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy())
                        for (s, n), r in zip(batch, res)])
        if batch[0][1] % (BATCH * 50) == 0:
            el = time.time() - t0
            print(f"frame {batch[-1][1]} t={START + batch[-1][1] / FPS:.0f}s elapsed={el:.0f}s "
                  f"rate={(batch[-1][1] + 1) / el:.1f} fps", flush=True)
    if pp:
        post_q.put(None); pp.join()
    rp.join(timeout=10)
    print("DONE", time.time() - t0, flush=True)
    shm.close(); shm.unlink()


if __name__ == "__main__":
    mp.freeze_support()
    main()
