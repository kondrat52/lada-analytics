"""positioning.py W [GAME_JSON] : each skater's role in a game (defenseman or forward) and the parts of the season
positioning numbers. Prints them; with GAME_JSON, writes them into its "positions" (publish does this itself, and
backfill.py for published games).

What it rests on: our labeled skaters' positions on the ice (ice.positions: his labeled tracks inside his shifts, in
feet) and where the play was each second (zones.play_position), over live play (inside a period, outside the
stoppages, which game.json has moved after the goals) outside our penalty kills, an extra attacker and a penalty
shot. Not 5 on 5: our power plays are in it, since the opponents' penalties are timed only in games published from
Nov 23, 2026, and leaving them out of some games only would make the games unlike. On TK's Nov 22 (5 opponents'
penalties, about 19% of the frames) leaving them out moved single-game values by up to 0.07 (a D's inside) and 0.14
(an F's goal_side). Our net is at V = -89, H < 0 is the left as the team attacks up. Each frame (8 a second) is one
sample.

Role: among the frames with 4+ of ours labeled, the share in which he was one of our two deepest (smallest V).
D at 0.6 and up, F at 0.4 and under, unclear in between or with under 10 s of such frames (role null). Across the 49
archived games a skater's share in one game against his other games correlates 0.90.

The season numbers, kept per game as parts (seconds: numerator and denominator). A season value is the plain mean
of his games' values in that role, each game counting once (season(), game_measures()); a game's value needs 10 s
of frames (5 s for rushes, for each orientation's left and for each orientation's lanes), as in the evidence pass:
  defensemen (games where he was D):
    left       with the play in our end (V < -25), the share of it on the left side (H < 0); worked out separately
               for the periods our net is at the picture's left and at its right, and the two averaged (one alone
               where only one has 5 s): the camera puts a skater left more often with our net on one side than on
               the other (+-0.075 on the raw share)
    inside     with the play in their end (V > 25), the share of it inside their blue line (V > 25)
    deep       the same frames, the share of it 15 ft or more past their blue line (V > 40)
    and from the season left L his side (side()): "L" at 0.55 and up, "R" at 0.45 and under, "both" in between
  forwards (games where he was F):
    depth      with the play in our end, his median V
    high       with the play in their end and 2+ of our forwards labeled, the share as our highest forward (the
               smallest V of them)
    goal_side  on rushes against (the play coming at our net at 12+ ft/s, between V -45 and +30), the share of it
               goal-side of the play (his V below the play's)
    lane_left, lane_right
               with the play in their end, the share of it in the left third of the ice (H < -14) and in the right
               third (H > 14); each worked out for the two net orientations and averaged, as a D's left (an
               orientation needs 5 s, the two together 10 s). The centre lane is the rest
    low        with the play in our end, the share of it from the tops of our circles down (V <= -54)
    out        the same frames, the share of it outside our blue line (V > -25). The top of our zone is the rest
A single game's values don't repeat well enough to show (a 4-6 game mean's reliability is 0.66-0.83), so the pages
show season numbers only, for a skater with 4+ games in that role. Measured and dropped (README's TODO): a
defenseman's share in front of our net (track dropouts bias it), pinches per minute, the gap on rushes, pairs."""
import json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FPS = 8
MIN_LAB = 4              # frames with 4+ of ours labeled tell the role
ROLE_D, ROLE_F = 0.6, 0.4
ROLE_MIN = 80            # such frames (10 s) before a game has a role
SEASON_D = 0.55          # season role: the frame-weighted share over his games, D above it
SEASON_GAMES = 4         # games in a role before the season numbers show a skater
END = 25                 # the blue lines: the play in our end at V < -25, in theirs at V > 25
DEEP = 40                # a D deep on attack: 15 ft or more past their blue line
LANE = 14                # a forward's lanes: the left and right thirds of the ice start 14 ft from the middle
LOW = 54                 # a forward low in our zone: from the tops of the circles down (35 ft out from our goal line)
SIDE = 550               # a D's side: his season left at 0.550 and up, or 0.450 and under (in thousandths, as published)
RUSH_SPEED, RUSH_LO, RUSH_HI = 12, -45, 30
# a single game's values (game_measures, which the season means take): the frames each needs, as in the evidence pass
MIN_SIDE, MIN_ZONE, MIN_RUSH = 40, 80, 40


