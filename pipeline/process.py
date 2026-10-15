"""Detect all people on the rink, record jersey color stats, save 4K crops of players in our jersey (rink.jersey).

Usage: process.py VIDEO OUTDIR FPS [START_SEC DUR_SEC]
  (restart after a crash with START_SEC = last t in dets.csv; frame numbers stay global)
Outputs:
  OUTDIR/dets.csv    frame,t,x1,y1,x2,y2,conf,blue,white,purple,red,dark,lblue,bhue (bhue from Oct 2026)
  OUTDIR/crops/      f{frame:06d}_{i:02d}.jpg  (candidates in our jersey)
  OUTDIR/ov/         ov_{sec:05d}.jpg overview frames every 10 s
"""
import os, sys, time, threading, queue, subprocess
import numpy as np, cv2
from ultralytics import YOLO
from rink import rink, jersey
from crops import wants_crop, save_crop, torso, blue_hue

import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe()
VID, OUT, FPS = sys.argv[1], sys.argv[2], float(sys.argv[3])
START = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
DUR = float(sys.argv[5]) if len(sys.argv) > 5 else None
_meta = next(imageio_ffmpeg.read_frames(VID))
W, FULL_H = _meta["size"]
# rink band: the wide-cut camera shows ceiling above the far boards; keep far boards + ice
R = rink(OUT)
Y0, Y1 = int(round(R.crop_top * FULL_H)), FULL_H
H = Y1 - Y0
os.makedirs(f"{OUT}/crops", exist_ok=True); os.makedirs(f"{OUT}/ov", exist_ok=True)

cmd = [FF, "-loglevel", "error", "-threads", "0"]
if START: cmd += ["-ss", str(START)]
cmd += ["-i", VID]
if DUR: cmd += ["-t", str(DUR)]
cmd += ["-vf", f"fps={FPS},crop={W}:{H}:0:{Y0}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
# unbuffered, read with readinto: on Windows a buffered read() of a 13 MB frame tops out at ~18 fps
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=0)
q = queue.Queue(maxsize=32)

def reader():
    n = 0; size = W * H * 3
    while True:
        buf = bytearray(size); mv = memoryview(buf); got = 0
        while got < size:
            k = proc.stdout.readinto(mv[got:])
            if not k:
                break
            got += k
        if got < size:
            q.put(None); return
        q.put((n, np.frombuffer(buf, np.uint8).reshape(H, W, 3)))
        n += 1
threading.Thread(target=reader, daemon=True).start()

model = YOLO(os.environ.get("YOLO_MODEL", "yolo11m.pt"))  # downloads on first use
import torch
DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

crop_test = jersey(OUT)["crop"]

def color_stats(img, b):
    t = torso(img, b)
    if t.size == 0:
        return [0] * 7
    hsv = cv2.cvtColor(t, cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(np.int16)
    Hh, Ss, Vv = hsv[:, 0], hsv[:, 1], hsv[:, 2]
    n = len(hsv)
    blue = ((Hh >= 90) & (Hh <= 125) & (Ss >= 70) & (Vv >= 70)).sum() / n
    lblue = ((Hh >= 90) & (Hh <= 118) & (Ss >= 50) & (Ss < 200) & (Vv >= 130)).sum() / n
    white = ((Ss < 45) & (Vv >= R.white_v)).sum() / n
    purple = ((Hh >= 125) & (Hh <= 165) & (Ss >= 60) & (Vv >= 50)).sum() / n
    red = (((Hh <= 8) | (Hh >= 170)) & (Ss >= 100) & (Vv >= 70)).sum() / n
    dark = (Vv < R.dark_v).sum() / n
    return [blue, white, purple, red, dark, lblue, blue_hue(Hh, Ss, Vv)]

fcsv = open(f"{OUT}/dets.csv", "a")
t0 = time.time(); done = False; BATCH = 8
while not done:
    batch = []
    while len(batch) < BATCH:
        item = q.get()
        if item is None:
            done = True; break
        batch.append(item)
    if not batch:
        break
    res = model.predict([f for _, f in batch], imgsz=1920, classes=[0], conf=0.15,
                        device=DEVICE, verbose=False)
    for (n, img), r in zip(batch, res):
        t = START + n / FPS
        n = n + int(round(START * FPS))  # global frame index so crop names/CSV continue across restarts
        sec = int(round(t))
        if abs(t - sec) < 0.5 / FPS and sec % 10 == 0:
            cv2.imwrite(f"{OUT}/ov/ov_{sec:05d}.jpg", cv2.resize(img, (1280, 381)), [cv2.IMWRITE_JPEG_QUALITY, 80])
        boxes = r.boxes.xyxy.cpu().numpy(); confs = r.boxes.conf.cpu().numpy()
        for i, (b, c) in enumerate(zip(boxes, confs)):
            bi = b.astype(int)
            cs = color_stats(img, bi)
            fcsv.write(f"{n},{t:.3f},{bi[0]},{bi[1]+Y0},{bi[2]},{bi[3]+Y0},{c:.3f}," +
                       ",".join(f"{v:.3f}" for v in cs) + "\n")
            if wants_crop(crop_test, cs, bi[3] - bi[1], n):
                save_crop(img, bi, f"{OUT}/crops/f{n:06d}_{i:02d}.jpg")
    if batch[0][0] % (BATCH * 50) == 0:
        el = time.time() - t0
        print(f"frame {batch[-1][0]} t={START + batch[-1][0] / FPS:.0f}s elapsed={el:.0f}s "
              f"rate={(batch[-1][0] + 1) / el:.1f} fps", flush=True)
    fcsv.flush()
print("DONE", time.time() - t0, flush=True)
