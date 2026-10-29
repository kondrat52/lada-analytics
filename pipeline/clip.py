"""clip.py FULLDIR VIDEO AUDIO OUT.mp4 T0 T1 [POSTER_T [FOCUS [NET]]]
Cut a zoomed highlight clip: a virtual camera follows the main cluster of players (from FULLDIR/dets.csv),
crops the 4K wide cut to 16:9 and encodes 1280x720 H.264 with the game audio. Writes OUT.jpg as a poster
frame (at POSTER_T, default the middle of the clip). FOCUS keeps the camera on part of the rink when players are
spread out: a source x in px (rink.py nets, e.g. 540 = Renton's left net), or "track:TRACKS.csv:TID[,TID...]" to follow one player's track(s)
(e.g. the player who took a penalty), "group:TRACKS.csv:TID,TID;TID;..." to keep several players in the frame
(one ;-separated list of tracks per player, the scorer first, then the assists), or "-" for none. NET "X,Y" (the
scoring net, Y a fallback for its height) makes it a goal clip: the camera closes in on that net around POSTER_T,
the goal (`goal_path`), and the clip ends with a zoomed half-speed replay of the goal. The audio is left out when
the recording's audio is silent."""
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
# a goal clip ends with the seconds around the goal again at half speed, zoomed in on the net and the slot (~580 of
# 3840 px): a scramble at the far net is a few dozen pixels tall at any crop the live camera can hold. Players
# aren't followed there, since a mislabeled track at the goal (BW's Oct 25 opener) pulls the net out of the frame
REPLAY, REPLAY_ZOOM = (-4.0, 1.5), (0.15, 0.25)


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


def goal_path(full, P, t0, t1, tg, net, players, frame_w, max_w, zoom=(NET_W, NET_HI)):
    """A goal clip's camera. It frames everyone credited with the goal (`players`: a track table per player,
    scorer first, empty where untracked) whenever one of them is tracked, and from 6 s before the goal (tg) to 2 s
    after, the scoring net (`net`, x and y) and the slot in front of it too; where neither applies, the main group
    (P, from camera_path). Following the main group alone missed TK's Oct 25 scorers: on Belousenko's goal it sat
    on the scramble at the net and the corner behind it, and he shot from the slot just outside the frame's edge.
    At the net the crop is `zoom` (smallest and largest width, as shares of the frame's), and a player who doesn't
    fit drops out, passers first and the one who widens the crop most first (a passer near the camera costs
    height: on BW's Oct 25 opener Zhuk at the near point kept with the far net made the crop wider than following
    the group did), the scorer last; away from the net the limit is max_w. The net's skate line comes from the detections standing at
    it (the goalie), so a camera framed a little differently that day still lands on it; the given y is the
    fallback."""
    if net:
        nx, ny = net
        d = load(f"{full}/dets.csv")
        d = d[(d.t >= t0) & (d.t <= t1) & (d.conf >= 0.3) & d.onice & ((d.fx - nx).abs() < 90)]
        ny, nh = (float(d.fy.median()), float(d.h.median())) if len(d) >= 20 else (ny, 80.0)
        slot = nx + (1 if nx < frame_w / 2 else -1) * 0.35 * zoom[0] * frame_w   # the net a third of the way in
    rows = []
    for t in P.index:
        pts = []                          # (x, y, h, player index: 0 = scorer)
        for i, p in enumerate(players):
            if not len(p):
                continue
            j = np.abs(p.index.values - t).argmin()
            if abs(p.index[j] - t) <= 0.5:
                pts.append((p.fx.iat[j], p.fy.iat[j], p.h.iat[j], i))
        at_net = net is not None and tg + LOCK[0] <= t <= tg + LOCK[1]
        if not pts and not at_net:
            rows.append((t, np.nan, np.nan, np.nan))
            continue
        if at_net:
            fixed = [(nx, ny, nh, -1), (slot, ny, nh, -1)]
            ax, ay, lo, hi = nx, ny, zoom[0] * frame_w, min(zoom[1] * frame_w, max_w)
        else:
            fixed = []
            a = min(pts, key=lambda q: q[3])
            ax, ay, lo, hi = a[0], a[1], min(1300, max_w), max_w   # 1300: as following one player
        # the passer who widens the crop most first, the scorer last
        pts.sort(key=lambda q: (q[3] == 0, -max(abs(q[0] - ax), abs(q[1] - ay) * OUT_W / OUT_H)))
        while True:
            S = fixed + pts
            left = min(x - h for x, y, h, _ in S); right = max(x + h for x, y, h, _ in S)
            top = min(y - 1.3 * h for x, y, h, _ in S); bottom = max(y + 0.3 * h for x, y, h, _ in S)
            w = max(right - left, (bottom - top) * OUT_W / OUT_H, lo)
            if w <= hi or len(S) <= max(1, len(fixed)):
                break
            pts.pop(0)
        w = min(w, hi)
        # skates at FEET_AT of the crop's height puts its middle at the set's middle
        rows.append((t, (left + right) / 2, (top + bottom) / 2 + (FEET_AT - 0.5) * w * OUT_H / OUT_W, w))
    G = pd.DataFrame(rows, columns=["t", "cx", "cy", "w"]).set_index("t")
    Q = G.fillna(P)
    # two short moving averages: an eased move of about 2 s onto the net and back off it
    return Q.rolling(9, center=True, min_periods=1).mean().rolling(9, center=True, min_periods=1).mean()


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
            players = [tr[tr.tid.isin([int(x) for x in g.split(",") if x])].groupby("t")[["fx", "fy", "h"]].first()
                       for g in tids.split(";")]
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
    P = goal_path(full, P0, t0, t1, tp, net, players, W, max_w) if net or players else P0
    enc_cmd = [FF, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OUT_W}x{OUT_H}",
               "-r", str(fps), "-i", "-"]
    if audio and os.path.exists(audio) and not _silent(audio, t0, t1):
        enc_cmd += ["-ss", str(t0), "-t", str(t1 - t0), "-i", audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "96k"]
        if net:
            enc_cmd += ["-af", "apad"]           # silence under the replay
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
        R = goal_path(full, P0, t0, t1, tp, net, [], W, max_w, REPLAY_ZOOM)
        render(R, tp + REPLAY[0], tp + REPLAY[1], repeat=2, label="REPLAY")
    enc.stdin.close(); enc.wait()
    if poster is not None:
        cv2.imwrite(os.path.splitext(out)[0] + ".jpg", poster, [cv2.IMWRITE_JPEG_QUALITY, 82])
    print(out, f"{os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
