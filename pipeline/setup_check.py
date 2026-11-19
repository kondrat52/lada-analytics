"""Checks on a game's setup that fetch, `jersey`, prepare and solve print: which bench is ours, which net our goalie
defends each period, whether the board's clock and the empty ice agree on the period edges; and the views of
frame600.png that the jersey and the bench are checked on.

What they rest on, from the 47 archived work folders (Nov 18, 2026):
- The bench follows our jersey at Renton (every camera) and Snoqualmie (A and B), 42 of 42 games, not at Kirkland
  (rink.bench_by_jersey has the counts). Snoqualmie's usual right bench was wrong for 14 of its 21 games; Y's Sep 21
  was solved on it.
- Our goalie defends the net at our bench's end in the 1st and switches ends each period: 141 of 141 periods once the
  bench is right. Two reads of dets.csv agree with the published nets on their own: which half our skaters line up
  in at a period's opening faceoff, each team in its own half (139 of the 140 periods with FO_MIN detections; the
  miss, Doofers' Sep 27 1st, disagreed with both other reads), and how many of our jersey's detections stand in each
  crease over the period (fetch's old rule, 138 of 141). Most of the three gave all 141. On TK's Nov 8 game fetch had
  the nets right, the session reversed them after misreading a frame, and the goal check found it after the review.
- The board's clock gives the edges; the empty ice (nobody on the open ice for min_break s) only roughly, 30-90 s off
  at an intermission and merging periods. On the 33 archived games with the clock's reads, the two parted by more
  than EDGE_TOL only where the clock was wrong: LADA R's Nov 2 3rd, ended 148 s early ("1:02" with an unlit leading 1
  read as 0:02), and TK's Oct 25 3rd, ended 134 s early where the operator set the clock back."""
import json, os, re, sys, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rink import RINKS, rink, jersey_bench, _config

OTHER = {"left": "right", "right": "left"}
FO_MIN = 20          # detections of our skaters a faceoff window needs before its side counts
EDGE_SEARCH = 300    # s around an intermission on the clock to look for the empty ice's break
# s a clock edge and the empty ice's may part before fetch warns. Over 135 pairs on 33 archived games the honest
# ones parted by up to 90 s (warm-ups before a faceoff, handshakes on the ice after the game), the two wrong clock
# edges by 141 and 160; 60 would have warned 5 times (3 false), 75 3 times (1), 90 to 140 twice (0)
EDGE_TOL = 100


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def tm(t):
    return f"{int(t) // 60}:{int(t) % 60:02d}"


# ---------------------------------------------------------------- bench

def _place(rk):
    return re.match(r"[a-z]+", rk).group(0).title()   # renton2nov -> Renton


def settle_bench(cfg, given=None):
    """Set "bench" in cfg (W/full/rink.json as fetch and `jersey` write it) and log which side and why: --bench wins,
    with a warning where it goes against the jersey; a bench set before by hand or with --bench stays; otherwise, where
    the rink's bench follows our jersey, it is set from it and marked "bench_from": "jersey", so that a jersey switch
    moves it again. Kirkland keeps its usual side. Old folders are never passed through here, so they solve as before."""
    rk, jer = cfg.get("rink", "renton"), cfg.get("jersey", "light blue")
    rule, have = jersey_bench(rk, jer), cfg.get("bench")
    seen = f"in {jer.split(' vs ')[0]} we have sat on the {rule} at every archived {_place(rk)} game"
    if given:
        cfg["bench"] = given
        cfg.pop("bench_from", None)
        log(f"bench: {given} (--bench)" if rule in (None, given) else
            f"WARNING bench: keeping --bench {given}, but {seen}: make sure bench_left.jpg and bench_right.jpg agree")
    elif have and cfg.get("bench_from") != "jersey":
        log(f"bench: {have} (set before in rink.json, so kept)" + ("" if rule in (None, have) else f"; WARNING: {seen}"))
    elif rule:
        cfg.update(bench=rule, bench_from="jersey")
        log(f"bench: {rule}, from our jersey ({seen})" + (f"; it was {have}" if have and have != rule else "")
            + "; --bench or \"bench\" in full/rink.json overrides it")
    else:
        log(f"bench: {have or RINKS[rk].bench_side}, {_place(rk)}'s usual: the bench there doesn't follow the jersey, "
            f"so check it on bench_left.jpg and bench_right.jpg (our jerseys sit at our bench); if it is the other one, "
            f"give --bench or set \"bench\" in full/rink.json")
    return cfg.get("bench")


