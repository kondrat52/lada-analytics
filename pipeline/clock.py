"""clock.py W [--write] : the period clock off the arena scoreboard -> W/clock.json: when each period's clock started
counting down and when it reached 0.0, and the video time of every clock time in between.

Needs the board per second (scoreboard.py: W/scoreboard.npy, or an archive's scoreboard_jpg.npz) and the rink's
`clock_box` (rink.py): the clock's digits inside the scoreboard crop, levelled by `clock_tilt` degrees where the board
hangs at an angle. The camera isn't framed the same every game (Snoqualmie A's board sat 50 px lower on Oct 12 and
18), so the box is first moved to where the board changes from second to second: the clock's digits.

Every second the digits are read twice with OCR (RapidOCR's recogniser; two crops, see `crops`). The reads are noisy:
the recogniser reads the seconds well, but drops a thin "1", runs "16" together into "b", reads a 7 as a 1, and gets
nothing while the LEDs flicker dark (for 15 s at a time at Renton's new camera). So the clock is the sequence that
agrees best with all the reads, digit by digit, and moves only the way a clock does (`fit`): down a second per second
while it runs, still while it is stopped (dear in a second whose reads changed), and now and then a jump: cheap to
18:00 or an intermission countdown (1:00, 1:30, 2:00) once it has shown 0.0 for a few seconds, dear anywhere else (a
misread minute makes a fake clock that jumps). The last minute shows ss.t in a period ("45.9") and 0:ss in an
intermission countdown ("0:45"). A period is a stretch that starts at 5:00 or more (18:00 so far) and counts down: it
starts at the last second the clock shows 18:00 and ends at its first 0.0.

On 13 archived games at all seven rink setups (Oct 24, 2026), 70 of 78 period edges came within 2 s of the
hand-read periods.json (59 within 1 s). At six more the board agreed with the clock and the hand-read edge followed
play or sat a few seconds off it (Kirkland's late start on Y's Oct 5, Beerteam's Sep 13, Blue Wings' Oct 11); two fell
where the board was dark (7 and 16 s off). A full fetch of Doofers' Oct 18 from YouTube put all six within 2 s. For
the sheets' 96 goals `video_t` gave 82 from 2 s before to 8 s after the goal itself. Most of the rest are the sheet's
own times: a power-play goal at the penalty's time, or 15-25 s late in a period whose clock runs through stoppages.

Writes W/clock.json: {"offset": [dx, dy], "periods": [{"label", "start", "end", "from", "ran_out", "knots",
"agree"}], "runs": [...]} with "knots" = [[t, clock seconds], ...] where the clock starts or stops running or jumps
(linear in between), and W/clock_check.jpg: the board 1 s before, at and after each period's start and end. `video_t`
turns a period's clock time into a video second. With --write the periods go into W/periods.json (periods already
there keep their nets, penalty kills and spans; new ones need a net). Without it, a periods.json that differs is
printed next to the clock's: on an archived folder that is the check against the hand-read periods.
"""
import json, os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rink import rink

CMAX = 20 * 60          # highest clock value considered (s)
STOP = 0.02             # fit cost of a second of stopped clock
STOP_CHANGED = 0.5      # ... more in a second whose reads changed
JUMP0, JUMP, JUMP_UP = 2.5, 25.0, 40.0  # ... of a jump to a value operators set (SET) once the clock has shown 0.0
                                       # HOLD s, of one down or up to SET from anywhere else, and of any other jump
                                       # up (a misread minute digit can't make a clock do that)
PERIOD, INTERMISSIONS = 1080, (60, 90, 120)   # 18:00 at every rink so far; the intermission countdowns seen
SET = (PERIOD,) + INTERMISSIONS
HOLD = 3                                # s a clock shows 0.0 before the operator sets it again
MIN_PERIOD = 300        # a stretch starting at this or more and counting down is a period
SEARCH = 60             # px the clock box may move to find the clock
OUT_H = 40              # px height of the levelled digits handed to the recogniser
READER = 4              # bump when reading changes: clock_reads.json from another reader is read again
SHEET_TOL, LONG_STOP = 3, 10   # video_t: a sheet time up to this many s under where the clock stopped this long


def box_corners(box, tilt):
    """The clock box's corners in the crop: box is the levelled rectangle, turned by tilt degrees about its centre
    (positive: the digits slope down to the right)."""
    x0, y0, x1, y1 = box
    c = np.array([(x0 + x1) / 2, (y0 + y1) / 2])
    a = np.radians(tilt)
    R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    pts = np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], float) - c
    return pts @ R.T + c