def _span_mask(T, spans):
    m = np.zeros(T, bool)
    for a, b in spans:
        m[int(a):int(np.ceil(b))] = True
    return m


def live_outside_kills(game, Ps, T):
    """Per second: live play outside our penalty kills, extra attackers and penalty shots; our power plays are in it
    (the module's docstring says why). game: game.json's dict (periods, stoppages, penalty_kills); Ps: periods.json's
    (its extra attackers and penalty shots)."""
    live = _span_mask(T, [(p["start"], p["end"]) for p in game["periods"]])
    live &= ~_span_mask(T, game.get("stoppages", []))
    pk = _span_mask(T, [(k["start"], k["end"]) for k in game.get("penalty_kills", [])])
    extra = _span_mask(T, [(k["start"], k["end"]) for P in Ps for k in P.get("extra", []) + P.get("ps", [])])
    return live & ~pk & ~extra


def frames(D, play, game, Ps, center_x):
    """Our labeled skaters' frames in live play outside our penalty kills (live_outside_kills) with the play
    measured: D (ice.positions) with play (the play's V that second), dplay (its speed, ft/s, < 0 coming at our net),
    sgn (+1 with our net at the picture's left), nlab (ours labeled in that frame) and rank (1 = our deepest in that
    frame)."""
    V = play["V"]; T = len(V)
    ev = live_outside_kills(game, Ps, T)
    fs = pd.Series(V).interpolate(limit=3, limit_area="inside")
    dplay = ((fs.shift(-2) - fs.shift(1)) / 3).values
    sgn = np.zeros(T)
    for p in game["periods"]:
        sgn[int(p["start"]):int(np.ceil(p["end"]))] = 1 if game["nets"][p["label"]] < center_x else -1
    F = D.copy(); F["s"] = F.t.astype(int)
    F = F[F.s < T]
    F = F[ev[F.s.values] & ~np.isnan(V[F.s.values])]
    F["play"] = V[F.s.values]; F["dplay"] = dplay[F.s.values]; F["sgn"] = sgn[F.s.values]
    F["nlab"] = F.groupby("t").player.transform("size")
    F["rank"] = F.groupby("t").V.rank(method="first")
    return F


sec = lambda n: round(int(n) / FPS, 3)


def parts(F):
    """number -> game.json's "positions" entry: role, role_share, role_sec, and the parts of his role's measures."""
    x4 = F[F.nlab >= MIN_LAB]
    R = x4.assign(b=x4["rank"] <= 2).groupby("player").agg(n4=("b", "size"), share=("b", "mean"))
    role = {int(p): ("D" if r.share >= ROLE_D else "F" if r.share <= ROLE_F else None) if r.n4 >= ROLE_MIN else None
            for p, r in R.iterrows()}
    fwd = [p for p, r in role.items() if r == "F"]
    oz4 = F[(F.play > END) & (F.nlab >= MIN_LAB) & F.player.isin(fwd)].copy()
    oz4["frank"] = oz4.groupby("t").V.rank(method="first")
    oz4["nF"] = oz4.groupby("t").player.transform("size")
    out = {}
    for p, r in R.iterrows():
        p = int(p); x = F[F.player == p]; e = dict(role=role[p], role_share=round(float(r.share), 3), role_sec=sec(r.n4))
        dz = x[x.play < -END]; oz = x[x.play > END]
        if role[p] == "D":
            e["left"] = [[sec((y.H < 0).sum()), sec(len(y))] for y in (dz[dz.sgn == 1], dz[dz.sgn == -1])]
            e["inside"] = [sec((oz.V > END).sum()), sec(len(oz))]
            e["deep"] = [sec((oz.V > DEEP).sum()), sec(len(oz))]
        elif role[p] == "F":
            o = oz4[(oz4.player == p) & (oz4.nF >= 2)]
            rush = x[(x.dplay < -RUSH_SPEED) & x.play.between(RUSH_LO, RUSH_HI)]
            e["depth"] = [round(float(dz.V.median()), 1) if len(dz) else None, sec(len(dz))]
            e["high"] = [sec((o.frank == 1).sum()), sec(len(o))]
            e["goal_side"] = [sec((rush.V < rush.play).sum()), sec(len(rush))]
            e["lane"] = [[sec((y.H < -LANE).sum()), sec((y.H > LANE).sum()), sec(len(y))]
                         for y in (oz[oz.sgn == 1], oz[oz.sgn == -1])]
            e["low"] = [sec((dz.V <= -LOW).sum()), sec(len(dz))]
            e["out"] = [sec((dz.V > -END).sum()), sec(len(dz))]
        out[str(p)] = e
    return out


