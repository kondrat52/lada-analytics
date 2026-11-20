"""run2.py OUTDIR REVDIR TMAX [active_json]: segments + reviews -> link -> joint solve -> shifts_final.csv"""
import sys, os, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import shifts as SH
from apply_review import parse_review, apply
from solver import solve, to_shifts
from rink import rink
out, rev, tmax = sys.argv[1], sys.argv[2], float(sys.argv[3])
active_spans = json.loads(sys.argv[4]) if len(sys.argv) > 4 else None
# optional [[t0, t1, n_skaters(, player in the box(, "on"))], ...]: a penalty kill (n 4, the player boxed), a
# player seen off the ice (n 5, the player kept off), or seen on the ice with "on" (n 5, the player kept on), or
# our goalie pulled for an extra attacker (n 6)
target_spans = json.loads(sys.argv[5]) if len(sys.argv) > 5 else []
tr = pd.read_csv(f"{out}/tracks_v1.csv"); S = pd.read_csv(f"{out}/segs_v1.csv")
rk = rink(out)
tr["depth"] = rk.bench_depth(tr.fx, tr.rel)   # how far behind our bench's boards (< 0: on the ice side)
man = pd.read_csv(f"{rev}/manifest.csv")
revs = [parse_review(open(f).read()) for f in sorted(glob.glob(f"{rev}/review_*.txt"))]
R = pd.concat(revs) if revs else pd.DataFrame(columns=["row_id"])
print("review rows:", len(R))
S2 = apply(S, tr, R, man, rk)
# people sitting behind the bench boards are not on the ice: drop those segments before labels propagate
med = [tr[(tr.tid == a) & (tr.t >= b) & (tr.t <= c)].depth.median() for a, b, c in zip(S2.tid, S2.t0, S2.t1)]
S2 = S2[pd.Series(med, index=S2.index).fillna(0) < 15].reset_index(drop=True)
# numbers the reviewers saw on our skaters join the roster for this game (goalies don't skate shifts), except
# players marked absent (run_game.py absent): a "3" on an absent #3 is a partial read of 43/53/35
from roster import ABSENT
seen = {int(p) for p in R.player if p.isdigit() and int(p) not in SH.GOALIES}
if seen & ABSENT:
    print("reviewers named absent players, ignored:", ", ".join(f"#{p} x{(R.player == str(p)).sum()}" for p in sorted(seen & ABSENT)))
SH.ROSTER = sorted(set(SH.ROSTER) | (seen - ABSENT))
S2 = SH.link(S2, rk)
S2.to_csv(f"{out}/segs_final.csv", index=False)
w = S2[S2.plabel >= 0].groupby("plabel").apply(lambda g: (g.t1 - g.t0).sum(), include_groups=False)
# a player a hand `on` span names plays even without 20 s of labeled track: the solver used to leave him out and drop
# his spans without a word (Beerteam's Nov 14: #54 Pfeifer in a dark green jersey that fails the jersey test). The
# spans of a player still left out are named below, with what they still do
span_on = {int(p[0]) for _a, _b, _n, *p in target_spans if len(p) > 1 and p[1] == "on" and p[0] is not None}
players = sorted(p for p in SH.ROSTER if w.get(p, 0) >= 20 or p in span_on)
span_only = [p for p in players if w.get(p, 0) < 20]   # known from his `on` spans alone: held off outside them (below)
span_lost = sorted({int(p[0]) for _a, _b, _n, *p in target_spans if p and p[0] is not None} - set(players))
for pl in span_lost:   # off the roster, absent, a goalie, or (only off spans or a kill) a player with no labeled track
    why = ("marked absent" if pl in ABSENT else "a goalie" if pl in SH.GOALIES else "not on the roster" if pl not in SH.ROSTER
           else f"{w.get(pl, 0):.0f} s of labeled track, 20 needed, and no `on` span")
    mine = [(a, b, n, q) for a, b, n, *q in target_spans if q and q[0] is not None and int(q[0]) == pl]
    onoff = [f"{'on' if len(q) > 1 and q[1] == 'on' else 'off'} {a:g}-{b:g}" for a, b, n, q in mine if n == 5]
    kills = [f"{a:g}-{b:g}" for a, b, n, q in mine if n != 5]
    print(f"WARNING #{pl} is left out of this solve ({why}): "
          + "; ".join(([f"his spans are ignored, so nobody's shifts follow them: {', '.join(onoff)}"] if onoff else [])
                      + ([f"the kill {', '.join(kills)} still sets one skater fewer on the ice"] if kills else [])))
print("players:", players)
S2["d0"] = np.asarray(rk.bench_depth(S2.x0, S2.r0)); S2["d1"] = np.asarray(rk.bench_depth(S2.x1, S2.r1))
ev = np.r_[S2[S2.bench0 & (S2.d0 > -10)].t0.values, S2[S2.bench1 & (S2.d1 > -10)].t1.values]
T = int(np.ceil(tmax)) + 1
active = None
if active_spans:
    active = np.zeros(T, bool)
    for a, b in active_spans: active[int(a):int(b)] = True
target = np.full(T, 5.0); boxed = []; kept = []
for a, b, n, *p in target_spans:
    if n != 5:   # a penalty kill takes one skater off (two overlapping kills, a 5-on-3, take two); a pulled goalie adds one
        target[int(a):int(b)] -= 5 - n
    if p and p[0] is not None:
        (kept if len(p) > 1 and p[1] == "on" else boxed).append((int(p[0]), int(a), int(b)))
# a player known only from his `on` spans is off wherever none covers him. With no labeled segments he costs nothing on
# or off, the multipliers make him the cheapest filler wherever fewer than five are on, and ties keep his state: on
# Beerteam's Nov 14 #54 came out 96 s over his 15 traced shifts (a 6-on stretch among them) until 17 hand-made `off`
# spans held him off. `boxed` just holds a player off the ice, as an `off` span does: the count is the target's alone
# (only a kill lowers it, above), so he is simply off, not in a box. Not where a labeled piece of his is either: a
# few seconds of track under the 20 s are his own evidence, which the hold would contradict.
for pl in span_only:
    cover, mine = np.zeros(T, bool), np.zeros(T, bool)
    for a, b, _n, *p in target_spans:
        if len(p) > 1 and p[1] == "on" and p[0] is not None and int(p[0]) == pl:
            cover[int(a):int(b)] = True
    for s in S2[S2.plabel == pl].itertuples():
        mine[max(0, int(np.floor(s.t0))):min(T, int(np.ceil(s.t1)) + 1)] = True
    held = ~(cover | mine)
    d = np.diff(np.r_[0, held.astype(np.int8), 0])
    boxed += [(pl, int(a), int(b)) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1))]
    print(f"#{pl} has {w.get(pl, 0):.0f} s of labeled track: on in his `on` spans ({int(cover.sum())} s), off everywhere "
          f"else" + (f" but his labeled pieces ({int((mine & ~cover).sum())} s outside the spans)" if (mine & ~cover).any() else ""))
target = np.maximum(target, 3)
st, viol = solve(S2, players, T, ev, target=target, active=active, boxed=boxed, kept=kept)
Rsh = to_shifts(st, players)
Rsh.to_csv(f"{out}/shifts_final.csv", index=False)
print("constraint violations (player-seconds):", viol)
print(Rsh.groupby("player").dur.agg(["count", "sum", "mean"]).round(0).to_string())
