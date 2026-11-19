"""clip.py FULLDIR VIDEO AUDIO OUT.mp4 T0 T1 [POSTER_T [FOCUS [NET [REPLAY_FROM [SHOT [PASS]]]]]]
Cut a zoomed highlight clip: a virtual camera follows the main cluster of players (from FULLDIR/dets.csv),
crops the 4K wide cut to 16:9 and encodes 1280x720 H.264 with the game audio. Writes OUT.jpg as a poster
frame (at POSTER_T, default the middle of the clip). FOCUS keeps the camera on part of the rink when players are
spread out: a source x in px (rink.py nets, e.g. 540 = Renton's left net), or "track:TRACKS.csv:TID[,TID...]" to follow one player's track(s)
(e.g. the player who took a penalty), "group:TRACKS.csv:TID,TID;TID;..." to keep several players in the frame
(one ;-separated list of tracks per player in priority order, the scorer first, then the assists), or "-" for none. NET "X,Y" (the
scoring net, Y a fallback for its height) makes it a goal clip: the camera closes in on that net around POSTER_T,
the goal (`goal_path`), and the clip ends with a zoomed half-speed replay of the goal, from REPLAY_FROM seconds
before it ("-" for the default: 4, or from 1.5 s before SHOT). SHOT "T,X,Y" is when the puck left the scorer's
stick and where his skates were: the camera then follows the play through the shot (`goal_path`); "-" for none.
PASS "T,X,Y" is the same for the pass that set it up: the passer (FOCUS's second player) stays in the frame until
it, and the replay starts PASS_LEAD (2 s) before it. The audio is left out when the recording's audio is silent.
A TRACKS.csv can also be a skater's positions traced by hand (columns t, x, y), which become track 0 (`read_tracks`).

Every cut first computes the camera's path and checks it (`check`): the warnings are printed and saved with the
clip's times in FULLDIR/../clips_check.json. --dry-run stops there, with a summary of the path (`summary`), and
needs neither the video nor the audio. `contact_sheet` tiles a rendered clip (run_game.py clips, clipsheet)."""
import json, os, sys, subprocess
import numpy as np, pandas as pd, cv2, imageio_ffmpeg
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from track import load
from rink import rink

FF = imageio_ffmpeg.get_ffmpeg_exe()
OUT_W, OUT_H = 1280, 720
MIN_W, MAX_W = 900, 2800           # crop width range in source pixels
FEET_AT = 0.56                       # players' skates sit this far down the frame
NET_W, NET_HI = 0.27, 0.30          # crop width at the net, as shares of the frame's (~1040 to 1150 of 3840 px)
LOCK = (-6.0, 2.0)                   # seconds around the goal that the scoring net is in the frame
# a goal clip ends with the seconds around the goal again at half speed, zoomed in on the net, the slot and the
# scorer where he fits (~580 to 960 of 3840 px): a scramble at the far net is a few dozen pixels tall at any crop the
# live camera can hold
REPLAY, REPLAY_ZOOM = (-4.0, 1.5), (0.15, 0.25)
BEHIND = 0.04                        # ice kept behind the net (share of the frame's width), so it is never at the edge
# before the shot the net joins the scorer only while both fit this crop width: LADA R's Nov 2 empty-netter, a rush
# from our blue line, kept the empty net and Bekker together in a 2000+ px frame from center ice, both specks, and
# looked like a cut to the net too early (TK's Oct 25 empty-netter, poked in from about 1000 px out, still fits)
LEAD_W = 1300                        # the width used when following one player
# with a pass (`--pass`) the passer stays in the frame until PASS_HOLD s after it, and the replay starts PASS_LEAD s
# before it: the camera path is smoothed over about 1 s either way, so at 0.5 and 1 s the replay of LADA Y's Nov 2
# 6th goal had left Lisitsyn's corner battle 0.4 s after his last touch, with him at the frame's bottom edge until then
PASS_HOLD, PASS_LEAD = 1.0, 2.0
TRACE_SNAP = 120                     # a hand-traced skater snaps to a detection this close (BT's Nov 7 1st goal)

# The self-checks on a goal clip's path (`check`), in one place
IN_EDGE = 0.25       # in the frame: skates this many body heights inside the crop's sides, the body's middle inside
                     # its top and bottom (a skater half out at the edge reads as gone on a phone)
# the scorer's track is his at the shot within this of the --shot spot: run_game's at_spot takes a track within 200 px
# up to 0.5 s from the shot, and he moves meanwhile (the Doofers' Nov 15 4th goal, accepted: 203 px). The wrong track
# on their 5th goal (#71's, which the user caught) was 302 px off
SPOT_PX = 250
NO_TRACK_S = 0.5     # a player is tracked at a moment with a box this close to it: goal_path holds him that long
# the camera on the net before the play: frames before the shot that keep the net but not the scorer, while the play
# (the scorer, else the main group) is out of the crop and the crop holds at most EMPTY_N detections (the goalie and
# one more: the empty-looking net the user saw). The three rushes the user caught (LADA R's Nov 2 empty-netter, LADA Y's
# Nov 2 4th goal, Beerteam's Nov 7 1st) had 3.0-4.2 s of it; 6 of the 87 goal clips the user accepted from the 14
# games to Nov 15 reach 2.5 s, and their sheets show the same early switch, unreported. Without the near-empty test
# 15 accepted clips fired, mostly a play at the net with the scorer just outside the crop
EARLY_NET_S, EMPTY_N = 2.5, 2
# the goal time is to the second, so a shot up to 1 s after it fits (two accepted shots were 0.25 and 0.5 s after)
SHOT_LATE_S = 1.0
# the accepted shots of the 14 games were up to 5.75 s before the goal (LADA R's Oct 26 opener: the drive that
# started the pile), and Belousenko's on TK's Oct 25 7 s (a scramble after it); much longer is another play
SHOT_LONG_S = 8.0
PASS_LONG_S = 8.0    # a pass this long before the shot is another play (the accepted ones: 0.5-5.3 s)
REPLAY_LEAD_S = 0.5  # the replay starts at least this long before the shot and the pass, and ends this long after the
                     # goal second (its defaults: 1.5 s before the shot, 2 s before the pass, 1.5 s after the goal)

_DETS = {}


def _dets(full):
    """dets.csv as track.load gives it, read once per run (2-3 s each, and a goal clip reads it up to five times).
    The callers only filter it, never change it in place."""
    if full not in _DETS:
        _DETS[full] = load(f"{full}/dets.csv")
    return _DETS[full]


