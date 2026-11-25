"""zones.py W GAME_JSON : where play happened, for the trends page. Prints {"offence": .., "defence": .., "basis": ..}.

Where the play is, per second (play_position): every detection on the ice in a frame (confidence 0.3+) is mapped
onto the ice in feet through the rink's calibration (rinkcam.py), our net at the bottom (V = -89 our goal line,
+89 theirs; H across, < 0 the left as the team attacks up, as ice.py). A frame with 6+ detections on the ice, 6+ of
them inside the boards, gives the median V and H of those inside; a second, the median of its frames.

Time in offence is the share of live play (inside a period, outside the stoppages: game.json's, already moved after
the goals) with the play past their blue line (V > 25), time in defence behind ours (V < -25); the rest is the middle
of the ice. "basis": "ft".

A rink without a calibration falls back to the picture ("basis": "px"): the median foot x of everyone detected,
between our net (0) and theirs (1), in thirds. The picture's thirds reach past the blue lines and count 4 to 8 points
more time in both ends than the feet do (the 49 archived games, Nov 24, 2026). Our net per period comes from
game.json's nets, theirs is the rink's other net (rink.py)."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rinkcam
from rink import rink, rink_name
from track import load

MIN_DETS = 6      # detections on the ice in a frame (and inside the boards, in feet): a bunch, not a lone skater
BLUE = 25         # ft from center to each blue line


def detections(full):
    """dets.csv's detections on the ice with confidence 0.3+, or None without dets.csv."""
    if not os.path.exists(f"{full}/dets.csv"):
        return None
    d = load(f"{full}/dets.csv")
    return d[d.onice & (d.conf >= 0.3)]


def play_position(full, game, d=None):
    """Per second (index = video second): the play's V and H in feet (NaN where not measured), as a dict
    {"V": array, "H": array}, or None for a rink without a calibration or a game without detections.
    d: detections() already loaded."""
    R = rink(full)
    unproject = rinkcam.camera(rink_name(full), np.load(f"{full}/boards_poly.npy"))
    if unproject is None:
        return None
    d = detections(full) if d is None else d
    if d is None or not len(d):
        return None
    d = d[["frame", "t", "fx", "fy"]].copy()
    X, Y = unproject(d.fx.values, d.fy.values)
    d["inside"] = rinkcam.inside(X, Y)
    d["V"] = np.nan; d["H"] = np.nan; d["per"] = False
    for p in game["periods"]:
        m = ((d.t >= p["start"]) & (d.t < p["end"])).values
        s = 1 if game["nets"][p["label"]] < R.center_x else -1   # our net on the image's left: we attack +X
        d.loc[m, "V"] = s * X[m]; d.loc[m, "H"] = -s * Y[m]; d.loc[m, "per"] = True
    d = d[d.per]
    n = d.groupby("frame").agg(t=("t", "first"), n=("V", "size"))
    inside = d[d.inside].groupby("frame").agg(V=("V", "median"), H=("H", "median"), ni=("V", "size"))
    fr = n.join(inside, how="left")
    fr = fr[(fr.n >= MIN_DETS) & (fr.ni >= MIN_DETS)]
    g = fr.groupby(fr.t.astype(int))
    T = int(max(d.t.max() if len(d) else 0, max(p["end"] for p in game["periods"]))) + 2
    V = np.full(T, np.nan); H = np.full(T, np.nan)
    med = g[["V", "H"]].median()
    V[med.index.values] = med.V.values; H[med.index.values] = med.H.values
    return dict(V=V, H=H)


def _live(game, T):
    live = np.zeros(T, bool)
    for p in game["periods"]:
        live[int(p["start"]):int(p["end"])] = True
    for a, b in game.get("stoppages", []):
        live[int(a):int(b)] = False
    return live


def _pixel_shares(full, game, d):
    """The picture's version, for a rink without a calibration: the median foot x of everyone detected, in thirds
    between our net and theirs."""
    R = rink(full)
    per_frame = d.groupby("frame").agg(t=("t", "first"), x=("fx", "median"), n=("fx", "size"))
    per_frame = per_frame[per_frame.n >= MIN_DETS]
    sec = per_frame.groupby(per_frame.t.astype(int)).x.median()
    T = int(max(sec.index.max(), max(p["end"] for p in game["periods"]))) + 2
    f = np.full(T, np.nan)
    for p in game["periods"]:
        ours = game["nets"][p["label"]]
        theirs = next(x for x in R.nets.values() if x != ours)
        s = sec[(sec.index >= p["start"]) & (sec.index < p["end"])]
        f[s.index.values] = np.clip((s.values - ours) / (theirs - ours), 0, 1)
    f[~_live(game, T)] = np.nan
    n = int(np.sum(~np.isnan(f)))
    if not n:
        return None
    return dict(offence=round(float(np.nansum(f > 2 / 3) / n), 4), defence=round(float(np.nansum(f < 1 / 3) / n), 4),
                basis="px")


def zone_shares(full, game, play=None, d=None):
    """full: W/full with dets.csv; game: game.json's dict (periods, nets, stoppages). play: play_position()'s, when
    already made; d: detections(), when already loaded. None without detections."""
    if play is None:
        d = detections(full) if d is None else d
        if d is None:
            return None
        play = play_position(full, game, d)
        if play is None:   # no calibration for the rink: the picture's thirds
            return _pixel_shares(full, game, d)
    V = play["V"].copy()
    V[~_live(game, len(V))] = np.nan
    n = int(np.sum(~np.isnan(V)))
    if not n:
        return None
    return dict(offence=round(float(np.nansum(V > BLUE) / n), 4), defence=round(float(np.nansum(V < -BLUE) / n), 4),
                basis="ft")


if __name__ == "__main__":
    print(json.dumps(zone_shares(f"{os.path.abspath(sys.argv[1])}/full", json.load(open(sys.argv[2], encoding="utf-8")))))
