"""rinkcal.py : calibrate a rink's camera for the ice maps (rinkcam.py -> pipeline/cams/<rink>.json, used by ice.py).
One calibration serves every game at that rink and camera (a video framed higher or lower is shifted by its own
boards curve). The steps, with the landmark brief, are in the process-game skill's references/ice.md:

  rinkcal.py frame W DIR                     an empty rink: the median of 41 frames of W's video -> DIR/median.png,
                                             DIR/enh.png (contrast-enhanced), DIR/half.jpg (half size, rulers) and
                                             DIR/left.jpg, DIR/right.jpg (1:1 halves, 50 px grid)
  rinkcal.py crop DIR X0 X1 Y0 Y1 [ZOOM] [plain]   DIR/lm/crop_X0_Y0.jpg: a zoomed crop with a 10 px grid in source px
  rinkcal.py fit DIR W pano|fisheye [OUT.json]     fit the camera to DIR/landmarks.json (read off the frame by a
                                             subagent), write pipeline/cams/<W's rink>.json (or OUT.json) and
                                             DIR/check.jpg, and print the checks: each marking's error in feet, where
                                             their goalie lands, and how many of our detections fall off the ice

pano (a panoramic strip, Snoqualmie A) is fitted in pixels: the projected markings against the landmarks, 40 random
starts. fisheye (Snoqualmie B) is fitted in feet: each landmark mapped onto the ice against its marking, the camera
held to physical bounds, plus a degree-2 warp on the ice; a pixel fit there stretched the far side 7 ft, an unbounded
feet fit put the camera at ice level."""
import json, os, subprocess, sys
import numpy as np, cv2
from scipy.optimize import least_squares
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rinkcam as rc
from rink import rink, rink_name

L, B = rc.L, rc.B
LINES = {"center": ("X", 0.0, B), "blue_left": ("X", -25.0, B), "blue_right": ("X", 25.0, B),
         "goal_left": ("X", -89.0, 36.75), "goal_right": ("X", 89.0, 36.75), "boards_far": ("Y", B, 72.0),
         "boards_near": ("Y", -B, 72.0), "boards_end_left": ("X", -L, 14.5), "boards_end_right": ("X", L, 14.5)}
CIRCLES = {"circle_center": (0, 0, 15), "circle_end_near_left": (-69, -22, 15), "circle_end_near_right": (69, -22, 15),
           "circle_end_far_left": (-69, 22, 15), "circle_end_far_right": (69, 22, 15), "ref_crease": (0, -B, 10),
           # the boards' rounded corners, for a rink whose faceoff circles have worn off (Renton's)
           "boards_corner_far_left": (-72, 14.5, 28), "boards_corner_far_right": (72, 14.5, 28),
           "boards_corner_near_left": (-72, -14.5, 28), "boards_corner_near_right": (72, -14.5, 28)}
POINTS = {"net_left": (-89, 0), "net_right": (89, 0), "dot_center": (0, 0),
          "dot_neutral_far_left": (-20, 22), "dot_neutral_far_right": (20, 22),
          "dot_neutral_near_left": (-20, -22), "dot_neutral_near_right": (20, -22),
          "dot_end_far_left": (-69, 22), "dot_end_near_left": (-69, -22),
          "dot_end_far_right": (69, 22), "dot_end_near_right": (69, -22),
          "center_far_crossing": (0, 15), "center_near_crossing": (0, -15),
          # where the lines meet the boards (painted on the boards' kickplate where the ice paint is faint)
          "center_far_boards": (0, B), "blue_left_far_boards": (-25, B), "blue_right_far_boards": (25, B),
          "center_near_boards": (0, -B), "blue_left_near_boards": (-25, -B), "blue_right_near_boards": (25, -B)}
WARP_TERMS = [(i, j) for i in range(3) for j in range(3 - i)]
BOARD_TOP = 3.5     # ft: "boards_near_top" is the near boards' top edge, for a camera that can't see their base
                    # (Renton's new one): fisheye fits only, matched where the line of sight over it meets the ice