def camera_path(full, t0, t1, focus=None, max_w=MAX_W):
    """Per detection frame (8 fps): crop centre x/y and width (at most max_w), smoothed."""
    d = _dets(full)
    d = d[(d.t >= t0 - 3) & (d.t <= t1 + 3) & (d.conf >= 0.3)]
    d = d[d.onice]
    grid = np.arange(0, 3840, 20)
    rows = []
    for t, g in d.groupby("t"):
        xs, ys, hs = g.fx.values, g.fy.values, g.h.values
        dens = np.exp(-((grid[:, None] - xs[None, :]) / 350.0) ** 2).sum(1)
        fx = focus(t) if callable(focus) else focus
        if callable(focus) and fx is not None:
            peak = fx                     # follow mode: the camera is on this player
        else:
            if fx is not None:
                dens = dens * np.exp(-((grid - fx) / 900.0) ** 2)
            peak = grid[dens.argmax()]
        m = np.abs(xs - peak) < 650
        if m.sum() < 2:
            m = np.ones(len(xs), bool)
        spread = np.quantile(xs[m], 0.8) - np.quantile(xs[m], 0.2)
        # zoom to the core of the play, wider for near-camera players (they look bigger)
        w = np.clip(1.15 * spread + 6 * np.median(hs[m]), MIN_W, max_w)
        feet = np.median(ys[m])
        if callable(focus) and fx is not None:
            near = np.abs(xs - fx) < 250
            feet = np.median(ys[near]) if near.any() else feet
            rows.append((t, fx, feet, max(w, 1300)))
        else:
            rows.append((t, np.median(xs[m]) * 0.5 + peak * 0.5, feet, w))
    P = pd.DataFrame(rows, columns=["t", "cx", "cy", "w"]).set_index("t").sort_index()
    k = 7 if callable(focus) else 15      # follow mode reacts faster
    P["cx"] = P.cx.rolling(k, center=True, min_periods=1).mean()
    P["cy"] = P.cy.rolling(k, center=True, min_periods=1).mean()  # median skate height of the cluster
    P["w"] = P.w.rolling(25, center=True, min_periods=1).mean()
    return P