def game_positions(W, game, play, D=None):
    """game.json's "positions" for work folder W: {"players": {number: parts}}, or None (no calibration for the
    rink, no labeled positions). game: game.json's dict with its stoppages already moved after the goals; play:
    zones.play_position's; D: ice.positions(W), when already made."""
    import ice
    from rink import rink
    if play is None:
        return None
    D = ice.positions(W) if D is None else D
    if D is None or not len(D):
        return None
    F = frames(D, play, game, json.load(open(f"{W}/periods.json")), rink(f"{W}/full").center_x)
    return dict(players=parts(F)) if len(F) else None


def _share(a):
    """[seconds, of seconds] -> the share, None when there are none."""
    return a[0] / a[1] if a and a[1] else None


MEASURES = {"D": ("left", "inside", "deep"), "F": ("depth", "high", "goal_side", "lane_left", "lane_right", "low", "out")}


def game_measures(e):
    """One game's values from its parts, each with the seconds it rests on: measure -> (value, seconds), the value
    None under the evidence pass's minimum frames (MIN_SIDE, MIN_ZONE, MIN_RUSH). A D's left is the mean of the two
    net orientations' shares, or the one orientation alone where only one has MIN_SIDE frames (the evidence pass's
    plain share of a game with only one orientation is that one's). A forward's lanes likewise, the orientations
    with MIN_SIDE frames needing MIN_ZONE between them."""
    v = {}
    if e.get("role") == "D":
        sides = [s for s in e["left"] if s[1] * FPS >= MIN_SIDE]
        v["left"] = (sum(_share(s) for s in sides) / len(sides) if sides else None, sum(s[1] for s in sides))
        v["inside"] = (_share(e["inside"]) if e["inside"][1] * FPS >= MIN_ZONE else None, e["inside"][1])
        d = e.get("deep") or [0, 0]   # none in a game's parts made before Nov 24, 2026 and not backfilled
        v["deep"] = (_share(d) if d[1] * FPS >= MIN_ZONE else None, d[1])
    elif e.get("role") == "F":
        v["depth"] = (e["depth"][0] if e["depth"][1] * FPS >= MIN_ZONE else None, e["depth"][1])
        v["high"] = (_share(e["high"]) if e["high"][1] * FPS >= MIN_ZONE else None, e["high"][1])
        v["goal_side"] = (_share(e["goal_side"]) if e["goal_side"][1] * FPS >= MIN_RUSH else None, e["goal_side"][1])
        # none of these in a game's parts made before Nov 27, 2026 and not backfilled
        ln = [s for s in e.get("lane") or [] if s[2] * FPS >= MIN_SIDE]
        n = sum(s[2] for s in ln)
        ok = n * FPS >= MIN_ZONE
        v["lane_left"] = (sum(s[0] / s[2] for s in ln) / len(ln) if ok else None, n)
        v["lane_right"] = (sum(s[1] / s[2] for s in ln) / len(ln) if ok else None, n)
        for m in ("low", "out"):
            a = e.get(m) or [0, 0]
            v[m] = (_share(a) if a[1] * FPS >= MIN_ZONE else None, a[1])
    return v


def game_values(e):
    """One game's values (game_measures without the seconds), for printing and checks; the pages show season numbers
    only."""
    return {k: x for k, (x, _) in game_measures(e).items()}