def locate(a, box, tilt, ring=3):
    """(dx, dy): where the box takes in the most change from second to second with the least just outside it (the
    clock's digits, the seconds above all), within SEARCH px of where rink.py puts it. Searched on the crop turned
    so that the box is level."""
    frac = np.zeros(a.shape[1:3], np.float64)
    prev = None
    for i in range(0, len(a), 256):
        v = np.stack([np.asarray(f).max(2) for f in a[i:i + 256]]).astype(np.int16)
        if prev is not None:
            v = np.concatenate([prev[None], v])
        frac += (np.abs(np.diff(v, axis=0)) > 40).sum(0)
        prev = v[-1]
    x0, y0, x1, y1 = box
    H, Wd = frac.shape
    lev = cv2.warpAffine(frac, cv2.getRotationMatrix2D(((x0 + x1) / 2, (y0 + y1) / 2), tilt, 1.0), (Wd, H)) if tilt else frac
    ii = np.pad(lev, ((1 + ring, ring), (1 + ring, ring))).cumsum(0).cumsum(1)   # padded: the ring may leave the crop

    def S(u0, v0, u1, v1):
        u0, v0, u1, v1 = u0 + ring, v0 + ring, u1 + ring, v1 + ring
        return ii[v1, u1] - ii[v0, u1] - ii[v1, u0] + ii[v0, u0]
    best, arg = -np.inf, (0, 0)
    for dy in range(-SEARCH, SEARCH + 1):
        for dx in range(-SEARCH, SEARCH + 1):
            u0, v0, u1, v1 = x0 + dx, y0 + dy, x1 + dx, y1 + dy
            if u0 < 0 or v0 < 0 or u1 > Wd or v1 > H:
                continue
            inner = S(u0, v0, u1, v1)
            s = 2 * inner - S(u0 - ring, v0 - ring, u1 + ring, v1 + ring) - 1e-3 * (abs(dx) + abs(dy))
            if s > best:
                best, arg = s, (dx, dy)
    t = np.radians(tilt)
    dx, dy = arg
    return int(round(dx * np.cos(t) - dy * np.sin(t))), int(round(dx * np.sin(t) + dy * np.cos(t)))


def levelled(a, box, tilt, off):
    """The clock box of every second, levelled and scaled to OUT_H px, as LED brightness (the brightest channel)."""
    x0, y0, x1, y1 = box
    s = OUT_H / (y1 - y0)
    w = int(round((x1 - x0) * s))
    M = cv2.getAffineTransform((box_corners(box, tilt) + off)[:3].astype(np.float32),
                               np.float32([(0, 0), (w, 0), (w, OUT_H)]))
    return np.stack([cv2.warpAffine(np.asarray(f).max(2).astype(np.float32), M, (w, OUT_H), flags=cv2.INTER_CUBIC,
                                    borderMode=cv2.BORDER_REPLICATE) for f in a])


def finish(v, pad=8):
    """0..1 brightness -> dark digits on white with a margin, as the recogniser wants them."""
    im = (255 - np.clip(v, 0, 1) * 255).astype(np.uint8)
    return cv2.cvtColor(cv2.copyMakeBorder(im, pad, pad, pad * 2, pad * 2, cv2.BORDER_CONSTANT, value=255), cv2.COLOR_GRAY2BGR)


def crops(v):
    """Two looks at every second's clock, which go wrong on different boards: "raw", the brightness stretched over
    the crop (the digits glow as they do on the board; at Renton the clock's frame shows too), and "bg", the
    brightness above each pixel's darkest level over the game (2nd percentile: the frame, labels and board are lit
    all game, every LED segment is dark some of the time), with under 30% of a bright level left white (unlit
    segments glow a little: a 3 would read as an 8). Both keep a second whose LEDs flickered dark blank instead of
    stretching its noise into digits."""
    lo, hi = np.percentile(v, 5, axis=(1, 2)), np.percentile(v, 99.5, axis=(1, 2))
    rng = np.maximum(hi - lo, 0.3 * float(np.percentile(hi - lo, 90)))
    raw = (v - lo[:, None, None]) / rng[:, None, None]
    b = np.maximum(v - np.percentile(v, 2, axis=0), 0)
    top = float(np.percentile(b, 99.5))
    bhi = np.maximum(np.percentile(b, 99.5, axis=(1, 2)), 0.5 * top)[:, None, None]
    return {"raw": raw, "bg": (b - 0.3 * bhi) / (0.7 * bhi)}