def goal_path(full, P, t0, t1, tg, net, players, frame_w, max_w, zoom=(NET_W, NET_HI), lock=LOCK, shot=None,
              keep_w=None, pas=None, trace=None):
    """A goal clip's camera. It frames everyone credited with the goal (`players`: a track table per player,
    scorer first, empty where untracked) whenever one of them is tracked, and from 6 s before the goal (tg) to 2 s
    after, the scoring net (`net`, x and y) and the slot in front of it too; where neither applies, the main group
    (P, from camera_path). Following the main group alone missed TK's Oct 25 scorers: on Belousenko's goal it sat
    on the scramble at the net and the corner behind it, and he shot from the slot just outside the frame's edge.
    At the net the crop is `zoom` (smallest and largest width, as shares of the frame's), and a player who doesn't
    fit drops out, passers first and the one who widens the crop most first (a passer near the camera costs
    height: on BW's Oct 25 opener Zhuk at the near point kept with the far net made the crop wider than following
    the group did), the scorer last; away from the net the limit is max_w. Some ice behind the net is always in,
    so a mislabeled track can't pull the net to the frame's edge (it did on that opener's replay). The net's skate
    line comes from the detections standing at it (the goalie), so a camera framed a little differently that day
    still lands on it; the given y is the fallback.
    `shot` (time, x, y: the shooter's skates as the puck left his stick, from the goal check) puts the play first:
    the scorer up to the shot, then the puck on a straight line to the net, with the net and the scorer kept while
    they fit `keep_w` (default max_w: both in one wide frame; the replay passes its tight width, so it stays close
    on the scorer and pans with the puck onto the net) and passers while they fit the tight crop. Without it TK's
    Oct 25 empty-netter, poked in from their blue line on the far boards, was 6 s of an empty net with the scorer
    dropped from the tight frame.
    `pas` (time, x, y: the passer's skates as the puck left his stick) keeps the passers in up to max_w until
    PASS_HOLD (1 s) after the pass, ahead of the net (at the pass spot itself for the PASS_LEAD s before it where his track is
    lost). The tight crop dropped LADA Y's passers on Nov 2 vs Best Vibes: Akulov at the point and Lisitsyn
    feeding from the half-wall were out of the frame when they passed, and out of the replay altogether.
    `trace` (a dict) gets what the checks need: the net's spot and the walked paths, and per frame which players
    and whether the net the frame kept (`check`)."""
    if net:
        nx, ny = net
        d = _dets(full)
        d = d[(d.t >= t0) & (d.t <= t1) & (d.conf >= 0.3) & d.onice & ((d.fx - nx).abs() < 90)]
        ny, nh = (float(d.fy.median()), float(d.h.median())) if len(d) >= 20 else (ny, 80.0)
        side = 1 if nx < frame_w / 2 else -1
        slot = nx + side * 0.35 * zoom[0] * frame_w      # the net a third of the way in
        behind = nx - side * BEHIND * frame_w
    if shot:
        ts, sx, sy = shot
        lock = (min(lock[0], ts - tg - 1), lock[1])
    if pas:
        # the passer's size at the pass from whoever stands there (where his track is lost): the goalie's height
        # put Lisitsyn, nearer the camera on the 3rd goal of LADA Y's Nov 2 game, half out of the frame's bottom
        dp = _dets(full)
        dp = dp[((dp.t - pas[0]).abs() <= 0.5) & (dp.conf >= 0.3) & ((dp.fx - pas[1]).abs() < 150)
                & ((dp.fy - pas[2]).abs() < 150)]
        ph = float(dp.h.median()) if len(dp) else (nh if net else 80.0)
        carrier = carrier_path(full, pas, shot, nh if net else 80.0) if shot else None
        passer = walk_back(full, pas[0] - PASS_LEAD - 1.0, pas, ph, False)
    keep_w = keep_w or max_w
    if trace is not None:
        trace.update(net=(nx, ny, nh) if net else None, lock=lock, frames=[],
                     carrier=carrier if pas else None, passer=passer if pas else None, pass_h=ph if pas else None)

    def box(S):
        left = min(x - h for x, y, h, _ in S); right = max(x + h for x, y, h, _ in S)
        top = min(y - 1.3 * h for x, y, h, _ in S); bottom = max(y + 0.3 * h for x, y, h, _ in S)
        return max(right - left, (bottom - top) * OUT_W / OUT_H), left, right, top, bottom

    rows = []
    for t in P.index:
        pts = []                          # (x, y, h, player index: 0 = scorer)
        for i, p in enumerate(players):
            if not len(p):
                continue
            j = np.abs(p.index.values - t).argmin()
            if abs(p.index[j] - t) <= 0.5:
                pts.append((p.fx.iat[j], p.fy.iat[j], p.h.iat[j], i))
        passing = pas is not None and t <= pas[0] + PASS_HOLD
        # from a second before the replay starts, so the smoothing doesn't open it on the frame without him
        if passing and pas[0] - PASS_LEAD - 1.0 <= t and not any(q[3] == 1 for q in pts):
            # an untracked passer: walked back from the pass along the detections, then the pass spot
            pts.append(tuple(float(np.interp(t, passer.index.values, passer[c].values)) for c in ("fx", "fy", "h"))
                       + (1,) if t <= pas[0] and len(passer) > 1 else (pas[1], pas[2], ph, 1))
        if pas and shot and pas[0] < t < shot[0] and not any(q[3] == 0 for q in pts):
            # an untracked scorer (theirs, always: tracks_v1 holds only ours) is the puck carrier between the pass
            # and the shot (`carrier_path`); with nobody to follow, the camera of Best Vibes' breakaway on LADA Y's
            # Nov 2 game sat on our empty-looking net while their #49 skated the length of the ice
            pts.append(tuple(float(np.interp(t, carrier.index.values, carrier[c].values)) for c in ("fx", "fy", "h"))
                       + (0,))
        at_net = net is not None and tg + lock[0] <= t <= tg + lock[1]
        if not pts and not at_net:
            rows.append((t, np.nan, np.nan, np.nan))
            if trace is not None:
                trace["frames"].append((t, None, False, False, None))   # the main group's camera (P)
            continue
        # what the frame keeps, most important first: groups of units (a player, or the net with the ice behind it
        # and the slot, which come and go together), each group with the widest crop it may cost
        scorer = [(q,) for q in pts if q[3] == 0]
        # a passer being held gets room around him: two heights of ice to each side and 0.6 below his skates (points
        # that only move the crop's edges). With the usual one height and 0.3 the crop that also held the net had
        # Lisitsyn's corner battles (LADA Y's Nov 2 game, the 3rd and 6th goals) on its bottom and right edges
        passers = [(q, (q[0] - 2 * q[2], q[1] + 0.6 * q[2], 1.0, q[3]), (q[0] + 2 * q[2], q[1] + 0.6 * q[2], 1.0, q[3]))
                   if passing else (q,) for q in pts if q[3] > 0]
        if at_net:
            fixed = ((behind, ny, nh, -1), (nx, ny, nh, -1), (slot, ny, nh, -1))
            ax, ay, lo, hi = nx, ny, zoom[0] * frame_w, min(zoom[1] * frame_w, max_w)
            if not shot:
                groups = [([fixed], np.inf), (scorer, max_w if passing else hi), (passers, max_w if passing else hi)]
            elif t < ts:
                lead = scorer or ([((sx, sy, nh, 0),)] if t >= ts - 1.5 else [])
                groups = ([(lead, np.inf), (passers, max_w), ([fixed], min(keep_w, LEAD_W))] if passing else
                          [(lead, np.inf), ([fixed], min(keep_w, LEAD_W)), (passers, hi)])
            elif t <= tg:
                f = (t - ts) / max(tg - ts, 0.1)
                puck = (sx + f * (nx - sx), sy + f * (ny - sy), nh, -1)
                groups = [([(puck,)], np.inf), ([fixed], keep_w), (scorer, keep_w), (passers, hi)]
            else:
                groups = [([fixed], np.inf), (scorer, keep_w), (passers, hi)]
        else:
            a = min(pts, key=lambda q: q[3])
            ax, ay, lo = a[0], a[1], min(1300, max_w)   # 1300: as following one player
            groups = [([(a,)], np.inf), ([(q,) for q in pts if q is not a], max_w)]
        if shot and groups[0][0]:
            ax, ay = groups[0][0][0][0][:2]      # the play: the scorer or the puck
        # drop the least important first, in a group the one who widens the crop most first, while the crop is
        # wider than that group may make it and leaving him out narrows it (again until nothing changes: one
        # between two others narrows nothing until one of them is gone)
        flat = lambda S: [q for u in S for q in u]
        far = lambda u: -max(max(abs(x - ax), abs(y - ay) * OUT_W / OUT_H) for x, y, h, _ in u)
        S, n = [u for g, _ in groups for u in g], -1
        while n != len(S):
            n = len(S)
            for g, cap in reversed(groups):
                for u in sorted(g, key=far):
                    rest = [k for k in S if k is not u]
                    if len(rest) < len(S) and rest and box(flat(S))[0] > cap and box(flat(rest))[0] < box(flat(S))[0]:
                        S = rest
        w, left, right, top, bottom = box(flat(S))
        if trace is not None:   # (t, the players kept, the net kept, at the net, the scorer's point if he has one)
            trace["frames"].append((t, {q[3] for q in flat(S) if q[3] >= 0},
                                    at_net and any(u is fixed for u in S), at_net,
                                    next((q[:3] for q in pts if q[3] == 0), None)))
        w = min(max(w, lo), max_w)
        # skates at FEET_AT of the crop's height puts its middle at the set's middle
        rows.append((t, (left + right) / 2, (top + bottom) / 2 + (FEET_AT - 0.5) * w * OUT_H / OUT_W, w))
    G = pd.DataFrame(rows, columns=["t", "cx", "cy", "w"]).set_index("t")
    Q = G.fillna(P)
    # two short moving averages: an eased move of about 2 s onto the net and back off it
    return Q.rolling(9, center=True, min_periods=1).mean().rolling(9, center=True, min_periods=1).mean()


