"""ice.py W [GAME_JSON] : where each of our skaters was on the ice during his shifts, for the game page's ice maps.
Prints each player's zone shares; with GAME_JSON, writes them into its "ice" (publish does this itself).

A player's positions are his labeled tracks (segs_final.csv's plabel) inside his shifts (shifts_all.csv), 8 a second,
each foot point mapped onto the ice with the rink's calibration (rinkcam.py; a rink without one gets no maps). Our
net is always at the bottom: V runs from our end boards (-100) to theirs (+100), H across (-42.5 = the left when
attacking up). Each map is a 2 ft grid of time over V -100..100 and H -42..42, smoothed (Gaussian, 4 ft), scaled to
its own peak and written as one character per cell (GRID_CHARS, 0 = none), row by row from our end, each row from
the left; zones split at the blue lines (V +-25)."""
import json, os, sys
import numpy as np, pandas as pd
from scipy.ndimage import gaussian_filter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rinkcam
from rink import rink, rink_name

DT = 1 / 8                     # tracks are 8 frames a second
CELL = 2                       # ft per grid cell
SIGMA = 4.0                    # ft
GRID_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
HALF_V, HALF_H = 100, 42        # the grid's extent in ft: end boards to end boards, 0.5 ft short of each side's


def positions(W):
    """DataFrame player, t, V, H of our skaters on the ice, or None when the rink has no calibration."""
    full = f"{W}/full"
    R = rink(full)
    board_y = float(np.polyval(np.load(f"{full}/boards_poly.npy"), R.center_x))
    unproject = rinkcam.camera(rink_name(full), board_y)
    if unproject is None:
        return None
    A = pd.read_csv(f"{W}/shifts_all.csv")
    rows = []
    for P in json.load(open(f"{W}/periods.json")):
        pdir = f"{W}/{P['label'].lower()}"
        sg = pd.read_csv(f"{pdir}/segs_final.csv")
        tr = pd.read_csv(f"{pdir}/tracks_v1.csv", usecols=["tid", "t", "fx", "fy", "onice"])
        tr = tr[tr.onice].copy()
        s = 1 if P["net"] < R.center_x else -1       # our net on the left: we attack +X
        X, Y = unproject(tr.fx.values, tr.fy.values)
        tr["V"] = s * X; tr["H"] = -s * Y
        tr = tr.set_index("tid")
        for n, g in A[A.period == P["label"]].groupby("player"):
            parts = []
            for r in sg[sg.plabel == n].itertuples():
                if r.tid not in tr.index:
                    continue
                x = tr.loc[[r.tid]]; x = x[(x.t >= r.t0) & (x.t <= r.t1)]
                # their goalie in a white that passes our jersey test can carry one of our numbers by chaining
                # (23 pieces on TK's Oct 25): a piece that spends most of its time in their crease is him
                crease = (x.V > 82) & (x.H.abs() < 8)
                if crease.sum() * DT >= 4 and crease.mean() >= 0.6:
                    continue
                parts.append(x)
            if not parts:
                continue
            x = pd.concat(parts).groupby("t")[["V", "H"]].first().reset_index()
            on = np.zeros(len(x), bool)
            for r in g.itertuples():
                on |= (x.t >= r.t0) & (x.t < r.t1)
            rows.append(x[on].assign(player=int(n)))
    if not rows:
        return None
    D = pd.concat(rows)
    return D[rinkcam.inside(D.V.values, D.H.values)]


def ice_map(d):
    """One map: seconds tracked, zone shares [offence, neutral, defence], and the grid (rows from our end up)."""
    h, _, _ = np.histogram2d(d.V, d.H, bins=[np.arange(-HALF_V, HALF_V + 1, 1.0), np.arange(-HALF_H, HALF_H + 1, 1.0)])
    h = gaussian_filter(h, SIGMA)
    nv, nh = h.shape[0] // CELL, h.shape[1] // CELL
    g = h[:nv * CELL, :nh * CELL].reshape(nv, CELL, nh, CELL).mean(axis=(1, 3))
    q = np.rint(g / g.max() * (len(GRID_CHARS) - 1)).astype(int) if g.max() > 0 else np.zeros_like(g, int)
    n = len(d)
    return dict(sec=round(n * DT, 1),
                zones=[round(float((d.V > 25).sum() / n), 3), round(float((d.V.abs() <= 25).sum() / n), 3),
                       round(float((d.V < -25).sum() / n), 3)],
                grid="".join(GRID_CHARS[v] for v in q.ravel()))


def ice_maps(W):
    """game.json's "ice": the team's map and each player's, or None (no calibration for the rink, no tracks)."""
    D = positions(W)
    if D is None or not len(D):
        return None
    team = ice_map(D)
    return dict(cell=CELL, cols=2 * HALF_H // CELL, rows=2 * HALF_V // CELL, team=team,
                players={str(n): ice_map(d) for n, d in D.groupby("player") if len(d) * DT >= 30})


if __name__ == "__main__":
    W = os.path.abspath(sys.argv[1])
    ice = ice_maps(W)
    if ice is None:
        sys.exit(f"no ice maps for {W}: {rink_name(W + '/full')} has no calibration in pipeline/cams/")
    for k, m in [("team", ice["team"])] + sorted(ice["players"].items(), key=lambda km: -km[1]["sec"]):
        print(f"{k:>5}  {m['sec'] / 60:5.1f} min   offence {m['zones'][0]:.0%}  neutral {m['zones'][1]:.0%}  "
              f"defence {m['zones'][2]:.0%}")
    if len(sys.argv) > 2:
        game = json.load(open(sys.argv[2], encoding="utf-8"))
        game["ice"] = ice
        json.dump(game, open(sys.argv[2], "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("wrote", sys.argv[2])