def bench_check(W):
    """Print our bench as prepare and solve will use it, with a warning where it goes against our jersey's side."""
    cfg = _config(f"{W}/full")
    rk, jer = cfg.get("rink", "renton"), cfg.get("jersey", "light blue")
    side, rule = rink(f"{W}/full").side, jersey_bench(rk, jer)
    src = "rink.json" if cfg.get("bench") else f"{_place(rk)}'s usual; rink.json sets none"
    if rule is None:
        log(f"bench: ours is on the {side} ({src}); {_place(rk)}'s bench doesn't follow the jersey, so make sure "
            f"frame600.png agrees")
    elif rule == side:
        log(f"bench: ours is on the {side} ({src}), as it has been in {jer.split(' vs ')[0]} at every archived "
            f"{_place(rk)} game")
    else:
        log(f"WARNING bench: ours is on the {side} ({src}), but in {jer.split(' vs ')[0]} we have sat on the {rule} at "
            f"every archived {_place(rk)} game. If frame600.png shows ours on the {rule}, set \"bench\": \"{rule}\" in "
            f"{W}/full/rink.json, then prepare again (unless the review has started) and solve")
    return side


# ---------------------------------------------------------------- nets

def _load(W):
    from track import load
    d = load(f"{W}/full/dets.csv")
    d["rel"] = d.fy - d.board
    return d


def net_votes(W, Ps, d=None, faceoff=True):
    """Per period, the side of the net our goalie defends by three reads that don't depend on each other: "rule" (our
    bench's end in the 1st, then switching), "faceoff" (the half our skaters, out of both creases, stand in from 3 s
    before to 1 s after the period's start, which must be a faceoff, as the clock's starts are and the empty ice's
    aren't; None under FO_MIN detections) with "share" on the left, and "crease" (more of our jersey's detections in
    that crease over the period) with the counts "nl" and "nr"."""
    R = rink(f"{W}/full")
    d = _load(W) if d is None else d
    us = d[d.ours]
    sk = us[us.onice & ~R.in_crease(us.fx, us.rel, R.nets["left"]) & ~R.in_crease(us.fx, us.rel, R.nets["right"])]
    out = []
    for k, P in enumerate(Ps):
        a, b = P["start"], P["end"]
        f0 = sk[(sk.t >= a - 3) & (sk.t < a + 1)]
        share = float((f0.fx < R.center_x).mean()) if faceoff and len(f0) >= FO_MIN else None
        w = us[(us.t >= a) & (us.t < b)]
        nl, nr = (int(R.in_crease(w.fx, w.rel, R.nets[s]).sum()) for s in ("left", "right"))
        out.append(dict(rule=R.side if k % 2 == 0 else OTHER[R.side], share=share,
                        faceoff=None if share in (None, 0.5) else "left" if share > 0.5 else "right",
                        crease=None if nl == nr == 0 else "left" if nl >= nr else "right", nl=nl, nr=nr))
    return out


def _vote_line(P, v, side):
    fo = f"faceoff {v['faceoff']} ({v['share']:.0%} of ours in the left half)" if v["faceoff"] else "faceoff -"
    cr = f"crease {v['crease']} ({v['nl']} left, {v['nr']} right)" if v["crease"] else "crease -"
    odd = any(x and x != side for x in (v["rule"], v["faceoff"], v["crease"]))
    return f"  {P['label']} {side}: rule {v['rule']}, {fo}, {cr}" + ("   <- they disagree" if odd else ""), odd


LOOK = ("where our skaters crowd during one of our penalty kills, the net where the board's score for us went up, or "
        "a crease zoom per period showing pads and a mask, not just a body at the net (`run_game.py frames W out.jpg "
        "--view left-net T ...`)")


def propose_nets(W, Ps, d=None, faceoff=True):
    """The net side per period that most of net_votes' three reads give (the rule on a tie: it held on 141 of 141
    periods), logged with each read. faceoff=False where the periods are the empty ice's, whose starts aren't
    faceoffs."""
    R = rink(f"{W}/full")
    votes = net_votes(W, Ps, d, faceoff)
    sides, odd = [], False
    log(f"nets, by the rule (our bench is on the {R.side}: our goalie at that end in the 1st, switching each period), "
        f"the opening faceoff" + ("" if faceoff else " (not read: these periods' starts aren't the clock's)")
        + " and our jersey in each crease:")
    for P, v in zip(Ps, votes):
        vs = [x for x in (v["rule"], v["faceoff"], v["crease"]) if x]
        side = max(("left", "right"), key=lambda s: (vs.count(s), s == v["rule"]))
        line, o = _vote_line(P, v, side)
        print(line, flush=True)
        sides.append(side); odd |= o
    if odd:
        log(f"WARNING nets: the reads disagree; before prepare, look: {LOOK}. If the bench is wrong, fix it first (the "
            f"rule follows it)")
    return sides


