"""rinkcam.py : a rink camera's calibration, image (u, v) px -> ice (X, Y) ft, for the ice maps (ice.py).

Ice: X along the length (0 = center line, +-100 the end boards; image left is -X), Y across (+42.5 the far boards,
-42.5 the near boards on the camera's side). NHL markings: blue lines +-25, goal lines +-89, neutral dots (+-20, +-22),
end dots (+-69, +-22), corners of radius 28.

A camera sits at C = (cx, cy, cz) ft, turned by yaw / pitch / roll. Two lens models:
- "pano", a panoramic strip (Snoqualmie A): azimuth a and elevation e of the ray give u = u0 + fx (a + a3 a^3),
  v = v0 - fy (tan(k e) / k + e3 e^3).
- "fisheye", a whole fisheye frame (Snoqualmie B): the ray's angle th off the optical axis gives the radius
  r = f (th + k1 th^3 + k2 th^5) around (u0, v0), squeezed vertically by asp; then an optional smooth correction on
  the ice ("warp": X += sum a x^i y^j, Y += sum b x^i y^j with x = X/100, y = Y/42.5).

pipeline/cams/<rink>.json holds each rink's calibration (rink.py's names) with "board_y", the far boards' y at
center_x in the video it was fitted on. A game whose video sits higher or lower (Snoqualmie A's YouTube cuts sit 52 px
above its LiveBarn files) is shifted by the difference, read off its own boards_poly.npy. rinkcal.py makes them."""
import json, os
import numpy as np

L, B = 100.0, 42.5
CAMS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cams")
PARAMS = {"pano": ["cx", "cy", "cz", "yaw", "pitch", "roll", "fx", "fy", "u0", "v0", "k", "a3", "e3"],
          "fisheye": ["cx", "cy", "cz", "yaw", "pitch", "roll", "f", "asp", "u0", "v0", "k1", "k2"]}


def _R(yaw, pitch, roll):
    """World -> camera (right, up, forward). yaw 0 looks toward +Y; positive pitch tilts down."""
    cy, sy = np.cos(yaw), np.sin(yaw)
    Rz = np.array([[cy, -sy, 0], [0, 0, 1], [sy, cy, 0]], float)
    cp, sp = np.cos(pitch), np.sin(pitch)
    Rx = np.array([[1, 0, 0], [0, cp, sp], [0, -sp, cp]], float)
    cr, sr = np.cos(roll), np.sin(roll)
    Rr = np.array([[cr, sr, 0], [-sr, cr, 0], [0, 0, 1]], float)
    return Rr @ Rx @ Rz


def _solve(f, y, x0):
    """x with f(x) = y for a monotonic f (Newton, numeric slope), elementwise."""
    x = np.array(x0, float)
    for _ in range(30):
        d = (f(x + 1e-6) - f(x - 1e-6)) / 2e-6
        x = x - (f(x) - y) / d
    return x


def _to_ice(p, d):
    """Rays d (camera frame, 3 x n) -> where they meet the ice; NaN for rays that don't."""
    w = _R(p["yaw"], p["pitch"], p["roll"]).T @ d
    t = -p["cz"] / w[2]
    X = p["cx"] + t * w[0]; Y = p["cy"] + t * w[1]
    X[t <= 0] = np.nan; Y[t <= 0] = np.nan
    return X, Y


def _pano(p, u, v):
    k = p["k"]
    au = (u - p["u0"]) / p["fx"]; ev = (p["v0"] - v) / p["fy"]
    g = (lambda e: e) if abs(k) < 1e-4 else (lambda e: np.tan(k * e) / k)
    a = _solve(lambda a: a + p["a3"] * a ** 3, au, au)
    e = _solve(lambda e: g(e) + p["e3"] * e ** 3, ev, ev if abs(k) < 1e-4 else np.arctan(k * ev) / k)
    return _to_ice(p, np.stack([np.cos(e) * np.sin(a), np.sin(e), np.cos(e) * np.cos(a)]))


def _fisheye(p, u, v):
    x = u - p["u0"]; y = (p["v0"] - v) / p["asp"]
    r = np.hypot(x, y) / p["f"]; ph = np.arctan2(y, x)
    th = _solve(lambda t: t + p["k1"] * t ** 3 + p["k2"] * t ** 5, r, r)
    return _to_ice(p, np.stack([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)]))


def project(model, p, X, Y):
    """Ice points -> image (u, v) through the lens alone (no warp): for fitting and drawing a calibration."""
    X = np.asarray(X, float); Y = np.asarray(Y, float)
    d = _R(p["yaw"], p["pitch"], p["roll"]) @ np.stack([X.ravel() - p["cx"], Y.ravel() - p["cy"],
                                                         np.full(X.size, -p["cz"])])
    if model == "pano":
        a = np.arctan2(d[0], d[2]); e = np.arctan2(d[1], np.hypot(d[0], d[2])); k = p["k"]
        u = p["u0"] + p["fx"] * (a + p["a3"] * a ** 3)
        v = p["v0"] - p["fy"] * ((e if abs(k) < 1e-4 else np.tan(k * e) / k) + p["e3"] * e ** 3)
    else:
        th = np.arctan2(np.hypot(d[0], d[1]), d[2]); ph = np.arctan2(d[1], d[0])
        r = p["f"] * (th + p["k1"] * th ** 3 + p["k2"] * th ** 5)
        u = p["u0"] + r * np.cos(ph); v = p["v0"] - p["asp"] * r * np.sin(ph)
    return u.reshape(X.shape), v.reshape(X.shape)


def lens(model, p, u, v):
    """Image (u, v) -> ice (X, Y) through the lens alone (no warp)."""
    return {"pano": _pano, "fisheye": _fisheye}[model](p, np.asarray(u, float).ravel(), np.asarray(v, float).ravel())


def warp(w, X, Y):
    """The smooth correction on the ice: w = {"terms": [[i, j], ...], "c": [a..., b...]}."""
    m = np.stack([(X / L) ** i * (Y / B) ** j for i, j in w["terms"]])
    n = len(w["terms"]); c = np.array(w["c"])
    return X + c[:n] @ m, Y + c[n:] @ m


def camera(rink_name, board_y=None):
    """unproject(u, v) -> (X, Y) for a rink's calibration, or None for a rink without one. board_y: the far boards'
    y at the rink's center_x in this game's video, to shift a video framed higher or lower than the calibration's."""
    path = os.path.join(CAMS, f"{rink_name}.json")
    if not os.path.exists(path):
        return None
    c = json.load(open(path))
    return from_params(c, (board_y - c["board_y"]) if board_y is not None else 0.0)


def from_params(c, dv=0.0):
    """unproject(u, v) for a calibration dict (a cams/*.json's), its video shifted down by dv px."""
    def unproject(u, v):
        X, Y = lens(c["model"], c["params"], np.asarray(u, float).ravel(), np.asarray(v, float).ravel() - dv)
        return warp(c["warp"], X, Y) if c.get("warp") else (X, Y)
    return unproject


def inside(X, Y):
    """On the ice: inside the boards, rounded corners included."""
    ax, ay = np.abs(X), np.abs(Y)
    return (ax <= L) & (ay <= B) & ((ax <= L - 28) | (ay <= B - 28) | (np.hypot(ax - (L - 28), ay - (B - 28)) <= 28))
