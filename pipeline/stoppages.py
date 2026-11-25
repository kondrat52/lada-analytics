"""Find stoppages (whistle -> puck drop) from player motion, and each shift's live play time.

Puck drop: everyone on the ice stands nearly still for 3+ s (faceoff setup), then bursts into motion.
Whistle: the last second of game-speed skating before that setup (players coast to their spots after a
whistle). The recordings have no usable audio, so this is all from video. Quick whistles whose faceoff
never gets still enough are missed, so play time is an upper-bound estimate.

After a goal the whistle is found too early: the players slow down while the play is still on (209 of 304 goals on
the 49 archived games fell inside an estimated stoppage, a median 7 s after its start). A goal inside a stoppage
moves that stoppage's start to just after the goal (after_goals); play time and everything else published from the
stoppages use the moved ones. stoppages.json keeps the motion estimate as it is, and so does game.json's
`stoppages_raw` (publish and backfill.py write it; the feed doesn't carry it); game.json's `stoppages` are the moved
ones. The correction always starts from the estimate, never from stoppages already moved, so a goal's time changed
later can move a start back as well as on.

What the rule costs: a stoppage moves to after its latest goal, so with two goals inside one estimated stoppage the
whistle and faceoff between them count as live (1 of the 224 stoppages moved on the 55 published games: Blue Wings'
Oct 25, goals at 1537 and 1580 inside [1535, 1613)). And 26 of the 224 moves are 30 s or longer, which may be a
faceoff the estimate missed rather than a slow whistle; live play stays an upper bound.

stoppages.py FULLDIR PERIODS.json SHIFTS.csv  -> adds a "play" column to SHIFTS.csv, writes stoppages.json next to it
(the goals come from highlights.json beside SHIFTS.csv, when there is one)
"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from track import load

FPS = 8
STILL, BURST, LIVE_PACE, MAX_STOP = 0.6, 1.0, 1.9, 75


def speed_per_second(full):
    """75th percentile skating speed (body-heights/s) of everyone on the ice, per second."""
    d = load(f"{full}/dets.csv")
    d = d[d.onice & (d.conf >= 0.3)]
    fr = {f: g[["fx", "fy", "h"]].values for f, g in d.groupby("frame")}
    rows = []
    def nearest(a, b):
        return np.hypot(a[:, None, 0] - b[None, :, 0], a[:, None, 1] - b[None, :, 1]).min(1)

    for f, a in fr.items():
        # a stuttering stream repeats frames (LADA R's Oct 19 video had ~2 distinct frames/s for 20 minutes), which
        # read as standing still: compare with the next frame that isn't a repeat, over the time between them. A
        # repeat leaves most boxes exactly where they were (some drop out or shift); a new frame, even of players
        # standing still, moves most boxes by a pixel or more of detector noise
        g = f + 1
        D = nearest(a, fr[g]) if g in fr else None
        while D is not None and np.median(D) < 0.01 and g - f < FPS and g + 1 in fr:
            g += 1
            D = nearest(a, fr[g])
        if D is None:
            continue
        v = D / a[:, 2] * FPS / (g - f)
        v = v[v < 8]
        if len(v) >= 4:
            rows.append((f / FPS, np.quantile(v, 0.75)))
    s = pd.DataFrame(rows, columns=["t", "v"])
    T = int(s.t.max()) + 1
    return s.groupby(s.t.astype(int)).v.median().reindex(range(T)).interpolate().rolling(3, center=True, min_periods=1).median().values


def drops(v, lo, hi, still=STILL, min_still=3, burst=BURST):
    out, st = [], None
    for t in range(lo, min(hi, len(v))):
        if v[t] <= still:
            st = t if st is None else st
        else:
            if st is not None and t - st >= min_still and v[t:t + 3].max() >= burst:
                out.append((st, t))
            st = None
    return out


def find_stoppages(v, periods):
    spans = []
    for p in periods:
        a, b = int(p["start"]), int(p["end"])
        ds = drops(v, a, b)
        # the period's opening faceoff is often a slow, milling setup: look for it more loosely
        first = drops(v, a, min(a + 60, b), still=0.8, min_still=2, burst=1.2)
        if first and (not ds or first[0][1] < ds[0][1] - 5):
            ds = [first[0]] + ds
        prev_drop = a
        for k, (s, e) in enumerate(ds):
            if k == 0 and s - a < 60:
                w = a                          # from the period start to its opening puck drop
            else:
                lo = max(s - MAX_STOP, prev_drop)
                fast = [t for t in range(lo, s) if v[t] >= LIVE_PACE]
                w = fast[-1] + 1 if fast else lo
            spans.append((w, e))
            prev_drop = e
    return spans


def goal_times(highlights):
    """The times of the goals (ours and theirs) in highlights.json's or game.json's highlights."""
    return [h["t"] for h in highlights or [] if h.get("type") == "goal"]


def after_goals(spans, goals):
    """The stoppages with a goal inside one ([start, end), start <= t < end) starting just after the goal, at
    int(t) + 1, its latest goal where it holds two; one left empty goes. spans: the motion estimate (stoppages.json,
    game.json's stoppages_raw). Applying it again with the same goals changes nothing, but on stoppages already
    moved a goal moved earlier can't move a start back: start from the estimate."""
    out = []
    for a, b in spans:
        gin = [t for t in goals if a <= t < b]
        if gin:
            a = int(max(gin)) + 1
        if b > a:
            out.append([int(a), int(b)])
    return out


def live_mask(periods, spans, T=None):
    """Per second: inside a period ([int(start), int(end))) and outside every stoppage ([a, b))."""
    T = T or int(max(p["end"] for p in periods)) + 2
    live = np.zeros(T, bool)
    for p in periods:
        live[int(p["start"]):int(p["end"])] = True
    for a, b in spans:
        live[int(a):int(b)] = False
    return live


def play_column(A, periods, spans):
    """Each shift's live play seconds: the live seconds in [int(t0), int(t1))."""
    live = live_mask(periods, spans)
    return [int(live[int(r.t0):int(r.t1)].sum()) for r in A.itertuples()]


def work_goals(W):
    """The goal times in W/highlights.json ([] before the highlights step)."""
    p = f"{W}/highlights.json"
    return goal_times(json.load(open(p, encoding="utf-8"))) if os.path.exists(p) else []


def corrected(W):
    """W's stoppages.json moved after the goals in W/highlights.json (after_goals), or None without stoppages.json."""
    if not os.path.exists(f"{W}/stoppages.json"):
        return None
    return after_goals(json.load(open(f"{W}/stoppages.json")), work_goals(W))


def main():
    full, pjson, shifts = sys.argv[1:4]
    periods = json.load(open(pjson))
    v = speed_per_second(full)
    spans = [[int(a), int(b)] for a, b in find_stoppages(v, periods)]
    W = os.path.dirname(os.path.abspath(shifts))
    json.dump(spans, open(f"{W}/stoppages.json", "w"))
    goals = work_goals(W)
    moved = after_goals(spans, goals)
    live = live_mask(periods, moved, max(len(v), int(max(p["end"] for p in periods)) + 1))
    A = pd.read_csv(shifts)
    A["play"] = play_column(A, periods, moved)
    A.to_csv(shifts, index=False)
    for p in periods:
        a, b = int(p["start"]), int(p["end"])
        print(f"{p['label']}: {sum(1 for s in moved if a <= s[0] < b)} stoppages, live {live[a:b].mean():.0%}")
    n = sum(1 for a, b in spans if any(a <= t < b for t in goals))
    if n:
        print(f"{n} stoppage(s) moved to start just after the goal inside them (highlights.json); play time counts them so")


if __name__ == "__main__":
    main()
