"""Driver for processing one game. Run with the hockey env's python (see setup_env.sh).

  run_game.py fetch   URL W [--team SLUG] [--rink NAME] [--jersey NAME] [--bench SIDE] [--limit SEC]   download,
                                             calibrate, detect (auto-restart), OCR, propose periods; --team: whose
                                             game, a folder in teams/ (tk); --rink: camera geometry from rink.py
                                             (renton); --jersey: our jersey that game (light blue, white); --bench:
                                             left or right, our bench (the rink's usual one unless set)
  run_game.py jersey  W NAME                 we wore another jersey than fetch was told: switch to it, cut its
                                             crops from the video (~5 min) and OCR them
  run_game.py skaters W T0 T1               our skaters detected on the ice per 5 s (find penalty kills)
  run_game.py unknown W                      numbers/surnames read that aren't on the roster (new players?)
  run_game.py absent  W [N ...] [--suggest]  roster numbers that didn't play this game (their partial reads would
                                             label others): recorded in W/full/rink.json, honoured by every step;
                                             --suggest tables the evidence (sheet, lines, reads, card rows)
  run_game.py schedule W                     the team's games from LADA's public API (ids, home/away, rink, lines)
  run_game.py sheet   W [--sn ID | --lada ID]  the game sheet from SportNinja's public API: score, shots, goals with
                                             scorers, penalties, who played -> W/sheet.json (goals/solve use it)
  run_game.py prepare W                      per period: tracking, review sheets, roster card
  run_game.py review  W [--opp DESC] [--note TEXT] [--chunk N]   write one filled reviewer prompt per chunk of
                                             sheets (W/rev_pN/prompt_cNN.md) and the plan of what is still to do
  run_game.py check   W                      which review rows are still missing or unreadable, per sheet
  run_game.py solve   W                      per period: apply reviews + solve; gantt charts; stats table; checks
  run_game.py gaps    W [--apply [F ...]]    write the by-eye check briefs for the lineup check's windows
                                             (W/scratch/gaps/prompt_pN.md, one subagent each); --apply merges the
                                             checkers' fixes.json into periods.json as on/off spans
  run_game.py goals   W                      candidate goals: center-ice faceoffs + long stoppages (verify by eye)
  run_game.py frames  W OUT.jpg --view rink|left-net|right-net|bench t1 t2 ...   4K frames (cropped) as a sheet, for
                                             verifying; --range T0 T1 STEP instead of times; or the crop by hand:
                                             X0 X1 Y0 Y1 TILE_W COLS t1 t2 ...
  run_game.py clip    W GAME_ID NAME T0 T1 POSTER_T [FOCUS]          zoomed clip into <site>/games/<id>/clips;
                                             FOCUS = x px (a net x from rink.py) or #N to follow player N
  run_game.py publish W GAME_ID --opponent RR --eyebrow "Sun Sep 27, 2026 · 7:50 PM · Renton" [--date ...]
  run_game.py archive W                      after publishing: drop the video, crops and sheets (~5 GB), keep the
                                             game's data (detections, reads, tracks, reviews; ~100 MB)

W is the per-game work folder (outside the repo). Every step skips work that is already done, so re-running
after an interruption continues where it stopped. W/full/rink.json records the team (fetch --team), and every
command works on that team's roster, games and site (roster.py). W/periods.json holds the period windows; fetch writes a
proposal, which you check and edit (add penalty kills) before prepare/solve. Every command sets ROSTER_ABSENT from
rink.json's "absent" list, so roster.py leaves those players out (see `absent`).
"""
import argparse, glob, json, os, re, shutil, signal, subprocess, sys, time
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable
FPS = 8
sys.path.insert(0, HERE)
from rink import rink


def sh(*args, **kw):
    print("+", " ".join(map(str, args)), flush=True)
    return subprocess.run([str(a) for a in args], check=True, **kw)


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ---------------------------------------------------------------- fetch