def _grid(img, x0, y0, step, label, zoom=1.0):
    """Grid lines every `step` source px, labels every `label`, in source coordinates."""
    h, w = img.shape[:2]
    x1, y1 = x0 + w / zoom, y0 + h / zoom
    for x in range((x0 // step + 1) * step, int(x1), step):
        X = int((x - x0) * zoom)
        cv2.line(img, (X, 0), (X, h), (0, 180, 0) if x % label == 0 else (0, 90, 0), 1)
        if x % label == 0:
            cv2.putText(img, str(x), (X + 2, 14), 0, 0.45, (0, 0, 255), 1)
    for y in range((y0 // step + 1) * step, int(y1), step):
        Y = int((y - y0) * zoom)
        cv2.line(img, (0, Y), (w, Y), (0, 180, 0) if y % label == 0 else (0, 90, 0), 1)
        if y % label == 0:
            cv2.putText(img, str(y), (2, Y - 3), 0, 0.45, (0, 0, 255), 1)
    return img


def cmd_frame(W, D):
    import imageio_ffmpeg
    os.makedirs(f"{D}/lm", exist_ok=True)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    wd, h = rink(f"{W}/full").size
    dur = next(imageio_ffmpeg.read_frames(f"{W}/video.webm"))["duration"]   # older folders have no video_info.json
    frames = []
    for t in np.linspace(60, dur - 60, 41):
        r = subprocess.run([ff, "-nostdin", "-loglevel", "error", "-ss", str(t), "-i", f"{W}/video.webm",
                            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
        frames.append(np.frombuffer(r.stdout, np.uint8).reshape(h, wd, 3))
    med = np.median(np.stack(frames), axis=0).astype(np.uint8)
    lab = cv2.cvtColor(med, cv2.COLOR_BGR2LAB); l, a, b = cv2.split(lab)
    enh = cv2.cvtColor(cv2.merge([cv2.createCLAHE(clipLimit=4.0, tileGridSize=(16, 16)).apply(l), a, b]), cv2.COLOR_LAB2BGR)
    assert cv2.imwrite(f"{D}/median.png", med) and cv2.imwrite(f"{D}/enh.png", enh)
    half = cv2.resize(enh, (wd // 2, h // 2))
    for x in range(0, wd // 2, 100):
        cv2.putText(half, str(x * 2), (x + 2, 24), 0, 0.45, (0, 0, 255), 1)
    for y in range(0, h // 2, 50):
        cv2.putText(half, str(y * 2), (12, y + 5), 0, 0.45, (0, 0, 255), 1)
    cv2.imwrite(f"{D}/half.jpg", half, [cv2.IMWRITE_JPEG_QUALITY, 90])
    m = wd // 2
    cv2.imwrite(f"{D}/left.jpg", _grid(enh[:, :m + 100].copy(), 0, 0, 50, 100), [cv2.IMWRITE_JPEG_QUALITY, 90])
    cv2.imwrite(f"{D}/right.jpg", _grid(enh[:, m - 100:].copy(), m - 100, 0, 50, 100), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f"{D}/median.png, enh.png, half.jpg, left.jpg, right.jpg")


def cmd_crop(D, x0, x1, y0, y1, zoom=2.0, plain=False):
    img = cv2.imread(f"{D}/{'median.png' if plain else 'enh.png'}")[y0:y1, x0:x1]
    img = cv2.resize(img, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_CUBIC)
    out = f"{D}/lm/crop_{x0}_{y0}.jpg"
    os.makedirs(f"{D}/lm", exist_ok=True)
    assert cv2.imwrite(out, _grid(img, x0, y0, 10, 50, zoom), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(out)


def _landmarks(lm):
    return [(k, np.array(v, float).reshape(-1, 2)) for k, v in lm.items()
            if isinstance(v, list) and v and (k in LINES or k in CIRCLES or k in POINTS or k == "boards_near_top")]


def _ice_residuals(items, X, Y, detail=False, cam=None):
    """Feet off each landmark's marking, for landmarks mapped onto the ice at (X, Y) (concatenated in items' order).
    cam: the fisheye params, for boards_near_top (where the line of sight over the boards' top meets the ice)."""
    out, per, i = [], {}, 0
    for k, q in items:
        x, y = X[i:i + len(q)], Y[i:i + len(q)]; i += len(q)
        if k == "boards_near_top":
            r = y - (cam["cy"] + cam["cz"] / (cam["cz"] - BOARD_TOP) * (-B - cam["cy"]))
        elif k in LINES:
            ax, c, _ = LINES[k]; r = (x if ax == "X" else y) - c
        elif k in CIRCLES:
            cx, cy, rr = CIRCLES[k]; r = np.hypot(x - cx, y - cy) - rr
        else:
            r = np.array([x[0] - POINTS[k][0], y[0] - POINTS[k][1]])
        out.append(r); per[k] = np.abs(r) if k not in POINTS else np.array([np.hypot(*r)])
    r = np.concatenate(out)
    return (r, per) if detail else r


def fit_pano(items):
    """Pixels: each landmark's distance to its projected marking (lines and circles sampled), 40 random starts."""
    names = rc.PARAMS["pano"]
    shapes = {}
    for k, _ in items:
        if k in LINES:
            ax, c, half = LINES[k]; s = np.linspace(-half, half, 400)
            shapes[k] = (np.full(400, c), s) if ax == "X" else (s, np.full(400, c))
        elif k in CIRCLES:
            cx, cy, r = CIRCLES[k]; t = np.linspace(0, np.pi if k == "ref_crease" else 2 * np.pi, 400)
            shapes[k] = (cx + r * np.cos(t), cy + r * np.sin(t))

    def res(x):
        p = dict(zip(names, x)); out = []
        for k, q in items:
            if k in POINTS:
                u, v = rc.project("pano", p, np.array([POINTS[k][0]], float), np.array([POINTS[k][1]], float))
                out.append(np.array([u[0] - q[0, 0], v[0] - q[0, 1]]))
            else:
                u, v = rc.project("pano", p, *shapes[k])
                out.append(np.sqrt(((q[:, None, 0] - u[None]) ** 2 + (q[:, None, 1] - v[None]) ** 2).min(1)))
        return np.nan_to_num(np.concatenate(out), nan=1e4)
    best, rng = None, np.random.default_rng(0)
    for _ in range(40):
        x0 = [rng.uniform(-10, 10), rng.uniform(-75, -45), rng.uniform(10, 40), rng.uniform(-0.1, 0.1),
              rng.uniform(0.1, 0.6), 0.0, rng.uniform(900, 1500), rng.uniform(900, 1500), 1900 + rng.uniform(-50, 50),
              rng.uniform(100, 700), rng.uniform(0.0, 1.0), 0.0, 0.0]
        try:
            f = least_squares(res, x0, loss="soft_l1", f_scale=6.0, max_nfev=4000)
        except Exception:
            continue
        if best is None or f.cost < best.cost:
            best = f
    return {"model": "pano", "params": {k: round(float(v), 6) for k, v in zip(names, best.x)}}


def fit_fisheye(items, size):
    """Feet: each landmark mapped onto the ice against its marking; camera 6-40 ft up, pixel aspect 0.6-1.7, plus a
    degree-2 warp kept small (0.3 ft per unit of coefficient); 60 random starts."""
    names, nt = rc.PARAMS["fisheye"], len(WARP_TERMS)
    U = np.concatenate([q[:, 0] for _, q in items]); V = np.concatenate([q[:, 1] for _, q in items])
    cu, cv_ = size[0] / 2, size[1] / 2

    def res(x):
        p = dict(zip(names, x[:12]))
        X, Y = rc.lens("fisheye", p, U, V)
        X, Y = rc.warp({"terms": WARP_TERMS, "c": x[12:]}, X, Y)
        return np.concatenate([np.nan_to_num(_ice_residuals(items, X, Y, cam=p), nan=100.0), 0.3 * x[12:]])
    lo = [-15, -75, 6, -0.3, -0.2, -0.2, 600, 0.6, cu - 200, cv_ - 280, -0.5, -0.5] + [-20] * 2 * nt
    hi = [15, -42, 40, 0.3, 1.2, 0.2, 2500, 1.7, cu + 200, cv_ + 320, 0.5, 0.5] + [20] * 2 * nt
    best, rng = None, np.random.default_rng(2)
    for _ in range(60):
        x0 = [rng.uniform(-8, 8), rng.uniform(-62, -44), rng.uniform(7, 30), rng.uniform(-0.1, 0.1),
              rng.uniform(0.0, 0.9), 0.0, rng.uniform(900, 1600), rng.uniform(0.7, 1.6), cu + rng.uniform(-50, 50),
              cv_ + rng.uniform(-100, 100), rng.uniform(-0.1, 0.05), 0.0] + [0.0] * 2 * nt
        try:
            f = least_squares(res, x0, bounds=(lo, hi), loss="soft_l1", f_scale=1.0, max_nfev=2000)
        except Exception:
            continue
        if best is None or f.cost < best.cost:
            best = f
    x = best.x
    return {"model": "fisheye", "params": {k: round(float(v), 6) for k, v in zip(names, x[:12])},
            "warp": {"terms": [list(t) for t in WARP_TERMS], "c": [round(float(c), 6) for c in x[12:]]}}


def draw_check(unproject, img, out):
    """The markings drawn back onto the frame by mapping every pixel onto the ice (any model, warp included)."""
    h, w = img.shape[:2]
    vv, uu = np.mgrid[0:h, 0:w].astype(float)
    X, Y = unproject(uu.ravel(), vv.ravel()); X = X.reshape(h, w); Y = Y.reshape(h, w)
    gx = np.hypot(*np.gradient(X)); g = np.maximum(gx, np.hypot(*np.gradient(Y)))
    near = lambda d, s: np.abs(d) < 1.6 * s
    o = img.copy()
    for c in (-89, 89):
        o[near(X - c, gx) & (np.abs(Y) < 36.75)] = (0, 0, 255)
    o[near(X, gx) & (np.abs(Y) < B)] = (0, 0, 255)
    for c in (-25, 25):
        o[near(X - c, gx) & (np.abs(Y) < B)] = (255, 80, 0)
    for cx, cy, r in CIRCLES.values():
        o[near(np.hypot(X - cx, Y - cy) - r, g) & (Y >= -B)] = (0, 0, 255)
    for k, (cx, cy) in POINTS.items():
        if k.startswith("dot"):
            o[np.hypot(X - cx, Y - cy) < 1.0] = (0, 255, 0)
    ins = rc.inside(np.nan_to_num(X, nan=1e3), np.nan_to_num(Y, nan=1e3))
    o[ins & ~cv2.erode(ins.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)] = (0, 255, 255)
    cv2.imwrite(out, cv2.resize(o, (w // 2, h // 2), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])


def checks(W, unproject, items, cam=None):
    """Print each marking's error in feet, where their goalie lands per period, and our detections off the ice."""
    import pandas as pd
    from track import load
    U = np.concatenate([q[:, 0] for _, q in items]); V = np.concatenate([q[:, 1] for _, q in items])
    r, per = _ice_residuals(items, *unproject(U, V), detail=True, cam=cam)
    for k, d in per.items():
        print(f"  {k:24s} n={len(d):2d}  median {np.median(d):5.2f} ft  max {d.max():5.2f} ft")
    print(f"markings: median {np.nanmedian(np.abs(r)):.2f} ft, 90% {np.nanquantile(np.abs(r), .9):.2f} ft")
    R = rink(f"{W}/full"); d = load(f"{W}/full/dets.csv")
    for P in json.load(open(f"{W}/periods.json")):
        theirs = next(x for x in R.nets.values() if x != P["net"])
        x = d[(d.t >= P["start"]) & (d.t <= P["end"]) & ~d.ours & d.onice & (np.abs(d.fx - theirs) < 120)]
        X, Y = unproject(x.fx.values, x.fy.values)
        ok = np.isfinite(X) & (np.abs(X) > 70) & (np.abs(Y) < 20)     # at their end: mostly him, in his crease
        # a rough check (+-3 ft): it also counts players behind the net, and a camera that sees the end zones edge-on
        # (Renton's new one) puts a few px of foot point at a few feet
        print(f"{P['label']}: their goalie at X {np.median(X[ok]):.1f}, Y {np.median(Y[ok]):.1f} (expect X +-82..90, Y near 0)")
    n = out = 0
    for P in json.load(open(f"{W}/periods.json")):
        tr = pd.read_csv(f"{W}/{P['label'].lower()}/tracks_v1.csv", usecols=["fx", "fy", "onice"]); tr = tr[tr.onice]
        X, Y = unproject(tr.fx.values, tr.fy.values)
        n += len(X); out += int((~rc.inside(np.nan_to_num(X, nan=1e3), np.nan_to_num(Y, nan=1e3))).sum())
    print(f"our on-ice track points off the ice: {out / n:.2%} of {n}")


def cmd_fit(D, W, model, out=None):
    W = os.path.abspath(W); full = f"{W}/full"
    items = _landmarks(json.load(open(f"{D}/landmarks.json")))
    R = rink(full)
    cam = fit_pano(items) if model == "pano" else fit_fisheye(items, R.size)
    cam = {"model": cam["model"], "boards_poly": [float(x) for x in np.load(f"{full}/boards_poly.npy")],
           "fitted": f"{os.path.basename(W)}: {sum(len(q) for _, q in items)} landmarks (rinkcal.py)", **cam}
    out = out or os.path.join(rc.CAMS, f"{rink_name(full)}.json")
    json.dump(cam, open(out, "w"), indent=1)
    print("wrote", out, cam["params"])
    unproject = rc.from_params(cam)
    draw_check(unproject, cv2.imread(f"{D}/median.png"), f"{D}/check.jpg")
    print(f"{D}/check.jpg: the markings drawn back on the frame")
    checks(W, unproject, items, cam["params"])


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "frame":
        cmd_frame(os.path.abspath(a[1]), a[2])
    elif a[0] == "crop":
        cmd_crop(a[1], *map(int, a[2:6]), float(a[6]) if len(a) > 6 else 2.0, len(a) > 7 and a[7] == "plain")
    elif a[0] == "fit":
        cmd_fit(a[1], a[2], a[3], a[4] if len(a) > 4 else None)
    else:
        sys.exit(__doc__)