def read_all(W, a=None):
    """Per second and look (crops): [text, score] of the clock; and the box offset used."""
    from rapidocr import RapidOCR
    from rapidocr.ch_ppocr_rec.typings import TextRecInput
    from scoreboard import load as load_board
    R = rink(f"{W}/full")
    a = load_board(W) if a is None else a
    off = locate(a, R.clock_box, R.clock_tilt)
    rec = RapidOCR(params={"Global.use_det": False, "Global.use_cls": False, "Rec.rec_batch_num": 32})._load_rec_model()
    reads = {}
    for look, v in crops(levelled(a, R.clock_box, R.clock_tilt, off)).items():
        reads[look] = []
        for i in range(0, len(v), 256):
            r = rec(TextRecInput(img=[finish(x) for x in v[i:i + 256]]))
            reads[look] += [[t.strip(), round(float(s), 3)] for t, s in zip(r.txts, r.scores)]
    return reads, off


# ---------------------------------------------------------------- the fit

SUBS = str.maketrans({"O": "0", "o": "0", "D": "0", "Q": "0", "U": "0", "I": "1", "l": "1", "|": "1", "i": "1",
                      "!": "1", "J": "1", "Z": "2", "z": "2", "S": "5", "s": "5", "b": "6", "G": "6", "B": "8",
                      "g": "9", "q": "9", "C": "0", "c": "0"})
WILD = 10                                     # the tenths digit of the last minute, which the fit doesn't track
CONFUSED = {(1, 7), (7, 1), (0, 8), (8, 0), (6, 8), (8, 6), (9, 8), (8, 9), (5, 6), (6, 5), (3, 8), (8, 3), (5, 9), (9, 5)}
SUB, CONF, DEL, DEL1, INS = 0.35, 0.2, 0.35, 0.1, 0.35   # digit costs: wrong, a look-alike, missed, a missed
                                                         # leading 1 (thin) or 0 (blank under 10 s at some boards), extra
NEAR = 0.15                                   # ... and of the read showing the second before or after
MINUTES = 0.5                                 # weight of the minute's ones digit: the recogniser reads the seconds well,
                                              # but at some boards drops or garbles the minute ("17:06" as "106") for
                                              # a whole minute