def check_nets(W, stop=False, d=None):
    """periods.json's nets against net_votes. With stop, exit where a period's net goes against both the rule and the
    faceoff (prepare drops our goalie's detections at that net, and once the review has started nothing can be
    re-prepared): none of the 47 archived games does, TK's Nov 8 with its nets reversed did in all three periods."""
    R = rink(f"{W}/full")
    Ps = json.load(open(f"{W}/periods.json"))
    if any(P.get("net") is None for P in Ps):
        sys.exit(f"periods.json has no net for {', '.join(P['label'] for P in Ps if P.get('net') is None)}: set each "
                 f"period's (rink.py nets: {R.nets})")
    sides = ["left" if P["net"] < R.center_x else "right" for P in Ps]
    votes = net_votes(W, Ps, d)
    lines = [_vote_line(P, v, s) for P, v, s in zip(Ps, votes, sides)]
    bad = [P["label"] for P, v, s in zip(Ps, votes, sides) if v["faceoff"] and s != v["rule"] and s != v["faceoff"]]
    if not any(o for _, o in lines):
        where = ", ".join(P["label"] + " " + s for P, s in zip(Ps, sides))
        log(f"nets: our goalie {where} (periods.json); the rule (at our bench's end in the 1st, switching), the opening "
            f"faceoffs and the crease counts agree")
        return True
    log(f"nets in periods.json against the rule (at our bench's end in the 1st, switching), the opening faceoff and the "
        f"crease count:")
    for line, _ in lines:
        print(line, flush=True)
    if not bad:
        log(f"WARNING nets: not all agree, but no period goes against both the rule and the faceoff. Where in doubt: {LOOK}")
        return True
    msg = (f"nets: in {', '.join(bad)} periods.json puts our goalie at the other end from both the rule and where our "
           f"skaters lined up at the opening faceoff")
    if stop:
        sys.exit(f"{msg}. Prepare drops his detections at that net, and nothing can be re-prepared once the review "
                 f"starts. Fix `net` in {W}/periods.json (rink.py nets: {R.nets}), or the bench if that is what is "
                 f"wrong. If you have seen that the nets are right, prepare again with --force; what shows it: {LOOK}")
    log(f"WARNING {msg}. Unless you have seen that they are right, fix `net` in periods.json (before prepare, if it "
        f"hasn't run). What shows it: {LOOK}")
    return False


# ---------------------------------------------------------------- period edges

def busy_ice(R, d, conf=0.3, fps=8):
    """Stretches with someone out on the open ice, between breaks of min_break+ s with nobody there (rink.py), from
    detections with rel. [[start, end], ...]"""
    T = int(d.t.max()) + 1
    out = d[R.open_ice(d.fx, d.rel) & (d.conf >= conf)]
    act = np.bincount(out.t.astype(int), minlength=T) / fps
    empty = pd.Series(act).rolling(5, center=True, min_periods=1).median().values < 0.5
    spans, s = [], None
    for t in range(T + 1):
        e = t < T and empty[t]
        if e and s is None:
            s = t
        if not e and s is not None:
            if t - s >= R.min_break:
                spans.append((s, t))
            s = None
    edges = [0] + [x for b in spans for x in b] + [T]
    return [[a, b] for a, b in zip(edges[0::2], edges[1::2]) if b > a]


def empty_ice(busy):
    """Fetch's periods before the clock, and the clock's cross-check: busy_ice's stretches of 240+ s."""
    return [p for p in busy if p[1] - p[0] >= 240]


