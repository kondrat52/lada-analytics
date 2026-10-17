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
players = sorted(p for p in SH.ROSTER if w.get(p, 0) >= 20)
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
target = np.maximum(target, 3)
st, viol = solve(S2, players, T, ev, target=target, active=active, boxed=boxed, kept=kept)
Rsh = to_shifts(st, players)
Rsh.to_csv(f"{out}/shifts_final.csv", index=False)
print("constraint violations (player-seconds):", viol)
print(Rsh.groupby("player").dur.agg(["count", "sum", "mean"]).round(0).to_string())
