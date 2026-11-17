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
it, and the replay starts PASS_LEAD (2 s) before it. The audio is left out when the recording's audio is silent."""
import os, sys, subprocess
import numpy as np, pandas as pd, cv2, imageio_ffmpeg
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from track import load

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


def camera_path(full, t0, t1, focus=None, max_w=MAX_W):
    """Per detection frame (8 fps): crop centre x/y and width (at most max_w), smoothed."""
    d = load(f"{full}/dets.csv")
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
              keep_w=None, pas=None):
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
    feeding from the half-wall were out of the frame when they passed, and out of the replay altogether."""
    if net:
        nx, ny = net
        d = load(f"{full}/dets.csv")
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
        dp = load(f"{full}/dets.csv")
        dp = dp[((dp.t - pas[0]).abs() <= 0.5) & (dp.conf >= 0.3) & ((dp.fx - pas[1]).abs() < 150)
                & ((dp.fy - pas[2]).abs() < 150)]
        ph = float(dp.h.median()) if len(dp) else (nh if net else 80.0)
        carrier = carrier_path(full, pas, shot, nh if net else 80.0) if shot else None
        passer = walk_back(full, pas[0] - PASS_LEAD - 1.0, pas, ph, False)
    keep_w = keep_w or max_w

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
    d = load(f"{full}/dets.csv")
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
        i0, bad = int(np.abs(t - anchor).argmin()), None
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


def _silent(audio, t0, t1):
    r = subprocess.run([FF, "-nostdin", "-loglevel", "error", "-ss", str(t0), "-t", str(t1 - t0), "-i", audio,
                        "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True)
    return not np.frombuffer(r.stdout, np.int16).any()


def main():
    full, video, audio, out = sys.argv[1:5]
    t0, t1 = float(sys.argv[5]), float(sys.argv[6])
    tp = float(sys.argv[7]) if len(sys.argv) > 7 else (t0 + t1) / 2
    focus, players = None, []
    if len(sys.argv) > 8:
        if sys.argv[8].startswith("group:"):
            path, tids = sys.argv[8][len("group:"):].rsplit(":", 1)
            tr = pd.read_csv(path)
            tr = tr[(tr.t >= t0 - 3) & (tr.t <= t1 + 3)]
            # each player's tracks in priority order: where two cover the same moment, the first one counts
            # the walk along each player's tracks starts where the goal check saw him: the scorer at the shot,
            # the passer at the pass
            anchors = [float(sys.argv[k].split(",")[0]) if len(sys.argv) > k and sys.argv[k] != "-" else None
                       for k in (11, 12)]
            players = [player_path(tr, [int(x) for x in g.split(",") if x], anchors[i] if i < 2 else None)
                       for i, g in enumerate(tids.split(";"))]
        elif sys.argv[8].startswith("track:"):
            path, tids = sys.argv[8][len("track:"):].rsplit(":", 1)   # the path may hold a drive colon (C:\...)
            tr = pd.read_csv(path)
            parts = [tr[tr.tid == int(x)].groupby("t").fx.first().sort_index() for x in tids.split(",")]

            def focus(t):
                # tracks in priority order: use the first one that covers time t
                for p in parts:
                    if len(p) and p.index.min() - 0.5 <= t <= p.index.max() + 0.5:
                        return float(np.interp(t, p.index, p.values))
                return None
        elif sys.argv[8] != "-":
            focus = float(sys.argv[8])
    meta = next(imageio_ffmpeg.read_frames(video))
    W, H = meta["size"]; fps = meta["fps"]
    max_w = min(MAX_W, H * OUT_W / OUT_H)            # a 16:9 crop must fit the frame
    P0 = camera_path(full, t0, t1, focus, max_w)
    net = tuple(float(v) for v in sys.argv[9].split(",")) if len(sys.argv) > 9 else None
    shot = tuple(float(v) for v in sys.argv[11].split(",")) if len(sys.argv) > 11 and sys.argv[11] != "-" else None
    pas = tuple(float(v) for v in sys.argv[12].split(",")) if len(sys.argv) > 12 else None
    if len(sys.argv) > 10 and sys.argv[10] != "-":
        replay = (-float(sys.argv[10]), REPLAY[1])
    else:
        replay = (min(REPLAY[0], shot[0] - tp - 1.5), REPLAY[1]) if shot else REPLAY
        if pas:
            replay = (min(replay[0], pas[0] - tp - PASS_LEAD), replay[1])
    P = goal_path(full, P0, t0, t1, tp, net, players, W, max_w, shot=shot, pas=pas) if net or players else P0
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
        # the net and the scorer, the net in the frame for the whole replay; with a pass, the passer until it (after
        # it he only widened the close-up at the net)
        rp = players[:1] + ([players[1][players[1].index <= pas[0] + PASS_HOLD]] if pas and len(players) > 1 else [])
        R = goal_path(full, P0, t0, t1, tp, net, rp, W, max_w, REPLAY_ZOOM,
                      (min(replay[0], LOCK[0]), LOCK[1]), shot, REPLAY_ZOOM[1] * W, pas)
        render(R, tp + replay[0], tp + replay[1], repeat=2, label="REPLAY")
    enc.stdin.close(); enc.wait()
    if poster is not None:
        cv2.imwrite(os.path.splitext(out)[0] + ".jpg", poster, [cv2.IMWRITE_JPEG_QUALITY, 82])
    print(out, f"{os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