def walk_back(full, t_from, end, sh, same_team):
    """Someone's skates from t_from to `end` (T, X, Y) along the detections, walked back from `end`: each frame to
    the nearest detection a skater of that size can reach, stopping where the walk breaks off. `same_team` keeps to
    the team (`ours`) of the detection at `end`; in a pile the jersey test isn't worth that (Lisitsyn's corner battle
    before the 3rd goal of LADA Y's Nov 2 game read as theirs)."""
    d = _dets(full)
    d = d[(d.t >= t_from - 0.2) & (d.t <= end[0] + 0.2) & (d.conf >= 0.3) & d.onice]
    at = d[(d.t - end[0]).abs() <= 0.15]
    dist = np.hypot(at.fx - end[1], at.fy - end[2])
    if len(at) and dist.min() < 150:
        k = dist.values.argmin()
        x, y, h = at.fx.iat[k], at.fy.iat[k], at.h.iat[k]
        if same_team:
            d = d[d.ours.astype(bool) == bool(at.ours.iat[k])]
    else:
        x, y, h, d = end[1], end[2], sh, d.iloc[:0]
    rows, miss = [(end[0], x, y, h)], 0
    for t in sorted(d.t.unique(), reverse=True):
        if not t_from < t < end[0]:
            continue
        g = d[d.t == t]
        dist = np.hypot(g.fx - x, g.fy - y).values
        # about 2.5 body heights a second (8 frames), more across a gap
        if len(g) and dist.min() < max(80.0, 0.8 * h) * (1 + miss):
            k = dist.argmin()
            x, y, h, miss = g.fx.iat[k], g.fy.iat[k], g.h.iat[k], 0
            rows.append((t, x, y, h))
        elif (miss := miss + 1) > 4:
            break
    return pd.DataFrame(rows, columns=["t", "fx", "fy", "h"]).set_index("t").sort_index()


def carrier_path(full, pas, shot, sh):
    """The puck carrier's skates from the pass to the shot (each T, X, Y) for a scorer with no track: walked back
    from the shot along the detections of the shooter's team, with a straight line to the pass where the walk breaks
    off. A straight line alone missed Best Vibes' #49 on LADA Y's Nov 2 game by 300 px: he cut across close to the
    camera (250 to 400 px tall) and was at our crease 1.5 s before he shot."""
    w = walk_back(full, pas[0], shot, sh, True)
    return pd.concat([pd.DataFrame([(pas[1], pas[2], w.h.iat[0])], columns=["fx", "fy", "h"], index=[pas[0]]), w])


def player_path(tr, tids, anchor=None):
    """One player's skates per detection frame from his tracks in priority order (where two cover the same moment
    the first counts), leaving out a track that would make him jump farther than a skater gets: on TK's Oct 25
    empty-netter a figure on our bench labeled with the scorer's number took over 2 s after the goal, 2000 px from
    him, and the camera swung to the bench. The walk starts at `anchor`, the shot, where the goal check saw him;
    without one there is no telling which of two far-apart tracks is him (BW's Oct 25 5th goal had a read #54 at
    one end and another #54 at the other), so all of them stand."""
    drop = set()
    while True:
        parts = [tr[tr.tid == x] for x in tids if x not in drop]
        if not parts:
            return tr.iloc[:0].groupby("t")[["fx", "fy", "h"]].first()
        p = pd.concat(parts).groupby("t")[["fx", "fy", "h", "tid"]].first()
        if anchor is None:
            return p[["fx", "fy", "h"]]
        t, x, y, k = p.index.values, p.fx.values, p.fy.values, p.tid.values
        # start on the first track (the one at the shot or pass) when it is there within 1 s: on the Doofers' Nov 15
        # 5th goal Babkin's track had no box at the shot's frame, Fedotov's (in the group by a later #26 piece) had
        # one 300 px away, the walk started on him and dropped Babkin, and the clip followed Fedotov
        d = np.abs(t - anchor)
        first = k == next(x for x in tids if x not in drop)
        i0 = int(np.where(first, d, np.inf).argmin()) if (first & (d <= 1)).any() else int(d.argmin())
        bad = None
        for order in (range(i0, len(p)), range(i0, -1, -1)):
            last = i0
            for i in order:
                if np.hypot(x[i] - x[last], y[i] - y[last]) > 200 + 700 * abs(t[i] - t[last]):
                    bad = k[i]
                    break
                last = i
            if bad is not None:
                break
        if bad is None or bad == k[i0]:
            return p[["fx", "fy", "h"]]
        drop.add(bad)




def read_tracks(full, path):
    """A tracks file (tracks_v1.csv's columns), or a skater's skates traced by hand (columns t, x, y; a row every
    0.5 s or so) for one the tracker lost, which becomes track 0. Beerteam's Nov 7 1st goal needed one: Lee #71
    chased the puck the length of the near boards at up to 1800 px/s, and neither his tracks nor the walk back from
    the shot kept up. Every detection frame from the trace's first row to its last gets the traced line's point,
    moved to the nearest detection within TRACE_SNAP px (with its height): player_path drops a track that moves
    more than 200 + 700·dt px between two samples, so every frame is sampled."""
    tr = pd.read_csv(path)
    if "tid" in tr:
        return tr
    tr = tr.rename(columns={"fx": "x", "fy": "y"}).sort_values("t")
    d = _dets(full)
    d = d[(d.t >= tr.t.min()) & (d.t <= tr.t.max()) & (d.conf >= 0.3) & d.onice]
    rows = []
    for t, g in d.groupby("t"):
        x, y = np.interp(t, tr.t, tr.x), np.interp(t, tr.t, tr.y)
        dist = np.hypot(g.fx - x, g.fy - y).values
        k = int(dist.argmin())
        rows.append((t, 0, g.fx.iat[k], g.fy.iat[k], g.h.iat[k]) if dist[k] < TRACE_SNAP else (t, 0, x, y, np.nan))
    out = pd.DataFrame(rows, columns=["t", "tid", "fx", "fy", "h"])
    return out.assign(h=out.h.fillna(out.h.median()).fillna(120.0))