def video_info(url, W):
    """Title, upload date and length of the video (W/video_info.json): LADA titles carry the date, time and rink."""
    p = f"{W}/video_info.json"
    if os.path.exists(p):
        return json.load(open(p))
    try:
        out = subprocess.run([PY, "-m", "yt_dlp", "-q", "--no-warnings", "--skip-download", "--print", "%(title)s",
                              "--print", "%(upload_date)s", "--print", "%(duration)s", url],
                             capture_output=True, text=True, timeout=120, check=True).stdout.splitlines()
        dur = int(float(out[2])) if len(out) > 2 and out[2] not in ("", "NA") else None
        info = dict(url=url, title=out[0], upload_date=out[1] if len(out) > 1 else "", duration=dur)
    except Exception as e:
        log(f"video title unavailable ({e})")
        return {}
    json.dump(info, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    log(f"video: {info['title']!r} ({dur // 60 if dur else '?'} min, uploaded {info['upload_date']})")
    return info


def download(url, W):
    vid = f"{W}/video.webm"
    if os.path.exists(vid):
        return vid
    # 4K where there is one; Doofers' Sep 19 video topped out at 1440p (fit_size scales it up)
    sh(PY, "-m", "yt_dlp", "-q", "--no-progress", "-f", "313/bestvideo[height=2160]/bestvideo[ext=webm]/bestvideo",
       "-o", vid, url)
    return vid


def fit_size(vid, W):
    """rink.py's geometry is in pixels of the rink's usual frame (`size`). A video of the same view at a lower
    resolution (Kirkland once came as 3600x1440, not 3840x1536) is scaled up once and the original kept beside it.
    As H.264 (in Matroska, under the same name): ffmpeg decodes it ~5x faster than AV1, which it has no fast
    decoder for here."""
    import imageio_ffmpeg
    size = getattr(rink(f"{W}/full"), "size", None)
    have = tuple(next(imageio_ffmpeg.read_frames(vid))["size"])
    if not size or have == tuple(size):
        return
    if abs(have[0] / size[0] - have[1] / size[1]) > 0.01:
        sys.exit(f"video is {have[0]}x{have[1]}, not a scaled {size[0]}x{size[1]}: new framing, see rink.py")
    log(f"video is {have[0]}x{have[1]}; scaling it to {size[0]}x{size[1]}")
    enc = ["h264_nvenc", "-preset", "p5", "-cq", "21"] if sys.platform == "win32" else ["libx264", "-crf", "20"]
    sh(imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-y", "-i", vid, "-vf",
       f"scale={size[0]}:{size[1]}:flags=bicubic", "-c:v", *enc, "-an", "-f", "matroska", f"{W}/video_up.webm")
    os.replace(vid, f"{W}/video_{have[0]}x{have[1]}.webm")
    os.replace(f"{W}/video_up.webm", vid)


def download_audio(url, W):
    """Only clips use the audio, so a failed download (YouTube has answered 403 once, then worked on a retry) warns
    instead of stopping fetch; re-running fetch tries again."""
    for _ in range(2):
        if os.path.exists(f"{W}/audio.m4a"):
            return
        try:
            sh(PY, "-m", "yt_dlp", "-q", "--no-progress", "-f", "140/bestaudio[ext=m4a]", "-o", f"{W}/audio.m4a", url)
        except subprocess.CalledProcessError:
            pass
    log("no audio: clips will be silent (re-run fetch to try again)")


def calibrate(vid, W):
    if os.path.exists(f"{W}/full/boards_poly.npy"):
        return
    import imageio_ffmpeg
    frame = f"{W}/frame600.png"
    sh(imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-y", "-ss", "600", "-i", vid, "-frames:v", "1", frame)
    sh(PY, f"{HERE}/boards.py", frame, f"{W}/full")


def _last_frame(dets):
    if not os.path.exists(dets) or os.path.getsize(dets) == 0:
        return None
    with open(dets, "rb") as f:
        f.seek(max(0, os.path.getsize(dets) - 4096))
        tail = f.read().decode(errors="ignore").strip().splitlines()
    return int(tail[-1].split(",")[0]) if tail else None


def _trim_last_frame(full):
    """Drop the last (possibly partial) frame so a restart can redo it. Returns its start time in seconds."""
    dets = f"{full}/dets.csv"
    f = _last_frame(dets)
    if f is None:
        return 0.0
    keep = [l for l in open(dets) if not l.startswith(f"{f},")]
    open(dets, "w").writelines(keep)
    for p in glob.glob(f"{full}/crops/f{f:06d}_*.jpg"):
        os.remove(p)
    return f / FPS


def detect(vid, W, limit=None):
    """Run process.py; if it slows to under ~45% of its normal speed for 8 minutes (memory growth on long runs),
    restart it from the last frame. Frame numbers stay global across restarts."""
    full = f"{W}/full"; logp = f"{full}/log.txt"
    if os.path.exists(logp) and "\nDONE" in "\n" + open(logp).read():
        return
    start = _trim_last_frame(full) if os.path.exists(f"{full}/dets.csv") else 0.0
    crashes = 0
    while True:
        cmd = [PY, f"{HERE}/process.py", vid, full, str(FPS)]
        if start or limit:
            cmd += [str(start)]
        if limit:
            cmd += [str(max(1.0, limit - start))]
        log(f"detect from t={start:.1f}s")
        lf = open(logp, "a"); lf.write(f"--- start {start:.3f}\n"); lf.flush()
        proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=W)
        t_start, hist, slow_since = time.time(), [], None
        while proc.poll() is None:
            time.sleep(30)
            lines = [l for l in open(logp).read().splitlines() if l.startswith("frame ")]
            if lines:
                m = re.search(r" t=(\d+)s", lines[-1])
                hist.append((time.time(), float(m.group(1))))
            # speed over the last 10 minutes, in video seconds per wall second (normal ~0.75 on an M3)
            recent = [h for h in hist if h[0] > time.time() - 600]
            if time.time() - t_start > 900 and len(recent) >= 2:
                rate = (recent[-1][1] - recent[0][1]) / max(1, recent[-1][0] - recent[0][0])
                slow_since = (slow_since or time.time()) if rate < 0.35 else None
                if slow_since and time.time() - slow_since > 480:
                    log(f"detection slowed to {rate:.2f} video-s/s; restarting")
                    proc.send_signal(signal.SIGTERM); proc.wait(30)
                    break
        if proc.returncode == 0 and "\nDONE" in "\n" + open(logp).read():
            log("detection done")
            return
        prev = start
        start = _trim_last_frame(full)
        if proc.returncode not in (None, 0, -signal.SIGTERM):
            crashes = crashes + 1 if start <= prev + 5 else 0
            if crashes >= 3:
                sys.exit(f"process.py keeps failing near t={start:.0f}s; see {logp}")
            log(f"process.py exited with {proc.returncode}; restarting from the last frame")


def ocr_skip(W):
    """Crops of people sitting deep in our bench (rink.ocr_skip_depth), listed in ocr_done_bench.txt so the OCR
    workers pass over them: those tracks are dropped as bench sitters, so their reads are never used."""
    from track import load
    full = f"{W}/full"; R = rink(full)
    if R.ocr_skip_depth is None:
        return
    d = load(f"{full}/dets.csv")
    deep = d[np.asarray(R.bench_depth(d.fx, d.fy - d.board)) > R.ocr_skip_depth]
    crops = set(os.listdir(f"{full}/crops"))
    names = [n for n in (f"f{f:06d}_{i:02d}.jpg" for f, i in zip(deep.frame, deep.i)) if n in crops]
    open(f"{full}/ocr_done_bench.tmp", "w").write("\n".join(names) + "\n")
    os.replace(f"{full}/ocr_done_bench.tmp", f"{full}/ocr_done_bench.txt")


def ocr(W):
    full = f"{W}/full"
    ocr_skip(W)
    crops = set(os.listdir(f"{full}/crops"))
    done = set()
    for p in glob.glob(f"{full}/ocr_done_*.txt"):
        done |= set(open(p).read().split())
    if not crops - done:
        return
    log(f"OCR on {len(crops - done)} crops (4 workers)")
    env = dict(os.environ, PYTHONHASHSEED="0")
    ps = [subprocess.Popen([PY, f"{HERE}/ocr_worker.py", full, "1000000000", "1", str(k), "4"], env=env,
                           stdout=open(f"{full}/ocr_log_{k}.txt", "w"), stderr=subprocess.STDOUT) for k in range(4)]
    for p in ps:
        p.wait()


def propose_periods(W):
    """Breaks = min_break+ seconds (rink.py) with nobody out on the open ice. Our goalie's net side per period from
    detections in our jersey standing in each crease."""
    from track import load
    R = rink(f"{W}/full")
    d = load(f"{W}/full/dets.csv"); d["rel"] = d.fy - d.board
    T = int(d.t.max()) + 1
    out = d[R.open_ice(d.fx, d.rel) & (d.conf >= 0.3)]
    act = np.bincount(out.t.astype(int), minlength=T) / FPS
    act = pd.Series(act).rolling(5, center=True, min_periods=1).median().values
    empty = act < 0.5
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
    periods = []
    for a, b in zip(edges[0::2], edges[1::2]):
        if b - a >= 240:
            periods.append([a, b])
    us = d[d.ours]
    res = []
    for k, (a, b) in enumerate(periods, 1):
        w = us[(us.t >= a) & (us.t < b)]
        nl, nr = (R.in_crease(w.fx, w.rel, R.nets[s]).sum() for s in ("left", "right"))
        res.append(dict(label=f"P{k}", start=int(a), end=int(b), net=R.nets["left" if nl >= nr else "right"], pk=[]))
    json.dump(res, open(f"{W}/periods.json", "w"), indent=2)
    for k in range(len(res) - 1):
        a, b = res[k]["end"], res[k + 1]["start"]
        sh(PY, f"{HERE}/ovsheet.py", f"{W}/full/ov", f"{W}/break_{k + 1}.jpg", a - 60, b + 40, 10, 2)
    sh(PY, f"{HERE}/ovsheet.py", f"{W}/full/ov", f"{W}/video_end.jpg", T - 120, T, 20, 2)
    print(json.dumps(res, indent=2))


def set_config(W, **kw):
    """Store team/rink/jersey choices in W/full/rink.json, which every later step reads (rink.py, team: __main__)."""
    from rink import RINKS, JERSEYS
    for k, known in (("rink", RINKS), ("jersey", JERSEYS), ("bench", ("left", "right"))):
        if kw.get(k) and kw[k] not in known:
            sys.exit(f"unknown {k} {kw[k]!r}; known: {', '.join(known)}")
    p = f"{W}/full/rink.json"
    cfg = json.load(open(p)) if os.path.exists(p) else {}
    cfg.update({k: v for k, v in kw.items() if v})
    if cfg:
        json.dump(cfg, open(p, "w"))


def scoreboard_sheet(W):
    """The arena scoreboard every 60 s (W/sb.jpg) from one pass over the video (W/scoreboard.npy): periods, score,
    penalties and shots are read off it, since the empty-ice period proposal is often wrong."""
    from scoreboard import scan, sheet
    if not os.path.exists(f"{W}/scoreboard.npy"):
        log("scoreboard: one pass over the video")
        scan(W)
    n = len(np.load(f"{W}/scoreboard.npy", mmap_mode="r"))
    sheet(W, f"{W}/sb.jpg", list(range(30, n, 60)), cols=6)


def cmd_fetch(a):
    W = os.path.abspath(a.W); os.makedirs(f"{W}/full", exist_ok=True)
    set_config(W, team=a.team, rink=a.rink, jersey=a.jersey, bench=a.bench)
    video_info(a.url, W)
    update_lada_games()
    vid = download(a.url, W)
    fit_size(vid, W)
    download_audio(a.url, W)
    calibrate(vid, W)
    detect(vid, W, a.limit)
    ocr(W)
    propose_periods(W)
    if not a.limit:
        scoreboard_sheet(W)
    sb = f"{W}/sb.jpg (the scoreboard every 60 s), " if os.path.exists(f"{W}/sb.jpg") else ""
    log(f"fetch done. Check {W}/periods.json against {sb}break_*.jpg and video_end.jpg")


def cmd_jersey(a):
    W = os.path.abspath(a.W)
    set_config(W, jersey=a.name)
    sh(PY, f"{HERE}/crops.py", f"{W}/video.webm", f"{W}/full", FPS, "--hue")   # a dets.csv made before bhue
    sh(PY, f"{HERE}/crops.py", f"{W}/video.webm", f"{W}/full", FPS)
    ocr(W)
    log(f"crops and reads for {a.name} done; now `unknown` and `prepare` (delete {W}/p* and {W}/rev_p* if an "
        "earlier prepare made them)")


# ---------------------------------------------------------------- helpers for the review

def periods(W):
    return json.load(open(f"{W}/periods.json"))


def cmd_skaters(a):
    tr = []
    for P in periods(a.W):
        p = f"{a.W}/{P['label'].lower()}/tracks_v1.csv"
        if os.path.exists(p):
            tr.append(pd.read_csv(p))
    if tr:
        t = pd.concat(tr)
    else:  # before prepare: raw detections in our jersey on the ice
        from track import load
        t = load(f"{a.W}/full/dets.csv"); t = t[t.ours]
    t = t[(t.t >= a.T0) & (t.t < a.T1) & t.onice]
    c = t.groupby([(t.t // 5).astype(int) * 5, "frame"]).size().groupby(level=0).quantile(0.75)
    print("our skaters on the ice (75th pct per 5 s; includes the goalie before prepare):")
    print(" ".join(f"{int(k) // 60}:{int(k) % 60:02d}={v:.0f}" for k, v in c.items()))


def _skater_speed(W):
    """Median speed of our tracked skaters per second, in body-heights/s (low = stoppage)."""
    tr = pd.concat([pd.read_csv(f"{W}/{P['label'].lower()}/tracks_v1.csv") for P in periods(W)])
    tr = tr[tr.onice].sort_values(["tid", "frame"])
    tr["v"] = np.hypot(tr.groupby("tid").fx.diff(), tr.groupby("tid").fy.diff()) / tr.h * FPS
    tr.loc[tr.groupby("tid").frame.diff() != 1, "v"] = np.nan
    T = int(tr.t.max()) + 1
    return tr.groupby(tr.t.astype(int)).v.median().reindex(range(T)).rolling(5, center=True, min_periods=1).median()


def cmd_goals(a):
    """After every goal the restart is a center-ice faceoff. List center-ice formations that aren't period
    starts, and every long stoppage with where play restarted. Each needs checking by eye (frames command)."""
    from track import load
    W = os.path.abspath(a.W)
    R = rink(f"{W}/full")
    d = load(f"{W}/full/dets.csv"); d = d[d.onice & (d.conf >= 0.3)]
    g = d.groupby("frame").agg(t=("t", "first"), n=("fx", "size"), mx=("fx", "median"),
                               q2=("fx", lambda s: s.quantile(.2)), q8=("fx", lambda s: s.quantile(.8)))
    s = g.assign(sx=g.q8 - g.q2).groupby(g.t.astype(int)).agg(n=("n", "median"), mx=("mx", "median"), sx=("sx", "median"))
    center = R.center_x
    sp = _skater_speed(W)
    Ps = periods(W)
    starts = [P["start"] for P in Ps]
    def label(t):
        P = next((P for P in Ps if P["start"] <= t <= P["end"]), None)
        return P["label"] if P else "break"
    if os.path.exists(f"{W}/sheet.json"):
        sheet_ = json.load(open(f"{W}/sheet.json", encoding="utf-8"))
        print("Game sheet (SportNinja) goals, with the video time the period clock implies (exact where the clock runs "
              "through stoppages, otherwise the earliest possible):")
        for x in sheet_["goals"]:
            t_ = x.get("video_t")
            print(f"  {x['period']} {x['clock']} {x['team']:<7} #{x['scorer']} {x['scorer_name']}" + (f"  ~{t_ // 60}:{t_ % 60:02d}" if t_ else ""))
        # sheet.json written before periods.json has no video times (each goal used to print as its period's start)
        if not any(x.get("video_t") for x in sheet_["goals"]):
            print(f"  no video times: sheet.json predates periods.json; run `run_game.py sheet {W}` again")
    print("Long stoppages (our skaters nearly still for 18+ s) and where play restarted:")
    slow = (sp < 0.55) | sp.isna()
    st = None
    for t in range(len(sp)):
        if slow.iloc[t]:
            st = t if st is None else st
            continue
        if st is not None and t - st >= 18 and label(st) != "break":
            w = s.loc[t - 6:t + 1]
            rx = w.mx.median()
            where = "CENTER ice" if abs(rx - center) < 250 else ("left end" if rx < center - 380 else "right end")
            near_start = any(abs(st - x) < 45 for x in starts)
            hint = "  <- goal? (center restart)" if where == "CENTER ice" and not near_start else ""
            # where was play just before it stopped?
            before = d[(d.t >= st - 6) & (d.t < st)].fx.median()
            side = "left net" if before < center - 580 else ("right net" if before > center + 620 else "mid-ice")
            print(f"  {st // 60}:{st % 60:02d}-{t // 60}:{t % 60:02d} {label(st)}: play stopped near {side}, "
                  f"restart at {where}{hint}")
        st = None
    print("Center-ice faceoff formations (11+ people lined up around center, still for 3+ s), not period starts:")
    s["mv"] = s.mx.diff().abs().rolling(3, center=True).mean()
    cand = (s.n >= 9) & ((s.mx - center).abs() < 220) & (s.sx < 1100) & (s.mv < 60)
    st = None
    for t in s.index:
        if cand.get(t, False):
            st = t if st is None else st
            continue
        if st is not None and t - st >= 3 and label(st) != "break" and not any(abs(st - x) < 45 for x in starts):
            print(f"  {st // 60}:{st % 60:02d} {label(st)}  <- look at the 60 s before it")
        st = None
    print("Our net per period:", {P["label"]: ("left" if P["net"] < center else "right") for P in Ps})
    print("Verify each with frames (full rink every 3 s, then zoom on the net): a goal shows a crowd at a net, the "
          "referee pointing at it, and one team celebrating before the center faceoff.")


def cmd_unknown(a):
    """Jersey numbers and surnames the OCR read that aren't in roster.json: new or substitute players, or an
    opponent whose jersey passes for ours. Writes W/unknown_<N>.jpg crop sheets to check each by eye."""
    from roster import SKATERS, GOALIES
    from reads import name_to_num
    W = os.path.abspath(a.W); full = f"{W}/full"
    o = pd.concat([pd.read_csv(f, header=None, names=["file", "text", "score"]) for f in glob.glob(f"{full}/ocr_*.csv")])
    o = o[o.score >= 0.85]; o["up"] = o.text.astype(str).str.upper().str.strip()
    known = set(SKATERS) | set(GOALIES)
    digits = "".join(str(n) for n in known)
    dig = o[o.up.str.fullmatch(r"\d{1,2}")]; dig = dig.assign(num=dig.up.astype(int))
    regular = dig[dig.num.isin(known)].num.value_counts()
    # a teammate who plays gets hundreds of reads; opponents' numbers and misreads get a few dozen
    floor = max(30, int(0.15 * regular[regular >= 100].median())) if (regular >= 100).any() else 30
    # single digits are mostly partial reads of roster numbers (8 from 18/78): only count ones no roster number has
    dig = dig[~dig.num.isin(known) & ((dig.num >= 10) | ~dig.num.astype(str).isin(list(digits)))]
    alpha = o[o.up.str.fullmatch(r"[A-Z]{4,}")]
    alpha = alpha[[name_to_num(t) is None for t in alpha.up]]
    cnt = dig.num.value_counts()
    fmt = lambda s: ", ".join(f"{k} x{v}" for k, v in s.items()) or "-"
    print(f"unknown numbers read {floor}+ times (regulars get ~{int(regular[regular >= 100].median()) if (regular >= 100).any() else 0}):")
    for n, c in cnt[cnt >= floor].items():
        files = sorted(set(dig[dig.num == n].file))
        sheet = f"{W}/unknown_{n}.jpg"
        subprocess.run([PY, f"{HERE}/sheet.py", sheet, "110", "180", "12"] +
                       [f"{full}/crops/{f}::" for f in files[::max(1, len(files) // 12)][:12]], stderr=subprocess.DEVNULL)
        print(f"  #{n}: {c} reads; surnames on the same crops: {fmt(alpha[alpha.file.isin(files)].up.value_counts().head(3))}; "
              f"crops: {sheet}")
    if not (cnt >= floor).any():
        print("  none")
    print("  fewer reads (usually opponents or misreads):", fmt(cnt[(cnt < floor) & (cnt >= 30)].head(8)))
    lone = alpha[~alpha.file.isin(set(dig.file))].up.value_counts()
    print("  other surnames read 20+ times:", fmt(lone[lone >= 20].head(8)))
    print("Check each sheet: our jersey (light blue, or white with blue numbers and trim when we wear white) = ours "
          "(add number and surname to roster.json, then prepare); another team's jersey = an opponent (ignore).")


def cmd_frames(a):
    import cv2, imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe(); vid = f"{a.W}/video.webm"
    if not os.path.exists(vid):
        sys.exit(f"no {vid}: frames need the video (archived folders have none; fetch downloads it again)")
    rest = list(a.rest)
    if a.view:   # a crop the rink knows (rink.py views): the whole rink, a zoom on one net, or our bench
        R = rink(f"{a.W}/full")
        if a.view == "bench" and "bench" not in R.views:
            x0, x1, y0, y1 = R.bench_view()
        elif a.view not in R.views:
            sys.exit(f"unknown view {a.view!r}; this rink has: {', '.join(R.views)}, bench")
        else:
            x0, x1, y0, y1 = R.views[a.view]
        tile_w = a.tile or (1000 if a.view == "rink" else 660)
        cols = a.cols or (2 if a.view == "rink" else 3)
    else:
        if len(rest) < 6:
            sys.exit("frames: give --view NAME, or X0 X1 Y0 Y1 TILE_W COLS before the times")
        x0, x1, y0, y1, tile_w, cols = (int(float(x)) for x in rest[:6]); rest = rest[6:]
    # ffmpeg rounds an odd crop of a 4:2:0 video (the H.264 a scaled-up video becomes) to even, and the frame then
    # comes back the wrong size: keep the box even
    x0, y0 = x0 - x0 % 2, y0 - y0 % 2; x1, y1 = x1 - (x1 - x0) % 2, y1 - (y1 - y0) % 2
    times = [float(t) for t in rest]
    if a.range:
        t0, t1, step = a.range
        times += [float(t) for t in np.arange(t0, t1 + 1e-6, step)]
    if not times:
        sys.exit("frames: no times given (list them, or --range T0 T1 STEP)")
    tiles = []
    for t in times:
        r = subprocess.run([FF, "-nostdin", "-loglevel", "error", "-ss", str(t), "-i", vid, "-frames:v", "1", "-vf",
                            f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                           capture_output=True)
        if len(r.stdout) != (y1 - y0) * (x1 - x0) * 3:
            sys.exit(f"no frame at {t:.0f} s (past the end of the video?)")
        im = np.frombuffer(r.stdout, np.uint8).reshape(y1 - y0, x1 - x0, 3)
        im = cv2.resize(im, (tile_w, int(tile_w * (y1 - y0) / (x1 - x0))), interpolation=cv2.INTER_AREA).copy()
        cv2.putText(im, f"{int(t) // 60}:{int(t) % 60:02d}", (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 220), 3)
        tiles.append(im)
    blank = np.full_like(tiles[0], 255)
    rows = [np.hstack(tiles[i:i + cols] + [blank] * (cols - len(tiles[i:i + cols]))) for i in range(0, len(tiles), cols)]
    cv2.imwrite(a.out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(a.out)


def cmd_clip(a):
    from roster import SITE_DIR
    W = os.path.abspath(a.W)
    out = f"{SITE_DIR}/games/{a.game_id}/clips/{a.name}.mp4"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = [PY, f"{HERE}/clip.py", f"{W}/full", f"{W}/video.webm", f"{W}/audio.m4a", out, a.t0, a.t1, a.poster]
    focus = a.focus
    if focus and focus.startswith("#"):
        # follow a player: his labeled tracks in this window, in time order (first covering track wins)
        num, t0, t1 = int(focus[1:]), float(a.t0), float(a.t1)
        P = next(P for P in periods(W) if P["start"] <= t0 <= P["end"])
        pdir = f"{W}/{P['label'].lower()}"
        sg = pd.read_csv(f"{pdir}/segs_final.csv")
        sg = sg[(sg.plabel == num) & (sg.t1 > t0) & (sg.t0 < t1)].sort_values("t0")
        focus = f"track:{pdir}/tracks_v1.csv:" + ",".join(str(int(x)) for x in sg.tid) if len(sg) else None
    sh(*cmd + ([focus] if focus else []))


def _lines_numbers(W):
    """Jersey numbers in LADA's planned lines for this game (lada_games.json by the folder's date), or None."""
    from roster import LADA_IDS
    m = re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(W))
    p = lada_games_path()
    if not m or not os.path.exists(p):
        return None
    for g in json.load(open(p, encoding="utf-8")).values():
        if str(g.get("date", ""))[:10] != m.group(0):
            continue
        lines = g.get("lines")
        if isinstance(lines, str):
            try:
                lines = json.loads(lines)
            except ValueError:
                return None
        if not isinstance(lines, dict):
            return None
        ids = {int(x) for grp in ("offence", "defence", "goalie") for ln in lines.get(grp, []) or [] for x in ln if x}
        return {n for n, i in LADA_IDS.items() if i in ids}
    return None


def suggest_absent(W):
    """Who probably didn't play, from the game sheet, LADA's lines, the OCR reads and the roster cards (after
    prepare). A table to decide from, not a verdict: the sheet is the scorekeeper's, the lines are a plan, and a
    covered number reads like absence."""
    from roster import ALL_SKATERS, GOALIE_NAMES, SUBS
    from reads import load_reads
    sheet_ = json.load(open(f"{W}/sheet.json", encoding="utf-8")) if os.path.exists(f"{W}/sheet.json") else None
    played = set(sheet_["played"]) if sheet_ else None
    lines = _lines_numbers(W)
    reads, names = load_reads(f"{W}/full")
    dig = reads[reads.src == "digit"].num.value_counts(); nm = names.num.value_counts()
    cards = {}
    for P in (periods(W) if os.path.exists(f"{W}/periods.json") else []):
        p = f"{W}/rev_{P['label'].lower()}/card_empty.json"
        if os.path.exists(p):
            cards[P["label"]] = set(json.load(open(p)))
    print(f"{'num':>4} {'name':<14} {'sheet':<8} {'lines':<6} {'digits':>6} {'names':>5} {'card rows':<12} suggestion")
    out = []
    for n, name in sorted({**ALL_SKATERS, **GOALIE_NAMES}.items()):
        on_sheet = None if played is None else (n in played)
        in_lines = None if lines is None else (n in lines)
        d, m_ = int(dig.get(n, 0)), int(nm.get(n, 0))
        card = "".join("x" if n in cards[k] else "o" for k in sorted(cards)) if cards else "-"
        evidence = d + 3 * m_
        if n in GOALIE_NAMES:
            why = "goalie: absent unless he played" if on_sheet is False else "goalie"
        elif on_sheet is False and in_lines is not True and evidence < 30 and "o" not in card:
            why = "absent"
        elif on_sheet is False and in_lines is not True and evidence < 100:
            why = "absent? (a few reads)"
        elif evidence < 30 and "o" not in card and in_lines is not True:
            why = "absent? (not on the sheet's out list; nothing read)" if on_sheet else "absent? (nothing read)"
        elif on_sheet is False or in_lines is False:
            why = "check: reads say he played" if evidence >= 100 else "check"
            if n < 10 and m_ == 0:
                why += " (a single digit: often partial reads of a two-digit number)"
        else:
            why = "played"
        if n in SUBS and why == "played" and evidence < 30:
            why = "sub, nothing read: absent?"
        out.append((n, why))
        fmt = lambda v: "-" if v is None else ("yes" if v else "NO")
        print(f"{n:>4} {name:<14} {fmt(on_sheet):<8} {fmt(in_lines):<6} {d:>6} {m_:>5} {card:<12} {why}")
    sug = [n for n, w in out if w.startswith("absent") or w.startswith("sub") or w.startswith("goalie: absent")]
    print("card rows: o = has a row on that period's roster card, x = empty (after prepare); digits = confident reads "
          "of the full number, names = nameplate reads")
    if sug:
        print(f"suggested: run_game.py absent {W} " + " ".join(str(n) for n in sug))
    print("Keep anyone LADA's lines list unless every card row and the reads are empty (a late arrival looks absent); "
          "an absent goalie makes the next one the goalie of the game.")


def cmd_absent(a):
    """Record roster numbers that didn't play (W/full/rink.json "absent"); with no numbers, show the roster as the
    pipeline sees it. `--suggest` tables the evidence per player. `--clear` forgets the list. Everything after
    prepare must be redone when it changes."""
    W = os.path.abspath(a.W)
    p = f"{W}/full/rink.json"
    cfg = json.load(open(p)) if os.path.exists(p) else {}
    if a.clear:
        cfg.pop("absent", None); json.dump(cfg, open(p, "w"))
    elif a.numbers:
        cfg["absent"] = sorted({int(n) for n in a.numbers} | set(cfg.get("absent", []))); json.dump(cfg, open(p, "w"))
    os.environ["ROSTER_ABSENT"] = ",".join(str(n) for n in cfg.get("absent", []))
    if a.suggest:
        suggest_absent(W)
    from roster import MEMBERS, SUBS, GOALIE_NAMES, ALL_SKATERS, TEAM
    absent = cfg.get("absent", [])
    print(f"{TEAM}: absent this game: " +
          (", ".join(f"#{n} {ALL_SKATERS.get(n) or GOALIE_NAMES.get(n, '?')}" for n in absent) or "nobody"))
    print("  skaters:", ", ".join(f"#{n} {v}" for n, v in sorted(MEMBERS.items())))
    print("  subs:   ", ", ".join(f"#{n} {v}" for n, v in sorted(SUBS.items())) or "-")
    print("  goalies:", ", ".join(f"#{n} {v}" for n, v in GOALIE_NAMES.items() if n not in absent) or "-")
    if absent and any(os.path.exists(f"{W}/rev_{P['label'].lower()}/manifest.csv") for P in periods(W)):
        print("  prepare has run already: its sheets and roster cards used the old roster. Move W/p* and W/rev_p* "
              "aside and prepare again, unless the review has started (then solve alone picks the change up).")


def _review_options(W, a=None):
    """Options for the reviewer prompts, kept in W/review.json so a re-run (missing sheets) uses the same ones."""
    p = f"{W}/review.json"
    opt = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    if a is not None:
        if a.opp:
            opt["opp"] = a.opp
        if a.note:
            opt["notes"] = opt.get("notes", []) + [n for n in a.note if n not in opt.get("notes", [])]
        if a.chunk:
            opt["chunk"] = a.chunk
        json.dump(opt, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    return opt


def _review_coverage(W, P):
    """Per sheet of a period: rows in the manifest, rows missing an answer, and whether the reviewer's file mentions
    a failed read. Returns (manifest, dict sheet -> info)."""
    from apply_review import parse_review
    rv = f"{W}/rev_{P['label'].lower()}"
    man = pd.read_csv(f"{rv}/manifest.csv")
    ans, trouble = {}, {}
    for f in sorted(glob.glob(f"{rv}/review_*.txt")):
        txt = open(f, encoding="utf-8", errors="replace").read()
        for _, r in parse_review(txt).iterrows():
            ans[r.row_id] = r.player
        if re.search(r"(fail|could not|couldn't|unable|error|not load|timed out)", txt, re.I):
            trouble[os.path.basename(f)] = True
    info = {}
    for sheet, g in man.groupby("sheet", sort=True):
        rows = list(g.row_id)
        fn = f"review_s{sheet[6:9]}.txt"
        info[sheet] = dict(rows=len(rows), missing=[r for r in rows if r not in ans], file=fn, trouble=trouble.get(fn, False))
    return man, info


def cmd_review(a):
    """Fill pipeline/review_prompt.md once per chunk of sheets and write it to W/rev_pN/prompt_cNN.md, with the
    roster (minus absent players), our jersey, the goalie, empty roster-card rows (point at another period's card,
    or say the player probably didn't play), the opponents' look and any notes. Chunks whose sheets are fully
    reviewed are marked done, so after a partial run this is the list of what is left to launch."""
    from roster import SKATERS, GOALIES, ABSENT, ALL_SKATERS
    from reads import load_reads
    W = os.path.abspath(a.W).replace("\\", "/")
    opt = _review_options(W, a)
    chunk = int(opt.get("chunk", 3))
    cfg = json.load(open(f"{W}/full/rink.json")) if os.path.exists(f"{W}/full/rink.json") else {}
    jersey = cfg.get("jersey", "light blue")
    jersey_desc = "white jerseys with blue numbers and blue trim" if jersey.startswith("white") else "light-blue jerseys"
    opp_desc = opt.get("opp") or ("dark or red jerseys" if jersey.startswith("white") else "white or dark jerseys")
    tmpl = open(f"{HERE}/review_prompt.md", encoding="utf-8").read()
    roster = ", ".join(f"#{n} {v.upper()}" for n, v in sorted(SKATERS.items()))
    goalie_line = (f"#{GOALIES[0]} is the goalie" if GOALIES else "Our goalie is not on the card") + \
        ' (big leg pads): report "G" for goalie rows.'
    Ps = periods(W)
    empty = {}
    for P in Ps:
        p = f"{W}/rev_{P['label'].lower()}/card_empty.json"
        empty[P["label"]] = set(json.load(open(p))) if os.path.exists(p) else set()
    reads, _ = load_reads(f"{W}/full")
    nreads = reads.num.value_counts()
    notes = "".join(f" {n.rstrip('.')}." for n in opt.get("notes", []))
    plan, todo = [], 0
    for P in Ps:
        lab = P["label"]; rv = f"{W}/rev_{lab.lower()}"
        if not os.path.exists(f"{rv}/manifest.csv"):
            log(f"{lab}: not prepared yet"); continue
        card_notes = ""; out, maybe = [], []
        for n in sorted(empty[lab]):
            if n not in SKATERS:
                continue
            other = next((Q["label"] for Q in Ps if Q["label"] != lab and n not in empty[Q["label"]]), None)
            if other:
                card_notes += (f" #{n} {SKATERS[n].upper()}'s row on this period's card is empty: also Read "
                               f"{W}/rev_{other.lower()}/roster_card.jpg for his look (that is another period; use only its #{n} row).")
            elif nreads.get(n, 0) < 30:
                out.append(f"#{n}")
            else:
                maybe.append(f"#{n} ({int(nreads.get(n, 0))} reads)")
        if out:
            card_notes += (f" {', '.join(out)} probably did not play this game (no row on any period's card and almost no "
                           f"reads); give one of these numbers only if you clearly read it.")
        if maybe:
            card_notes += (f" {', '.join(maybe)}: no row on any period's card, but the number was read often, so the "
                           f"player may have played; report the number if you see it.")
        man, info = _review_coverage(W, P)
        sheets = sorted(info)
        for k in range(0, len(sheets), chunk):
            cs = sheets[k:k + chunk]; cid = f"c{k // chunk:02d}"
            left = [x for x in cs if info[x]["missing"]]
            scratch = f"{W}/scratch/{lab.lower()}_{cid}"
            text = tmpl.format(rev=rv, scratch=scratch, jersey_desc=jersey_desc,
                               roster=roster, card_notes=card_notes, notes=notes, goalie_line=goalie_line,
                               sheets=", ".join(left or cs), opp_desc=opp_desc)
            pf = f"{rv}/prompt_{cid}.md"
            open(pf, "w", encoding="utf-8").write(text)
            state = "done" if not left else f"todo ({sum(len(info[x]['missing']) for x in left)} rows)"
            plan.append(f"{lab} {cid} {' '.join(x[:-4] for x in cs)} -> {pf}  [{state}]")
            todo += bool(left)
    open(f"{W}/review_plan.txt", "w", encoding="utf-8").write("\n".join(plan) + "\n")
    print("\n".join(plan))
    print(f"{todo} chunk(s) to launch: for each, one general-purpose subagent whose whole prompt is\n"
          f"  'Read <prompt file> and do exactly what it says. Reply with one line: how many rows you wrote.'\n"
          f"  About 6 at a time. Then `run_game.py check {a.W}`.")
    if ABSENT:
        print("absent (not on the roster above):", ", ".join(f"#{n} {ALL_SKATERS.get(n, '?')}" for n in sorted(ABSENT)))


def cmd_check(a):
    """Review coverage: every manifest row needs an answer in some review_*.txt (apply_review.parse_review, as solve
    reads them). Lists missing rows per sheet and files whose notes mention failed image reads. Exit status 1 while
    rows are missing."""
    W = os.path.abspath(a.W)
    missing_total = 0
    for P in periods(W):
        lab = P["label"]
        if not os.path.exists(f"{W}/rev_{lab.lower()}/manifest.csv"):
            continue
        man, info = _review_coverage(W, P)
        miss = {s: i["missing"] for s, i in info.items() if i["missing"]}
        n_miss = sum(len(m) for m in miss.values())
        missing_total += n_miss
        print(f"{lab}: {len(man)} rows in {len(info)} sheets, {len(man) - n_miss} answered" +
              (f", {n_miss} missing" if n_miss else ""))
        for s, m in miss.items():
            print(f"  {s}: missing {', '.join(m)}" + ("  (whole sheet)" if len(m) == info[s]["rows"] else ""))
        for s, i in info.items():
            if i["trouble"]:
                print(f"  {i['file']} mentions a failed read: look, and redo the sheet with a fresh reviewer if so "
                      f"(move the old file to old_{i['file']})")
    if missing_total:
        print(f"{missing_total} rows still missing: `run_game.py review {a.W}` lists the chunks to relaunch")
        sys.exit(1)
    print("every review row is answered")


def cmd_prepare(a):
    W = os.path.abspath(a.W)
    for P in periods(W):
        p = P["label"].lower(); pd_ = f"{W}/{p}"; rv = f"{W}/rev_{p}"
        if os.path.exists(f"{rv}/manifest.csv"):
            log(f"{p}: already prepared (reviews are tied to this segmentation; not redoing)")
            continue
        sh(PY, f"{HERE}/run_period.py", f"{W}/full", pd_, P["start"], P["end"], P["net"])
        sh(PY, f"{HERE}/review_sheets.py", pd_, rv, 8)
        sh(PY, f"{HERE}/roster_card.py", pd_, f"{rv}/roster_card.jpg", 8)
        n = len(glob.glob(f"{rv}/sheet_*.jpg"))
        log(f"{p}: {n} review sheets in {rv}")


def cmd_solve(a):
    W = os.path.abspath(a.W)
    labels = []
    for P in periods(W):
        p = P["label"].lower()
        # off: a player seen off the ice by hand (his track ends mid-ice, so nothing ends his shift), 5 still on
        tgt = [[k["start"], k["end"], 5, k["player"]] for k in P.get("off", [])]
        tgt += [[k["start"], k["end"], 5, k["player"], "on"] for k in P.get("on", [])]   # seen on the ice, track lost
        tgt += [[k["start"], k["end"], 4, k.get("player")] for k in P.get("pk", [])]   # player: off, in the box
        tgt += [[k["start"], k["end"], 6] for k in P.get("extra", [])]   # our goalie pulled for an extra attacker
        sh(PY, f"{HERE}/run2.py", f"{W}/{p}", f"{W}/rev_{p}", P["end"], json.dumps(live_spans(P)), json.dumps(tgt))
        sh(PY, f"{HERE}/gantt.py", f"{W}/{p}/shifts_final.csv", f"{W}/{p}/segs_final.csv", f"{W}/gantt_{p}.png",
           P["start"], P["end"])
        labels.append(f"{p}:{P['label']}")
    sh(PY, f"{HERE}/final_stats.py", *labels, cwd=W)
    # live play vs stoppages -> "play" column in shifts_all.csv + stoppages.json
    sh(PY, f"{HERE}/stoppages.py", f"{W}/full", f"{W}/periods.json", f"{W}/shifts_all.csv")
    A = pd.read_csv(f"{W}/shifts_all.csv")
    for P in periods(W):   # shift seconds vs 5 skaters for the whole period (4 inside penalty kills, 6 with the goalie pulled)
        length = P["end"] - P["start"]; pk = sum(k["end"] - k["start"] for k in P.get("pk", []))
        ex = sum(k["end"] - k["start"] for k in P.get("extra", []))
        ps = sum(k["end"] - k["start"] for k in P.get("ps", []))
        want = 5 * (length - ps) - pk + ex; have = int(A[A.period == P["label"]].dur.sum())
        print(f"{P['label']}: {have} s of shifts; 5 x {length - ps} s - {pk} s of penalty kill"
              + (f" + {ex} s of extra attacker" if ex else "") + f" = {want} s ({have / want:.0%})")
    lineup_check(W)
    log(f"gantt charts: {W}/gantt_*.png (the bottom panel should sit at 5, 4 during a penalty kill); look at them "
        f"when the lineup check lists something")


def live_spans(P):
    """The period minus its penalty shots against us ("ps": [{"start", "end"}]): while their shooter faces our goalie,
    all our skaters are at the bench, so the solver puts nobody on, as in an intermission."""
    spans, t = [], P["start"]
    for k in sorted(P.get("ps", []), key=lambda k: k["start"]):
        spans.append([t, k["start"]]); t = k["end"]
    return spans + [[t, P["end"]]]


def _target(Ps, T):
    """Skaters expected on the ice per second: 5, one fewer per penalty kill (never under 3), one more with the
    goalie pulled, none during a penalty shot against us."""
    tgt = np.full(T, 5.0)
    for P in Ps:
        for k in P.get("pk", []):
            tgt[int(k["start"]):int(k["end"])] -= 1
        for k in P.get("extra", []):
            tgt[int(k["start"]):int(k["end"])] += 1
    tgt = np.maximum(tgt, 3)
    for P in Ps:
        for k in P.get("ps", []):
            tgt[int(k["start"]):int(k["end"])] = 0
    return tgt


def lineup_windows(W, min_len=15):
    """Stretches of min_len+ seconds where the published shifts (shifts_all.csv) don't put the expected number of us
    on the ice, and goals in highlights.json with the wrong count or a credited player off the ice. Returns
    (windows, goal_notes): each window a dict with period, t0, t1, n_on, expected, mid, on_mid (who the shifts have
    on at the midpoint) and live (seconds of the window outside the estimated stoppages, None without
    stoppages.json); goal_notes are strings."""
    A = pd.read_csv(f"{W}/shifts_all.csv")
    Ps = periods(W)
    T = int(max(P["end"] for P in Ps)) + 2
    tgt = _target(Ps, T)
    cnt = np.zeros(T)
    for r in A.itertuples():   # a shift covers the seconds t with t0 <= t < t1
        cnt[int(np.ceil(r.t0)):min(int(np.ceil(r.t1)), T)] += 1
    live = None
    if os.path.exists(f"{W}/stoppages.json"):
        live = np.zeros(T, bool)
        for P in Ps:
            live[int(P["start"]):int(P["end"])] = True
        for a, b in json.load(open(f"{W}/stoppages.json")):
            live[int(a):int(b)] = False
    def on(t):
        return sorted(int(p) for p in A[(A.t0 <= t) & (A.t1 > t)].player)
    windows = []
    for P in Ps:
        run = None
        for t in range(P["start"], P["end"] + 1):
            d = (cnt[t] - tgt[t]) if t < P["end"] else None
            if run and d != run[1]:
                if t - run[0] >= min_len:
                    mid = (run[0] + t) // 2
                    windows.append(dict(period=P["label"], t0=run[0], t1=t, n_on=int(tgt[run[0]] + run[1]),
                                        expected=int(tgt[run[0]]), mid=mid, on_mid=on(mid),
                                        live=int(live[run[0]:t].sum()) if live is not None else None))
                run = None
            if d and not run:
                run = (t, d)
    notes = []
    hp = f"{W}/highlights.json"
    for h in (json.load(open(hp)) if os.path.exists(hp) else []):
        if h["type"] != "goal":
            continue
        t = int(h["t"])
        if len(on(t)) != tgt[t]:
            notes.append(f"  goal at {t}: on the ice {on(t)}, expected {int(tgt[t])} skaters")
        # the game sheet's scorer and assists (optional "scorer": 54, "assists": [36]) must be on the ice
        credited = [int(h["scorer"])] if h.get("scorer") else []
        credited += [int(x) for x in h.get("assists", [])]
        for p in credited:
            if h.get("team", "for") == "for" and p not in on(t):
                notes.append(f"  goal at {t}: #{p} is credited on the game sheet but not on the ice ({on(t)})")
    return windows, notes


def _window_line(w):
    s = (f"  {w['period']} {w['t0']}-{w['t1']} ({w['t1'] - w['t0']} s): {w['n_on']} on the ice, expected "
         f"{w['expected']}; on at {w['mid']}: {w['on_mid']}")
    if w["live"] is not None:
        s += "; all of it in a stoppage" if w["live"] == 0 else f"; {w['live']} s of it live"
    return s


def lineup_check(W, min_len=15):
    """Print the lineup check (see lineup_windows). Each window is a missed player, an unlisted penalty, a bad label
    or a slow line change during a stoppage; `run_game.py gaps` writes the briefs for checking them by eye."""
    windows, notes = lineup_windows(W, min_len)
    bad = [_window_line(w) for w in windows] + notes
    log("lineup check: " + ("OK" if not bad else f"{len(bad)} to look at"))
    for b in bad:
        print(b)
    if windows:
        print(f"  -> `run_game.py gaps {W}` writes the by-eye check briefs for these windows")
    return windows


# ---------------------------------------------------------------- gaps: the by-eye check of the lineup windows

def _bench_sitters(W, P, R, min_len=20, min_frac=0.6):
    """Labeled segments of min_len+ s that spend most of their frames in our bench zone: a player sitting at the
    bench whom the tracker followed as if he were on the ice (Snoqualmie's benches sit right by the camera)."""
    p = P["label"].lower()
    S = pd.read_csv(f"{W}/{p}/segs_final.csv"); tr = pd.read_csv(f"{W}/{p}/tracks_v1.csv")
    tr = tr.assign(bz=np.asarray(R.bench_zone(tr.fx, tr.rel)))
    out = []
    for s_ in S[(S.plabel >= 0) & (S.t1 - S.t0 >= min_len)].itertuples():
        g = tr[(tr.tid == s_.tid) & (tr.t >= s_.t0) & (tr.t <= s_.t1)]
        if len(g) and g.bz.mean() >= min_frac:
            out.append((int(s_.plabel), int(s_.tid), s_.t0, s_.t1, float(g.bz.mean())))
    return out


def cmd_gaps(a):
    """From the lineup check's windows write one filled checker prompt per period (W/scratch/gaps/prompt_pN.md,
    pipeline/gap_prompt.md): the team's look, the rink, the roster, the known events, each window with the tracked
    pieces behind it, and long pieces that sit at our bench. Each prompt is one general-purpose subagent's whole job;
    it writes fixes.json in its scratch folder. `gaps W --apply` then merges every fixes.json into periods.json
    (on/off spans) for the next solve."""
    from roster import SKATERS, GOALIES, ABSENT, TEAM, GOALIE_NAMES
    W = os.path.abspath(a.W).replace("\\", "/")
    gdir = f"{W}/scratch/gaps"; os.makedirs(gdir, exist_ok=True)
    if a.apply is not None:
        return apply_fixes(W, a.apply or sorted(glob.glob(f"{gdir}/*/fixes.json")))
    if not os.path.exists(f"{W}/shifts_all.csv"):
        sys.exit("no shifts_all.csv: solve first")
    R = rink(f"{W}/full")
    Ps = periods(W)
    windows, notes = lineup_windows(W, a.min_len)
    pending = sorted(glob.glob(f"{gdir}/*/fixes.json"))
    if pending:
        print("fixes not yet applied (`gaps --apply` merges them into periods.json):", ", ".join(pending))
    cfg = json.load(open(f"{W}/full/rink.json")) if os.path.exists(f"{W}/full/rink.json") else {}
    opt = _review_options(W)
    jersey = cfg.get("jersey", "light blue")
    jersey_desc = ("WHITE jerseys with blue numbers and blue trim" if jersey.startswith("white")
                   else "LIGHT-BLUE jerseys with white numbers")
    opp_desc = (opt.get("opp") or ("dark or red jerseys" if jersey.startswith("white") else "white or dark jerseys")).rstrip(".")
    notes_txt = "".join(f" {n.rstrip('.')}." for n in opt.get("notes", []))
    roster = ", ".join(f"#{n} {v.upper()}" for n, v in sorted(SKATERS.items()))
    if GOALIES:
        goalie_line = f"Our goalie is #{GOALIES[0]} {GOALIE_NAMES.get(GOALIES[0], '').upper()} (big leg pads), never a skater."
    else:
        goalie_line = "Our goalie isn't on the roster card (a sub in goal, big leg pads); he is never a skater."
    side = lambda P: "LEFT" if P["net"] < R.center_x else "RIGHT"
    nets_line = "Our net is the " + ", ".join(f"{side(P)} one in {P['label']}" for P in Ps) + " (the goalie's end)."
    cards = [f"{W}/rev_{P['label'].lower()}/roster_card.jpg" for P in Ps]
    card = next((c for c in cards if os.path.exists(c)), cards[0])
    bside = R.side
    bx0, bx1, by0, by1 = R.bench_view()
    rink_desc = f"{cfg.get('rink', 'renton')}: {(R.__class__.__doc__ or '').strip().split('. ')[0].rstrip('.')}."
    bench_desc = (f"Our bench is {R.bench_where[bside]}; `--view bench` crops x {bx0}-{bx1}, y {by0}-{by1}. "
                  f"The opponents' bench is the other one.")
    box_desc = f" Our penalty box is {R.box_where[bside]}; a boxed player is off the ice (the solver knows the pk spans)."
    hl = json.load(open(f"{W}/highlights.json")) if os.path.exists(f"{W}/highlights.json") else []
    sheet_ = json.load(open(f"{W}/sheet.json", encoding="utf-8")) if os.path.exists(f"{W}/sheet.json") else {}
    tmpl = open(f"{HERE}/gap_prompt.md", encoding="utf-8").read()
    man = {}
    for P in Ps:
        mp = f"{W}/rev_{P['label'].lower()}/manifest.csv"
        if os.path.exists(mp):
            m = pd.read_csv(mp); man[P["label"]] = dict(zip(m.tid, m.row_id))
    plan = []
    for P in Ps:
        lab = P["label"]; p = lab.lower()
        ws = [w for w in windows if w["period"] == lab]
        sitters = _bench_sitters(W, P, R) if os.path.exists(f"{W}/{p}/tracks_v1.csv") else []
        if not ws and not sitters:
            continue
        ev = []
        for k in P.get("pk", []):
            ev.append(f"penalty kill {k['start']}-{k['end']}" + (f" with #{k['player']} in the box" if k.get("player") else "")
                      + " (4 skaters expected)")
        for k in P.get("extra", []):
            ev.append(f"goalie pulled {k['start']}-{k['end']} (6 skaters expected)")
        for k in P.get("ps", []):
            ev.append(f"penalty shot against us {k['start']}-{k['end']} (nobody of ours on the ice)")
        goals = [(int(h["t"]), h.get("team", "for"), h.get("scorer")) for h in hl if h.get("type") == "goal"] or \
                [(g["video_t"], g["team"], g.get("scorer")) for g in sheet_.get("goals", []) if g.get("video_t")]
        for t, team, sc in sorted(goals):
            if P["start"] <= t <= P["end"]:
                ev.append(f"goal {'for us' if team == 'for' else 'against us'} at about {t}" + (f" (#{sc})" if team == "for" and sc else ""))
        ev_txt = (f"\nKnown events in {lab} ({P['start']}-{P['end']} s of video): " + "; ".join(ev) + ".\n") if ev else ""
        S = pd.read_csv(f"{W}/{p}/segs_final.csv") if os.path.exists(f"{W}/{p}/segs_final.csv") else None
        wl = []
        for k, w in enumerate(ws, 1):
            live = "" if w["live"] is None else (" all of it in a stoppage;" if w["live"] == 0 else f" {w['live']} s of it live;")
            line = (f"{k}. {lab} {w['t0']}-{w['t1']} ({w['t1'] - w['t0']} s;{live} the solver has {w['n_on']} on, "
                    f"expected {w['expected']}): {w['on_mid']}.")
            if S is not None:
                ov = S[(S.t1 > w["t0"] - 3) & (S.t0 < w["t1"] + 3) & ((S.plabel >= 0) | (S.t1 - S.t0 >= 5))]
                pieces = []
                for s_ in ov.sort_values("t0").itertuples():
                    who = f"#{int(s_.plabel)}" if s_.plabel >= 0 else "unlabeled"
                    src = f", label {'reviewed' if s_.src == 'review' else 'read'}" if s_.num >= 0 else ""
                    row = man.get(lab, {}).get(s_.tid)
                    ends = (" starts at the bench" if s_.bench0 else "") + (" ends at the bench" if s_.bench1 else "")
                    pieces.append(f"{who} tid {int(s_.tid)}{f' ({row})' if row else ''} {s_.t0:.0f}-{s_.t1:.0f}{src}{ends}")
                if pieces:
                    line += "\n   pieces: " + "; ".join(pieces)
            wl.append(line)
        st_txt = ""
        if sitters:
            st_txt = ("\nLong tracked pieces that stay in our bench zone (a player sitting at the bench whom the tracker "
                      "counted as on the ice? check each: if he was sitting, that is an \"off\" span over the piece "
                      "until he climbs over the boards):\n" +
                      "\n".join(f"- #{pl} tid {tid}{f' ({man.get(lab, {}).get(tid)})' if man.get(lab, {}).get(tid) else ''} "
                                f"{t0:.0f}-{t1:.0f}, {fr:.0%} of its frames at the bench" for pl, tid, t0, t1, fr in sitters) + "\n")
        chunk = max(1, a.chunk)
        for c in range(0, max(len(wl), 1), chunk):
            suffix = "" if len(wl) <= chunk else "abcdefgh"[c // chunk]
            scratch = f"{gdir}/{p}{suffix}"
            text = tmpl.format(W=W, PY=PY.replace("\\", "/"), ROOT=ROOT.replace("\\", "/"), scratch=scratch,
                               team_desc=TEAM, jersey_desc=jersey_desc, opp_desc=opp_desc, roster=roster,
                               notes=notes_txt, goalie_line=goalie_line, nets_line=nets_line, card=card,
                               rink_desc=rink_desc, frame_size=f"{R.size[0]}x{R.size[1]}", bench_desc=bench_desc,
                               box_desc=box_desc, events=ev_txt,
                               windows="\n".join(wl[c:c + chunk]) or "(none this period; only the bench pieces below)",
                               sitters=st_txt if c == 0 else "", out_file=f"{scratch}/fixes.json")
            pf = f"{gdir}/prompt_{p}{suffix}.md"
            open(pf, "w", encoding="utf-8").write(text)
            plan.append(f"{lab}{suffix}: {len(wl[c:c + chunk])} window(s)" + (f", {len(sitters)} bench piece(s)" if sitters and c == 0 else "") + f" -> {pf}")
    for n in notes:
        print(n)
    if not plan:
        print("lineup check: OK; nothing to brief" + (f"; {len(notes)} goal note(s) above" if notes else ""))
        return
    print("\n".join(plan))
    print(f"{len(plan)} prompt(s): for each, one general-purpose subagent whose whole prompt is\n"
          f"  'Read <prompt file> and do exactly what it says. Reply with one line per window.'\n"
          f"  Then `run_game.py gaps {a.W} --apply` merges their fixes.json files into periods.json, and solve again.")
    if ABSENT:
        print("absent (not on the roster above):", ", ".join(f"#{n}" for n in sorted(ABSENT)))


def apply_fixes(W, files):
    """Merge gap checkers' fixes.json files ([{"period", "kind": "on"|"off", "player", "start", "end", "why"}, ...])
    into periods.json; entries with "ok" or "unsure" are printed, not applied. Applied files are renamed."""
    Ps = periods(W)
    have = {(P["label"], k, int(e["player"]), round(float(e["start"]), 1), round(float(e["end"]), 1))
            for P in Ps for k in ("on", "off") for e in P.get(k, [])}
    added = 0
    if not files:
        print("no fixes.json to apply (checkers write W/scratch/gaps/<period>/fixes.json)")
        return
    for f in files:
        try:
            fixes = json.load(open(f, encoding="utf-8"))
        except ValueError as e:
            print(f"{f}: not JSON ({e}); skipped"); continue
        print(f"{f}:")
        for e in fixes if isinstance(fixes, list) else [fixes]:
            if not isinstance(e, dict):
                continue
            if e.get("kind") not in ("on", "off"):
                print(f"  noted {e.get('period', '')} {e.get('window', '')}: {e.get('ok') or e.get('unsure') or e}")
                continue
            try:
                player, t0, t1 = int(e["player"]), float(e["start"]), float(e["end"])
            except (KeyError, TypeError, ValueError):
                print(f"  bad entry, skipped: {e}"); continue
            P = next((P for P in Ps if P["label"] == e.get("period")), None) or \
                next((P for P in Ps if P["start"] <= t0 <= P["end"]), None)
            if P is None or t1 <= t0:
                print(f"  no period for {e}; skipped"); continue
            t0, t1 = max(t0, P["start"]), min(t1, P["end"])
            key = (P["label"], e["kind"], player, round(t0, 1), round(t1, 1))
            if key in have:
                print(f"  already in periods.json: {P['label']} {e['kind']} #{player} {t0}-{t1}"); continue
            P.setdefault(e["kind"], []).append(dict(start=t0, end=t1, player=player))
            have.add(key); added += 1
            print(f"  + {P['label']} {e['kind']:3s} #{player} {t0}-{t1}: {e.get('why') or e.get('note', '')}")
        os.replace(f, f[:-5] + ".applied.json")
    if added:
        for P in Ps:
            for k in ("on", "off"):
                if k in P:
                    P[k] = sorted(P[k], key=lambda x: (x["start"], x["player"]))
        json.dump(Ps, open(f"{W}/periods.json", "w"), indent=1)
    print(f"{added} span(s) added to {W}/periods.json" + ("; solve again" if added else ""))


LADA_API = "https://api.ladaseattle.com/api/v1"


def _lada_get(path):
    import urllib.request
    with urllib.request.urlopen(f"{LADA_API}/{path}", timeout=20) as r:
        return json.load(r)


def lada_games_path():
    from roster import TEAM_DIR
    return f"{TEAM_DIR}/lada_games.json"


def update_lada_games():
    """Remember the team's games from LADA's public API in teams/<slug>/lada_games.json: the upcoming ones
    (`game/next/30`: id, date, opponent, home/away, rink, planned lines) and the last one played (score, game sheet
    link). LADA only ever shows the single last game, so a game published a week late would have lost its id;
    the cache keeps every game it has seen. Best effort: a network problem just leaves the file as it is."""
    from roster import LADA_TEAM_ID
    p = lada_games_path()
    games = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    seen = 0
    for path in (f"team/{LADA_TEAM_ID}/game/next/30", f"team/{LADA_TEAM_ID}/game/last"):
        try:
            got = _lada_get(path)
        except Exception as e:
            log(f"LADA {path} unavailable ({e})")
            continue
        for g in got if isinstance(got, list) else [got]:
            if not g.get("id"):
                continue
            cur = games.setdefault(str(g["id"]), {})
            for k in ("date", "opponentName", "playHome", "rinkId", "rinkName", "lines", "teamGoals", "opponentGoals",
                      "boxscoreLink"):
                if g.get(k) is not None:
                    cur[k] = g[k]
            seen += 1
    rinks = {g["rinkId"]: g["rinkName"] for g in games.values() if g.get("rinkId") and g.get("rinkName")}
    for i, g in games.items():   # a game seen only as "last" lacks home/away, rink and lines: the game record has them
        if "playHome" in g:
            continue
        try:
            rec = _lada_get(f"game/{i}")
        except Exception:
            continue
        for k in ("playHome", "rinkId", "lines", "teamGoals", "opponentGoals", "boxscoreLink"):
            if rec.get(k) is not None:
                g[k] = rec[k]
        if rec.get("rinkId") in rinks:
            g["rinkName"] = rinks[rec["rinkId"]]
        seen += 1
    if seen:
        games = dict(sorted(games.items(), key=lambda kv: kv[1].get("date", "")))
        json.dump(games, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    return games


def lada_game_id(date):
    """LADA's id for our game on `date` (YYYY-MM-DD), from the cache (update_lada_games) or the league's "last game"
    call. None, with a note to set it by hand, when neither knows the game."""
    games = update_lada_games()
    hits = [int(i) for i, g in games.items() if str(g.get("date", ""))[:10] == date]
    if hits:
        return hits[0]
    found = probe_lada_games(date)
    if found:
        return found
    log(f"LADA doesn't list a game on {date} (teams/<slug>/lada_games.json); set lada_game_id in game.json by hand")
    return None


def probe_lada_games(date, span=40):
    """LADA hands out game ids in schedule order, so a game that has dropped out of "last" sits near the ids of
    the other teams' games around that date. Look at the ids every team's cache and published games know, probe
    `game/<id>` around the nearest ones for this team's games, remember every one found, and return the id of
    the game on `date` if any."""
    from roster import LADA_TEAM_ID, REPO
    known = {}
    for f in glob.glob(f"{REPO}/teams/*/lada_games.json"):
        for i, g in json.load(open(f, encoding="utf-8")).items():
            known[int(i)] = str(g.get("date", ""))[:10]
    for f in glob.glob(f"{REPO}/teams/*/games/*/game.json"):
        g = json.load(open(f, encoding="utf-8"))
        if g.get("lada_game_id"):
            known[int(g["lada_game_id"])] = g.get("date", "")
    if not known:
        return None
    anchors = sorted(known, key=lambda i: abs(int(known[i][:4] + known[i][5:7] + known[i][8:10]) - int(date.replace("-", ""))) if len(known[i]) >= 10 else 10 ** 9)[:3]
    p = lada_games_path()
    games = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    found = None; seen = set()
    for a in anchors:
        for d in range(-span, span + 1):
            i = a + d
            if i in seen or i in known and known[i] != date and i not in [int(k) for k in games]:
                continue
            seen.add(i)
            try:
                g = _lada_get(f"game/{i}")
            except Exception:
                continue
            if g.get("teamId") != LADA_TEAM_ID:
                continue
            cur = games.setdefault(str(i), {})
            cur["date"] = (g.get("dayTime") or "")[:19]
            for k in ("playHome", "rinkId", "lines", "teamGoals", "opponentGoals", "boxscoreLink"):
                if g.get(k) is not None:
                    cur[k] = g[k]
            if cur["date"][:10] == date:
                found = i
                break
        if found:
            break
    if games:
        games = dict(sorted(games.items(), key=lambda kv: kv[1].get("date", "")))
        json.dump(games, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    if found:
        log(f"LADA game {found} found by probing ids near the other teams' games")
    return found


SN_API = "https://metal-api.sportninja.net/v1"


def _clock_s(txt):
    """'00:17:20' (H:MM:SS of the period clock, counting down) -> seconds."""
    h, m, sec = (int(x) for x in txt.split(":"))
    return h * 3600 + m * 60 + sec


def sportninja_id(date, lada_id=None):
    """The SportNinja game id (the last part of LADA's boxscoreLink) for our game on `date`: from the LADA cache,
    else from LADA's record of `lada_id`."""
    for i, g in update_lada_games().items():
        if str(g.get("date", ""))[:10] == date and g.get("boxscoreLink"):
            return g["boxscoreLink"].rstrip("/").rsplit("/", 1)[-1]
    if lada_id:
        try:
            link = _lada_get(f"game/{lada_id}").get("boxscoreLink") or ""
            return link.rstrip("/").rsplit("/", 1)[-1] or None
        except Exception as e:
            log(f"LADA game {lada_id} unavailable ({e})")
    return None


def cmd_sheet(a):
    """SportNinja's game sheet, public at metal-api.sportninja.net: which side we were, the score, shots per period,
    every goal with its period clock, scorer and assists, every penalty with the player, type and minutes, and who
    played. Prints it and writes W/sheet.json. With periods.json in place, each goal and penalty gets an estimated
    video time (period start + what the clock had run; exact where the clock runs through stoppages, otherwise the
    earliest it can be)."""
    import urllib.request
    from roster import TEAM_NAME, TEAM, ALL_SKATERS, GOALIE_NAMES, SKATERS
    from lada_ids import fold
    W = os.path.abspath(a.W) if a.W else None
    m = re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(W or ""))
    date = a.date or (m.group(0) if m else None)
    sn = a.sn or (sportninja_id(date, a.lada) if date else None)
    if not sn:
        sys.exit("no SportNinja game found: give --sn <id> (the end of LADA's boxscoreLink) or --lada <LADA game id>")
    with urllib.request.urlopen(f"{SN_API}/games/{sn}", timeout=30) as r:
        g = json.load(r)["data"]
    home, vis = g["homeTeam"], g["visitingTeam"]
    names = {home["id"]: home["name"], vis["id"]: vis["name"]}
    mine = [t for t in (home, vis) if fold(TEAM_NAME) in fold(t["name"]) or fold(t["name"]) in fold(TEAM_NAME)]
    if not mine:
        sys.exit(f"neither {home['name']!r} nor {vis['name']!r} looks like {TEAM_NAME!r}")
    us = mine[0]["id"]; side = "home" if us == home["id"] else "visiting"; them = vis["id"] if side == "home" else home["id"]
    ros = {r["team_id"]: {p["id"]: p for p in r["players"]} for r in g.get("playerRosters", [])}
    def who(team, pid_):
        p = ros.get(team, {}).get(pid_)
        return (p["player_number"], p["name_last"]) if p else (None, pid_)
    pname = {p["id"]: p["period_type"]["name"] for p in g["periods"]}
    plabel = {p["id"]: f"P{p['period_type']['sort_order']}" for p in g["periods"]}
    pdur = {p["id"]: int(p["duration"] / 1000) for p in g["periods"]}
    Ps = {P["label"]: P for P in periods(W)} if W and os.path.exists(f"{W}/periods.json") else {}
    def video_t(period_id, clock):
        P = Ps.get(plabel[period_id])
        if not P:
            return None
        return int(P["start"] + pdur[period_id] - _clock_s(clock))
    out = dict(sportninja_id=sn, us=side, home=home["name"], visiting=vis["name"],
               score=[g["home_team_score"] if side == "home" else g["visiting_team_score"],
                      g["visiting_team_score"] if side == "home" else g["home_team_score"]],
               rink=f"{(g.get('venue') or {}).get('name', '')} {(g.get('facility') or {}).get('name', '')}".strip(),
               shots={}, goals=[], penalties=[], played=[], played_names=[], not_marked_playing=[])
    for P in g["periods"]:
        ours_, theirs_ = (P["shots_home_count"], P["shots_visiting_count"]) if side == "home" else (P["shots_visiting_count"], P["shots_home_count"])
        out["shots"][plabel[P["id"]]] = [ours_, theirs_]
    for x in sorted(g["goals"], key=lambda x: (pname[x["period_id"]], -_clock_s(x["period_clock_time"]))):
        sh = x["shot"]; num, last = who(sh["team_id"], sh["player_id"])
        assists = [who(sh["team_id"], a_["player"]["id"]) for a_ in x.get("assists", [])]
        out["goals"].append(dict(period=plabel[x["period_id"]], clock=x["period_clock_time"][3:],
                                 team="for" if sh["team_id"] == us else "against", scorer=num, scorer_name=last,
                                 assists=[n for n, _ in assists if n], assist_names=[l for _, l in assists],
                                 video_t=video_t(x["period_id"], x["period_clock_time"])))
    for o in sorted(g["offenses"], key=lambda o: (pname[o["period_id"]], -_clock_s(o["period_clock_time"]))):
        num, last = who(o["team_id"], o["player_id"]) if o.get("player_id") else (None, "bench")
        served = (o.get("penalty") or {}).get("served_by_player_id")
        if served and served != o.get("player_id"):   # a bench minor: someone else sits in the box
            sn_, sl_ = who(o["team_id"], served); last = f"{last}, served by #{sn_} {sl_}"; num = num or sn_
        out["penalties"].append(dict(period=plabel[o["period_id"]], clock=o["period_clock_time"][3:],
                                     team="ours" if o["team_id"] == us else "theirs", player=num, name=last,
                                     type=o["offense_type"]["name"], severity=o["offense_severity"]["name"],
                                     minutes=o["penalty"]["amount"], video_t=video_t(o["period_id"], o["period_clock_time"])))
    for p in ros.get(us, {}).values():
        if p["is_playing"]:
            out["played"].append(p["player_number"]); out["played_names"].append(f"#{p['player_number']} {p['name_last']}")
    out["played"] = sorted(n for n in out["played"] if n is not None)
    known = set(ALL_SKATERS) | set(GOALIE_NAMES)
    out["not_marked_playing"] = sorted(n for n in SKATERS if n not in out["played"])
    out["playing_not_in_roster"] = sorted(x for x in out["played_names"] if int(x.split()[0][1:]) not in known)
    if W:
        json.dump(out, open(f"{W}/sheet.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    tm = lambda t: f"{t // 60}:{t % 60:02d}" if t is not None else "?"
    print(f"{TEAM} were {'HOME' if side == 'home' else 'VISITORS'} vs {names[them]} at {out['rink']}: {out['score'][0]}-{out['score'][1]}")
    print("shots (ours-theirs):", ", ".join(f"{k} {v[0]}-{v[1]}" for k, v in out["shots"].items()),
          f"total {sum(v[0] for v in out['shots'].values())}-{sum(v[1] for v in out['shots'].values())}")
    print("goals:")
    for x in out["goals"]:
        a_ = ", ".join(f"#{n}" for n in x["assists"]) or "-"
        print(f"  {x['period']} {x['clock']} {x['team']:<7} #{x['scorer']} {x['scorer_name']} (A: {a_})  video ~{tm(x['video_t'])}")
    print("penalties:" if out["penalties"] else "penalties: none")
    for o in out["penalties"]:
        print(f"  {o['period']} {o['clock']} {o['team']:<6} #{o['player']} {o['name']} {o['type']} {o['minutes']} min  video ~{tm(o['video_t'])}")
    print("played (sheet):", ", ".join(out["played_names"]))
    if out["not_marked_playing"]:
        print("roster numbers not marked playing (absent candidates; the sheet is the scorekeeper's, so check):",
              ", ".join(f"#{n} {SKATERS[n]}" for n in out["not_marked_playing"]))
    if out["playing_not_in_roster"]:
        print("marked playing but not in roster.json:", ", ".join(out["playing_not_in_roster"]))
    if W:
        print(f"wrote {W}/sheet.json" + ("" if Ps else "; video times appear once periods.json exists"))


def cmd_schedule(a):
    """The team's games LADA knows (the cache plus a fresh look): date, opponent, home or away, rink, LADA id,
    whether a shift sheet exists, and the planned lines' players who have no LADA id in roster.json yet."""
    from roster import GAMES_DIR, LADA_IDS, TEAM
    games = update_lada_games()
    have = {os.path.basename(d)[:10] for d in glob.glob(f"{GAMES_DIR}/*")}
    known = {v: k for k, v in LADA_IDS.items()}
    print(f"{TEAM}: {len(games)} games in LADA's view (* = shift sheet published)")
    for i, g in games.items():
        d = str(g.get("date", ""))[:16].replace("T", " ")
        side = "HOME" if g.get("playHome") else "away" if g.get("playHome") is False else "?"
        score = f" {g['teamGoals']}-{g['opponentGoals']}" if g.get("teamGoals") is not None else ""
        print(f"  {'*' if d[:10] in have else ' '} {d} {side:<4} vs {g.get('opponentName', '?'):<28} {g.get('rinkName', '?'):<13} id {i}{score}")
        lines = g.get("lines")
        if isinstance(lines, str):
            try:
                lines = json.loads(lines)
            except ValueError:
                lines = None
        if isinstance(lines, dict):
            ids = [int(x) for grp in ("offence", "defence") for ln in lines.get(grp, []) for x in ln if x]
            new = [x for x in ids if x not in known]
            listed = sorted(known[x] for x in ids if x in known)
            print(f"      lines: {' '.join(f'#{n}' for n in listed)}" + (f"; LADA ids not in roster.json: {new}" if new else ""))
    print("A LADA id not in roster.json is a player worth asking about (ids come from pipeline/lada_ids.py). The lines "
          "are the plan, not attendance.")


def cmd_publish(a):
    W = os.path.abspath(a.W)
    from reads import load_reads
    from roster import GAMES_DIR
    gd = f"{GAMES_DIR}/{a.game_id}"; os.makedirs(gd, exist_ok=True)
    shutil.copy(f"{W}/shifts_all.csv", f"{gd}/shifts.csv")
    Ps = periods(W)
    from roster import TEAM, OPPONENTS
    import datetime
    reads, names = load_reads(f"{W}/full")
    played = set(pd.read_csv(f"{W}/shifts_all.csv").player)
    lineup_check(W)
    date = a.date or a.game_id[:10]
    d = datetime.date.fromisoformat(date)
    game = dict(
        id=a.game_id, date=date, title=a.title or f"{TEAM} vs {OPPONENTS.get(a.opponent, a.opponent)}, {d:%b} {d.day}",
        eyebrow=a.eyebrow, opponent=a.opponent, video=a.video or open(f"{W}/url.txt").read().strip(),
        periods=[dict(label=P["label"], start=P["start"], end=P["end"]) for P in Ps],
        nets={P["label"]: P["net"] for P in Ps},
        penalty_kills=[dict(period=P["label"], **k) for P in Ps for k in P.get("pk", [])],
        notes=[], video_ends_early=bool(a.video_ends_early),
        fun=dict(name_reads={str(k): int(v) for k, v in names.num.value_counts().items() if k in played}),
        pipeline=dict(detections=sum(1 for _ in open(f"{W}/full/dets.csv")),
                      crops=len(os.listdir(f"{W}/full/crops")) if os.path.isdir(f"{W}/full/crops") else None,
                      reads=int(len(reads)),
                      reviewed=int(sum(len(pd.read_csv(m)) for m in glob.glob(f"{W}/rev_p*/manifest.csv")))))
    gj = f"{gd}/game.json"
    if os.path.exists(gj):  # keep hand-written fields (notes, title tweaks) from an earlier publish
        old = json.load(open(gj))
        for k in ("notes", "title", "eyebrow", "highlights", "video_ends_early", "lada_game_id", "opponent_name", "zones",
                  "shots", "shots_source"):
            if old.get(k):
                game[k] = old[k]
        if game["pipeline"]["crops"] is None and (old.get("pipeline") or {}).get("crops"):
            game["pipeline"]["crops"] = old["pipeline"]["crops"]   # an archived folder has no crops any more
    if not game.get("lada_game_id"):  # links the game to the LADA app's schedule and scores
        game["lada_game_id"] = lada_game_id(date)
    if os.path.exists(f"{W}/stoppages.json"):
        game["stoppages"] = json.load(open(f"{W}/stoppages.json"))
    if os.path.exists(f"{W}/highlights.json"):  # [{type, team|player, t, clip, poster, note}] from the clips step
        game["highlights"] = json.load(open(f"{W}/highlights.json"))
    if os.path.exists(f"{W}/shots.json") and json.load(open(f"{W}/shots.json")).get("checked"):
        game["shots"] = json.load(open(f"{W}/shots.json"))["periods"]   # shots.py, once checked against the board
        game["shots_source"] = "board"
    elif not game.get("shots") and os.path.exists(f"{W}/sheet.json"):
        # the game sheet's shots per period (SportNinja); the board's OCR is wrong more often than not
        sh_shots = json.load(open(f"{W}/sheet.json", encoding="utf-8")).get("shots") or {}
        if all(P["label"] in sh_shots for P in Ps):
            game["shots"] = {P["label"]: sh_shots[P["label"]] for P in Ps}
            game["shots_source"] = "sheet"
    from zones import zone_shares   # time in offence / defence for the trends page (needs the detections)
    game["zones"] = zone_shares(f"{W}/full", game) or game.get("zones")
    json.dump(game, open(gj, "w"), indent=2, ensure_ascii=False)
    # every team, not just $TEAM: the root page counts each team's games, and each team's menu lists the teams with games
    sh(PY, f"{HERE}/build_site.py", env={k: v for k, v in os.environ.items() if k not in ("TEAM", "ROSTER_ABSENT")})
    log(f"wrote {gd}; the sites rebuilt in docs/. Review, then commit and push to publish.")


def _size(path):
    n = 0
    for d, _, fs in os.walk(path):
        n += sum(os.lstat(os.path.join(d, f)).st_size for f in fs)
    return n


def cmd_archive(a):
    """Keep a finished game's data so it can be re-solved later (as ~/hockey-work/2026-09-27-vs-rr): detections, OCR
    reads, tracks, segments, reviews, periods, results, rink. Drop what is big and can be downloaded or regenerated:
    the video and audio, crops, overview frames, the scoreboard frames, contact sheets and charts."""
    W = os.path.abspath(a.W)
    if not os.path.exists(f"{W}/shifts_all.csv"):
        sys.exit(f"{W} has no shifts_all.csv: archive a game only after solve and publish")
    before = _size(W)
    if os.path.exists(f"{W}/scoreboard.npy"):   # the board every second as JPEGs (~20 MB): re-checks without the video
        from scoreboard import compress
        compress(W)
    drop = [f"{W}/{n}" for n in ("video.webm", "audio.m4a", "yolo11m.pt", "scoreboard.npy", "full/crops", "full/ov")]
    drop += glob.glob(f"{W}/*.jpg") + glob.glob(f"{W}/*.png") + glob.glob(f"{W}/rev_p*/*.jpg")
    drop += glob.glob(f"{W}/full/ocr_done_*.txt") + glob.glob(f"{W}/p*/crops")
    drop += glob.glob(f"{W}/video_*.webm")   # the download as it came, kept by fit_size when it scaled the video
    drop += [f"{W}/scratch"]                 # the reviewers' private folders (run_game.py review)
    for p in drop:
        if os.path.islink(p) or os.path.isfile(p):
            os.remove(p)
        elif os.path.isdir(p):
            shutil.rmtree(p)
    log(f"archived {W}: {before / 1e9:.1f} GB -> {_size(W) / 1e6:.0f} MB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch"); f.add_argument("url"); f.add_argument("W"); f.add_argument("--limit", type=float)
    f.add_argument("--team", help="whose game: a folder in teams/ (tk, bw, bt, df, y, r); default the work folder's, else tk")
    f.add_argument("--rink", help="camera geometry (see rink.py); default renton")
    f.add_argument("--jersey", help="our jersey that game (rink.JERSEYS); default light blue")
    f.add_argument("--bench", help="left or right: the side of the frame our bench is on (rink.py); default the rink's usual one")
    j = sub.add_parser("jersey"); j.add_argument("W"); j.add_argument("name")
    s = sub.add_parser("skaters"); s.add_argument("W"); s.add_argument("T0", type=float); s.add_argument("T1", type=float)
    sub.add_parser("prepare").add_argument("W")
    sub.add_parser("goals").add_argument("W")
    sub.add_parser("unknown").add_argument("W")
    sub.add_parser("archive").add_argument("W")
    sc = sub.add_parser("schedule"); sc.add_argument("W", nargs="?", help="a work folder (its team), or --team")
    sc.add_argument("--team", help="the team's slug when there is no work folder yet")
    sh_ = sub.add_parser("sheet"); sh_.add_argument("W", nargs="?", help="work folder (named <...>YYYY-MM-DD<...>)")
    sh_.add_argument("--team"); sh_.add_argument("--date", help="YYYY-MM-DD when the folder name lacks it")
    sh_.add_argument("--sn", help="SportNinja game id (the end of LADA's boxscoreLink)")
    sh_.add_argument("--lada", help="LADA game id, to look the SportNinja id up")
    sub.add_parser("check").add_argument("W")
    ab = sub.add_parser("absent"); ab.add_argument("W"); ab.add_argument("numbers", type=int, nargs="*")
    ab.add_argument("--clear", action="store_true", help="forget the absent list")
    ab.add_argument("--suggest", action="store_true", help="table the evidence per player: sheet, LADA lines, reads, card rows")
    rv = sub.add_parser("review"); rv.add_argument("W")
    rv.add_argument("--opp", help="the opponents' look, e.g. 'white jerseys; they also wear #11 and #43'")
    rv.add_argument("--note", action="append", help="a sentence for every reviewer, e.g. a player's look (repeatable)")
    rv.add_argument("--chunk", type=int, help="sheets per reviewer (3)")
    fr = sub.add_parser("frames"); fr.add_argument("W"); fr.add_argument("out")
    fr.add_argument("--view", help="rink, left-net or right-net (rink.py views) instead of X0 X1 Y0 Y1 TILE_W COLS")
    fr.add_argument("--tile", type=int, help="tile width in px (1000 for the rink, 660 for a net)")
    fr.add_argument("--cols", type=int, help="tiles per row (2 for the rink, 3 for a net)")
    fr.add_argument("--range", type=float, nargs=3, metavar=("T0", "T1", "STEP"), help="times T0, T0+STEP, ... T1")
    fr.add_argument("rest", nargs="*", help="[X0 X1 Y0 Y1 TILE_W COLS] t1 t2 ...")
    c = sub.add_parser("clip"); c.add_argument("W"); c.add_argument("game_id"); c.add_argument("name")
    c.add_argument("t0"); c.add_argument("t1"); c.add_argument("poster"); c.add_argument("focus", nargs="?")
    sub.add_parser("solve").add_argument("W")
    gp = sub.add_parser("gaps"); gp.add_argument("W")
    gp.add_argument("--apply", nargs="*", metavar="FIXES.json", help="merge checkers' fixes into periods.json (default: every scratch/gaps/*/fixes.json)")
    gp.add_argument("--chunk", type=int, default=6, help="windows per checker prompt (6)")
    gp.add_argument("--min-len", type=int, default=15, help="shortest window to list, in seconds (15)")
    p = sub.add_parser("publish"); p.add_argument("W"); p.add_argument("game_id")
    p.add_argument("--opponent", required=True); p.add_argument("--eyebrow", required=True)
    p.add_argument("--date"); p.add_argument("--title"); p.add_argument("--video")
    p.add_argument("--video-ends-early", action="store_true", help="recording stops before the final horn")
    a = ap.parse_args()
    if sys.platform == "win32":   # keep Windows awake while this runs (caffeinate does it on the Mac)
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    if a.cmd in ("fetch", "sheet") and a.W:   # sheet usually runs before fetch has made the folder
        os.makedirs(a.W, exist_ok=True)
    if a.cmd == "fetch":
        open(f"{a.W}/url.txt", "w").write(a.url)
    # the team, before anything imports roster.py: fetch's --team, else the one fetch stored, else Turbo Kings
    cfg = f"{a.W}/full/rink.json" if getattr(a, "W", None) else ""
    team = getattr(a, "team", None) or (json.load(open(cfg)).get("team") if os.path.exists(cfg) else None) or "tk"
    if not os.path.exists(f"{ROOT}/teams/{team}/roster.json"):
        sys.exit(f"unknown team {team!r}: no teams/{team}/roster.json")
    os.environ["TEAM"] = team
    # players marked absent (run_game.py absent) stay out of the roster for every step but the site build
    absent = json.load(open(cfg)).get("absent", []) if os.path.exists(cfg) else []
    os.environ["ROSTER_ABSENT"] = ",".join(str(n) for n in absent)
    {"fetch": cmd_fetch, "skaters": cmd_skaters, "prepare": cmd_prepare, "solve": cmd_solve, "goals": cmd_goals,
     "frames": cmd_frames, "clip": cmd_clip, "publish": cmd_publish, "unknown": cmd_unknown,
     "archive": cmd_archive, "jersey": cmd_jersey, "absent": cmd_absent, "review": cmd_review, "check": cmd_check,
     "schedule": cmd_schedule, "sheet": cmd_sheet, "gaps": cmd_gaps}[a.cmd](a)