def shown(c, alt=False):
    """The digits the board shows at clock value c (whole seconds): m:ss or mm:ss, and in the last minute ss.t
    (a period's) or, with alt, 0:ss (an intermission countdown's)."""
    if c >= 60:
        return [int(x) for x in f"{c // 60}{c % 60:02d}"]
    return [0, c // 10, c % 10] if alt else [c // 10, c % 10, WILD]


def _display(alt):
    d = [shown(c, alt) for c in range(CMAX + 1)]
    n = np.array([len(x) for x in d])
    # per display digit (and one past the last, for extra characters after it): the minute's ones digit counts MINUTES
    wt = np.array([[MINUTES if (c >= 60 or alt) and j == n[c] - 3 else 1.0 for j in range(5)] for c in range(CMAX + 1)])
    return np.array([x + [-1] * (4 - len(x)) for x in d]), n, wt


DISPLAYS = [_display(False), _display(True)]


def digits(txt):
    """A read -> its digits ('' if it has other characters than digits, look-alike letters and separators, or fewer
    than two digits: a lone character is what a dark board reads as)."""
    t = txt.replace(" ", "").translate(SUBS)
    t = "".join(ch for ch in t if ch not in ":.,;'")
    return t if t.isascii() and t.isdigit() and 2 <= len(t) <= 6 else ""


def distance(d):
    """Edit distance from the digit string d to what the board shows at every clock value (vectorised over them;
    the nearer of the last minute's two ways)."""
    return np.minimum(*[_distance(d, *x) for x in DISPLAYS])


def _distance(d, DIG, L, WT):
    r = [int(x) for x in d]
    N = len(DIG)
    D = np.zeros((len(r) + 1, 5, N))
    for j in range(1, 5):                     # display digits missed by the read
        dj = DIG[:, j - 1]
        dc = np.where(dj == WILD, 0.0, np.where((j == 1) & ((dj == 1) | (dj == 0)), DEL1, DEL)) * WT[:, j - 1]
        D[0, j] = D[0, j - 1] + dc
    for i in range(1, len(r) + 1):
        D[i, 0] = D[i - 1, 0] + INS * WT[:, 0]
        for j in range(1, 5):
            dj = DIG[:, j - 1]
            sub = np.where((dj == r[i - 1]) | (dj == WILD), 0.0,
                           np.where(np.isin(dj, [b for a_, b in CONFUSED if a_ == r[i - 1]]), CONF, SUB)) * WT[:, j - 1]
            dc = np.where(dj == WILD, 0.0, np.where((j == 1) & ((dj == 1) | (dj == 0)), DEL1, DEL)) * WT[:, j - 1]
            ins = INS * np.where(j < L, WT[:, j], 1.0)
            D[i, j] = np.minimum.reduce([D[i - 1, j - 1] + sub, D[i, j - 1] + dc, D[i - 1, j] + ins])
    return D[len(r), L, np.arange(N)]


def observations(reads):
    """Per second, the cost of each clock value: each look's read costs its score times its distance from what the
    board would show (capped at 1), or from what it shows a second either side plus NEAR (the brightest frame can
    come from anywhere in its second, but the period's edges are the board's own first 17:59 and first 0.0); the
    looks that read something are averaged."""
    cache, out = {}, []
    for rs in zip(*reads.values()):
        os_ = []
        for txt, sc in rs:
            d = digits(txt) if sc > 0 else ""
            if not d:
                continue
            if d not in cache:
                x = np.minimum(distance(d), 1.0)
                cache[d] = np.minimum(x, np.minimum(np.r_[x[1:], 1.0], np.r_[1.0, x[:-1]]) + NEAR)
            os_.append(sc * cache[d])
        out.append(sum(os_) / len(os_) if os_ else None)
    return out


def running_min(x):
    """Running minimum of x and where it was reached."""
    m = np.minimum.accumulate(x)
    return m, np.maximum.accumulate(np.where(x == m, np.arange(len(x)), 0))


def changes(reads):
    """Per second, 1 where every look that read digits both then and the second before saw their last two change: a
    running clock changes them every second (seconds or tenths), a stopped one shows the same thing second after
    second, and one look's slip shouldn't make it run."""
    out = np.zeros(len(next(iter(reads.values()))))
    looks = [[digits(t)[-2:] if s > 0 else "" for t, s in rs] for rs in reads.values()]
    for t in range(1, len(out)):
        pairs = [(x[t - 1], x[t]) for x in looks if x[t - 1] and x[t]]
        out[t] = float(bool(pairs) and all(a != b for a, b in pairs))
    return out


def fit(reads):
    """The clock value (whole seconds) per second that best explains the reads: Viterbi over 0..CMAX, plus HOLD
    states for 0.0 held 1..HOLD s, with steps of -1 (running), 0 (stopped, STOP) or a jump: JUMP0 to a SET value
    once 0.0 has been held HOLD s (a period's end; an intermission's), JUMP down or up to a SET value from anywhere
    else, JUMP_UP for any other jump up. Held 0.0 comes out as 0."""
    obs = observations(reads)
    stop_t = STOP + STOP_CHANGED * changes(reads)
    T, N = len(obs), CMAX + 1
    vals = np.arange(N)
    to_set = np.isin(vals, SET) | np.isin(vals - 1, SET)          # or the fit a second above it
    up_cost = np.where(to_set, JUMP, JUMP_UP)
    held_cost = np.where(to_set, JUMP0, JUMP_UP)
    back = np.zeros((T, N + HOLD), np.int16)
    # the video starts before the opening faceoff: 18:00, a countdown, or blank; anything else costs a jump
    cost = np.r_[np.where(to_set | (vals <= max(INTERMISSIONS)), 0.0, JUMP), np.zeros(HOLD)]
    if obs[0] is not None:
        cost += np.r_[obs[0], np.full(HOLD, obs[0][0])]
    back[0] = np.arange(N + HOLD)
    for t in range(1, T):
        v, z = cost[:N], cost[N:]
        cands = [np.r_[v[1:], np.inf], np.r_[np.inf, v[1:] + stop_t[t]]]   # running (from c+1); stopped (not at 0.0)
        args = [np.minimum(vals + 1, N - 1), vals]
        cands.append(z[-1] + held_cost); args.append(np.full(N, N + HOLD - 1))
        sm, si = running_min(v[::-1])                               # down into c: the cheapest value above it
        cands.append(np.r_[sm[::-1][1:], np.inf] + JUMP); args.append(np.r_[(N - 1 - si[::-1])[1:], 0])
        src = np.r_[min(v[0], z[:-1].min()), v[1:]]                  # up into c: the cheapest value below it
        zarg = 0 if v[0] <= z[:-1].min() else N + int(np.argmin(z[:-1]))
        pm, pi = running_min(src)
        cands.append(np.r_[np.inf, pm[:-1]] + up_cost); args.append(np.r_[0, np.where(pi[:-1] == 0, zarg, pi[:-1])])
        C = np.stack(cands); k = np.argmin(C, axis=0)
        newv = C[k, vals]; argv = np.stack(args)[k, vals]
        # holding 0.0 one second longer, for half a stop: where the board is dark, a clock that was running ran out
        newz = np.r_[v[0], z[:-1]] + stop_t[t] / 2
        argz = np.r_[0, N + np.arange(HOLD - 1)]
        if z[-1] < z[-2]:
            newz[-1] = z[-1] + stop_t[t] / 2; argz[-1] = N + HOLD - 1
        cost = np.r_[newv, newz]
        if obs[t] is not None:
            cost = cost + np.r_[obs[t], np.full(HOLD, obs[t][0])]
        back[t] = np.r_[argv, argz]
    seq = np.zeros(T, int); seq[-1] = int(np.argmin(cost))
    for t in range(T - 1, 0, -1):
        seq[t - 1] = back[t, seq[t]]
    return np.where(seq >= N, 0, seq)


def agrees(reads, seq):
    """Per second: True where the reads are within a digit's slip of the fitted clock, None where nothing was read."""
    return [None if o is None else bool(o[c] <= 0.2) for o, c in zip(observations(reads), seq)]


def runs(seq):
    """Split the fitted clock where it jumps up after running out, or by MIN_PERIOD or more (a smaller jump up is
    the operator correcting it). Each run: (first second, last second)."""
    cut = [0] + [t for t in range(1, len(seq)) if seq[t] > seq[t - 1] and (seq[t - 1] <= 1 or seq[t] - seq[t - 1] >= MIN_PERIOD)]
    return [(a, b - 1) for a, b in zip(cut, cut[1:] + [len(seq)])]


def knots(seq, a, b):
    """[[t, c], ...] at a, b and wherever the clock changes between running, stopped and jumping."""
    def kind(t):
        d = seq[t - 1] - seq[t]
        return "run" if d == 1 else "stop" if d == 0 else "jump"
    out = [[a, int(seq[a])]]
    for t in range(a + 1, b + 1):
        if kind(t) == "jump" or (t + 1 <= b and kind(t + 1) != kind(t)):
            out.append([t, int(seq[t])])
    if out[-1][0] != b:
        out.append([b, int(seq[b])])
    return out


def periods_of(seq, reads):
    ag = agrees(reads, seq)
    out, rs = [], []
    for a, b in runs(seq):
        top = int(seq[a:b + 1].max())
        i = a + int(np.argmax(seq[a:b + 1]))
        r = PERIOD if PERIOD <= top <= PERIOD + 30 else top   # 18:00 (the fit can start a little above it)
        while i < b and seq[i + 1] >= r:           # the last second at the starting value
            i += 1
        zero = [t for t in range(i, b + 1) if seq[t] == 0]
        end = zero[0] if zero else b
        if zero:   # the fit's 0 covers 00.9 to 00.0: the end is the board's first 00.0, if it is read within 2 s
            end = next((t for t in range(max(i, end - 2), min(end + 3, b + 1))
                        if any(digits(rs[t][0]) in ("00", "000") for rs in reads.values())), end)
        kind = "period" if top >= MIN_PERIOD and seq[i] - seq[end] >= 120 else "other"
        rs.append(dict(start=a, end=b, top=top, kind=kind))
        if kind == "period":
            s = [x for x in ag[i:end + 1] if x is not None]
            out.append(dict(label=f"P{len(out) + 1}", start=int(i), end=int(end), **{"from": top},
                            ran_out=bool(zero), knots=knots(seq, i, end), agree=round(sum(s) / max(1, len(s)), 2)))
    return out, rs


def video_t(clk, label, clock_s):
    """The first video second at which period `label`'s clock showed clock_s or less (a goal stops the clock at its
    time; where the clock runs through stoppages this is the moment of play too). The sheet's time can sit a few
    seconds under where the board stopped for it (10:26 on Blue Wings' Oct 18 sheet, the board stopped at 10:30), and
    the clock passes it only after the faceoff: so where the clock stopped LONG_STOP s or more up to SHEET_TOL s above
    clock_s, and never at clock_s itself, the moment is that stop's first second."""
    P = next((P for P in clk["periods"] if P["label"] == label), None)
    if P is None:
        return None
    ks = P["knots"]
    stops = [(t0, c0) for (t0, c0), (t1, c1) in zip(ks, ks[1:]) if c0 == c1 and t1 - t0 >= LONG_STOP]
    above = [t for t, c in stops if 0 < c - clock_s <= SHEET_TOL]
    if above and not any(clock_s - 1 <= c <= clock_s for _, c in stops):
        return above[-1]
    for (t0, c0), (t1, c1) in zip(ks, ks[1:]):
        if c1 <= clock_s:
            if c0 <= clock_s:
                return t0
            return int(t0 + (c0 - clock_s)) if t1 - t0 == c0 - c1 else t1
    return ks[-1][0]


def load(W):
    p = f"{W}/clock.json"
    return json.load(open(p)) if os.path.exists(p) else None


def run(W, a=None):
    """Read (cached in W/clock_reads.json), fit, write W/clock.json and W/clock_check.jpg; returns clock.json's dict."""
    R = rink(f"{W}/full")
    cache = f"{W}/clock_reads.json"
    c = json.load(open(cache)) if os.path.exists(cache) else None
    if not c or (c.get("reader"), c.get("box"), c.get("tilt")) != (READER, list(R.clock_box), R.clock_tilt):
        reads, off = read_all(W, a)
        c = dict(reader=READER, box=list(R.clock_box), tilt=R.clock_tilt, offset=[int(x) for x in off], reads=reads)
        json.dump(c, open(cache, "w"))
    seq = fit(c["reads"])
    ps, rs = periods_of(seq, c["reads"])
    out = dict(offset=c["offset"], periods=ps, runs=rs)
    json.dump(out, open(f"{W}/clock.json", "w"))
    from scoreboard import sheet
    ts = [t for P in ps for e in (P["start"], P["end"]) for t in (e - 1, e, e + 1)]
    if ts:
        sheet(W, f"{W}/clock_check.jpg", ts, cols=6)
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("W"); ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    W = os.path.abspath(a.W)
    out = run(W)
    tm = lambda t: f"{t // 60}:{t % 60:02d}"
    for P in out["periods"]:
        print(f"{P['label']} {P['start']}-{P['end']} ({tm(P['start'])}-{tm(P['end'])} of video), clock from "
              f"{tm(P['from'])}{'' if P['ran_out'] else ', never reached 0.0'}; reads agreeing {P['agree']:.0%}")
    print(f"offset {out['offset']}; check {W}/clock_check.jpg (each row: a period's start and end, 1 s apart)")
    if len(out["periods"]) != 3:
        print(f"{len(out['periods'])} periods on the clock, not 3: take them from sb.jpg by eye")
    pj = f"{W}/periods.json"
    old = json.load(open(pj)) if os.path.exists(pj) else []
    if a.write:
        by = {P["label"]: P for P in old}
        new = []
        for P in out["periods"]:
            q = dict(by.get(P["label"]) or dict(label=P["label"], net=None, pk=[]))
            q.update(start=P["start"], end=P["end"])
            new.append(q)
        json.dump(new, open(pj, "w"), indent=1)
        print(f"wrote {pj}" + ("; set each period's net" if any(q["net"] is None for q in new) else ""))
    elif old:
        diff = [(P["label"], P["start"], P["end"], Q["start"], Q["end"]) for P, Q in zip(old, out["periods"])
                if (P["start"], P["end"]) != (Q["start"], Q["end"])]
        if diff or len(old) != len(out["periods"]):
            print("periods.json differs:", ", ".join(f"{l} {a_}-{b_} (clock {c_}-{d_})" for l, a_, b_, c_, d_ in diff)
                  + (f"; {len(old)} periods there, {len(out['periods'])} on the clock" if len(old) != len(out["periods"]) else ""))


if __name__ == "__main__":
    main()