def _silent(audio, t0, t1):
    r = subprocess.run([FF, "-nostdin", "-loglevel", "error", "-ss", str(t0), "-t", str(t1 - t0), "-i", audio,
                        "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True)
    return not np.frombuffer(r.stdout, np.int16).any()


def plan(argv, size):
    """Everything a cut decides before it reads a frame, from clip.py's arguments (argv as sys.argv) and the
    video's frame size (W, H): the live camera's path P, the replay's path R and window, and what the checks need.
    Only the size comes from the video, and fetch scales every video to its rink's (rink.py), so a dry run takes
    that when the video is gone."""
    full = argv[1]
    t0, t1 = float(argv[5]), float(argv[6])
    tp = float(argv[7]) if len(argv) > 7 else (t0 + t1) / 2
    focus, players = None, []
    if len(argv) > 8:
        if argv[8].startswith("group:"):
            path, tids = argv[8][len("group:"):].rsplit(":", 1)
            tr = read_tracks(full, path)
            tr = tr[(tr.t >= t0 - 3) & (tr.t <= t1 + 3)]
            # each player's tracks in priority order: where two cover the same moment, the first one counts
            # the walk along each player's tracks starts where the goal check saw him: the scorer at the shot,
            # the passer at the pass
            anchors = [float(argv[k].split(",")[0]) if len(argv) > k and argv[k] != "-" else None
                       for k in (11, 12)]
            players = [player_path(tr, [int(x) for x in g.split(",") if x], anchors[i] if i < 2 else None)
                       for i, g in enumerate(tids.split(";"))]
        elif argv[8].startswith("track:"):
            path, tids = argv[8][len("track:"):].rsplit(":", 1)   # the path may hold a drive colon (C:\...)
            tr = read_tracks(full, path)
            parts = [tr[tr.tid == int(x)].groupby("t").fx.first().sort_index() for x in tids.split(",")]

            def focus(t):
                # tracks in priority order: use the first one that covers time t
                for p in parts:
                    if len(p) and p.index.min() - 0.5 <= t <= p.index.max() + 0.5:
                        return float(np.interp(t, p.index, p.values))
                return None
        elif argv[8] != "-":
            focus = float(argv[8])
    W, H = size
    max_w = min(MAX_W, H * OUT_W / OUT_H)            # a 16:9 crop must fit the frame
    P0 = camera_path(full, t0, t1, focus, max_w)
    net = tuple(float(v) for v in argv[9].split(",")) if len(argv) > 9 else None
    shot = tuple(float(v) for v in argv[11].split(",")) if len(argv) > 11 and argv[11] != "-" else None
    pas = tuple(float(v) for v in argv[12].split(",")) if len(argv) > 12 else None
    if len(argv) > 10 and argv[10] != "-":
        replay = (-float(argv[10]), REPLAY[1])
    else:
        replay = (min(REPLAY[0], shot[0] - tp - 1.5), REPLAY[1]) if shot else REPLAY
        if pas:
            replay = (min(replay[0], pas[0] - tp - PASS_LEAD), replay[1])
    trace = {}
    P = goal_path(full, P0, t0, t1, tp, net, players, W, max_w, shot=shot, pas=pas, trace=trace) if net or players else P0
    R = None
    if net:
        # the net and the scorer, the net in the frame for the whole replay; with a pass, the passer until it (after
        # it he only widened the close-up at the net)
        rp = players[:1] + ([players[1][players[1].index <= pas[0] + PASS_HOLD]] if pas and len(players) > 1 else [])
        R = goal_path(full, P0, t0, t1, tp, net, rp, W, max_w, REPLAY_ZOOM,
                      (min(replay[0], LOCK[0]), LOCK[1]), shot, REPLAY_ZOOM[1] * W, pas)
    return dict(argv=argv, full=full, out=argv[4], name=os.path.splitext(os.path.basename(argv[4]))[0],
                t0=t0, t1=t1, tp=tp, focus=focus, players=players, net=net, shot=shot, pas=pas, replay=replay,
                ra=tp + replay[0], rb=tp + replay[1], W=W, H=H, max_w=max_w, P0=P0, P=P, R=R, trace=trace)


# ---------------------------------------------------------------- the checks on a path

def crop_at(pl, X, t):
    """The crop (x0, y0, w, h in source px) path X renders at time t, as render() places it."""
    cx, cy, w = (float(np.interp(t, X.index.values, X[c].values)) for c in ("cx", "cy", "w"))
    h = w * OUT_H / OUT_W
    return float(np.clip(cx - w / 2, 0, pl["W"] - w)), float(np.clip(cy - FEET_AT * h, 0, pl["H"] - h)), w, h


def inside(box, x, y, h):
    x0, y0, w, ch = box
    return x0 + IN_EDGE * h <= x <= x0 + w - IN_EDGE * h and y0 <= y - h / 2 <= y0 + ch


def off_by(box, x, y):
    """How far (px) a point is outside a crop, 0 inside."""
    x0, y0, w, ch = box
    return float(np.hypot(max(x0 - x, 0, x - x0 - w), max(y0 - y, 0, y - y0 - ch)))


def at(p, t, gap=NO_TRACK_S):
    """A player's (x, y, h) at t from his path, as goal_path takes it, or None without a box within gap."""
    if p is None or not len(p):
        return None
    j = int(np.abs(p.index.values - t).argmin())
    return (float(p.fx.iat[j]), float(p.fy.iat[j]), float(p.h.iat[j])) if abs(p.index[j] - t) <= gap else None


def clip_s(pl, t, replay=False):
    """Seconds into the rendered clip of video time t: the live part, or the replay after it at half speed."""
    return round(t - pl["t0"] if not replay else pl["t1"] - pl["t0"] + 2 * (t - pl["ra"]), 2)


def check(pl):
    """Warnings on a goal clip from its camera path alone, each {"check", "t", "at" (clip s), "msg"}: what the user
    caught on the 14 games to Nov 15 where the path shows it. A goal or shot time off by seconds (the replay ends
    before the puck is in, or opens on the pile a drive started) doesn't show here; the contact sheet shows it."""
    if not pl["net"]:
        return []
    out = []

    def warn(code, t, msg, replay=False):
        out.append(dict(check=code, t=round(float(t), 2), at=clip_s(pl, t, replay), msg=msg))
    tg, shot, pas, ra, rb, tr = pl["tp"], pl["shot"], pl["pas"], pl["ra"], pl["rb"], pl["trace"]
    nx, ny, nh = tr["net"]
    sc = pl["players"][0] if pl["players"] else None
    ps = pl["players"][1] if len(pl["players"]) > 1 else None
    # the times given
    if shot and shot[0] > tg + SHOT_LATE_S:
        warn("shot-time", shot[0], f"the shot ({shot[0]:g}) is after the goal ({tg:g}): one of the two times is wrong")
    elif shot and tg - shot[0] > SHOT_LONG_S:
        warn("shot-time", shot[0], f"the shot is {tg - shot[0]:.1f} s before the goal: a shot that led to a scramble "
             "is fine (the replay runs from it), a goal time that is seconds early is not; sheet the crease")
    if shot and not pl["t0"] <= shot[0] <= pl["t1"]:
        warn("shot-time", shot[0], f"the shot ({shot[0]:g}) is outside the clip ({pl['t0']:g}-{pl['t1']:g})")
    if pas and shot and not 0 <= shot[0] - pas[0] <= PASS_LONG_S:
        warn("pass-time", pas[0], f"the pass ({pas[0]:g}) is {shot[0] - pas[0]:.1f} s before the shot ({shot[0]:g})")
    # the replay's window
    if shot and ra > shot[0] - REPLAY_LEAD_S:
        warn("replay-window", ra, f"the replay starts at {ra:g} and the shot is at {shot[0]:g}: give --replay-from "
             "back to before the shot", True)
    if pas and ra > pas[0] - REPLAY_LEAD_S:
        warn("replay-window", ra, f"the replay starts at {ra:g}, after the pass ({pas[0]:g})", True)
    if rb < tg + REPLAY_LEAD_S:
        warn("replay-window", rb, f"the replay ends at {rb:g}, before the goal second ({tg:g})", True)
    # the scorer's tracks: missing, or someone else's
    ts = shot[0] if shot else tg
    q = at(sc, ts)
    if sc is not None and not len(sc):
        warn("scorer-track", ts, "the scorer has no track in the clip: the camera follows the assists or the main "
             "group; give --shot at his spot (its track is taken whatever its label) or --tracks")
    elif sc is not None and q is None:
        near = float(np.abs(sc.index.values - ts).min())
        warn("scorer-track", ts, f"the scorer has no track at the {'shot' if shot else 'goal'} (the nearest box is "
             f"{near:.1f} s away): the camera follows someone else then; give --shot at his spot or --tracks")
    elif q and shot and np.hypot(q[0] - shot[1], q[1] - shot[2]) > SPOT_PX:   # the group follows someone else
        warn("scorer-track", ts, f"the scorer's track is {np.hypot(q[0] - shot[1], q[1] - shot[2]):.0f} px from the "
             "--shot spot at the shot: the group follows someone else (a track that carries his number but isn't "
             "him?); check the track on a crop, then --tracks")
    # the shooter at the shot, the net at the goal, the passer at the pass: in the live part and the replay
    shooter_h = q[2] if q and shot and np.hypot(q[0] - shot[1], q[1] - shot[2]) <= SPOT_PX else nh
    qp = at(ps, pas[0]) if pas else None
    passer = (qp if qp and np.hypot(qp[0] - pas[1], qp[1] - pas[2]) <= SPOT_PX else
              (pas[1], pas[2], tr["pass_h"])) if pas else None
    for X, replay in ((pl["P"], False), (pl["R"], True)):
        part = "the replay" if replay else "the live camera"
        shown = lambda t: not replay or ra <= t <= rb     # the replay only covers its window
        if shot and shown(ts) and not inside(crop_at(pl, X, ts), shot[1], shot[2], shooter_h):
            warn("shooter-out", ts, f"the shooter's spot is outside {part}'s frame at the shot "
                 f"({off_by(crop_at(pl, X, ts), shot[1], shot[2]):.0f} px off)", replay)
        if shown(tg) and not inside(crop_at(pl, X, tg), nx, ny, nh):
            warn("net-out", tg, f"the net is outside {part}'s frame at the goal second", replay)
        if pas and shown(pas[0]) and not inside(crop_at(pl, X, pas[0]), *passer):
            warn("passer-out", pas[0], f"the passer is outside {part}'s frame at the pass "
                 f"({off_by(crop_at(pl, X, pas[0]), passer[0], passer[1]):.0f} px off)", replay)
    # the camera on the net before the play is there. goal_path frames the net from tg + lock[0] (6 s before the
    # goal, or 1 s before an earlier shot). With --shot the scorer leads and the net joins only within LEAD_W; without
    # it the net leads and the scorer stays only within the close-up's width. So the net is framed without the scorer
    # where he has no point (untracked, or a goal against with no --pass for carrier_path; the shot spot leads only
    # from 1.5 s before the shot) or doesn't fit. That is wrong only while the play is elsewhere: where the scorer is
    # (his point; else walked back from the shot along his team's detections), else where the main group is (P0); and
    # it shows as wrong while the frame is all but empty (a goalie alone)
    lock = tr["lock"]
    early = [(t, pt) for t, kept, net_in, at_net, pt in tr["frames"] if at_net and t < ts and net_in and 0 not in kept]
    if early:
        walk = walk_back(pl["full"], tg + lock[0] - 1, shot, nh, True) if shot else None
        d = _dets(pl["full"])
        d = d[(d.t >= early[0][0] - 0.01) & (d.t <= early[-1][0] + 0.01) & (d.conf >= 0.3) & d.onice]
        byt = {t: g for t, g in d.groupby("t")}
        dt = float(np.median(np.diff(pl["P"].index.values))) if len(pl["P"]) > 1 else 0.125
        away = []
        for t, pt in early:
            if pt is None and walk is not None and len(walk) > 1 and walk.index.min() <= t:
                pt = tuple(float(np.interp(t, walk.index.values, walk[c].values)) for c in ("fx", "fy", "h"))
            who = "the scorer" if pt else "the main group"
            if pt is None:
                pt = (float(np.interp(t, pl["P0"].index.values, pl["P0"].cx.values)),
                      float(np.interp(t, pl["P0"].index.values, pl["P0"].cy.values)), nh)
            box = crop_at(pl, pl["P"], t)
            g = byt.get(t)
            n_in = 0 if g is None else sum(inside(box, x, y, h) for x, y, h in zip(g.fx, g.fy, g.h))
            if not inside(box, *pt) and n_in <= EMPTY_N:
                away.append((t, who, off_by(box, pt[0], pt[1])))
        if len(away) * dt >= EARLY_NET_S:
            a0, a1 = away[0][0], away[-1][0]
            whos = sorted({w for _, w, _ in away})
            fix = ("no --shot, so the net leads and the scorer stays only while he fits the close-up; give --shot (the "
                   "scorer then leads, and the net joins him only within 1300 px), and --pass or --tracks if he has no "
                   "track there" if not shot else
                   "the scorer has no point to follow there; give --pass at the pass or pickup that sprang the rush (the "
                   "carrier is then walked from it to the shot), or --tracks with the rusher's track or a hand trace")
            warn("early-net", a0, f"the camera shows the net all but empty for {len(away) * dt:.1f} s between {a0:g} "
                 f"and {a1:g} (the {'shot' if shot else 'goal'} {ts:g}), while {' / '.join(whos)} is up to "
                 f"{max(o for _, _, o in away):.0f} px out of the frame: {fix}")
    return out


def record(pl, warns, dry):
    """The clip's times, its marks in clip seconds and the warnings, into W/clips_check.json (W = FULLDIR/..),
    one entry per clip: run_game.py clips reads them for the contact sheets and the checker's brief."""
    marks = {"poster": [clip_s(pl, pl["tp"])]}
    if pl["net"]:
        marks = {k: [clip_s(pl, t), clip_s(pl, t, True) if pl["ra"] <= t <= pl["rb"] else None]
                 for k, t in (("goal", pl["tp"]), ("shot", (pl["shot"] or [None])[0]), ("pass", (pl["pas"] or [None])[0]))
                 if t is not None}
    rec = dict(args=pl["argv"][5:], dry_run=dry, t0=pl["t0"], t1=pl["t1"], poster=pl["tp"],
               net=list(pl["net"]) if pl["net"] else None, shot=list(pl["shot"]) if pl["shot"] else None,
               pas=list(pl["pas"]) if pl["pas"] else None, replay=[round(pl["ra"], 3), round(pl["rb"], 3)] if pl["net"] else None,
               live_s=pl["t1"] - pl["t0"], length_s=pl["t1"] - pl["t0"] + (2 * (pl["rb"] - pl["ra"]) if pl["net"] else 0),
               marks=marks, warnings=warns)
    p = os.path.join(os.path.dirname(os.path.abspath(pl["full"])), "clips_check.json")
    allc = json.load(open(p)) if os.path.exists(p) else {}
    allc[pl["name"]] = rec
    json.dump(allc, open(p, "w"), indent=1)
    return p


def summary(pl, warns):
    """The dry run's report: the crop's centre and width every 0.5 s around the shot and the goal, live and in the
    replay, with whether the scorer, the net and the passer are in it, and where the replay starts and ends."""
    f = lambda v: f"{v:g}"
    L = []
    if not pl["net"]:
        what = ("following a track" if callable(pl["focus"]) else f"weighted to x {pl['focus']:g}" if pl["focus"] is not None
                else "on the main group")
        L.append(f"{pl['name']}: {f(pl['t0'])}-{f(pl['t1'])} s, poster {f(pl['tp'])} (clip {clip_s(pl, pl['tp'])} s); camera {what}")
        L.append("       t   clip   centre      width")
        for t in np.arange(np.floor(pl["tp"] * 2) / 2 - 3, pl["tp"] + 2.01, 0.5):
            x0, y0, w, h = crop_at(pl, pl["P"], t)
            L.append(f"{t:8.2f} {clip_s(pl, t):6.2f}  {x0 + w / 2:5.0f},{y0 + FEET_AT * h:<5.0f} {w:5.0f}")
        return "\n".join(L)
    tg, shot, pas, ra, rb = pl["tp"], pl["shot"], pl["pas"], pl["ra"], pl["rb"]
    nx, ny, nh = pl["trace"]["net"]
    sc = pl["players"][0] if pl["players"] else None
    ps = pl["players"][1] if len(pl["players"]) > 1 else None
    why = ("--replay-from" if len(pl["argv"]) > 10 and pl["argv"][10] != "-" else
           f"{PASS_LEAD:g} s before the pass" if pas and abs(ra - (pas[0] - PASS_LEAD)) < 1e-6 else
           "1.5 s before the shot" if shot and abs(ra - (shot[0] - 1.5)) < 1e-6 else f"{-REPLAY[0]:g} s before the goal")
    L.append(f"{pl['name']}: live {f(pl['t0'])}-{f(pl['t1'])} s (clip 0-{clip_s(pl, pl['t1'])} s), goal {f(tg)} at the net at x {nx:.0f}"
             + (f", shot {f(shot[0])} at {shot[1]:.0f},{shot[2]:.0f}" if shot else ", no --shot")
             + (f", pass {f(pas[0])} at {pas[1]:.0f},{pas[2]:.0f}" if pas else "")
             + f"; {len(pl['players'])} credited player(s) tracked" * bool(pl["players"]))
    L.append(f"  replay {ra:g}-{rb:g} s ({why}; clip {clip_s(pl, ra, True)}-{clip_s(pl, rb, True)} s at half speed)")
    first = next((t for t, kept, net_in, *_ in pl["trace"]["frames"] if net_in), None)
    if first is not None:
        L.append(f"  the live camera takes in the net from {first:g} (clip {clip_s(pl, first)} s)")
    marks = {}
    for t, label in ((tg, "goal"), (ra, "replay starts"), (rb, "replay ends"), (shot and shot[0], "shot"),
                     (pas and pas[0], "pass")):
        if t:
            marks.setdefault(round(float(t), 3), []).append(label)
    lo = min([ra, tg] + ([shot[0] - 2.5] if shot else [tg - 2.5]))
    times = sorted(set(np.round(np.arange(np.ceil(lo * 2) / 2, tg + 1.51, 0.5), 3)) | set(marks))

    def cell(X, t, replay):
        if replay and not ra - 1e-6 <= t <= rb + 1e-6:
            return " " * 33
        box = crop_at(pl, X, t)
        s = at(sc, t) or ((shot[1], shot[2], nh) if shot and abs(t - shot[0]) < 0.13 else None)
        p = at(ps, t) or ((pas[1], pas[2], nh) if pas and abs(t - pas[0]) < 0.13 else None)
        yn = lambda q: " - " if q is None else (" in" if inside(box, *q) else "OUT")
        return (f"{clip_s(pl, t, replay):6.2f} {box[0] + box[2] / 2:5.0f},{box[1] + FEET_AT * box[3]:<5.0f}{box[2]:5.0f} "
                f"{yn(s)} {yn((nx, ny, nh))} {yn(p)}")
    L.append("       t       live: clip centre     width sc  net pa     replay: clip centre     width sc  net pa")
    for t in times:
        L.append(f"{t:8.2f}  {cell(pl['P'], t, False)}    {cell(pl['R'], t, True)}  {', '.join(marks.get(t, []))}")
    L.append("  (sc: the scorer's track, or the --shot spot at the shot; pa: the passer's, or the --pass spot)")
    return "\n".join(L)


# ---------------------------------------------------------------- the contact sheet

MARK_COLORS = {"shot": (40, 40, 230), "goal": (0, 200, 255), "pass": (230, 170, 0), "poster": (200, 60, 200)}


def contact_sheet(mp4, out, marks=(), step=1.0, span=None, cols=6, tile_w=320, title="", live_s=None):
    """A rendered clip in one image: a tile every `step` s of clip time (the replay at half speed, so 0.5 s of
    play each), each with its clip second (top right, "R" from live_s on: the replay's own label is top left); the
    tile nearest each mark ((label, clip s): the shot, the goal, the pass) framed and labeled. It reads the mp4
    itself, so it shows what the viewer sees."""
    cap = cv2.VideoCapture(mp4)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    end = (int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1) / fps
    a, b = span if span else (0.0, end)
    times = np.round(np.arange(max(a, 0.0), min(b, end) + 1e-6, step), 3)
    if not len(times):
        raise SystemExit(f"{mp4}: nothing to tile in {a:g}-{b:g} s (the clip is {end:.1f} s)")
    want = {}
    for i, t in enumerate(times):
        want.setdefault(int(round(t * fps)), []).append(i)
    th = int(round(tile_w * OUT_H / OUT_W))
    tiles, k = [None] * len(times), 0
    while k <= max(want):
        ok, fr = cap.read()
        if not ok:
            break
        for i in want.get(k, []):
            tiles[i] = cv2.resize(fr, (tile_w, th), interpolation=cv2.INTER_AREA)
        k += 1
    cap.release()
    blank = np.full((th, tile_w, 3), 255, np.uint8)
    tiles = [blank.copy() if im is None else im for im in tiles]
    tags = {}
    for label, c in marks:
        if c is not None and a - step <= c <= b + step:
            tags.setdefault(int(np.abs(times - c).argmin()), []).append(label)
    font = cv2.FONT_HERSHEY_SIMPLEX
    for i, (im, t) in enumerate(zip(tiles, times)):
        for j, label in enumerate(tags.get(i, [])):
            col = MARK_COLORS.get(label.split()[0].lower(), (40, 40, 230))
            cv2.rectangle(im, (2 + 3 * j, 2 + 3 * j), (tile_w - 3 - 3 * j, th - 3 - 3 * j), col, 3)
            (tw, tth), _ = cv2.getTextSize(label.upper(), font, 0.6, 2)
            y = th - 8 - 24 * j
            cv2.rectangle(im, (6, y - tth - 6), (12 + tw, y + 4), col, -1)
            cv2.putText(im, label.upper(), (9, y), font, 0.6, (0, 0, 0), 2, cv2.LINE_AA)
        lab = f"{t:.1f}" + (" R" if live_s is not None and t >= live_s - 1e-6 else "")
        (lw, _), _ = cv2.getTextSize(lab, font, 0.6, 1)
        cv2.rectangle(im, (tile_w - lw - 10, 0), (tile_w, 24), (0, 0, 0), -1)
        cv2.putText(im, lab, (tile_w - lw - 5, 18), font, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    rows = [np.hstack(tiles[i:i + cols] + [blank] * (cols - len(tiles[i:i + cols]))) for i in range(0, len(tiles), cols)]
    sheet = np.vstack(rows)
    if title:
        bar = np.full((32, sheet.shape[1], 3), 255, np.uint8)
        cv2.putText(bar, title, (8, 22), font, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
        sheet = np.vstack([bar, sheet])
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return out


def sheet_marks(rec):
    """A clips_check.json entry's marks as contact_sheet takes them, live first, then the replay's."""
    out = []
    for k, cs in rec.get("marks", {}).items():
        for c, part in zip(cs, ("", " (replay)")):
            if c is not None:
                out.append((k + part, c))
    return out


def main():
    dry = "--dry-run" in sys.argv
    argv = [a for a in sys.argv if a != "--dry-run"]
    full, video, audio, out = argv[1:5]
    meta = next(imageio_ffmpeg.read_frames(video)) if not dry or os.path.exists(video) else None
    pl = plan(argv, tuple(meta["size"]) if meta else tuple(rink(full).size))
    warns = check(pl)
    rec = record(pl, warns, dry)
    if dry:
        print(summary(pl, warns))
    for w in warns:
        print(f"clip check: {pl['name']}: {w['msg']} (clip {w['at']:g} s)")
    if dry:
        print(f"dry run: nothing cut; the checks are in {rec}")
        return
    W, H = pl["W"], pl["H"]; fps = meta["fps"]
    t0, t1, tp, net, replay, P, R = pl["t0"], pl["t1"], pl["tp"], pl["net"], pl["replay"], pl["P"], pl["R"]
    enc_cmd = [FF, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OUT_W}x{OUT_H}",
               "-r", str(fps), "-i", "-"]
    if audio and os.path.exists(audio) and not _silent(audio, t0, t1):
        enc_cmd += ["-ss", str(t0), "-t", str(t1 - t0), "-i", audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "96k"]
        if net:   # silence under the replay, to the clip's end (endless padding overran -shortest's queue on VP9)
            enc_cmd += ["-af", f"apad=whole_dur={t1 - t0 + 2 * (replay[1] - replay[0])}"]
    enc_cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                "-shortest", out]
    enc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE)

    def render(path, a, b, repeat=1, label=None):
        """Crop the video from a to b along path into the encoder, each frame `repeat` times; the frame at tp."""
        dec = subprocess.Popen([FF, "-nostdin", "-loglevel", "error", "-ss", str(a), "-i", video, "-t", str(b - a),
                                "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE,
                               stdin=subprocess.DEVNULL, bufsize=W * H * 3 * 2)
        k, at_tp = 0, None
        ts = path.index.values
        while True:
            buf = dec.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break
            t = a + k / fps; k += 1
            cx, cy, w = (np.interp(t, ts, path[c].values) for c in ("cx", "cy", "w"))
            h = w * OUT_H / OUT_W
            x0 = int(np.clip(cx - w / 2, 0, W - w)); y0 = int(np.clip(cy - FEET_AT * h, 0, H - h))
            img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)[y0:y0 + int(h), x0:x0 + int(w)]
            frame = cv2.resize(img, (OUT_W, OUT_H), interpolation=cv2.INTER_AREA if w >= OUT_W else cv2.INTER_CUBIC)
            if at_tp is None and t >= tp:
                at_tp = frame.copy()
            if label:
                for col, th in (((0, 0, 0), 6), ((255, 255, 255), 2)):
                    cv2.putText(frame, label, (36, 64), cv2.FONT_HERSHEY_SIMPLEX, 1.4, col, th, cv2.LINE_AA)
            for _ in range(repeat):
                enc.stdin.write(frame.tobytes())
        dec.wait()
        return at_tp

    poster = render(P, t0, t1)
    if net:
        render(R, tp + replay[0], tp + replay[1], repeat=2, label="REPLAY")
    enc.stdin.close(); enc.wait()
    if poster is not None:
        cv2.imwrite(os.path.splitext(out)[0] + ".jpg", poster, [cv2.IMWRITE_JPEG_QUALITY, 82])
    print(out, f"{os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