def season(games, key_of):
    """Season roles and positioning from game.json dicts (with "positions"); key_of(number, game) -> the season key
    (a guest's own, a second number's primary). Returns key -> {role, role_share, games: {D, F}, D, F}: D and F
    (None under SEASON_GAMES games in that role) with each measure's season value and the seconds it rests on. A
    season value is the plain mean of his game values in that role (game_measures), each game with the measure
    counting once whatever its seconds: on the 27 defensemen with 4+ games, split halves over games repeat better
    so (left 0.79 against 0.76 with the seconds pooled, inside 0.53 against 0.47), and the evidence pass's
    reliabilities were measured on it. Depth is in ft from our goal line; *_sec adds up the seconds of the games
    the mean takes. A D's side and side_share come from his season left (side()). The role is the frame-weighted
    share over all his games."""
    acc = {}
    for g in games:
        for n, e in ((g.get("positions") or {}).get("players") or {}).items():
            a = acc.setdefault(key_of(int(n), g), dict(w=0.0, ws=0.0, D=[], F=[]))
            a["w"] += e["role_sec"]; a["ws"] += e["role_sec"] * e["role_share"]
            if e.get("role") in ("D", "F"):
                a[e["role"]].append(game_measures(e))
    out = {}
    for k, a in acc.items():
        share = a["ws"] / a["w"] if a["w"] * FPS >= ROLE_MIN else None
        r = dict(role=None if share is None else "D" if share > SEASON_D else "F",
                 role_share=None if share is None else round(share, 3),
                 games={"D": len(a["D"]), "F": len(a["F"])}, D=None, F=None)
        for role, names in MEASURES.items():
            if len(a[role]) < SEASON_GAMES:
                continue
            r[role] = dict(games=len(a[role]))
            for m in names:
                got = [g[m] for g in a[role] if g[m][0] is not None]
                x = sum(v for v, _ in got) / len(got) if got else None
                r[role][m] = (None if x is None else round(x + 89, 1)) if m == "depth" else _round(x)
                r[role][f"{m}_sec"] = round(sum(s for _, s in got), 1)
                if m == "left":
                    r[role]["side"], r[role]["side_share"] = side(r[role]["left"])
        out[k] = r
    return out


def _round(x):
    return None if x is None else round(x, 3)


def side(L):
    """A D's side from his season left share L (as published, to 0.001): ("L", L) at 0.55 and up, ("R", 1 - L) at
    0.45 and under, ("both", None) in between, (None, None) without L. Compared in thousandths, so a published 0.45
    is "R" (as floats, 0.45 <= 1 - 0.55 is false)."""
    if L is None:
        return None, None
    m = round(L * 1000)
    if m >= SIDE:
        return "L", m / 1000
    if m <= 1000 - SIDE:
        return "R", (1000 - m) / 1000
    return "both", None


if __name__ == "__main__":
    import zones, stoppages
    W = os.path.abspath(sys.argv[1])
    gj = sys.argv[2] if len(sys.argv) > 2 else None
    if gj:   # its stoppages moved after its goals, from the motion estimate (stoppages_raw) where game.json keeps it,
        # as publish and backfill.py do, so a goal's time changed since can move a start back
        game = json.load(open(gj, encoding="utf-8"))
        raw = game["stoppages_raw"] if "stoppages_raw" in game else game.get("stoppages", [])
        g = dict(game, stoppages=stoppages.after_goals(raw, stoppages.goal_times(game.get("highlights"))))
    else:    # a work folder alone: its periods, nets, kills and stoppages, moved after highlights.json's goals
        Ps = json.load(open(f"{W}/periods.json"))
        g = dict(periods=[dict(label=P["label"], start=P["start"], end=P["end"]) for P in Ps],
                 nets={P["label"]: P["net"] for P in Ps}, stoppages=stoppages.corrected(W) or [],
                 penalty_kills=[dict(period=P["label"], **k) for P in Ps for k in P.get("pk", [])])
    pos = game_positions(W, g, zones.play_position(f"{W}/full", g))
    if pos is None:
        sys.exit(f"no positions for {W}: no calibration for its rink, or no labeled tracks")
    for n, e in sorted(pos["players"].items(), key=lambda ne: (ne[1]["role"] or "U", -ne[1]["role_share"])):
        v = game_values(e)
        print(f"#{n:>3} {e['role'] or '-':2s} {e['role_share']:.2f} of {e['role_sec']:6.1f} s   " +
              "  ".join(f"{k} {x:.3f}" if x is not None else f"{k} -" for k, x in v.items()))
    if gj:
        game["positions"] = pos
        json.dump(game, open(gj, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("wrote", gj)