def edge_pairs(clock_ps, busy):
    """Each clock edge with the empty-ice edge that stands for the same moment: the end and start around each
    intermission on the clock with the break between empty_ice's periods nearest it (within EDGE_SEARCH s; where the
    empty ice found none, as when it merged two periods, nothing is compared), and the last period's end with the end
    of the last stretch of play (busy_ice's last of 60+ s: on Y's Nov 9 the 3 minutes after a late timeout were too
    short for empty_ice). The 1st's start isn't compared: the empty ice starts at 0 whenever the video opens with
    players out. [(label, "start" | "end", clock t, empty-ice t)]"""
    periods, play = empty_ice(busy), [p for p in busy if p[1] - p[0] >= 60]
    if not clock_ps or not periods:
        return []
    breaks = [(e0[1], e1[0]) for e0, e1 in zip(periods, periods[1:])]
    out = []
    for P, Q in zip(clock_ps, clock_ps[1:]):
        near = [b for b in breaks if b[1] > P["end"] - EDGE_SEARCH and b[0] < Q["start"] + EDGE_SEARCH]
        if near:
            b = min(near, key=lambda b: abs(b[0] + b[1] - P["end"] - Q["start"]))
            out += [(P["label"], "end", P["end"], b[0]), (Q["label"], "start", Q["start"], b[1])]
    return out + [(clock_ps[-1]["label"], "end", clock_ps[-1]["end"], play[-1][1])]


def edge_check(W, clock_ps, busy, T=None):
    """Warn where a clock edge and the empty ice's part by more than EDGE_TOL s, with what to look at first. T: the
    video's length in s."""
    for lab, kind, tc, te in edge_pairs(clock_ps, busy):
        if abs(tc - te) <= EDGE_TOL:
            continue
        if kind == "end" and te > tc:
            what = ((f"the open ice was still busy when the video ended at {te} ({tm(te)})" if te == T else
                     f"the open ice emptied only at {te} ({tm(te)})") + f", {te - tc} s later: if our skaters stayed out, "
                    f"play went on and the clock was misread (LADA R's Nov 2: \"1:02\" with an unlit leading 1 read as "
                    f"0:02)")
        elif kind == "end":
            what = (f"the open ice was empty from {te} ({tm(te)}), {tc - te} s before: the operator may have run the "
                    f"clock off on an empty rink")
        elif te < tc:
            what = (f"the open ice was busy from {te} ({tm(te)}), {tc - te} s before: the board may have sat at 18:00 "
                    f"through play, or that was the warm-up")
        else:
            what = f"the open ice stayed empty until {te} ({tm(te)}), {te - tc} s later"
        a, b = min(tc, te) - 30, max(tc, te) + 30
        log(f"WARNING periods: the clock {'ends' if kind == 'end' else 'starts'} {lab} at {tc} ({tm(tc)}), but {what}. "
            f"Before moving the edge, run `run_game.py skaters {W} {a} {b}` (our skaters out per 5 s) and look at "
            f"clock_check.jpg and a 2 s sheet of the board there (`scoreboard.py {W} out.jpg $(seq {a} 2 {b})`)")


def clock_report(W, clk):
    """Per period on the clock: whether it ran out, how many reads agree with the fit, and how long the board was
    dark at its edges (W/clock_reads.json: where it was, the fit assumed the clock kept running); and the 3rd's end
    where publish may need --video-ends-early: a clock that never reached 0.0, or one that "reached" it on a dark
    board within seconds of the video's end (TK's Nov 8: dark for the last 30 s, the video stopped with 20 s left;
    of the 33 archived clocks only that one and TK's Nov 15, which did run out at the video's end, look so)."""
    import clock
    p = f"{W}/clock_reads.json"
    reads = json.load(open(p))["reads"] if os.path.exists(p) else None
    n = len(next(iter(reads.values()))) if reads else 0
    dark = lambda a, b: sum(not any(clock.digits(r[t][0]) for r in reads.values() if r[t][1] > 0)
                            for t in range(max(0, a), min(b, n))) if reads else 0
    for P in clk["periods"]:
        ds, de = dark(P["start"], P["start"] + 21), dark(P["end"] - 20, P["end"] + 1)
        log(f"clock: {P['label']} {P['start']}-{P['end']} ({tm(P['start'])}-{tm(P['end'])} of video), from "
            f"{tm(P['from'])}, {'ran out' if P['ran_out'] else 'never reached 0.0'}; {P['agree']:.0%} of the reads agree"
            + (f"; the board was dark for {ds} of the 21 s from its start" if ds >= 10 else "")
            + (f"; dark for {de} of the 21 s up to its end, so that edge is an estimate" if de >= 10 else ""))
    if len(clk["periods"]) < 3:
        return
    P = clk["periods"][-1]
    if not P["ran_out"]:
        log(f"WARNING clock: the {P['label']} clock never reached 0.0 before the video ended (it shows "
            f"{tm(P['knots'][-1][1])} at {P['end']}): if the recording stops before the final horn, publish needs "
            f"--video-ends-early")
    elif reads and n - P["end"] <= 10 and dark(P["end"] - 20, P["end"] + 1) >= 15:
        log(f"WARNING clock: the board was dark before the {P['label']} clock's 0.0 at {P['end']}, {n - P['end']} s "
            f"before the video ends, so the reader assumed the clock ran out. Look at the last tiles of "
            f"clock_check.jpg and video_end.jpg: if play was still on when the video stopped (TK's Nov 8), "
            f"{P['label']} ends at the video's end and publish needs --video-ends-early")


# ---------------------------------------------------------------- framing

ROLL_DEG = 1.5      # degrees: a turn up to this that lines the curve up is a roll; Renton's Nov 7 re-aim took 2.6


def roll_fit(P, name):
    """(degrees, px down, worst px across the middle, worst px at the frame ends) of the turn and shift that line the
    far-boards curve P up with rink `name`'s ice-map camera (rinkcam.align; a "same_as" camera is its base's), or
    None without one. The curve alone can't tell a roll from a re-aim by how well it fits (8-9 px across the middle
    for both on the archives), only by how far it turns: TK's Nov 15 against renton2nov -0.96 degrees (a roll: the
    center line leaned), TK's Nov 8 against renton2 -2.62 (a re-aim: the center line stayed upright)."""
    import rinkcam
    path = os.path.join(rinkcam.CAMS, f"{name}.json")
    if not os.path.exists(path):
        return None
    c = json.load(open(path))
    if "same_as" in c:
        c = json.load(open(os.path.join(rinkcam.CAMS, f"{c['same_as']}.json")))
    a, dy = rinkcam.align(c, P)
    uc, vc = c["params"]["u0"], c["params"]["v0"]
    off = lambda xs: float(np.abs((lambda u, v: v - np.polyval(c["boards_poly"], u))(
        *rinkcam._turn((a, dy), xs, np.polyval(P, xs), uc, vc))).max())
    return (float(np.degrees(a)), float(dy), off(np.linspace(500, 2 * uc - 500, 40)),
            off(np.r_[np.linspace(0, 500, 6), np.linspace(2 * uc - 500, 3840, 6)]))


def roll_hint(P, name):
    """framing_shift's words for a curve that no class's reference fits: the turn and shift onto this rink's camera,
    and whether that reads as a roll or a re-aim."""
    fit = roll_fit(P, name)
    if fit is None:
        return ""
    deg, dy, mid, ends = fit
    turn = (f"; turned {deg:+.2f} degrees and moved {dy:+.0f} px it lies within {mid:.0f} px of {name}'s ice-map camera "
            f"across the middle, {ends:.0f} at the frame ends")
    if abs(deg) <= ROLL_DEG:
        return (turn + f": a roll of about {abs(deg):.1f} degrees, as on TK's Nov 15 game, which the ice maps correct; "
                f"run as {name} if the nets, the bench and the board crop hold on frame600.png")
    return (turn + f": more than a roll, as TK's Nov 8 re-aim was against renton2 (-2.62), so look at the center line on "
            f"frame600.png: upright means re-aimed, and the camera needs a class of its own in rink.py, measured off "
            f"frame600.png before the scoreboard scan runs (the board, nets, box posts, near boards and center line; "
            f"renton2nov's values are an example), then its ice-map camera (rinkcal.py)")


# ---------------------------------------------------------------- frame600 views

def frame_views(W, width=1920):
    """frame600_small.jpg (frame600.png at about 1920 wide: 4K is too big to read whole) and bench_left.jpg and
    bench_right.jpg (each bench as `frames --view bench` crops it), to check our jersey and our bench on."""
    import cv2
    im = cv2.imread(f"{W}/frame600.png")
    if im is None:
        return
    h, w = im.shape[:2]
    cv2.imwrite(f"{W}/frame600_small.jpg", cv2.resize(im, (width, round(h * width / w)), interpolation=cv2.INTER_AREA),
                [cv2.IMWRITE_JPEG_QUALITY, 88])
    R = rink(f"{W}/full")
    for side in ("left", "right"):
        x0, x1, y0, y1 = type(R)(R.P, bench=side).bench_view()
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        cv2.imwrite(f"{W}/bench_{side}.jpg", im[y0:int(y1), x0:int(x1)], [cv2.IMWRITE_JPEG_QUALITY, 90])
    log(f"jersey and bench: {W}/frame600_small.jpg, {W}/bench_left.jpg, {W}/bench_right.jpg (our jerseys sit at our "
        f"bench)")
