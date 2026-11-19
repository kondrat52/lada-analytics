"""Driver for processing one game. Run with the hockey env's python (see setup_env.sh).

  run_game.py download URL W [--cookies BROWSER]   the video, its audio and title, before fetch (which then skips
                                             them); --cookies firefox: with that browser's YouTube cookies, for a
                                             video YouTube serves only to a signed-in browser (the user runs it)
  run_game.py fetch   URL W [--team SLUG] [--rink NAME] [--jersey NAME] [--bench SIDE] [--limit SEC]   download,
                                             calibrate, detect (auto-restart), OCR, read the board's clock, propose
                                             periods; --team: whose game, a folder in teams/ (tk); --rink: camera
                                             geometry from rink.py (renton); --jersey: our jersey that game (light
                                             blue, white); --bench: left or right, our bench (unless set: the jersey's
                                             at Renton and Snoqualmie, the rink's usual one at Kirkland)
  run_game.py jersey  W NAME                 we wore another jersey than fetch was told: switch to it (and the bench
                                             with it unless it was given), cut its crops from the video (~5 min),
                                             OCR them and check the nets again
  run_game.py skaters W T0 T1               our skaters detected on the ice per 5 s (find penalty kills)
  run_game.py unknown W                      numbers/surnames read that aren't on the roster (new players?)
  run_game.py absent  W [N ...] [--suggest]  roster numbers that didn't play this game (their partial reads would
                                             label others): recorded in W/full/rink.json, honoured by every step;
                                             --suggest tables the evidence (sheet, lines, reads, card rows) and, where
                                             it conflicts, what else was read on the same crops and tracks
  run_game.py schedule W                     the team's games from LADA's public API (ids, home/away, rink, lines)
  run_game.py sheet   W [--sn ID | --lada ID]  the game sheet from SportNinja's public API: score, shots, goals with
                                             scorers, penalties, who played -> W/sheet.json (goals/solve use it);
                                             the ids are kept there, so only the first run needs --sn or --lada
  run_game.py scores [--team T]              every published game's final score from its game sheet into game.json
                                             (sheets get corrected after the game); then build_site.py
  run_game.py goals   W [--brief]            the sheet's goals at the seconds the board's clock implies; after prepare,
                                             candidates too (center-ice faceoffs, long stoppages); --brief writes the
                                             goal and penalty checkers' briefs (W/scratch/goals/prompt_*.md), which
                                             need no tracks
  run_game.py pk      W [--write [--rough]]  our penalty kills from the sheet and the board's clock alone (coincident
                                             minors: none); --write merges them into periods.json for the first solve,
                                             but not those the penalty checker has answered, nor rough ones (a period
                                             without a board clock read) unless --rough
  run_game.py prepare W [--force]            per period: tracking, review sheets, roster card; first checks the bench
                                             and the nets (--force: prepare on nets the checks contradict)
  run_game.py review  W [--opp DESC] [--note TEXT] [--chunk N] [--batch N]   write one filled reviewer prompt per
                                             chunk of sheets (W/rev_pN/prompt_cNN.md); print the next batch of
                                             prompts to launch (20; also W/review_todo.txt) and what the prompts say
                                             beyond the template
  run_game.py check   W [--wait [SECONDS]]   which review rows are still missing or unreadable, per sheet, and the
                                             reviewers' numbers that aren't on the roster; --wait: first block until
                                             the last launch is answered or 540 s pass, then say what is still open
  run_game.py highlights W [--write]         highlights.json from the checkers' answers and the sheet (our scorers
                                             always the sheet's; theirs named in the note), with what doesn't add up;
                                             --write writes it and puts the checker's kills in periods.json in place
                                             of the proposed ones
  run_game.py solve   W                      per period: apply reviews + solve; gantt charts; stats table; checks
  run_game.py gaps    W [--apply [F ...]]    write the by-eye check briefs for the lineup check's windows, the
                                             goals it flags, any shift of 5+ minutes, a player whose ice time
                                             collapses in a period and leads left open (W/scratch/gaps/prompt_pN.md,
                                             one subagent each); --apply merges the checkers' fixes.json into
                                             periods.json as on/off spans and names the items left unanswered
  run_game.py span    W on|off|extra|ps [PLAYER] T0 T1 --note WHY   one hand-made span into its period in
                                             periods.json, logged in W/hand_spans.txt; span W --list prints the log
  run_game.py frames  W OUT.jpg --view rink|left-net|right-net|bench t1 t2 ...   4K frames (cropped) as a sheet, for
                                             verifying; --range T0 T1 STEP instead of times; or the crop by hand:
                                             X0 X1 Y0 Y1 TILE_W COLS t1 t2 ...; --tracks draws our tracked boxes
                                             with track id and the solver's label
  run_game.py follow  W OUT.jpg P TID [TID ...] [--range T0 T1 STEP]   crops of tracked pieces of period P over time,
                                             one row per track id
  run_game.py clip    W GAME_ID NAME T0 T1 POSTER_T [FOCUS]          zoomed clip into <site>/games/<id>/clips;
                                             FOCUS = x px (a net x from rink.py) or #N to follow player N; --tracks
                                             to follow chosen tracks; --dry-run: check the camera path, cut nothing
  run_game.py clips   W GAME_ID [--only NAME,...] [--dry-run]   every clip highlights.json lists (W/clip_args.json
                                             overrides per clip), checked, with a contact sheet each and the
                                             checker's brief (W/scratch/clips/prompt.md)
  run_game.py clipsheet MP4 OUT.jpg [--W W] [--mark LABEL=SEC]   any rendered clip as one image of tiles
  run_game.py publish W GAME_ID --opponent RR [--eyebrow "Sun Sep 27, 2026 · 7:50 PM · Renton"] [--notes TEXT ...]
                                             [--notes-file F] [--no-open | --open]: game.json + shifts.csv, every site
                                             rebuilt, the game's table and fun stats printed, its page opened on a
                                             first publish (--open: on a republish too)
  run_game.py archive W                      after publishing: drop the video, crops and sheets (~5 GB), keep the
                                             game's data (detections, reads, tracks, reviews, the checkers' briefs
                                             and answers in scratch/; ~100 MB)

W is the per-game work folder (outside the repo). Every step skips work that is already done, so re-running
after an interruption continues where it stopped. W/full/rink.json records the team (fetch --team), and every
command works on that team's roster, games and site (roster.py); before fetch has written it, the folder's name
says whose game it is (bw-2026-11-07-vs-db; Turbo Kings' have no prefix). W/periods.json holds the period windows;
fetch writes a proposal, which you check (the nets above all) before prepare; pk --write adds the penalty kills,
highlights --write the checker's, gaps --apply and span the on/off spans (add_span: one rule for duplicates). Every
command sets ROSTER_ABSENT from rink.json's "absent" list, so roster.py leaves those players out (see `absent`).
"""
import argparse, glob, json, os, re, shutil, signal, subprocess, sys, time
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable
FPS = 8
# OCR workers x onnxruntime threads each. On the PC (i9-9900K, 8 cores / 16 threads) single-threaded workers read the
# same rows faster than 4 x 2, whose second threads mostly wait. Full fetches of TK's Nov 15 video (204k crops, the
# board scan on the GPU, Nov 19, 2026), one each on a quiet machine: 6 x 1 detection 15.6 min, OCR done 1.7 after it,
# fetch 18.5; 8 x 1 17.2, 0.2, 18.6; 4 x 2 14.8, 4.9, 20.9. 6 x 1 and 8 x 1 tie on fetch and both beat 4 x 2, whose OCR
# ends 5 minutes after detection; 6 x 1 over 8 x 1 because it slows detection less. 4 x 2 detects fastest, so a game
# with few crops, where detection sets the pace, may come out a little slower than with 4 x 2 (not measured).
# Elsewhere (the Mac, where OCR runs after detection) 4 x 2 as before: nothing else was measured there.
OCR_WORKERS, OCR_THREADS = (6, 1) if sys.platform == "win32" else (4, 2)
COOKIES = []   # yt-dlp's --cookies-from-browser BROWSER, set by `download --cookies`
sys.path.insert(0, HERE)
from rink import rink
import setup_check   # bench, nets, period edges and the frame600 views: what fetch, prepare and solve print


def sh(*args, **kw):
    print("+", " ".join(map(str, args)), flush=True)
    return subprocess.run([str(a) for a in args], check=True, **kw)


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# the arguments main() passes through norm_path: every command's work folder (clipsheet's --W too), frames', follow's
# and clipsheet's OUT, clipsheet's MP4, publish's --notes-file, gaps --apply's files, clip --tracks's file
PATH_ARGS = ("W", "out", "mp4", "notes_file", "apply", "tracks")


def norm_path(p):
    """A path as a Git Bash session hands it over: '/c/Users/...' (MSYS's form, which Windows Python can't open:
    FileNotFoundError, or cv2.imwrite failing silently) becomes 'C:/Users/...', and a quoted '~' is expanded."""
    p = os.path.expanduser(p)
    m = re.match(r"/([a-zA-Z])(?=/|$)", p) if sys.platform == "win32" else None
    return f"{m.group(1).upper()}:{p[2:] or '/'}" if m else p


def team_of_folder(W):
    """Whose game a work folder's name says (regress.game_of: bw-2026-11-07-vs-db is Blue Wings', a name without a
    prefix Turbo Kings'), or None for a name that isn't a game folder's. Before fetch writes full/rink.json this is
    all there is: `sheet` used to fall back on Turbo Kings, fail for every other team, and refresh Turbo Kings'
    lada_games.json on the way."""
    from regress import game_of
    slug, gid = game_of(os.path.basename(os.path.normpath(W)), None)
    return slug if gid else None


# ---------------------------------------------------------------- fetch

def video_info(url, W):
    """Title, upload date and length of the video (W/video_info.json): LADA titles carry the date, time and rink."""
    p = f"{W}/video_info.json"
    if os.path.exists(p):
        return json.load(open(p))
    try:
        out = subprocess.run([PY, "-m", "yt_dlp", *COOKIES, "-q", "--no-warnings", "--skip-download", "--print", "%(title)s",
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
    sh(PY, "-m", "yt_dlp", *COOKIES, "-q", "--no-progress", "-f", "313/bestvideo[height=2160]/bestvideo[ext=webm]/bestvideo",
       "-o", vid, url)
    return vid


def fit_size(vid, W, dy=0):
    """rink.py's geometry is in pixels of the rink's usual frame (`size`). A video of the same view at a lower
    resolution (Kirkland once came as 3600x1440, not 3840x1536) is scaled up once and the original kept beside it.
    As H.264 (in Matroska, under the same name): ffmpeg decodes it ~5x faster than AV1, which it has no fast
    decoder for here. dy (framing_shift): the picture also moves up by that many px (down if negative) in the same
    encode, for an upload that sits low under a black band."""
    import imageio_ffmpeg
    size = getattr(rink(f"{W}/full"), "size", None)
    have = tuple(next(imageio_ffmpeg.read_frames(vid))["size"])
    if not size or (have == tuple(size) and not dy):
        return
    if abs(have[0] / size[0] - have[1] / size[1]) > 0.01:
        sys.exit(f"video is {have[0]}x{have[1]}, not a scaled {size[0]}x{size[1]}: new framing, see rink.py")
    w, h = size
    vf = [f"scale={w}:{h}:flags=bicubic"] if have != tuple(size) else []
    if dy:
        vf.append(f"crop={w}:{h - dy}:0:{dy},pad={w}:{h}:0:0:black" if dy > 0 else
                  f"crop={w}:{h + dy}:0:0,pad={w}:{h}:0:{-dy}:black")
    log((f"video is {have[0]}x{have[1]}; scaling it to {w}x{h}" if vf[0].startswith("scale") else "re-encoding the video")
        + (f", shifted {'up' if dy > 0 else 'down'} {abs(dy)} px" if dy else ""))
    # nvenc's p1 preset: 2.3x faster than p5 for the same quality (PSNR 50.4 vs 50.5 dB against the scaled source on
    # a 4-minute slice, Nov 2, 2026) at a 15% larger file; the encode was the re-encode's bottleneck, not the decode
    enc = ["h264_nvenc", "-preset", "p1", "-cq", "21"] if sys.platform == "win32" else ["libx264", "-crf", "20"]
    sh(imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-y", "-i", vid, "-vf", ",".join(vf),
       "-c:v", *enc, "-an", "-f", "matroska", f"{W}/video_up.webm")
    os.replace(vid, f"{W}/video_{have[0]}x{have[1]}.webm")
    os.replace(f"{W}/video_up.webm", vid)


def download_audio(url, W):
    """Only clips use the audio, so a failed download (YouTube has answered 403 once, then worked on a retry) warns
    instead of stopping fetch; re-running fetch tries again."""
    for _ in range(2):
        if os.path.exists(f"{W}/audio.m4a"):
            return
        try:
            sh(PY, "-m", "yt_dlp", *COOKIES, "-q", "--no-progress", "-f", "140/bestaudio[ext=m4a]", "-o", f"{W}/audio.m4a", url)
        except subprocess.CalledProcessError:
            pass
    log("no audio: clips will be silent (re-run fetch to try again)")


def calibrate(vid, W, force=False):
    """The far-boards curve (boards.py) from a frame at the rink's usual size: a smaller video's frame is scaled
    up for it, so the curve can be measured before fit_size encodes anything."""
    if os.path.exists(f"{W}/full/boards_poly.npy") and not force:
        return
    import imageio_ffmpeg
    frame = f"{W}/frame600.png"
    size = getattr(rink(f"{W}/full"), "size", None)
    have = tuple(next(imageio_ffmpeg.read_frames(vid))["size"])
    vf = ["-vf", f"scale={size[0]}:{size[1]}:flags=bicubic"] if size and have != tuple(size) else []
    sh(imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-y", "-ss", "600", "-i", vid, *vf, "-frames:v", "1", frame)
    sh(PY, f"{HERE}/boards.py", frame, f"{W}/full")
    setup_check.frame_views(W)   # frame600_small.jpg, bench_left.jpg and bench_right.jpg: the jersey and the bench


def framing_offset(W):
    """(dy, ys): how many px the video's far-boards curve sits below the rink's usual framing (rink.ref_boards at
    rink.REF_XS), and the curve's y there; None where the rink has no reference or no curve yet."""
    from rink import REF_XS
    R = rink(f"{W}/full")
    if R.P is None or not getattr(R, "ref_boards", None):
        return None
    ys = np.polyval(R.P, REF_XS)
    return float(np.median(ys - np.array(R.ref_boards))), [int(round(y)) for y in ys]


def framing_shift(W):
    """How far fit_size should move the picture up (px) so the far boards fall where the rink's geometry expects
    them: late uploads (LiveBarn's files) have sat 53 px low at Kirkland and 70 px low at Snoqualmie B under a black
    band, and every board-based step then failed silently (the scoreboard crop held the board's top edge). Only
    rinks with `reframe` get shifted; elsewhere (Snoqualmie A's 52 px lower framing, Renton's band classes) the
    offset is logged."""
    from rink import REF_XS, RINKS, Renton2, rink_name
    off = framing_offset(W)
    if off is None:
        return 0
    dy, ys = off
    R = rink(f"{W}/full")
    where = f"far boards at x {list(REF_XS)}: {ys}, usually {list(R.ref_boards)}"
    if abs(dy) <= 20:
        return 0
    if not getattr(R, "reframe", False):
        hint = ""
        if isinstance(R, Renton2):   # Renton's new camera has come framed four ways: name the one that fits
            fits = {n: float(np.max(np.abs(np.array(ys) - C.ref_boards))) for n, C in RINKS.items()
                    if issubclass(C, Renton2) and C is not type(R)}
            best = min(fits, key=fits.get)
            # none fits: how far this rink's ice-map camera has to turn onto the curve tells a roll from a re-aim
            hint = (f" (the curve fits {best}'s within {fits[best]:.0f} px: set that rink in full/rink.json)"
                    if fits[best] <= 25 else
                    f" (no Renton framing fits{setup_check.roll_hint(R.P, rink_name(W + '/full'))})")
        log(f"framing: the picture sits {dy:+.0f} px from the rink's usual ({where}){hint}")
        return 0
    if os.path.exists(f"{W}/full/dets.csv"):
        sys.exit(f"the picture sits {dy:+.0f} px from the rink's usual framing ({where}), but detection has run on "
                 f"it: move {W}/full aside (keep rink.json) and fetch again")
    log(f"framing: the picture sits {dy:+.0f} px from the rink's usual ({where}); shifting it into place")
    return int(round(dy))


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
        # the repo's copy of the model: with W as the working directory process.py used to download 40 MB into W
        env = dict(os.environ, YOLO_MODEL=f"{ROOT}/yolo11m.pt") if os.path.exists(f"{ROOT}/yolo11m.pt") else None
        proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=W, env=env)
        t_start, hist, slow_since = time.time(), [], None
        while proc.poll() is None:
            try:   # back as soon as it exits (a 30 s sleep left fetch up to 30 s behind a finished detection)
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass
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
    log(f"OCR on {len(crops - done)} crops ({OCR_WORKERS} workers)")
    env = dict(os.environ, PYTHONHASHSEED="0", OCR_THREADS=str(OCR_THREADS))
    ps = [subprocess.Popen([PY, f"{HERE}/ocr_worker.py", full, "1000000000", "1", str(k), str(OCR_WORKERS)], env=env,
                           stdout=open(f"{full}/ocr_log_{k}.txt", "w"), stderr=subprocess.STDOUT) for k in range(OCR_WORKERS)]
    for p in ps:
        p.wait()


def ocr_alongside(W):
    """The OCR workers started with detection instead of after it: ocr_worker.py polls full/crops and keeps going
    until detection's DONE is in log.txt, so they read each crop as it lands (skipping the newest 2 s, which may
    still be being written) and finish seconds after detection instead of 8-14 minutes after it. Measured on a
    4-minute slice of TK's Nov 1 game (PC, RTX 5090, 16 cores): detection 52.6 s then OCR 46 s, against 77 s for
    both at once, detection itself a fifth slower with the four workers beside it. On the Mac the workers starved
    the decoder, so there OCR stays after detection (ocr()), as it does with OCR_AFTER=1. Returns the worker
    processes to wait on after detect(); ocr() then picks up anything they missed."""
    full = f"{W}/full"; logp = f"{full}/log.txt"
    if sys.platform != "win32" or os.environ.get("OCR_AFTER"):
        return []
    if os.path.exists(logp) and any(l.startswith("DONE") for l in open(logp)):
        return []   # detection already done: ocr() after it does the work
    os.makedirs(f"{full}/crops", exist_ok=True)
    open(logp, "a").close()
    log(f"OCR: {OCR_WORKERS} workers alongside detection")
    env = dict(os.environ, PYTHONHASHSEED="0", OCR_THREADS=str(OCR_THREADS))
    return [subprocess.Popen([PY, f"{HERE}/ocr_worker.py", full, "1000000000", "1", str(k), str(OCR_WORKERS)], env=env,
                             stdout=open(f"{full}/ocr_log_{k}.txt", "a"), stderr=subprocess.STDOUT) for k in range(OCR_WORKERS)]


def propose_periods(W):
    """The periods the board's clock gives (clock.json), else breaks = min_break+ seconds (rink.py) with nobody out
    on the open ice; a warning where the two part (setup_check.edge_check). Our goalie's net side per period by most
    of three reads: our bench's end in the 1st and switching, the opening faceoff, our jersey in each crease."""
    from track import load
    R = rink(f"{W}/full")
    d = load(f"{W}/full/dets.csv"); d["rel"] = d.fy - d.board
    T = int(d.t.max()) + 1
    busy = setup_check.busy_ice(R, d, fps=FPS)
    periods = setup_check.empty_ice(busy)
    clk = json.load(open(f"{W}/clock.json")) if os.path.exists(f"{W}/clock.json") else None
    if clk and clk["periods"]:
        log("periods from the board's clock: " + ", ".join(f"{P['label']} {P['start']}-{P['end']}" for P in clk["periods"])
            + "; empty ice would say " + ", ".join(f"{a}-{b}" for a, b in periods)
            + ("" if len(clk["periods"]) == 3 else f". {len(clk['periods'])} periods on the clock, not 3: take them "
               f"from {W}/sb.jpg by eye"))
        setup_check.edge_check(W, clk["periods"], busy, T)
        periods = [[P["start"], P["end"]] for P in clk["periods"]]
    else:
        log("periods from the empty ice, because " + ("the board's clock gave none" if clk else "there is no clock.json")
            + ": " + ", ".join(f"{a}-{b}" for a, b in periods) + ". The empty ice has merged periods and missed edges by "
            f"30-90 s: take them from {W}/sb.jpg by eye")
    res = [dict(label=f"P{k}", start=int(a), end=int(b), net=None, pk=[]) for k, (a, b) in enumerate(periods, 1)]
    for P, side in zip(res, setup_check.propose_nets(W, res, d, faceoff=bool(clk and clk["periods"]))):
        P["net"] = R.nets[side]
    # never over an edited periods.json: it is replaced only while it is still fetch's last proposal
    # (periods.proposed.json keeps each one), or the same as this one
    pp, pq = f"{W}/periods.json", f"{W}/periods.proposed.json"
    have = json.load(open(pp)) if os.path.exists(pp) else None
    last = json.load(open(pq)) if os.path.exists(pq) else None
    if have is not None and have != res and have != last:
        log(f"periods.json has been edited since fetch proposed it (kills, spans, edges or nets): kept as it is; this "
            f"run's proposal is in {pq}")
    else:
        json.dump(res, open(pp, "w"), indent=2)
    json.dump(res, open(pq, "w"), indent=2)
    for k in range(len(res) - 1):
        a, b = res[k]["end"], res[k + 1]["start"]
        sh(PY, f"{HERE}/ovsheet.py", f"{W}/full/ov", f"{W}/break_{k + 1}.jpg", a - 60, b + 40, 10, 2)
    sh(PY, f"{HERE}/ovsheet.py", f"{W}/full/ov", f"{W}/video_end.jpg", T - 120, T, 20, 2)
    print(json.dumps(res, indent=2))


def set_config(W, **kw):
    """Store team/rink/jersey choices in W/full/rink.json, which every later step reads (rink.py, team: __main__).
    Fetch (bench given or not) and a jersey switch also settle the bench: from the jersey where the rink's bench
    follows it, unless --bench or an earlier hand-set bench says otherwise (setup_check.settle_bench)."""
    from rink import RINKS, JERSEYS
    for k, known in (("rink", RINKS), ("jersey", JERSEYS), ("bench", ("left", "right"))):
        if kw.get(k) and kw[k] not in known:
            sys.exit(f"unknown {k} {kw[k]!r}; known: {', '.join(known)}")
    p = f"{W}/full/rink.json"
    cfg = json.load(open(p)) if os.path.exists(p) else {}
    cfg.update({k: v for k, v in kw.items() if v})
    if "bench" in kw or kw.get("jersey"):
        setup_check.settle_bench(cfg, kw.get("bench"))
    if cfg:
        json.dump(cfg, open(p, "w"))


def _detection_end(W):
    """When process.py wrote its DONE (log.txt's last write), or None while it runs."""
    logp = f"{W}/full/log.txt"
    if os.path.exists(logp) and "\nDONE" in "\n" + open(logp).read():
        return os.path.getmtime(logp)
    return None


def scoreboard_alongside(W):
    """The scoreboard's pass over the video in a thread while process.py detects. On the GPU where it can
    (scoreboard.gpu_ok; SCOREBOARD_CPU=1 to not), at normal priority: NVDEC decodes and only the board comes back, so
    the scan stops competing with detection and OCR for the CPU. Else on the CPU at below-normal priority, as before,
    where it took 18-28 minutes of a fetch from Nov 2 to 17, ending 5-12 minutes after detection (3-5 alone).
    Returns the thread for scoreboard_wait; if the scan fails, scoreboard_sheet scans again."""
    if os.path.exists(f"{W}/scoreboard.npy"):
        return None
    import threading
    from scoreboard import scan
    def run():
        t0 = time.time()
        try:
            how = scan(W, low_priority=True)
            th.ended = time.time(); det = _detection_end(W)
            took = f"scoreboard: scanned in {(th.ended - t0) / 60:.1f} min ({how})"
            if det is not None and det < t0:   # a fetch run again for the scan alone (detection done earlier)
                log(f"{took}; detection was already done")
            elif det is None or det >= th.ended:
                log(f"{took} alongside detection, which is still running")
            else:
                log(f"{took} alongside detection, ending {(th.ended - det) / 60:.1f} min after it")
        except Exception as e:
            log(f"scoreboard scan alongside detection failed ({e!r})")
    log("scoreboard: one pass over the video, alongside detection")
    th = threading.Thread(target=run, daemon=True)
    th.ended = None
    th.start()
    return th


def scoreboard_wait(th, W):
    """Join the scan; one that ended before detection says by how much."""
    th.join()
    det = _detection_end(W)
    if th.ended and det and th.ended < det:
        log(f"scoreboard: the scan ended {(det - th.ended) / 60:.1f} min before detection")


def scoreboard_sheet(W):
    """The arena scoreboard every 60 s (W/sb.jpg) from one pass over the video (W/scoreboard.npy): periods, score,
    penalties and shots are read off it, since the empty-ice period proposal is often wrong."""
    from scoreboard import scan, sheet
    if not os.path.exists(f"{W}/scoreboard.npy"):
        log("scoreboard: one pass over the video")
        scan(W)
    n = len(np.load(f"{W}/scoreboard.npy", mmap_mode="r"))
    sheet(W, f"{W}/sb.jpg", list(range(30, n, 60)), cols=6)


def read_clock(W):
    """The period clock off the board (clock.py, about 1.5 minutes of OCR the first time) -> W/clock.json: the
    periods' edges for propose_periods and the video second of every clock time for sheet and goals;
    W/clock_check.jpg to check them."""
    import clock
    log("clock: reading the period clock off the board")
    setup_check.clock_report(W, clock.run(W))


def cmd_fetch(a):
    W = os.path.abspath(a.W); os.makedirs(f"{W}/full", exist_ok=True)
    set_config(W, team=a.team, rink=a.rink, jersey=a.jersey, bench=a.bench)
    video_info(a.url, W)
    update_lada_games()
    vid = download(a.url, W)
    calibrate(vid, W)
    dy = framing_shift(W)
    fit_size(vid, W, dy)
    if dy:
        calibrate(vid, W, force=True)
        dy2 = framing_offset(W)[0]
        log(f"re-encoded; the far boards now sit {dy2:+.0f} px from the usual framing")
        if abs(dy2) > 10:
            sys.exit(f"still {dy2:+.0f} px off after the shift: look at {W}/frame600.png and boards.py's curve")
    download_audio(a.url, W)
    board = None if a.limit else scoreboard_alongside(W)
    workers = ocr_alongside(W)
    detect(vid, W, a.limit)
    if board:
        scoreboard_wait(board, W)
    for p in workers:
        p.wait()
    ocr(W)
    if not a.limit:
        scoreboard_sheet(W)
        read_clock(W)
    propose_periods(W)
    sb = (f"{W}/clock_check.jpg (each period's edges on the board), {W}/sb.jpg (the board every 60 s), "
          if os.path.exists(f"{W}/sb.jpg") else "")
    log(f"fetch done. Check {W}/periods.json against {sb}break_*.jpg and video_end.jpg")


def cmd_download(a):
    """The video, its audio and its title, before fetch (which skips what is there). YouTube answers "Sign in to
    confirm you're not a bot" for days at a time (3 of the 4 games fetched on Oct 31), and only a signed-in browser's
    cookies get through: `--cookies firefox`. Reading the browser's cookies is the user's own to run (with `!` in
    Claude Code), and this is the one line to give them."""
    global COOKIES
    W = os.path.abspath(a.W); os.makedirs(f"{W}/full", exist_ok=True)
    open(f"{W}/url.txt", "w").write(a.url)
    COOKIES = ["--cookies-from-browser", a.cookies] if a.cookies else []
    video_info(a.url, W)
    download(a.url, W)
    download_audio(a.url, W)
    log(f"downloads done in {W}; now fetch as usual (it skips them)")


def cmd_jersey(a):
    W = os.path.abspath(a.W)
    set_config(W, jersey=a.name)
    sh(PY, f"{HERE}/crops.py", f"{W}/video.webm", f"{W}/full", FPS, "--hue")   # a dets.csv made before bhue
    sh(PY, f"{HERE}/crops.py", f"{W}/video.webm", f"{W}/full", FPS)
    ocr(W)
    log(f"crops and reads for {a.name} done; now `unknown` and `prepare` (delete {W}/p* and {W}/rev_p* if an "
        "earlier prepare made them)")
    if os.path.exists(f"{W}/periods.json"):   # fetch proposed the nets with the old jersey's detections and bench
        setup_check.check_nets(W)


# ---------------------------------------------------------------- helpers for the review

def periods(W):
    return json.load(open(f"{W}/periods.json"))


# ---------------------------------------------------------------- spans in periods.json: one writer for the four
# commands that add them (gaps --apply: on/off; pk --write and highlights --write: pk, and off for a player boxed
# without a kill; span: on/off/extra/ps by hand)

def same_span(e, start, end, player=None):
    """The duplicate rule: the same player (None for extra and ps) from the same second to the same second, to 0.1 s."""
    return (e.get("player") == player and round(float(e["start"]), 1) == round(float(start), 1)
            and round(float(e["end"]), 1) == round(float(end), 1))


def add_span(P, kind, start, end, player=None):
    """Append a span to period P's `kind` list (on, off, pk: with "player"; extra, ps: without) unless same_span
    finds it there already. Returns the span added, or None for a duplicate."""
    if any(same_span(e, start, end, player) for e in P.get(kind, [])):
        return None
    e = dict(start=start, end=end) if kind in ("extra", "ps") else dict(start=start, end=end, player=player)
    P.setdefault(kind, []).append(e)
    return e


def save_periods(W, Ps, sort=()):
    """Write W/periods.json in the indent it has (fetch writes 2, the span writers 1), the span lists named in `sort`
    ordered by start, then player (`span` leaves its list as a hand edit would)."""
    p = f"{W}/periods.json"
    second = (open(p).read().splitlines() + ["", ""])[1] if os.path.exists(p) else ""
    for P in Ps:
        for k in sort:
            if k in P:
                P[k] = sorted(P[k], key=lambda s: (s["start"], s.get("player") or 0))
    json.dump(Ps, open(p, "w"), indent=(len(second) - len(second.lstrip(" "))) or 1)


def log_span(W, P, kind, start, end, player, why):
    """One line in W/hand_spans.txt for a span added outside the checkers' fixes.json (when, what, why); `span --list`
    prints the file and archive keeps it. Returns the line."""
    line = f"{time.strftime('%Y-%m-%d %H:%M')}  {P['label']} {kind} {f'#{player} ' if player is not None else ''}{start}-{end}: {why}"
    open(f"{W}/hand_spans.txt", "a", encoding="utf-8").write(line + "\n")
    return line


def _logged_whys(W):
    """W/hand_spans.txt's on/off spans as {(period, kind, player, start, end): why}, the key the gap briefs' history
    uses for the checkers' spans (answers.json)."""
    p, out = f"{W}/hand_spans.txt", {}
    for ln in (open(p, encoding="utf-8").read().splitlines() if os.path.exists(p) else []):
        m = re.match(r"^\S+ \S+\s+(P\d+) (on|off) #(\d+) ([\d.]+)-([\d.]+): (.*)$", ln)
        if m:
            out[(m.group(1), m.group(2), int(m.group(3)), float(m.group(4)), float(m.group(5)))] = m.group(6)
    return out


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
    """The game sheet's goals with the video second the board's clock implies for each, then (once prepare has made
    tracks) the candidates from the video: after every goal the restart is a center-ice faceoff, so center-ice
    formations that aren't period starts, and every long stoppage with where play restarted. Each needs checking by
    eye (frames command). --brief writes the goal and penalty checkers' briefs instead (goal_briefs)."""
    W = os.path.abspath(a.W)
    if a.brief:
        return goal_briefs(W)
    R = rink(f"{W}/full")
    center = R.center_x
    Ps = periods(W)
    starts = [P["start"] for P in Ps]
    def label(t):
        P = next((P for P in Ps if P["start"] <= t <= P["end"]), None)
        return P["label"] if P else "break"
    if os.path.exists(f"{W}/sheet.json"):
        import clock as clock_
        sheet_ = json.load(open(f"{W}/sheet.json", encoding="utf-8"))
        clk = clock_.load(W)
        print("Game sheet (SportNinja) goals, with the video time the period clock implies (the second the board's clock "
              "showed it, where clock.json was read; otherwise exact only where the clock runs through stoppages):")
        for x in sheet_["goals"]:
            # sheet.json is usually written before fetch has read the clock, or before periods.json exists
            t_ = _sheet_t(clk, Ps, x["period"], _mmss(x["clock"])) if x["period"] in [P["label"] for P in Ps] else x.get("video_t")
            print(f"  {x['period']} {x['clock']} {x['team']:<7} #{x['scorer']} {x['scorer_name']}" + (f"  ~{t_ // 60}:{t_ % 60:02d} ({t_} s)" if t_ is not None else ""))
        if _missing_periods(sheet_, Ps):
            print(_missing_periods(sheet_, Ps))
    if not all(os.path.exists(f"{W}/{P['label'].lower()}/tracks_v1.csv") for P in Ps):
        print("No tracks yet (prepare makes them): the faceoff and stoppage candidates come from `goals` after prepare; "
              f"the goal checkers' briefs need none (`goals {a.W} --brief`).")
        print("Our net per period:", {P["label"]: ("left" if P["net"] < center else "right") for P in Ps})
        return
    from track import load
    d = load(f"{W}/full/dets.csv"); d = d[d.onice & (d.conf >= 0.3)]
    g = d.groupby("frame").agg(t=("t", "first"), n=("fx", "size"), mx=("fx", "median"),
                               q2=("fx", lambda s: s.quantile(.2)), q8=("fx", lambda s: s.quantile(.8)))
    s = g.assign(sx=g.q8 - g.q2).groupby(g.t.astype(int)).agg(n=("n", "median"), mx=("mx", "median"), sx=("sx", "median"))
    sp = _skater_speed(W)
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


# ---------------------------------------------------------------- goals and penalties: checker briefs, kills, highlights

PERIOD_NAMES = {"P1": "1st period", "P2": "2nd period", "P3": "3rd period", "P4": "overtime"}
HL_WORK = ("shot", "pass", "on_ice")   # highlights.json keys for the clips and the lineup check, never published
HL_RECORD = ("sheet_n",)               # generated.json's only: the sheet's goal or penalty number of each entry
GOAL_DIR = "scratch/goals"             # under W: the goal and penalty checkers' briefs and answers
KILL_GOAL_PAD = 1                      # s: a kill ended by a power-play goal ends this long after the goal's second
# Where the clock runs through stoppages the board runs a 2-minute minor for 3:00, and its time on the sheet is the
# faceoff after the call, a median 32 s after the whistle (15 archived kills, 7 games, every rink): the kill starts
# KILL_LEAD s before it. Where the clock stops at whistles the sheet's time is the whistle and minors run 2:00 (16).
RUNNING_MINOR, KILL_LEAD = 3, 30
OT_LENGTH = 300   # s of clock in a period after the 3rd when sheet.json doesn't say (LADA's overtime is 5:00)


def _plen(label, sheet_=None):
    """Seconds of clock in period `label`: the game sheet's (SportNinja's durations, kept in sheet.json by `sheet`),
    else 18:00 for the 1st to 3rd and OT_LENGTH after them."""
    import clock as clock_
    L = (sheet_ or {}).get("period_lengths", {}).get(label)
    return int(L) if L else clock_.PERIOD if label in ("P1", "P2", "P3") else OT_LENGTH


def _game_clock(Ps, sheet_=None):
    """({label: seconds of clock}, {label: seconds of game clock run at its start}) for periods.json's periods."""
    Ls, off, run = {}, {}, 0
    for P in Ps:
        Ls[P["label"]], off[P["label"]] = _plen(P["label"], sheet_), run
        run += Ls[P["label"]]
    return Ls, off


def _missing_periods(sheet_, Ps):
    """A line saying which of the sheet's periods with a goal or a penalty periods.json lacks, or ''."""
    miss = sorted({x["period"] for x in sheet_.get("goals", []) + sheet_.get("penalties", [])} - {P["label"] for P in Ps})
    return (f"the game sheet has {', '.join(miss)}, which periods.json lacks: its goals and penalties are left out until "
            f"that period is in periods.json (start, end and net)") if miss else ""


def _mmss(clock):
    """A period clock as the sheet or a checker writes it ('07:59', '7:59', or '38.2' in the last minute) -> seconds."""
    clock = str(clock).strip()
    if ":" not in clock:
        return int(float(clock))
    m, s = clock.split(":")
    return int(m) * 60 + int(float(s))


def _mm(c):
    return f"{int(c) // 60}:{int(c) % 60:02d}"


def _num(v):
    """A JSON number as the hand-written files have them: 72, 1383.5."""
    return None if v is None else int(v) if float(v) == int(float(v)) else round(float(v), 2)


def _clock_period(clk, Ps, label):
    """clock.json's period `label`, if it covers the same stretch of video as periods.json's (as `sheet` checks)."""
    C = next((C for C in clk["periods"] if C["label"] == label), None) if clk else None
    P = next((P for P in Ps if P["label"] == label), None)
    return C if C and (not P or (C["start"] < P["end"] and P["start"] < C["end"])) else None


def _sheet_t(clk, Ps, label, c, L=None):
    """The video second of a sheet time (c s left in period `label`, L s of clock long: _plen): where the board's
    clock showed it (clock.video_t), else the period's start plus the clock run, exact only where the clock runs
    through stoppages and otherwise the earliest the moment can be."""
    import clock as clock_
    if _clock_period(clk, Ps, label):
        return clock_.video_t(clk, label, c)
    P = next((P for P in Ps if P["label"] == label), None)
    return int(P["start"] + (L or _plen(label)) - c) if P else None


def _clock_reaches(clk, Ps, label, c, L=None):
    """The first video second period `label`'s clock showed c s or less: a penalty's expiry, which unlike a sheet time
    isn't moved to the start of a stop just above it. The period's end if the clock never got there."""
    P = next(P for P in Ps if P["label"] == label)
    C = _clock_period(clk, Ps, label)
    if not C:
        return min(P["end"], int(P["start"] + (L or _plen(label)) - c))
    ks = C["knots"]
    for (t0, c0), (t1, c1) in zip(ks, ks[1:]):
        if c1 <= c:
            return t0 if c0 <= c else int(t0 + c0 - c) if t1 - t0 == c0 - c1 else t1
    return P["end"]


def _clock_stops(clk, Ps, label, t0=None, t1=None, min_len=5):
    """[(first second, last second, clock)] where period `label`'s clock stood still min_len+ s, within t0..t1."""
    C = _clock_period(clk, Ps, label)
    ks = C["knots"] if C else []
    return [(a, b, c) for (a, c), (b, c1) in zip(ks, ks[1:]) if c == c1 and b - a >= min_len
            and (t0 is None or b >= t0) and (t1 is None or a <= t1)]


CLOCK_STOPS = 6   # a period whose clock stood still this often (3+ s, before its last 2 minutes) stops at whistles


def _clock_still(C):
    """A clock.json period C per second of video: (t, clock, early, still, stops): early = before the last 2 minutes
    on the clock (which stop at whistles at most rinks), still = the clock didn't run that second, stops = stretches
    of 3+ s early and still. One count for the gap briefs' clock line (_clock_line) and the kills and goal briefs
    (_clock_runs): on the 20 games with clock.json (Nov 18) every 1st and 2nd had 0-3, every 3rd 9-28."""
    ks = np.array(C["knots"], float)
    t = np.arange(ks[0, 0], ks[-1, 0] + 1)
    c = np.interp(t, ks[:, 0], ks[:, 1])
    early, still = c[:-1] > 120, np.diff(c) > -0.5
    edge = np.diff(np.r_[0, early & still, 0].astype(int))
    stops = int(((np.flatnonzero(edge == -1) - np.flatnonzero(edge == 1)) >= 3).sum())
    return t, c, early, still, stops


def _clock_runs(clk, Ps, label):
    """True where the period's clock ran through stoppages, False where it stopped at whistles (CLOCK_STOPS+ stops,
    _clock_still), None without the board's clock."""
    C = _clock_period(clk, Ps, label)
    if not C:
        return None
    return _clock_still(C)[4] < CLOCK_STOPS


def _penalty_items(sheet_):
    """The sheet's penalties as infractions: a team's entries for one player at one clock (a minor plus a misconduct)
    are one, with the minutes of its minor or major part (0 for a misconduct alone, which takes the player but not a
    skater). In sheet order and numbered from 1: the penalty brief and `highlights` both count them so."""
    items = []
    for p in sheet_.get("penalties", []):
        k = (p["team"], p["player"], p["period"], p["clock"])
        x = next((x for x in items if (x["team"], x["player"], x["period"], x["clock"]) == k), None)
        if x is None:
            x = dict(n=len(items) + 1, team=p["team"], player=p["player"], name=p["name"], period=p["period"],
                     clock=p["clock"], type=p["type"], parts=[], minutes=0, major=False)
            items.append(x)
        x["parts"].append(f"{p['type']} ({p['severity']}, {p['minutes']} min)")
        if "misconduct" not in p["severity"].lower():
            x.update(type=p["type"], minutes=max(x["minutes"], int(p["minutes"])), major=p["severity"] == "Major")
    return items


def penalty_kills(W, Ps, sheet_=None, clk=None):
    """Our penalty kills as the game sheet and the board's clock imply them, before anyone has looked at a frame:
    each of our penalties from the second the clock showed its time for its minutes of clock, carried into the next
    period past an intermission, and ended early by a power-play goal against (a minor, while we are a man short).
    One of ours and one of theirs at the same clock for the same minutes cancel: coincident, 5 on 5, no kill (LADA
    Y's Nov 9). A minor at the clock of the other team's goal is a delayed call the goal wiped out (BW's Oct 11: never
    on the board), or the sheet gave the goal the penalty's time: no kill, and the brief asks. Returns
    _penalty_items, both teams', each with e0/e1 (seconds of game clock run at its start and end), `spans`
    ([label, start, end] in video seconds per period, [] for no kill), `why`, `pair`, `end_goal`, and `rough` where
    a span lies in a period without a board clock read: its start is then only the earliest the kill can be (on the
    archived games without clock.json, 85-438 s early in 12 of 35 kills), so `pk --write` leaves it to the penalty
    checker. Each period runs its own length of clock (_game_clock: an overtime is 5:00)."""
    import clock as clock_
    sheet_ = sheet_ or json.load(open(f"{W}/sheet.json", encoding="utf-8"))
    clk = clock_.load(W) if clk is None else clk
    labels = [P["label"] for P in Ps]
    Ls, off = _game_clock(Ps, sheet_)
    total = sum(Ls.values())
    run = lambda lab, c: off[lab] + Ls[lab] - c   # game clock run by c s left in period lab
    items = _penalty_items(sheet_)
    for x in items:
        x.update(spans=[], why="", pair=None, end_goal=None, wiped=None, runs=None, board=x["minutes"], rough=False)
        x["e0"] = run(x["period"], _mmss(x["clock"])) if x["period"] in labels else None
        if x["e0"] is not None:
            x["runs"] = _clock_runs(clk, Ps, x["period"])
            x["board"] = RUNNING_MINOR if x["runs"] and x["minutes"] == 2 and not x["major"] else x["minutes"]
        x["e1"] = None if x["e0"] is None else x["e0"] + 60 * x["board"]
    for x in items:   # coincident: one of ours and one of theirs, same clock, same minutes
        if x["team"] == "ours" and x["minutes"] and x["pair"] is None and x["e0"] is not None:
            y = next((y for y in items if y["team"] == "theirs" and y["minutes"] == x["minutes"] and y["e0"] == x["e0"]
                      and y["pair"] is None), None)
            if y:
                x["pair"], y["pair"] = y["n"], x["n"]
    live = lambda x, e: (x["minutes"] and x["pair"] is None and x["wiped"] is None and x["e0"] is not None
                         and x["e0"] <= e < x["e1"])
    end_of = lambda lab: off[lab] + Ls[lab]
    goals = [(run(g["period"], _mmss(g["clock"])), g) for g in sheet_.get("goals", []) if g["period"] in labels]
    for e, g in sorted(goals, key=lambda eg: eg[0]):
        short, other = ("ours", "theirs") if g["team"] == "against" else ("theirs", "ours")
        for x in items:
            if x["team"] == short and x["e0"] == e and live(x, e) and not x["major"]:
                x["wiped"] = g
        man = lambda team: sum(bool(live(x, e)) for x in items if x["team"] == team)
        if man(short) > man(other):   # a power-play goal ends the earliest running minor of the short team
            x = min((x for x in items if x["team"] == short and live(x, e) and not x["major"]), key=lambda x: x["e0"],
                    default=None)
            if x:
                x["e1"], x["end_goal"] = e, g
    for x in items:
        if x["team"] != "ours":
            continue
        y = next((y for y in items if y["n"] == x["pair"]), None)
        if x["e0"] is None:
            x["why"] = f"{x['period']} isn't in periods.json"
        elif not x["minutes"]:
            x["why"] = "a misconduct: he sits, we don't play short"
        elif y:
            x["why"] = f"coincident with their #{y['player']}'s {y['minutes']} min: 5 on 5, no kill"
        elif x["wiped"]:
            x["why"] = (f"at the clock of their goal ({x['wiped']['clock']}): a delayed call the goal wiped out, or the "
                        f"sheet gave the goal the penalty's time; no kill until the penalty checker says")
        if x["why"]:
            continue
        for k, lab in enumerate(labels):
            a, b = max(x["e0"], off[lab]), min(x["e1"], off[lab] + Ls[lab])
            if b <= a:
                continue
            P, end_run = Ps[k], off[lab] + Ls[lab]
            start = max(P["start"], _sheet_t(clk, Ps, lab, end_run - a, Ls[lab]) - (KILL_LEAD if x["runs"] else 0)) if a == x["e0"] else P["start"]
            if x["end_goal"] and b == x["e1"]:
                end = _sheet_t(clk, Ps, lab, _mmss(x["end_goal"]["clock"]), Ls[lab]) + KILL_GOAL_PAD
            else:
                end = P["end"] if b == end_run else _clock_reaches(clk, Ps, lab, end_run - b, Ls[lab])
            start, end = int(start), int(min(end, P["end"]))
            if end <= start:   # never a span of no length (the clock read past the period's end)
                continue
            x["spans"].append([lab, start, end])
            x["rough"] |= _clock_period(clk, Ps, lab) is None
        x["why"] = "; ".join(w for w in (
            f"{x['board']}:00 on the board, the clock running" if x["board"] != x["minutes"] else "",
            f"ended by their power-play goal at {x['end_goal']['clock']}" if x["end_goal"] else "",
            f"{_mm(x['e1'] - end_of(x['period']))} carried into {x['spans'][-1][0]}" if len(x["spans"]) > 1 else "",
            "to the end of the game" if x["e1"] > total else "") if w)
    return items


def _pen_line(x, items):
    who = f"#{x['player']} {x['name']}" if x["player"] is not None else x["name"]
    s = f"  {x['period']} {_mm(_mmss(x['clock']))} {x['team']:<6} {who}, {' + '.join(x['parts'])}"
    if x["team"] == "theirs":
        y = next((y for y in items if y["n"] == x["pair"]), None)
        return s + (f" (coincident with our #{y['player']}'s: 5 on 5)" if y else "")
    if not x["spans"]:
        return s + f": no kill ({x['why']})"
    return (s + ": kill " + ", ".join(f"{lab} {a}-{b}" for lab, a, b in x["spans"]) + (f" ({x['why']})" if x["why"] else "")
            + (": ROUGH, no board clock read there, so its start is only the earliest it can be" if x["rough"] else ""))


def _kill_answer(e):
    """A penalty checker's `kill`: ("kill", start, end); ("none", why) for no kill, null with a reason (coincident
    minors at 5 on 5, never served, a penalty shot, a misconduct); or ("unsure", what) where the checker couldn't see
    it (the field left out, "unsure", null without a reason, or not a [start, end]), which leaves periods.json's kill
    as it is."""
    k = e.get("kill")
    if isinstance(k, (list, tuple)) and len(k) == 2:
        try:
            return "kill", float(k[0]), float(k[1])
        except (TypeError, ValueError):
            pass
    if k is None and "kill" in e and str(e.get("why") or "").strip():
        return "none", str(e["why"]).strip()
    what = str(e.get("note") or e.get("why") or "").strip()
    return "unsure", (f"kill {k!r} isn't [start, end]" + (f"; {what}" if what else "") if k not in (None, "", "unsure")
                      else what or "no reason given")


def cmd_pk(a):
    """Our penalty kills from the game sheet and the board's clock alone (penalty_kills), so that the first solve
    has them. --write merges them into periods.json, leaving out: a kill already there for the same player over the
    same stretch (another player's overlapping kill stays beside it: a 5 on 3), a penalty the penalty checker has
    answered (pens.json: `highlights --write` puts the checker's kill in), and a rough proposal, in a period without
    a board clock read, unless --rough (the penalty checker then gives the kill)."""
    import clock as clock_
    W = os.path.abspath(a.W)
    if not os.path.exists(f"{W}/sheet.json"):
        sys.exit(f"no {W}/sheet.json: `run_game.py sheet {a.W}` first")
    Ps, clk = periods(W), clock_.load(W)
    sheet_ = json.load(open(f"{W}/sheet.json", encoding="utf-8"))
    items = penalty_kills(W, Ps, sheet_, clk)
    if _missing_periods(sheet_, Ps):
        print(_missing_periods(sheet_, Ps))
    print("Penalties on the game sheet, and our kills from the board's clock" if clk else
          "Penalties on the game sheet, and our kills (no clock.json: each period's start plus the clock run, exact only "
          "where the clock runs through stoppages)")
    for x in items:
        print(_pen_line(x, items))
    if not items:
        print("  none")
    if not a.write:
        print(f"`run_game.py pk {a.W} --write` merges the kills into periods.json")
        return
    pf = f"{W}/{GOAL_DIR}/pens/pens.json"
    answered = {int(e["n"]): _kill_answer(e) for e in (_load_answers(pf) if os.path.exists(pf) else [])
                if str(e.get("n", "")).isdigit()}
    added = 0
    for x in items:
        ans = answered.get(x["n"])
        if x["spans"] and ans and ans[0] != "unsure":
            print(f"  #{x['player']} {x['period']} {x['clock']}: the penalty checker gave "
                  + (f"its kill ({ans[1]:g}-{ans[2]:g})" if ans[0] == "kill" else f"no kill ({ans[1]})")
                  + f" in {pf}: `highlights --write` puts that in periods.json, so the proposal isn't written")
            continue
        if x["rough"] and not a.rough:
            print(f"  #{x['player']} {x['period']} {x['clock']}: rough (no board clock read), not written: the penalty "
                  f"checker's kill comes in with `highlights --write` (--rough writes this one)")
            continue
        for lab, s, e in x["spans"]:
            P = next(P for P in Ps if P["label"] == lab)
            same = [k for k in P.get("pk", []) if k["start"] < e and s < k["end"] and k.get("player") == x["player"]]
            if same:   # a kill over this stretch already (by hand, or an earlier run): stronger than same_span
                print(f"  {lab} #{x['player']} {s}-{e}: periods.json has " +
                      ", ".join(f"{k['start']}-{k['end']}" for k in same) + " already; left as it is")
                continue
            add_span(P, "pk", s, e, x["player"])
            added += 1
            print(f"  + {lab} pk #{x['player']} {s}-{e}")
    if added:
        save_periods(W, Ps, sort=("pk",))
    print(f"{added} kill(s) added to {W}/periods.json")


def _opp_look(jersey, opt):
    """The opponents' look for a brief: review's --opp once given (review.json), else the jersey test's name after
    "vs" in rink.json ("white vs royal blue": royal blue jerseys; LADA R's against LADA Y: light blue), else a guess
    from our own jersey."""
    if opt.get("opp"):
        return opt["opp"].rstrip(".")
    if " vs " in jersey:
        return f"{jersey.split(' vs ', 1)[1].strip()} jerseys"
    return "dark or red jerseys" if jersey.startswith("white") else "white or dark jerseys"


def _net_side(R, x):
    """'LEFT' or 'RIGHT': the end of the frame a net (its x) is at, as every brief names it."""
    return "LEFT" if x < R.center_x else "RIGHT"


def _brief_context(W, P=None):
    """What every by-eye brief (the gap, goal, penalty and clip checkers') says about the game, in one wording: our
    look and the opponents', the roster, the goalie, our net per period, the rink (rink.py's one-sentence `brief`),
    the frame, our bench and box, the roster card (period P's own, else another period's; card_line is empty before
    prepare has made one) and, for a period P, the board's clock (_clock_line; empty without clock.json)."""
    from roster import SKATERS, GOALIES, TEAM, GOALIE_NAMES
    R, Ps = rink(f"{W}/full"), periods(W)
    cfg = json.load(open(f"{W}/full/rink.json")) if os.path.exists(f"{W}/full/rink.json") else {}
    opt = _review_options(W)
    jersey = cfg.get("jersey", "light blue")
    card = next((c for c in (f"{W}/rev_{Q['label'].lower()}/roster_card.jpg" for Q in ([P] if P else []) + Ps)
                 if os.path.exists(c)), None)
    bx0, bx1, by0, by1 = R.bench_view()
    other = "right" if R.side == "left" else "left"
    return dict(
        W=W, PY=PY.replace("\\", "/"), ROOT=ROOT.replace("\\", "/"), team_desc=TEAM,
        jersey_desc=("WHITE jerseys with blue numbers and blue trim" if jersey.startswith("white")
                     else "LIGHT-BLUE jerseys with white numbers"),
        opp_desc=_opp_look(jersey, opt),
        notes="".join(f" {n.rstrip('.')}." for n in opt.get("notes", [])),
        roster=", ".join(f"#{n} {v.upper()}" for n, v in sorted(SKATERS.items())),
        goalie_line=(f"Our goalie is #{GOALIES[0]} {GOALIE_NAMES.get(GOALIES[0], '').upper()} (big leg pads), never a skater."
                     if GOALIES else "Our goalie isn't on the roster card (a sub in goal, big leg pads); he is never a skater."),
        nets_line=("Our net is the " + ", ".join(f"{_net_side(R, Q['net'])} one in {Q['label']}" for Q in Ps)
                   + " (the goalie's end).") if all(Q.get("net") is not None for Q in Ps) else "",
        card=card,
        card_line=(f"Read {card} once for everyone's look (sock stripes, pants, helmet and glove colours tell players "
                   f"apart when the number is hidden).\n" if card else ""),
        rink_desc=f"{cfg.get('rink', 'renton')}: {R.brief}",
        frame_size=f"{R.size[0]}x{R.size[1]}",
        bench_desc=(f"Our bench is {R.bench_where[R.side]}; `--view bench` crops x {bx0}-{bx1}, y {by0}-{by1}. "
                    f"The opponents' bench is the other one."),
        box_ours=R.box_where.get(R.side, "beside our bench"), box_theirs=R.box_where.get(other, "beside their bench"),
        box_desc=(f" Our penalty box is {R.box_where.get(R.side, 'beside our bench')}; a boxed player is off the ice (the "
                  f"solver knows the pk spans)."),
        clock_line=_clock_line(W, P) if P else "",
        wide="{} {} {} {} 1990 1".format(*R.views["rink"]),
        dets=(f'$PY -I -c "import sys, numpy as np, pandas as pd; t, x, y = map(float, sys.argv[1:]); '
              f"d = pd.read_csv(r'{W}/full/dets.csv', header=None, usecols=range(6), names='frame t x1 y1 x2 y2'.split()); "
              f"d = d[(d.t - t).abs() < 0.07].assign(fx=lambda d: (d.x1 + d.x2) / 2); d['dist'] = np.hypot(d.fx - x, d.y2 - y); "
              f"print(d.nsmallest(3, 'dist')[['t', 'fx', 'y2', 'dist']].round(1).to_string(index=False))\""))


def _clock_text(W, P):
    """The goal and penalty briefs' sentence on period P's clock: the gap briefs' clock line, or without clock.json
    where the seconds in the brief come from."""
    return _clock_line(W, P).strip() or (f"No board clock was read for {P['label']}: the seconds below are its start "
                                         f"plus the clock run, exact only where the clock runs through stoppages.")


def _penalty_state(items, e):
    """Who sat in a box at game-clock second e, as the sheet has it: a sentence for a goal's brief line, or ''."""
    on = [x for x in items if x["minutes"] and x["pair"] is None and x["wiped"] is None and x["e0"] is not None
          and x["e0"] <= e <= x["e1"]]
    if not on:
        return ""
    who = "; ".join(f"{'our' if x['team'] == 'ours' else 'their'} #{x['player']} ({x['period']} {_mm(_mmss(x['clock']))}, "
                    f"{x['board']}:00 on the board)" for x in on)
    ours, theirs = sum(x["team"] == "ours" for x in on), sum(x["team"] == "theirs" for x in on)
    if ours == theirs:
        return f" In the box by the sheet: {who}: even strength (4 on 4), so a goal ends no penalty."
    state = "we are a man short" if ours > theirs else "they are a man short"
    return (f" In the box by the sheet: {who}, so {state}: a power-play goal ends the short team's earliest minor and its "
            f"panel goes dark as it goes in. A power-play goal's sheet time can be off (Roadrunners' on TK's Oct 17 "
            f"game was 37 s after the sheet's 12:25, when the panel went dark).")


def _goal_lines(sheet_, clk, Ps, items, lab, opp):
    """The brief's lines for period lab's goals: sheet order, scorer, the clock's second, where it stopped, the
    search window, the penalties running, and the other times worth trying when nothing is there."""
    Ls, off = _game_clock(Ps, sheet_)
    L, end = Ls[lab], next(P["end"] for P in Ps if P["label"] == lab)
    runs = _clock_runs(clk, Ps, lab)
    out, score = [], [0, 0]
    for n, g in enumerate(sheet_.get("goals", []), 1):
        before = f"{score[0]}-{score[1]}"
        score[0 if g["team"] == "for" else 1] += 1
        if g["period"] != lab:
            continue
        c = _mmss(g["clock"]); vt = _sheet_t(clk, Ps, lab, c, L)
        names = lambda nums, nm: ", ".join(f"#{a} {b}" for a, b in zip(nums, nm)) or "unassisted"
        if g["team"] == "for":
            who = f"OURS, #{g['scorer']} {str(g['scorer_name']).upper()} (assists: {names(g['assists'], [str(x).upper() for x in g['assist_names']])})"
        else:
            who = f"THEIRS ({opp}), #{g['scorer']} {g['scorer_name']} (assists: {names(g['assists'], g['assist_names'])})"
        s = f"{n}. {lab} {_mm(c)}, {who}. Score before it {before} (ours first)."
        C = _clock_period(clk, Ps, lab)
        if C and C["knots"][0][1] < c:   # LADA R's Nov 9 video began at 17:23 of the 1st, after a goal at 17:50
            out.append(s + f" The board's clock was already at {_mm(C['knots'][0][1])} when {lab}'s video begins "
                           f"({C['knots'][0][0]} s): this goal is probably before the video starts. Check the score on the "
                           f"board then; if so, report it with \"t\": null.")
            continue
        stops = _clock_stops(clk, Ps, lab, vt - 40, vt + 60, min_len=3)
        # stops at about the sheet's time: a slip of a second or two, or the operator moving the clock during the
        # stoppage (BW's Nov 15: stopped at 8:48 for the goal, the sheet's 8:42 at the next stop)
        near = [a for a, _, cc in stops if c - 2 <= cc <= c + 10]
        # a stop-time clock that didn't stop near the sheet's time: every stop around it (Y's Nov 2: the sheet's 11:39
        # was a goal at 11:54, the clock still for 5 s; TK's Nov 1: 4:56 was a goal at 4:05)
        wide = runs is False and not near and _clock_stops(clk, Ps, lab, vt - 60, vt + 120, min_len=5)
        stops = wide or stops
        s += (f" The board's clock first showed {_mm(c)} at {vt} s ({_mm(vt)} of video)" if C else
              f" The period's start plus the clock run puts {_mm(c)} at {vt} s ({_mm(vt)} of video)")
        s += ("; it stood still at " + ", ".join(f"{_mm(cc)} from {a} to {b} s" for a, b, cc in stops) + "." if stops else
              "; it didn't stop within a minute of that." if runs is not None else ".")
        lo, hi = ((min(near + [vt]) - 15, vt + 5) if near else
                  (min(a for a, _, _ in wide) - 15, max(a for a, _, _ in wide) + 5) if wide else
                  (vt - 30, end) if runs is None else (vt - 30, vt + 10))
        s += f" Search {max(lo, next(P['start'] for P in Ps if P['label'] == lab))}-{hi} s first" + (
            " (the clock stopped at about the sheet's time: the goal is a second or two before one of those stops)." if near else
            " (the clock didn't stop at the sheet's time, which is wrong then: the goal is a second or two before one of "
            "those stops, the one followed by a center-ice faceoff and a score change; on TK's Nov 1 game the sheet's "
            "4:56 was a goal at 4:05, 73 s later)." if wide else
            " (the clock ran on here, so the sheet's time can trail the goal by up to 25 s)." if runs else
            " (no board clock was read for this period, so that second is only the earliest the goal can be: every "
            "stoppage the clock stood through puts it later, by minutes in a 3rd; search on from there to the period's "
            "end)." if runs is None else
            " (the clock didn't stop at the sheet's time here: look wider if nothing is there).")
        if c < 60 and runs is not None:   # TK's Oct 25 (0:49), LADA R's Nov 2 (0:02): 59 and 160 s after the clock's
            s += (f" In the last minute the board shows tenths and the clock reading has gone wrong there before: if "
                  f"nothing is there, look on to {end} s, the period's end.")
        s += _penalty_state(items, off[lab] + L - c)
        same = [x for x in items if x["period"] == lab and x["clock"] == g["clock"]]
        if same:
            s += (" The sheet has a penalty at this same clock (" + ", ".join(f"{'our' if x['team'] == 'ours' else 'their'} "
                  f"#{x['player']} {x['type']}" for x in same) + "): either the goal wiped out a delayed call, or the sheet "
                  "gave the goal the penalty's time; say which in `note`.")
        alt = [f"{_mm(c)} in {Q['label']} is at {_sheet_t(clk, Ps, Q['label'], c, Ls[Q['label']])} s" for Q in Ps
               if Q["label"] != lab and c <= Ls[Q["label"]]]
        lost = c - 600 if c >= 600 else c + 600 if c + 600 <= L else None   # 17:17 for 7:17 and back
        if lost is not None:
            alt.append(f"{_mm(lost)} (a lost or extra digit) in {lab} is at {_sheet_t(clk, Ps, lab, lost, L)} s")
        s += (" If nothing is there: " + "; ".join(alt) + ".") if alt else ""
        out.append(s)
    return out


def _pen_brief_lines(items, clk, Ps, sheet_=None):
    out = []
    for x in items:
        c = _mmss(x["clock"])
        vt = _sheet_t(clk, Ps, x["period"], c, _plen(x["period"], sheet_)) if x["e0"] is not None else None
        who = f"#{x['player']} {x['name']}" if x["player"] is not None else x["name"]
        s = f"{x['n']}. {x['period']} {_mm(c)}, {'OURS' if x['team'] == 'ours' else 'THEIRS'} {who}: {' + '.join(x['parts'])}."
        if vt is None:
            out.append(s + f" {x['period']} isn't in periods.json: find it on the board."); continue
        runs = _clock_runs(clk, Ps, x["period"])
        s += (f" The board's clock first showed {_mm(c)} at {vt} s ({_mm(vt)} of video)." if runs is not None else
              f" No board clock was read for {x['period']}: its start plus the clock run puts {_mm(c)} at {vt} s "
              f"({_mm(vt)} of video), only the earliest the call can be; search on from there, the panel shows it.")
        s += {True: " This period's clock runs through stoppages: that second is usually the faceoff after the call, about "
                    "30 s after the whistle, and the infraction 20-50 s before it (up to 73 s on the archived games); look "
                    "back from there.",
              False: " This period's clock stops at whistles: that second is the whistle, 1-10 s after the infraction "
                     "(where the operator ran the clock on after the whistle, the whistle is at an earlier stop).",
              None: ""}[runs]
        y = next((y for y in items if y["n"] == x["pair"]), None)
        if y:
            s += (f" Coincident with {'their' if y['team'] == 'theirs' else 'our'} #{y['player']}'s (item {y['n']}): "
                  f"count both teams on a faceoff frame after the call to tell 5 on 5 from 4 on 4.")
        if not x["minutes"]:
            s += " A misconduct: the player sits 10 minutes, his team doesn't play short."
        if x["wiped"]:
            s += (f" The sheet has a goal at the same clock ({x['wiped']['clock']}): a delayed call the goal wiped out "
                  f"(never on the board), or the sheet gave the goal the penalty's time; say which.")
        if x["team"] == "ours" and x["spans"]:
            s += ((" From the clock alone the kill would run " if not x["rough"] else
                   " From the period's start plus the clock run (no board clock read) the kill would start no earlier "
                   "than ")
                  + ", ".join(f"{lab} {a}-{b}" for lab, a, b in x["spans"])
                  + (f" ({x['why']})" if x["why"] else "") + ": find the real one"
                  + (" (it is not in periods.json: yours is the kill solve takes)." if x["rough"] else "."))
        elif x["team"] == "theirs" and x["end_goal"]:
            s += f" Our goal at {x['end_goal']['clock']} falls inside it (a power-play goal ends a minor)."
        out.append(s)
    return out


def goal_briefs(W):
    """One goal checker's brief per period with goals on the game sheet (W/scratch/goals/prompt_pN.md, from
    pipeline/goal_prompt.md) and one for all of the sheet's penalties, ours and theirs (prompt_pens.md, from
    pipeline/pen_prompt.md), with the rules the session used to carry by hand. They need only what fetch leaves and
    periods.json with its nets (frames, the board, sheet.json, clock.json), no tracks, so the checkers can run beside
    prepare and the review. Each writes one JSON file in its scratch folder, which `highlights` reads."""
    import clock as clock_
    W = W.replace("\\", "/")
    if not os.path.exists(f"{W}/sheet.json"):
        sys.exit(f"no {W}/sheet.json: `run_game.py sheet {W}` first")
    sheet_ = json.load(open(f"{W}/sheet.json", encoding="utf-8"))
    clk, Ps, R = clock_.load(W), periods(W), rink(f"{W}/full")
    if any(P.get("net") is None for P in Ps):   # the briefs tell each checker which net is ours
        sys.exit(f"set each period's net in {W}/periods.json first")
    opp = _opp_name(sheet_)
    game = dict(opp_name=opp, opp_poss=_their_scorer(dict(scorer=None, scorer_name=""), opp).strip(),
                board_side="HOME" if sheet_.get("us") == "home" else "GUEST", sheet_side=sheet_.get("us", "?"))
    items = penalty_kills(W, Ps, sheet_, clk)
    gd = f"{W}/{GOAL_DIR}"; os.makedirs(gd, exist_ok=True)
    plan = [_missing_periods(sheet_, Ps)] if _missing_periods(sheet_, Ps) else []
    # these briefs can come before the roster work: a sub the sheet has playing who isn't in roster.json yet is named
    from roster import ALL_SKATERS, GOALIE_NAMES
    known = set(ALL_SKATERS) | set(GOALIE_NAMES)
    new_ = [x for x in sheet_.get("played_names", []) if re.match(r"#(\d+)", x) and int(re.match(r"#(\d+)", x).group(1)) not in known]
    sub_line = ("; and on the game sheet as playing, not in roster.json yet: " + ", ".join(new_)) if new_ else ""
    def context(P=None):
        ctx = _brief_context(W, P)
        ctx["roster"] += sub_line
        return ctx
    for P in Ps:
        lab = P["label"]; p = lab.lower()
        lines = _goal_lines(sheet_, clk, Ps, items, lab, opp)
        if not lines:
            continue
        ours = _net_side(R, P["net"]).lower(); theirs = "right" if ours == "left" else "left"
        # the gap briefs' context for this period: its own roster card once prepare has made one, its clock line
        text = open(f"{HERE}/goal_prompt.md", encoding="utf-8").read().format(
            **context(P), **game, scratch=f"{gd}/{p}", out_file=f"{gd}/{p}/goals.json", period=lab,
            period_name=PERIOD_NAMES.get(lab, lab), pstart=P["start"], pend=P["end"], our_side=ours.upper(),
            our_net=R.nets[ours], their_side=theirs.upper(), their_net=R.nets[theirs],
            clock_desc=_clock_text(W, P), goals="\n".join(lines))
        open(f"{gd}/prompt_{p}.md", "w", encoding="utf-8").write(text)
        plan.append(f"{lab}: {len(lines)} goal(s) -> {gd}/prompt_{p}.md (answers {gd}/{p}/goals.json)")
    if items:
        text = open(f"{HERE}/pen_prompt.md", encoding="utf-8").read().format(
            **context(), **game, scratch=f"{gd}/pens", out_file=f"{gd}/pens/pens.json",
            clock_desc=" ".join(_clock_text(W, P) for P in Ps), pens="\n".join(_pen_brief_lines(items, clk, Ps, sheet_)))
        open(f"{gd}/prompt_pens.md", "w", encoding="utf-8").write(text)
        plan.append(f"penalties: {len(items)} ({sum(x['team'] == 'ours' for x in items)} ours) -> {gd}/prompt_pens.md "
                    f"(answers {gd}/pens/pens.json)")
    print("\n".join(plan) or "the game sheet has no goals and no penalties: nothing to brief")
    if any("-> " in x for x in plan):
        print(f"{len(plan)} brief(s): for each, one general-purpose subagent whose whole prompt is\n"
              f"  'Read <brief> and do exactly what it says. Reply with one line per goal or penalty.'\n"
              f"  All at once, beside prepare and the review. Then `run_game.py highlights {W} --write`.")


def _load_answers(f):
    """A checker's JSON answer as a list of dicts; a broken file is reported and counts as none."""
    try:
        x = json.load(open(f, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"{f}: not readable JSON ({e}); skipped")
        return []
    return [e for e in (x if isinstance(x, list) else [x]) if isinstance(e, dict)]


def _spot(v):
    """A checker's [t, x, y] (shot or pass) as numbers, or None."""
    try:
        return [_num(v[0]), int(round(float(v[1]))), int(round(float(v[2])))] if v else None
    except (TypeError, ValueError, IndexError):
        return None


def _note(period, clock, desc, score=None):
    """'1st period, clock 16:52: <desc>, 1-0', as the hand-written notes have it."""
    return (f"{PERIOD_NAMES.get(period, period)}, clock {_mm(_mmss(clock))}: {str(desc).strip().rstrip('.')}"
            + (f", {score[0]}-{score[1]}" if score else ""))


def _opp_name(sheet_):
    return sheet_["visiting"] if sheet_.get("us") == "home" else sheet_.get("home", "the opponents")


def _their_scorer(g, opp):
    """An opponents' goal's scorer and assists as the sheet gives them, for its note: "T.B.D.'s #91 Muratidinov from
    #48 Nanakul" (their numbers stay out of `scorer` and `assists`, which hold ours)."""
    who = lambda n, nm: " ".join(x for x in (f"#{n}" if n is not None else "", str(nm or "")) if x)
    ast = " and ".join(who(n, nm) for n, nm in zip(g.get("assists") or [], g.get("assist_names") or []))
    poss = opp + ("'" if opp.endswith("s") else "'s")   # "BladeRunners'", "T.B.D.'s"
    return f"{poss} {who(g['scorer'], g['scorer_name'])}" + (f" from {ast}" if ast else "")


def _build_highlights(W, Ps, sheet_, clk, items, gseen, pseen, say):
    """The goal and penalty entries from the sheet and the checkers' answers, goals by t then penalties by t; `say`
    collects what the session should know (missing entries, odd times, a scorer seen differently)."""
    from roster import ALL_SKATERS, GOALIE_NAMES
    labels = [P["label"] for P in Ps]
    goals, opp = sheet_.get("goals", []), _opp_name(sheet_)
    def when(n):   # the goal's place in the game, for the running score
        e, g = gseen.get(n) or {}, goals[n - 1]
        if e.get("t") is not None:
            return float(e["t"])
        return _sheet_t(clk, Ps, g["period"], _mmss(g["clock"]), _plen(g["period"], sheet_)) if g["period"] in labels \
            else float("inf")   # a period periods.json lacks comes last, so it can't shift every note's running score
    score, gl = [0, 0], []
    for n in sorted(range(1, len(goals) + 1), key=lambda n: (when(n), n)):
        g = goals[n - 1]; e = gseen.get(n)
        score[0 if g["team"] == "for" else 1] += 1
        what = f"goal {n} ({g['period']} {g['clock']}, {g['team']}, #{g['scorer']} {g['scorer_name']})"
        if not e:
            say.append(f"{what}: no entry from the goal checker; not in highlights.json"); continue
        if e.get("t") is None:
            say.append(f"{what}: the checker didn't find it ({e.get('desc') or e.get('note') or 'no reason given'}); "
                       f"not in highlights.json: the page counts goals on video"); continue
        t, per = _num(e["t"]), e.get("period") or g["period"]
        P = next((P for P in Ps if P["start"] <= t <= P["end"]), None)
        if P is None or P["label"] != per:
            say.append(f"{what}: t {t} is " + (f"in {P['label']}, not {per}" if P else "outside every period"))
        h = dict(type="goal", team=g["team"], t=t, sheet_n=n)   # sheet_n: generated.json's only (HL_RECORD)
        desc = str(e.get("desc") or "").strip()
        if g["team"] == "for":   # scorer and assists hold OUR numbers (lineup check, page, season tables)
            if g.get("scorer") is not None:
                h.update(scorer=g["scorer"], assists=list(g.get("assists") or []))
            desc = desc or f"{g['scorer_name']} #{g['scorer']}"
        elif g.get("scorer") is not None and f"#{g['scorer']}" not in desc:
            # theirs: the sheet's scorer and assists go into the note, as sessions typed them ("T.B.D.'s #21 Schiller")
            desc = ", ".join(x for x in (_their_scorer(g, opp), desc) if x)
        if not e.get("desc"):
            say.append(f"{what}: the checker gave no desc; the note names only the scorer")
        h["note"] = _note(per, e.get("clock") or g["clock"], desc, score)
        h.update(shot=_spot(e.get("shot")), **{"pass": _spot(e.get("pass"))},
                 on_ice=sorted({int(x) for x in e.get("on_ice") or [] if str(x).lstrip("-").isdigit()}))
        if e.get("team") and e["team"] != g["team"]:
            say.append(f"{what}: the checker calls it {e['team']}; the sheet's {g['team']} stands")
        if h["shot"] and h["shot"][0] > t:
            say.append(f"{what}: shot at {h['shot'][0]} is after t {t}")
        elif h["shot"] and t - h["shot"][0] > 15:
            say.append(f"{what}: shot at {h['shot'][0]} is {t - h['shot'][0]:.1f} s before t {t} (a replay that long?)")
        if h["pass"] and (h["pass"][0] > t or (h["shot"] and h["pass"][0] > h["shot"][0])):
            say.append(f"{what}: pass at {h['pass'][0]} comes after the shot or the goal")
        seen = e.get("scorer_seen")
        if seen is not None and str(seen) != str(g["scorer"]) and g["team"] == "for":
            say.append(f"{what}: the checker saw #{seen} put it in ({e.get('scorer_sure') or 'sureness not given'}); the "
                       f"sheet's #{g['scorer']} stands on the page: ask the user to check with the team")
        odd = [p for p in h["on_ice"] if p not in ALL_SKATERS and p not in GOALIE_NAMES]
        if odd:
            say.append(f"{what}: on_ice has numbers not on our roster: {odd}")
        if str(e.get("sure", "")).lower() == "low":
            say.append(f"{what}: the checker is unsure of t or shot ({e.get('note') or e.get('desc')})")
        if g["period"] in labels:
            vt = _sheet_t(clk, Ps, g["period"], _mmss(g["clock"]))
            if abs(t - vt) > 30:
                say.append(f"{what}: t {t} is {t - vt:+.0f} s from the sheet's time ({vt} s)")
        if e.get("note"):
            say.append(f"{what}: the checker's note: {e['note']}")
        gl.append(h)
    gl.sort(key=lambda h: h["t"])
    for k, h in enumerate(gl, 1):   # key order as the hand-written files have it
        rest = {x: h.pop(x) for x in ("note",) + HL_WORK}
        h.update(clip=f"clips/goal-{k}.mp4", poster=f"clips/goal-{k}.jpg", **rest)
    pl = []
    mine = [x for x in items if x["team"] == "ours"]
    for x in mine:
        e = pseen.get(x["n"]) or {}
        what = f"penalty {x['n']} ({x['period']} {x['clock']}, #{x['player']} {x['name']})"
        if not e:
            say.append(f"{what}: no entry from the penalty checker; entered from the sheet at its clock's second")
        player = x["player"] if x["player"] is not None else e.get("sat")
        t = e.get("t") if e.get("t") is not None else e.get("whistle")
        if t is None:
            t = x["spans"][0][1] if x["spans"] else _sheet_t(clk, Ps, x["period"], _mmss(x["clock"])) if x["e0"] is not None else None
        if t is None:
            say.append(f"{what}: no time for it; not in highlights.json"); continue
        desc = e.get("desc") or f"{x['type'].lower()}, {x['minutes']} minutes"
        pl.append(dict(type="penalty", player=player, t=_num(t), sheet_n=x["n"],
                       note=_note(e.get("period") or x["period"], e.get("clock") or x["clock"], desc)))
        if e and _kill_answer(e)[0] == "none":   # the unsure ones: _apply_kills says what stays
            say.append(f"{what}: no kill: {_kill_answer(e)[1]}")
        if e.get("ps"):
            say.append(f"{what}: a penalty shot against us at {e['ps']}: add it as a `ps` span in periods.json (solve "
                       f"puts nobody on), and clip the shot as a moment")
    pl.sort(key=lambda h: h["t"])
    for h in pl:
        many = sum(q["player"] == h["player"] for q in pl) > 1
        name = f"penalty-{h['player'] if h['player'] is not None else 'bench'}" + (f"-{int(h['t'])}" if many else "")
        h.update(clip=f"clips/{name}.mp4", poster=f"clips/{name}.jpg", note=h.pop("note"))
    return gl + pl


def _merge_highlights(old, new, gen, say):
    """new entries onto an existing highlights.json without losing hand edits. An entry's record in gen (the entries
    the last `highlights --write` wrote, generated.json) is found by the sheet's goal or penalty number (sheet_n), and
    its entry in highlights.json by the record's clip, however far the checker's t moved; a record whose entry is no
    longer there was deleted by hand and stays out. Without a record (a file written by hand, or one from before
    generated.json kept the numbers) an entry matches by its clip within 60 s (goals), else by team or player and
    time. A field the record holds takes the new value; one that differs from the record was edited by hand and
    stays, as does anything without a record. Clip names stay. Entries the checkers don't give (moments, a goal they
    no longer find) stay as they are."""
    out, used = [], set()
    gen = gen or []
    def record(h):
        return next((x for x in gen if x.get("type") == h["type"] and x.get("sheet_n") is not None
                     and x.get("sheet_n") == h.get("sheet_n")), None)
    def match(h):
        rec = record(h)
        if rec is not None:
            return next((i for i, o in enumerate(old) if i not in used and o.get("type") == h["type"]
                         and o.get("clip") == rec.get("clip")), None), rec
        cands = [i for i, o in enumerate(old) if i not in used and o.get("type") == h["type"]]
        if h["type"] == "goal":
            same = [i for i in cands if old[i].get("clip") == h["clip"] and old[i].get("team") == h["team"]
                    and abs(float(old[i]["t"]) - float(h["t"])) <= 60]
            near = [i for i in cands if old[i].get("team") == h["team"] and abs(float(old[i]["t"]) - float(h["t"])) <= 30]
        else:
            same, near = [], [i for i in cands if old[i].get("player") == h["player"] and abs(float(old[i]["t"]) - float(h["t"])) <= 90]
        i = (same or sorted(near, key=lambda i: abs(float(old[i]["t"]) - float(h["t"]))) or [None])[0]
        return i, (next((x for x in gen if x.get("clip") == old[i].get("clip")), None) if i is not None else None)
    # a deleted entry's clip name stays its record's, so that no new entry takes it
    taken = {o.get("clip") for o in old} | {x.get("clip") for x in gen}
    for h in new:
        i, g = match(h)
        if i is None and g is not None:   # its record is there, its entry isn't: deleted by hand
            h.update(clip=g.get("clip"), poster=g.get("poster"))   # the record goes on saying so
            say.append(f"{g.get('clip', '?')[6:-4]} ({h['type']} {h.get('sheet_n')} on the sheet): deleted from "
                       f"highlights.json by hand, so left out; take its entry out of scratch/goals/generated.json to "
                       f"have it back")
            continue
        if i is None:
            if h["clip"] in taken:   # a name an old entry keeps: the next free goal-K, or penalty-N-T
                base = h["clip"][:-4]
                if h["type"] == "goal":
                    stem, k = base.rsplit("-", 1)[0], 1
                    while f"{stem}-{k}.mp4" in taken:
                        k += 1
                    base = f"{stem}-{k}"
                else:
                    base = f"{base}-{int(float(h['t']))}"
                h.update(clip=f"{base}.mp4", poster=f"{base}.jpg")
            taken.add(h["clip"]); out.append(h)
            say.append(f"{h['clip'][6:-4]}: new entry")
            continue
        used.add(i); o = old[i]
        m, changed, kept = dict(o), [], []
        for k, v in h.items():
            if k in ("clip", "poster") + HL_RECORD or o.get(k) == v:
                continue
            if k not in o or (g is not None and g.get(k) == o[k]):
                m[k] = v; changed.append(f"{k} {o.get(k)!r} -> {v!r}" if k in o else f"{k} {v!r} added")
            else:
                kept.append(f"{k} kept as edited ({o[k]!r}; the checkers say {v!r})")
        h.update(clip=o.get("clip"), poster=o.get("poster"))   # the record names the kept clip
        if changed or kept:
            say.append(f"{o.get('clip', '?')[6:-4]}: " + "; ".join(changed + kept))
        out.append(m)
    for i, o in enumerate(old):
        if i not in used:
            out.append(o)
            if o.get("type") in ("goal", "penalty"):
                say.append(f"{o.get('clip', '?')[6:-4]} at {o.get('t')}: kept from highlights.json, though the checkers "
                           f"and the sheet no longer give it")
    rank = {"goal": 0, "penalty": 1}
    return sorted(out, key=lambda h: (rank.get(h.get("type"), 2), float(h["t"]) if h.get("type") in rank else 0))


def _apply_kills(Ps, items, pseen, say):
    """Each of our penalties' kill in periods.json (the one `pk` proposed, or any there for that player and stretch)
    replaced by the penalty checker's, split at intermissions, each change said. A penalty that sat without a kill
    (coincident minors at 5 on 5, a misconduct) gets an `off` span for the player over box_in..box_out. Returns
    whether periods.json changed and those off spans as (period, span, penalty number), for W/hand_spans.txt."""
    def split(a, b):
        return [(P["label"], _num(max(a, P["start"])), _num(min(b, P["end"]))) for P in Ps if max(a, P["start"]) < min(b, P["end"])]
    fresh, changed, offs = [], False, []
    for x in sorted((x for x in items if x["team"] == "ours"), key=lambda x: x["player"] is None):
        e = pseen.get(x["n"])
        if not e:
            continue
        who = e.get("sat") if e.get("sat") is not None else x["player"]
        ans = _kill_answer(e)
        if ans[0] == "unsure":   # "couldn't see it" is no reason to drop a kill: the one in periods.json stays
            have = [f"{P['label']} {k['start']}-{k['end']}" for P in Ps for k in P.get("pk", [])
                    if k.get("player") in (x["player"], who) and any(lab == P["label"] and k["start"] < b and a < k["end"]
                                                                       for lab, a, b in x["spans"])]
            say.append(f"penalty {x['n']} #{who}: the checker gives no kill and no reason for none ({ans[1]}): "
                       + (f"periods.json's kill {', '.join(have)} stays" if have else "periods.json has no kill for it")
                       + "; give `kill` in pens.json, or null with a `why`, and run this again")
            continue
        new = split(ans[1], ans[2]) if ans[0] == "kill" else []
        look = new + [tuple(s) for s in x["spans"]]
        ok = lambda k: k.get("player") in (x["player"], who)   # a bench minor's kill (no player) is its own
        old = [(P, k) for P in Ps for k in P.get("pk", []) if all(k is not f for f in fresh) and ok(k)
               and any(lab == P["label"] and k["start"] < b and a < k["end"] for lab, a, b in look)]
        was = sorted((P["label"], _num(k["start"]), _num(k["end"])) for P, k in old)
        if was != sorted(new) or any(k.get("player") != who for _, k in old):
            for P, k in old:
                P["pk"].remove(k)
            for lab, a, b in new:
                P = next(P for P in Ps if P["label"] == lab)
                k = add_span(P, "pk", a, b, who)
                if k is not None:
                    fresh.append(k)
            fmt = lambda s: ", ".join(f"{lab} {a}-{b}" for lab, a, b in s) or "none"
            say.append(f"penalty {x['n']} #{who}: kill {fmt(was)} -> {fmt(new)}" + (f" ({e.get('why')})" if e.get("why") else ""))
            changed = True
        if not new and who is not None and e.get("box_in") is not None and e.get("box_out") is not None:
            for lab, a, b in split(float(e["box_in"]), float(e["box_out"])):
                P = next(P for P in Ps if P["label"] == lab)
                o = add_span(P, "off", a, b, who)
                if o is None:
                    continue
                offs.append((P, o, x["n"])); changed = True
                say.append(f"penalty {x['n']} #{who}: + {lab} off {a}-{b}, in the box with no kill")
    for P in Ps:
        for k in ("pk", "off"):
            if k in P:
                P[k] = sorted(P[k], key=lambda s: (s["start"], s.get("player") or 0))
    return changed, offs


def cmd_highlights(a):
    """highlights.json from the goal and penalty checkers' answers (W/scratch/goals/pN/goals.json, pens/pens.json)
    and sheet.json, in the format the page reads: per goal the checker's t, for ours the sheet's scorer and assists
    (always; theirs are named in the note only, since those keys hold our numbers), a note '1st period, clock 16:52:
    <desc>, 1-0' with the running score, clips/goal-K; per penalty of ours its
    infraction, note and clip. Each goal also carries the checker's shot, pass and on_ice for the clips and the
    lineup check (publish leaves them out of game.json). It prints what doesn't add up. An existing
    highlights.json is updated entry by entry (_merge_highlights). With --write it writes the file and replaces our
    kills in periods.json with the checker's (_apply_kills); without, it only prints."""
    import clock as clock_
    W = os.path.abspath(a.W).replace("\\", "/")
    if not os.path.exists(f"{W}/sheet.json"):
        sys.exit(f"no {W}/sheet.json: `run_game.py sheet {a.W}` first")
    Ps, clk = periods(W), clock_.load(W)
    sheet_ = json.load(open(f"{W}/sheet.json", encoding="utf-8"))
    gd = f"{W}/{GOAL_DIR}"
    gseen, say = {}, []
    for f in sorted(glob.glob(f"{gd}/p*/goals.json")):
        for e in _load_answers(f):
            if e.get("n") is None:
                say.append(f"the goal checker reports a goal the sheet doesn't have, at {e.get('t')} ({e.get('team')}): "
                           f"{e.get('desc') or e.get('note')}; not entered (the sheet's score stands): ask the user")
            else:
                gseen[int(e["n"])] = e
    pf = f"{gd}/pens/pens.json"
    pseen = {int(e["n"]): e for e in (_load_answers(pf) if os.path.exists(pf) else []) if e.get("n") is not None}
    if not gseen and sheet_.get("goals"):
        say.append(f"no goal checker's answers in {gd}/p*/goals.json (`goals {a.W} --brief` writes the briefs)")
    items = penalty_kills(W, Ps, sheet_, clk)
    if _missing_periods(sheet_, Ps):
        say.append(_missing_periods(sheet_, Ps))
    if not os.path.exists(pf) and any(x["team"] == "ours" for x in items):
        say.append(f"no {pf}: our penalties are entered from the sheet and the proposed kills stay")
    new = _build_highlights(W, Ps, sheet_, clk, items, gseen, pseen, say)
    hp, rec = f"{W}/highlights.json", f"{gd}/generated.json"
    if os.path.exists(hp):
        old = json.load(open(hp, encoding="utf-8"))
        hl = _merge_highlights(old, new, json.load(open(rec, encoding="utf-8")) if os.path.exists(rec) else None, say)
    else:
        hl = new
    kills, offs = _apply_kills(Ps, items, pseen, say)
    for h in hl:
        who = (f" #{h['scorer']}" + (f" (A {', '.join(f'#{x}' for x in h.get('assists') or [])})" if h.get("assists") else "")
               if h.get("scorer") is not None and h["type"] == "goal" else f" #{h['player']}" if h["type"] == "penalty" else "")
        work = "".join(f" {k} {h[k]}" for k in HL_WORK if h.get(k))
        print(f"  {h.get('clip', '?')[6:-4]:<18} {h['t']:>7} {h.get('team', '')}{who}{work}: {h.get('note', h.get('title', ''))}")
    for s in say:
        print("  !", s)
    sc = sheet_.get("score")
    gf, ga = (sum(h["type"] == "goal" and h["team"] == x for h in hl) for x in ("for", "against"))
    print(f"goals on video {gf}-{ga}" + (f", the sheet's final {sc[0]}-{sc[1]}" if sc else ""))
    if not a.write:
        print(f"`run_game.py highlights {a.W} --write` writes {hp}" + (" and the kills into periods.json" if kills else ""))
        return
    os.makedirs(gd, exist_ok=True)
    hl = [{k: v for k, v in h.items() if k not in HL_RECORD} for h in hl]
    json.dump(hl, open(hp, "w", encoding="utf-8"), indent=1)   # ASCII: lineup_windows and gaps read it without an encoding
    json.dump(new, open(rec, "w", encoding="utf-8"), indent=1)
    if kills:
        save_periods(W, Ps, sort=("pk", "off"))
        for P, o, n in offs:   # the spans no checker's fixes.json holds go into span's log, marked as this command's
            log_span(W, P, "off", o["start"], o["end"], o["player"],
                     f"in the box with no kill, penalty {n}; added by highlights --write")
    print(f"wrote {hp}" + (f" and the kills into {W}/periods.json" + (f" ({len(offs)} off span(s) logged in "
                                                                       f"{W}/hand_spans.txt)" if offs else "")
                           + "; solve again" if kills else ""))


def seen_off(h, on_t):
    """Our skaters the goal checker read on the ice at a goal (highlights.json "on_ice") whom the solver has off: a
    lost track or a wrong label (on TK's Nov 1 and Y's Nov 9 games such a comparison caught a wrong lineup)."""
    from roster import GOALIES
    return [int(p) for p in h.get("on_ice") or [] if int(p) not in on_t and int(p) not in GOALIES]


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


def _grab(vid, t, x0, x1, y0, y1):
    """The video's frame at t s cropped to x0-x1 x y0-y1 (even sizes: see cmd_frames), as BGR; None past the end."""
    import imageio_ffmpeg
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-loglevel", "error", "-ss", str(t), "-i", vid,
                        "-frames:v", "1", "-vf", f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}", "-f", "rawvideo", "-pix_fmt",
                        "bgr24", "-"], capture_output=True)
    if len(r.stdout) != (y1 - y0) * (x1 - x0) * 3:
        return None
    return np.frombuffer(r.stdout, np.uint8).reshape(y1 - y0, x1 - x0, 3).copy()


_TRACKS = {}


def _track_tables(W, p):
    """A period's tracked boxes (tracks_v1.csv) and the solver's pieces (segs_final.csv), read once."""
    if p not in _TRACKS:
        tr = pd.read_csv(f"{W}/{p}/tracks_v1.csv", usecols=["frame", "t", "x1", "y1", "x2", "y2", "tid"])
        S = pd.read_csv(f"{W}/{p}/segs_final.csv", usecols=["tid", "t0", "t1", "plabel"]) \
            if os.path.exists(f"{W}/{p}/segs_final.csv") else pd.DataFrame(columns=["tid", "t0", "t1", "plabel"])
        _TRACKS[p] = (tr, S)
    return _TRACKS[p]


def _piece_label(S, tid, t):
    """The solver's label for track tid at t: "#N", "?" (no number) or "x" (not in the solve: run2.py drops pieces
    seated behind our bench's boards)."""
    s = S[(S.tid == tid) & (S.t0 <= t + 0.07) & (S.t1 >= t - 0.07)]
    return "x" if s.empty else (f"#{int(s.plabel.iloc[0])}" if s.plabel.iloc[0] >= 0 else "?")


def _draw_tracks(im, W, t, x0, y0, s):
    """Draw our tracked boxes nearest t on a tile cut at (x0, y0) and scaled by s, each with its tid and label (ten
    checkers in four games wrote their own scripts for this, Nov 1-15)."""
    import cv2
    P = next((P for P in periods(W) if P["start"] - 5 <= t <= P["end"] + 5), None)
    if P is None or not os.path.exists(f"{W}/{P['label'].lower()}/tracks_v1.csv"):
        return
    tr, S = _track_tables(W, P["label"].lower())
    f = tr.frame.values[np.abs(tr.frame.values - t * FPS).argmin()]
    if abs(f - t * FPS) > FPS:
        return
    fs = 0.5 if s < 0.4 else 0.7
    for r in tr[tr.frame == f].itertuples():
        lab = _piece_label(S, r.tid, r.t)
        col = (0, 210, 0) if lab[0] == "#" else (0, 220, 255) if lab == "?" else (170, 170, 170)
        p1, p2 = (int((r.x1 - x0) * s), int((r.y1 - y0) * s)), (int((r.x2 - x0) * s), int((r.y2 - y0) * s))
        if p2[0] < 0 or p2[1] < 0 or p1[0] > im.shape[1] or p1[1] > im.shape[0]:
            continue
        cv2.rectangle(im, p1, p2, col, 2)
        org = (max(p1[0], 0), max(p1[1] - 5, 14))
        cv2.putText(im, f"{r.tid} {lab}", org, cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 0, 0), 4)   # outline: legible anywhere
        cv2.putText(im, f"{r.tid} {lab}", org, cv2.FONT_HERSHEY_SIMPLEX, fs, col, 1)


def cmd_follow(a):
    """Crops of tracked pieces over time, one row per tid of period a.period: a piece's number, where it came from,
    a swap at a crossing. Each crop is 1.5 box heights square around the box, labeled with the time and the solver's
    label then."""
    import cv2
    W = os.path.abspath(a.W); vid = f"{W}/video.webm"
    if not os.path.exists(vid):
        sys.exit(f"no {vid}: follow needs the video (archived folders have none; fetch downloads it again)")
    P = next((P for P in periods(W) if P["label"].lower() == a.period.lower()), None)
    if P is None:
        sys.exit(f"no period {a.period} in periods.json")
    tr, S = _track_tables(W, P["label"].lower())
    fw, fh = rink(f"{W}/full").size
    H, rows = 240, []
    for tid in a.tids:
        g = tr[tr.tid == tid]
        if g.empty:
            print(f"tid {tid}: not tracked in {P['label']}"); continue
        t0, t1, step = a.range or (g.t.min(), g.t.max(), max(1.0, round((g.t.max() - g.t.min()) / 9)))
        tiles = []
        for t in np.arange(t0, t1 + 1e-6, step):
            r = g.iloc[int(np.abs(g.t.values - t).argmin())]
            im = None
            if abs(r.t - t) <= 1:   # the box nearest t, if the piece was tracked then
                h = r.y2 - r.y1; cx, cy = (r.x1 + r.x2) / 2, (r.y1 + r.y2) / 2
                x0, y0 = int(max(0, cx - 0.75 * h)) // 2 * 2, int(max(0, cy - 0.8 * h)) // 2 * 2
                x1, y1 = min(fw, x0 + int(1.5 * h) // 2 * 2), min(fh, y0 + int(1.5 * h) // 2 * 2)
                im = _grab(vid, r.t, x0, x1, y0, y1)
            if im is None:
                im = np.full((H, H, 3), 255, np.uint8); txt = f"{int(t) // 60}:{int(t) % 60:02d} no box"
            else:
                im = cv2.resize(im, (H, H), interpolation=cv2.INTER_CUBIC)
                txt = f"{int(r.t) // 60}:{int(r.t) % 60:02d} {_piece_label(S, tid, r.t)}"
            cv2.rectangle(im, (0, 0), (12 + 13 * len(txt), 30), (0, 0, 0), -1)
            cv2.putText(im, txt, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            tiles.append(im)
        head = np.full((H, 110, 3), 255, np.uint8)   # the row's tid at its left end
        cv2.putText(head, f"tid {tid}", (6, H // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        rows.append(np.hstack([head] + tiles))
    if not rows:
        sys.exit("nothing to show")
    w = max(r.shape[1] for r in rows)
    rows = [np.hstack([r, np.full((H, w - r.shape[1], 3), 255, np.uint8)]) if r.shape[1] < w else r for r in rows]
    cv2.imwrite(a.out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(a.out)


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
        if a.tracks:
            _draw_tracks(im, os.path.abspath(a.W), t, x0, y0, tile_w / (x1 - x0))
        cv2.putText(im, f"{int(t) // 60}:{int(t) % 60:02d}", (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 220), 3)
        tiles.append(im)
    blank = np.full_like(tiles[0], 255)
    rows = [np.hstack(tiles[i:i + cols] + [blank] * (cols - len(tiles[i:i + cols]))) for i in range(0, len(tiles), cols)]
    cv2.imwrite(a.out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(a.out)


def _tracks_arg(spec, pdir):
    """`clip --tracks` as (tracks file, tid lists per player, scorer first). "TID,TID;TID" are tracks in the
    period's tracks_v1.csv, each player's in priority order; "FILE.csv[:TIDS]" is a tracks file of its own: a
    stretch tracked into a folder of its own by run_period.py (LADA R's Nov 2 empty-netter came after the 3rd's tracks
    ended), or a skater traced by hand as t, x, y rows (clip.read_tracks; Beerteam's Nov 7 1st goal), all its
    tracks when no TIDS follow. Such a file belongs outside W/scratch, where archive keeps only the checkers' .md and
    .json: a clip re-cut from the archive needs it (with clip_args.json and clips_check.json, which archive keeps)."""
    m = re.match(r"^(.+\.csv)(?::([\d,;]*))?$", spec, re.I)
    if not m:
        return f"{pdir}/tracks_v1.csv", [[int(x) for x in g.split(",") if x.strip()] for g in spec.split(";")]
    path = os.path.abspath(norm_path(m.group(1)))   # clip_args.json's paths don't pass through main()
    scratch = os.path.abspath(f"{os.path.dirname(os.path.abspath(pdir))}/scratch")
    if os.path.normcase(path).startswith(os.path.normcase(scratch) + os.sep):
        print(f"WARNING clip --tracks: {path} is inside {scratch}, where archive keeps only the checkers' .md and "
              f".json; move it out (say to "
              f"{os.path.dirname(scratch)}/traces/) and give that path, so the clip can be cut again from the archive",
              flush=True)
    if m.group(2):
        return path, [[int(x) for x in g.split(",") if x] for g in m.group(2).split(";")]
    tr = pd.read_csv(path)
    return path, [list(dict.fromkeys(int(x) for x in tr.sort_values("t").tid)) if "tid" in tr else [0]]


def cmd_clip(a):
    from roster import SITE_DIR
    W = os.path.abspath(a.W)
    out = f"{SITE_DIR}/games/{a.game_id}/clips/{a.name}.mp4"
    dry = getattr(a, "dry_run", False)
    if not dry:
        if not os.path.exists(f"{W}/video.webm"):
            sys.exit(f"no {W}/video.webm: a cut needs the video (archived folders have none); --dry-run computes and "
                     "checks the camera's path without it")
        os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = [PY, f"{HERE}/clip.py", f"{W}/full", f"{W}/video.webm", f"{W}/audio.m4a", out, a.t0, a.t1, a.poster]
    focus = a.focus
    tracks = getattr(a, "tracks", None)

    def at_spot(pdir, spot, what):
        """The track at a goal check's spot ("T,X,Y": a shot or a pass), whatever its label, or None."""
        ts, sx, sy = (float(v) for v in spot.split(","))
        tr = pd.read_csv(f"{pdir}/tracks_v1.csv")
        # then 0.5 s: in a pile at the post a track loses its box (Babkin's last one on the Doofers' Nov 15 5th goal
        # was 0.375 s before the goal check's shot, 20 px from it)
        for dt in (0.25, 0.5):
            near = tr[(tr.t - ts).abs() <= dt]
            dist = np.hypot(near.fx - sx, near.fy - sy)
            if len(near) and dist.min() < 200:
                return int(near.tid.iat[int(dist.values.argmin())])
        print(f"clip: no track within 200 px of the {what} at {spot}")
        return None

    # a goal against has no players to name: tracks_v1 holds only ours, so a track at their shot or pass is one of
    # our defenders; clip.py frames the pass spot itself for the 1.5 s before the pass
    if (focus and focus.startswith("#")) or tracks:
        # follow a player (his labeled tracks in this window, in time order: the first covering track wins), or
        # for a goal keep the scorer and assists in the frame ("#14,#13,#89", scorer first)
        nums = [int(n.strip().lstrip("#")) for n in focus.split(",")] if focus and focus.startswith("#") else []
        t0, t1 = float(a.t0), float(a.t1)
        P = next(P for P in periods(W) if P["start"] - 30 <= float(a.poster) <= P["end"] + 30)
        pdir = f"{W}/{P['label'].lower()}"
        path, tids = f"{pdir}/tracks_v1.csv", []
        if nums:
            sg = pd.read_csv(f"{pdir}/segs_final.csv")
            sg = sg[(sg.t1 > t0) & (sg.t0 < t1)].sort_values("t0")
            # a player's tracks in priority order: those his number was read on first. On TK's Oct 25 game a still
            # figure on the far boards was also labeled 61 beside the real #61, and the camera jumped between them
            # a tid is one tracked body over all its pieces, and clip.py follows the whole of it, so leave out one that
            # is someone else's for longer in this window: Fedotov's track on the Doofers' Nov 15 5th goal was #71 for
            # 20 s and #26 for the last 2, and the camera followed him as Babkin
            dur = (np.minimum(sg.t1, t1) - np.maximum(sg.t0, t0)).clip(lower=0)

            def ranked(n):
                mine = dur[sg.plabel == n].groupby(sg.tid).sum()
                other = dur[(sg.plabel >= 0) & (sg.plabel != n)].groupby(sg.tid).sum()
                keep = [x for x in mine.index if mine[x] >= other.get(x, 0)]
                s = sg[(sg.plabel == n) & sg.tid.isin(keep)]
                return s.assign(unread=s.num != n, less=-s.nreads).sort_values(["unread", "less", "t0"]).tid.drop_duplicates()
            tids = [[int(x) for x in ranked(n)] for n in nums]
        chosen = 0
        if tracks:
            # tracks chosen by hand replace the labeled ones player by player (scorer first); a tracks file of its
            # own holds the whole group. R's Oct 26 4th goal: #12's labeled tracks took in our goalie (1465)
            path_, mine = _tracks_arg(tracks, pdir)
            tids, chosen = (mine + tids[len(mine):] if path_ == path else mine), len(mine)
            path = path_
        if a.shot and chosen < 1 and tids:
            # the goal check's shot names the scorer's track at it, whatever its label: on TK's Oct 25 empty-netter
            # the tracks labeled 64 were other players, and the camera framed one of them with the empty net
            tid = at_spot(pdir, a.shot, "shot (the scorer's labeled tracks stand)")
            if tid is not None:
                tids[0] = [tid] + [x for x in tids[0] if x != tid]
        if a.pass_ and len(tids) > 1 and chosen < 2:
            # the passer (the first assist) is the track at the pass, whatever its label
            tid = at_spot(pdir, a.pass_, "pass")
            if tid is not None:
                tids[1] = [tid] + [x for x in tids[1] if x != tid]
        tids = [",".join(str(x) for x in g) for g in tids]
        if len(tids) > 1 or a.net:
            focus = f"group:{path}:" + ";".join(tids) if any(tids) else None
        else:
            focus = f"track:{path}:{tids[0]}" if tids[0] else None
    net = []
    if a.net:
        # the net the goal went into: ours (`net` in periods.json) for one against, the other one for ours
        R = rink(f"{W}/full")
        tg = float(a.poster)
        ours = next(P for P in periods(W) if P["start"] - 30 <= tg <= P["end"] + 30)["net"]
        side = next(s for s, x in R.nets.items() if (x == ours) == (a.net == "against"))
        v = R.views[f"{side}-net"]
        net = [f"{R.nets[side]},{getattr(R, 'NET_Y', (v[2] + v[3]) / 2)}"]
        if a.replay_from or a.shot or a.pass_:
            net += [a.replay_from or "-"] + ([a.shot or "-"] if a.shot or a.pass_ else []) + ([a.pass_] if a.pass_ else [])
    sh(*cmd + ([focus or "-"] + net if net else [focus] if focus else []) + (["--dry-run"] if dry else []))


# s before and after the poster that a clip of each kind runs, as the sessions cut them: the last cut of each clip in
# the 15 archived clips.sh files and the clip logs of 13 more games (Nov 18) ran t-12 .. t+10 for 117 of 147 goals
# (most others the same window around a half second) and for 19 of 39 penalties, whose other 20 windows were each
# used once or twice (t-12 .. t+12 twice, on Y's Nov 9 game), mostly to show more of the walk to the box
CLIP_WINDOW = {"goal": (12, 10), "penalty": (12, 10), "moment": (12, 10)}


def clip_line(h, over):
    """One highlights.json entry's `clip` arguments as (name, {argument: value}), as the sessions wrote them in each
    game's clips.sh: CLIP_WINDOW around the poster at t (t-12 .. t+10 for every kind); a goal with --net and the goal check's shot and pass, ours
    framing the scorer and assists; a penalty following the player who took it; a moment on the main group. The clip
    starts at least 8 s before the pass (or the shot), as LADA Y's Nov 2 clips did for the build-up. `over` (the
    clip's entry in W/clip_args.json) replaces any of it: t0, t1, focus ("-" for none), shot, pass (null: leave it
    out), replay_from, tracks."""
    name = os.path.splitext(os.path.basename(h["clip"]))[0]
    o = {"shot": h.get("shot"), "pass": h.get("pass"), **over}
    t, kind = float(h["t"]), h.get("type")
    shot, pas = (o["shot"], o["pass"]) if kind == "goal" else (None, None)
    first = min([float(v[0]) for v in (shot, pas) if v] + [t])
    focus = o.get("focus")
    if focus is None and kind == "goal" and h.get("team", "for") == "for" and h.get("scorer") is not None:
        focus = ",".join(f"#{n}" for n in [h["scorer"]] + list(h.get("assists") or []))
    elif focus is None and kind == "penalty" and h.get("player") is not None:
        focus = f"#{h['player']}"
    g = lambda v: f"{float(v):.3f}".rstrip("0").rstrip(".")   # :g keeps 6 digits, and 2719.625 lost its last
    before, after = CLIP_WINDOW.get(kind, CLIP_WINDOW["goal"])
    args = dict(t0=g(o.get("t0", min(t - before, np.floor(first - 8)))), t1=g(o.get("t1", t + after)), poster=g(t),
                focus=None if focus in (None, "", "-") else str(focus), net=h.get("team", "for") if kind == "goal" else None,
                shot=",".join(g(v) for v in shot) if shot else None, pass_=",".join(g(v) for v in pas) if pas else None,
                replay_from=g(o["replay_from"]) if o.get("replay_from") is not None and kind == "goal" else None,
                tracks=str(o["tracks"]) if o.get("tracks") else None)
    return name, args


def _clip_cmd(name, c):
    """A clip's arguments as the `run_game.py clip` line a clips.sh held."""
    import shlex
    opts = [(f"--{k.rstrip('_').replace('_', '-')}", c[k]) for k in ("net", "shot", "pass_", "replay_from", "tracks")]
    return " ".join(["$PY pipeline/run_game.py clip $W $G", name, c["t0"], c["t1"], c["poster"]]
                    + ([shlex.quote(c["focus"])] if c["focus"] else []) + [f"{k} {shlex.quote(v)}" for k, v in opts if v])


def cmd_clips(a):
    """Cut every clip highlights.json lists (clip_line, with W/clip_args.json's hand-set arguments), each checked on
    its camera path first; tile each rendered clip into a contact sheet (W/scratch/clips/NAME.jpg) and write the brief
    for the one subagent that checks them all (clip_brief). --only re-cuts the named clips and leaves the rest;
    --dry-run computes and checks the paths and cuts nothing. A clip that fails doesn't stop the others, the brief
    covers those that were cut, and the exit status is 1 when any failed."""
    from roster import SITE_DIR
    from clip import contact_sheet, sheet_marks
    W = os.path.abspath(a.W).replace("\\", "/")
    if not os.path.exists(f"{W}/highlights.json"):
        sys.exit(f"no {W}/highlights.json: `run_game.py highlights {a.W} --write` builds it from the goal and penalty "
                 f"checkers' answers")
    if not a.dry_run and not os.path.exists(f"{W}/video.webm"):
        sys.exit(f"no {W}/video.webm: cutting needs the video (archived folders have none); --dry-run checks the paths")
    over = json.load(open(f"{W}/clip_args.json", encoding="utf-8")) if os.path.exists(f"{W}/clip_args.json") else {}
    hl = [h for h in json.load(open(f"{W}/highlights.json", encoding="utf-8")) if h.get("clip")]
    jobs = [clip_line(h, over.get(os.path.splitext(os.path.basename(h["clip"]))[0], {})) for h in hl]
    unknown = sorted(set(over) - {n for n, _ in jobs})
    if a.only:
        want = [n.strip() for n in a.only.split(",") if n.strip()]
        match = lambda n, w: n == w or n.startswith(w + "-")   # penalty-97: penalty-97-1676 and penalty-97-2820
        miss = [w for w in want if not any(match(n, w) for n, _ in jobs)]
        if miss:
            sys.exit(f"--only: no clip {', '.join(miss)} in highlights.json (it has {', '.join(n for n, _ in jobs)})")
        jobs = [(n, c) for n, c in jobs if any(match(n, w) for w in want)]
    if unknown:
        print(f"clip_args.json names clips highlights.json doesn't list: {', '.join(unknown)}")
    print(f"W={W}; G={a.game_id}", flush=True)
    done, failed = [], []
    for name, c in jobs:
        print(_clip_cmd(name, c) + (" --dry-run" if a.dry_run else ""), flush=True)
        try:
            cmd_clip(argparse.Namespace(W=W, game_id=a.game_id, name=name, dry_run=a.dry_run, **c))
        except subprocess.CalledProcessError as e:
            print(f"clips: {name} failed (exit {e.returncode}); going on with the rest", flush=True); failed.append(name)
            continue
        except (SystemExit, Exception) as e:   # a clip that can't be set up (no track, no period) is one failure
            print(f"clips: {name} failed ({type(e).__name__}: {e}); going on with the rest", flush=True); failed.append(name)
            continue
        done.append(name)
    checks = json.load(open(f"{W}/clips_check.json")) if os.path.exists(f"{W}/clips_check.json") else {}
    if not a.dry_run:
        for name in list(done):
            try:
                rec = checks[name]
                mk = "  ".join(f"{k.upper()} {'/'.join(f'{v:g}' for v in vs if v is not None)}" for k, vs in rec["marks"].items())
                title = (f"{name}: live 0-{rec['live_s']:g} s" + (f", replay {rec['live_s']:g}-{rec['length_s']:g} s at half "
                         "speed" if rec["replay"] else "") + f"  |  {mk}  (clip seconds)")
                contact_sheet(f"{SITE_DIR}/games/{a.game_id}/clips/{name}.mp4", f"{W}/scratch/clips/{name}.jpg",
                              sheet_marks(rec), title=title, live_s=rec["live_s"] if rec["replay"] else None)
            except (SystemExit, Exception) as e:
                print(f"clips: {name}'s contact sheet failed ({type(e).__name__}: {e})"); done.remove(name); failed.append(name)
    n = 0
    for name in done:
        for w in checks.get(name, {}).get("warnings", []):
            print(f"  {name} at clip {w['at']:g} s: {w['msg']}"); n += 1
    print(f"{len(done)} clip(s) {'checked' if a.dry_run else 'cut and checked'}, {n} warning(s)"
          + (f"; failed: {', '.join(failed)}" if failed else ""))
    if done and not a.dry_run:
        pf = clip_brief(W, a.game_id, done, checks)
        print(f"contact sheets in {W}/scratch/clips/. One general-purpose subagent whose whole prompt is\n"
              f"  'Read {pf} and do exactly what it says. Reply with one line per clip.'\n"
              f"  It writes {W}/scratch/clips/answers.json. Show the user nothing until it has answered.")
    if failed:
        sys.exit(f"clips: {len(failed)} of {len(jobs)} failed ({', '.join(failed)}); `run_game.py clips {a.W} "
                 f"{a.game_id} --only {','.join(failed)}` tries them again")


def cmd_clipsheet(a):
    """Tile any rendered clip into one image (clip.contact_sheet), marked from --W's clips_check.json entry for the
    clip of that name (written by every cut and dry run) and/or --mark LABEL=SEC."""
    from clip import contact_sheet, sheet_marks
    name = os.path.splitext(os.path.basename(a.mp4))[0]
    marks, title, live_s = [], name, None
    if a.W:
        p = f"{os.path.abspath(a.W)}/clips_check.json"
        rec = (json.load(open(p)) if os.path.exists(p) else {}).get(name)
        if rec is None:
            sys.exit(f"no {name} in {p}: run `clip ... --dry-run` or `clips --dry-run` first, or give --mark")
        marks = sheet_marks(rec)
        title = f"{name}: live 0-{rec['live_s']:g} s" + (f", replay {rec['live_s']:g}-{rec['length_s']:g} s" if rec["replay"] else "")
        live_s = rec["live_s"] if rec["replay"] else None
    for m in a.mark or []:
        label, _, s = m.rpartition("=")
        marks.append((label or "mark", float(s)))
    span = (a.from_ or 0.0, a.to if a.to is not None else 1e9) if a.from_ is not None or a.to is not None else None
    print(contact_sheet(a.mp4, a.out, marks, a.step, span, title=title, live_s=live_s))


def clip_brief(W, game_id, names, checks):
    """The brief for the one subagent that checks every clip's contact sheet (W/scratch/clips/prompt.md, from
    pipeline/clip_prompt.md): per clip who scores from where into which net, the pass, the infraction, the moments
    to look at in clip seconds and the path check's warnings, then the questions the user's complaints raised."""
    from roster import ALL_SKATERS, GOALIE_NAMES, SITE_DIR
    R = rink(f"{W}/full")
    Ps = periods(W)
    ctx = _brief_context(W)   # our look and the opponents' as the gap and goal briefs word them
    hl = {os.path.splitext(os.path.basename(h["clip"]))[0]: h
          for h in json.load(open(f"{W}/highlights.json", encoding="utf-8")) if h.get("clip")}
    scratch = f"{W}/scratch/clips"
    who = lambda n: f"#{n} {ALL_SKATERS.get(n, GOALIE_NAMES.get(n, '')).upper()}".strip()
    blocks = []
    for name in names:
        h, rec = hl[name], checks.get(name, {})
        P = next((P for P in Ps if P["start"] - 30 <= float(h["t"]) <= P["end"] + 30), None)
        when = f"{P['label'] if P else 'a break'}, {float(h['t']):g} s of video"
        mk = rec.get("marks", {})
        cs = lambda k: (f"clip {mk[k][0]:g} s" + (f", replay {mk[k][1]:g} s" if len(mk[k]) > 1 and mk[k][1] is not None
                                                     else ", not in the replay" if len(mk[k]) > 1 else ""))
        L = [f"### {name}\nSheet: {scratch}/{name}.jpg. Clip: {SITE_DIR.replace(chr(92), '/')}/games/{game_id}/clips/{name}.mp4."]
        note = (h.get("note") or "").strip()
        if h["type"] == "goal":
            ours = h.get("team", "for") == "for"
            nx = rec["net"][0] if rec.get("net") else None
            side = _net_side(R, nx) if nx is not None else "?"
            scorer = (who(h["scorer"]) + (" from " + ", ".join(who(n) for n in h.get("assists") or []) if h.get("assists") else ""))\
                if ours and h.get("scorer") is not None else "their scorer (see the note)"
            L.append(f"Goal {'for us' if ours else 'against us'}, {when}: {note}")
            L.append(f"Scored by {scorer} into {'their' if ours else 'our'} net, the {side} one.")
            must = []
            if rec.get("shot"):
                dx = abs(rec["shot"][1] - nx)
                far = ("at the crease" if dx < 250 else "from close in" if dx < 600 else "from the slot or the circles"
                       if dx < 1100 else "from the point or farther out")
                dy = rec["shot"][2] - rec["net"][1]
                across = " on the far side" if dy < -80 else " on the near side" if dy > 80 else ""
                must.append(f"the shooter as the puck leaves his stick, {far}{across} ({cs('shot')}, tiles SHOT)")
            else:
                must.append("the scorer as he scores (no shot time was given: the last touch before the goal)")
            must.append(f"the puck in {'their' if ours else 'our'} net or the goalie beaten ({cs('goal')}, tiles GOAL)")
            if rec.get("pas"):
                passer = who(h["assists"][0]) if ours and h.get("assists") else "the passer"
                must.append(f"{passer} as he passes ({cs('pass')}, tiles PASS)")
            elif ours and h.get("assists"):
                must.append(f"the assist{'s' if len(h['assists']) > 1 else ''} in the build-up (no pass time was given)")
            L.append("Must be visible: " + "; ".join(must) + ".")
            if rec.get("replay"):
                L.append(f"The replay is clip {rec['live_s']:g}-{rec['length_s']:g} s: play {rec['replay'][0]:g}-"
                         f"{rec['replay'][1]:g} s at half speed.")
        elif h["type"] == "penalty":
            L.append(f"Our {who(h['player'])}'s penalty, {when}: {note}")
            L.append(f"Must be visible: {who(h['player'])} and the infraction in the seconds before the call "
                     f"(clip {mk.get('poster', [0])[0]:g} s, tile POSTER), not the main group elsewhere. If the note says "
                     "the infraction isn't on camera, say whether the clip shows the player and the call.")
        else:
            L.append(f"{h.get('title', 'A moment')}, {when}: {note}")
            L.append(f"Must be visible: what the title says, around clip {mk.get('poster', [0])[0]:g} s (tile POSTER).")
        ws = rec.get("warnings", [])
        L.append("The camera-path check warned: " + "; ".join(f"{w['msg']} (clip {w['at']:g} s)" for w in ws)
                 + ". Confirm or refute each from the sheet." if ws else "The camera-path check found nothing; look anyway.")
        blocks.append("\n".join(L))
    tmpl = open(f"{HERE}/clip_prompt.md", encoding="utf-8").read()
    text = tmpl.format(**ctx, scratch=scratch, n=len(names), clips="\n\n".join(blocks),
                       out_file=f"{scratch}/answers.json", example=names[0])
    os.makedirs(scratch, exist_ok=True)
    pf = f"{scratch}/prompt.md"
    open(pf, "w", encoding="utf-8").write(text)
    return pf


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


def _name_ratio(txt, nm):
    """reads.name_to_num's score of an OCR'd text against one surname: the whole name, or for a read cut off at the
    jersey's edge its best same-length window."""
    import difflib
    from reads import _NORM
    txt, nm = txt.translate(_NORM), nm.translate(_NORM)
    r = difflib.SequenceMatcher(None, txt, nm).ratio()
    for k in range(0, max(1, len(nm) - len(txt) + 1)):
        r = max(r, difflib.SequenceMatcher(None, txt, nm[k:k + len(txt)]).ratio() * (0.85 if len(txt) < 6 else 1))
    return r


def _shared_names():
    """Surnames two of this game's skaters share (a father and son) -> their numbers. name_to_num leaves them out,
    so a piece of one lands on whoever is nearest: SLENOK and OLENOK, from TISLENOK #38 and #98, counted as 38 name
    reads for Belousenko #11 on the Doofers' Nov 15 game, who didn't play."""
    from roster import SKATERS
    by = {}
    for n, v in SKATERS.items():
        by.setdefault(v.upper(), []).append(n)
    return {k: sorted(v) for k, v in by.items() if len(v) > 1}


def _reads_label(txt, shared, cache):
    """A nameplate read as whose it is: 'BABKIN #26', 'TISLENOK #38/#98' (a surname two share), or the text as read
    when it is nobody's on the roster (an opponent's nameplate, or a misread)."""
    from reads import name_to_num
    from roster import SKATERS
    if txt not in cache:
        n = next((n for n, v in SKATERS.items() if v.upper() == txt and txt not in shared), None) or name_to_num(txt)
        best = max(shared, key=lambda s: _name_ratio(txt, s), default=None)
        r = _name_ratio(txt, best) if best else 0
        # a tie stays with the unique name (INSKIY is KOMASHINSKY's as much as POLYANSKIY's)
        if best and (txt == best or (r >= 0.65 and (n is None or r > _name_ratio(txt, SKATERS[n].upper())))):
            cache[txt] = f"{best} " + "/".join(f"#{k}" for k in shared[best])
        else:
            cache[txt] = f"{SKATERS[n].upper()} #{n}" if n is not None else txt
    return cache[txt]


def _read_with(W, numbers):
    """A function (files, n) -> lines: what else OCR read on one player's crops and on the tracks they belong to
    (after prepare; before it, on the crops of the same spot within half a second), the surnames by player and the
    numbers, most first, so another player's or an opponent's crops show. The sessions used to script this by hand
    from full/ocr_*.csv. numbers: number -> name to show."""
    o = pd.concat([pd.read_csv(f, header=None, names=["file", "text", "score"], dtype={"text": str})
                   for f in glob.glob(f"{W}/full/ocr_*.csv")]).dropna().drop_duplicates(["file", "text"])
    o["text"] = o.text.str.strip()
    dig = o[o.text.str.fullmatch(r"\d{1,2}") & (o.score >= 0.9)]   # load_reads' thresholds; 3 letters for BER
    dig = dig.assign(num=dig.text.astype(int))
    alpha = o[o.text.str.fullmatch(r"[A-Z]{3,}") & (o.score >= 0.7)]
    tr = [pd.read_csv(p, usecols=["frame", "i", "tid"]).assign(per=p) for p in sorted(glob.glob(f"{W}/p[0-9]*/tracks_v1.csv"))]
    dd = None
    if tr:
        tr = pd.concat(tr); tr["file"] = [f"f{int(f):06d}_{int(i):02d}.jpg" for f, i in zip(tr.frame, tr.i)]
    elif os.path.exists(f"{W}/full/dets.csv"):
        # before prepare, the same spot within half a second stands in for a track: on the Doofers' Nov 15 game it
        # gave 46, 26 and 97 for #6's crops and on Y's Nov 9 14 and 74 for #4's, what the sessions found by eye
        dd = pd.read_csv(f"{W}/full/dets.csv", header=None, usecols=[0, 2, 3, 4, 5], names=["frame", "x1", "y1", "x2", "y2"])
        dd["file"] = [f"f{f:06d}_{i:02d}.jpg" for f, i in zip(dd.frame, dd.groupby("frame").cumcount())]
        dd = dd[dd.file.isin(set(o.file))].assign(fx=(dd.x1 + dd.x2) / 2, fy=dd.y2, h=dd.y2 - dd.y1)
    shared, cache = _shared_names(), {}

    def fmt(fs, n):
        nm = alpha[alpha.file.isin(fs)].text.map(lambda t: _reads_label(t, shared, cache)).value_counts().head(4)
        dg = dig[dig.file.isin(fs) & (dig.num != n)].num.value_counts().head(4)
        return ("names " + (", ".join(f"{k} x{v}" for k, v in nm.items()) or "-") + "; numbers " +
                (", ".join(f"#{k}{' ' + numbers[k] if k in numbers else ''} x{v}" for k, v in dg.items()) or "-"))

    def around(files, n):
        out = [f"same crops ({len(files)}): {fmt(files, n)}"]
        if len(tr):
            k = tr[tr.file.isin(files)][["per", "tid"]].drop_duplicates()
            out.append(f"same tracks ({len(k)}): {fmt(set(tr.merge(k).file), n)}")
        elif dd is not None:
            w = FPS // 2
            E = dd[dd.file.isin(files)]
            by = dict(tuple(dd[dd.frame.isin({f + k for f in E.frame for k in range(-w, w + 1)})].groupby("frame")))
            near = set()
            for e in E.itertuples():
                for g in (by[f] for f in range(e.frame - w, e.frame + w + 1) if f in by):
                    near |= set(g.file[((g.fx - e.fx).abs() < 0.5 * e.h) & ((g.fy - e.fy).abs() < 0.25 * e.h)])
            out.append(f"same spot within 0.5 s ({len(near)} crops; tracks come with prepare): {fmt(near, n)}")
        return out
    return around


def suggest_absent(W):
    """Who probably didn't play, from the game sheet, LADA's lines, the OCR reads and the roster cards (after
    prepare). A table to decide from, not a verdict: the sheet is the scorekeeper's, the lines are a plan, and a
    covered number reads like absence. Where the reads and the sheet (or the cards) disagree, it lists what else was
    read on the same crops and tracks: on four of the last 14 games "reads say he played" meant opponents wearing
    the number, partial reads of teammates' numbers, or pieces of a surname two players share."""
    from roster import ALL_SKATERS, GOALIE_NAMES, SUBS
    from reads import load_reads
    sheet_ = json.load(open(f"{W}/sheet.json", encoding="utf-8")) if os.path.exists(f"{W}/sheet.json") else None
    played = set(sheet_["played"]) if sheet_ else None
    lines = _lines_numbers(W)
    reads, names = load_reads(f"{W}/full")
    # a name read that is a piece of a surname two players share counts for nobody (references/lada.md, "shared")
    shared, cache = _shared_names(), {}
    lab = names.text.map(lambda t: _reads_label(t, shared, cache))
    is_frag = lab.str.contains("/").values   # labeled with a shared surname, e.g. "TISLENOK #38/#98"
    frag = names[is_frag].assign(shared=lab.values[is_frag])
    names = names[~is_frag]
    reads = pd.concat([reads[reads.src == "digit"], names[reads.columns]])
    dig = reads[reads.src == "digit"].num.value_counts(); nm = names.num.value_counts()
    cards = {}
    for P in (periods(W) if os.path.exists(f"{W}/periods.json") else []):
        p = f"{W}/rev_{P['label'].lower()}/card_empty.json"
        if os.path.exists(p):
            cards[P["label"]] = set(json.load(open(p)))
    print(f"{'num':>4} {'name':<14} {'sheet':<8} {'lines':<6} {'digits':>6} {'names':>5} {'card rows':<12} suggestion")
    out, conflicts = [], []
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
        # the reads against the sheet: strong reads where the sheet (or the table) says no, or the sheet's yes with
        # next to nothing read
        if n not in GOALIE_NAMES and (why.startswith("check") or (on_sheet and evidence < 30)):
            conflicts.append((n, name, on_sheet, d, m_))
        fmt = lambda v: "-" if v is None else ("yes" if v else "NO")
        print(f"{n:>4} {name:<14} {fmt(on_sheet):<8} {fmt(in_lines):<6} {d:>6} {m_:>5} {card:<12} {why}")
    sug = [n for n, w in out if w.startswith("absent") or w.startswith("sub") or w.startswith("goalie: absent")]
    print("card rows: o = has a row on that period's roster card, x = empty (after prepare); digits = confident reads "
          "of the full number, names = nameplate reads")
    for n, g in frag[frag.num.isin([n for n, w in out if w != "played"])].groupby("num"):
        print(f"#{n} {ALL_SKATERS.get(n, '?')}: {len(g)} name read(s) not counted, pieces of a surname two roster "
              f"numbers share: {', '.join(f'{k} ({v})' for k, v in g.shared.value_counts().items())}, e.g. "
              f"{', '.join(g.text.value_counts().index[:4])}")
    if conflicts:
        around = _read_with(W, {**ALL_SKATERS, **GOALIE_NAMES})
        print("Where the reads and the sheet disagree, what else was read with that number (a name without a number "
              "is nobody on our roster: an opponent's nameplate, or a misread):")
        for n, name, on_sheet, d, m_ in conflicts:
            sheet_says = "marked playing" if on_sheet else "not marked playing" if on_sheet is False else "no sheet"
            print(f"  #{n} {name} ({sheet_says}; {d} digit and {m_} name reads)")
            files = set(reads[reads.num == n].file)
            for line in (around(files, n) if files else ["nothing read at all"]):
                print(f"      {line}")
    if sug:
        print(f"suggested: run_game.py absent {W} " + " ".join(str(n) for n in sug))
    print("Keep anyone LADA's lines list unless every card row and the reads are empty (a late arrival looks absent); "
          "an absent goalie makes the next one the goalie of the game.")


def cmd_absent(a):
    """Record roster numbers that didn't play (W/full/rink.json "absent"); with no numbers, show the roster as the
    pipeline sees it. `--suggest` tables the evidence per player. `--clear` forgets the list. Prepare takes the list
    as it is then: its OCR labels (shifts.segment_track counts only roster numbers' reads, so an absent "3" can't
    take 43's pieces) and the roster cards' rows; `review` takes it when it writes the prompts' roster. Solve takes it
    as it is at the solve (run2.py: an absent player gets no shifts and reviewers' rows naming him are ignored), but
    can't relabel the pieces prepare gave his number: those count for nobody. So a change before the review starts means
    moving W/p* and W/rev_p* aside and preparing again; once the review has started (its rows point at prepare's
    pieces), solve alone picks it up."""
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
        print("  prepare has run already: its OCR labels and roster cards used the old list. Before the review starts, "
              "move W/p* and W/rev_p* aside and prepare again; once it has started, solve alone picks "
              "the change up (an absent player gets no shifts, and the pieces prepare labeled with his number count "
              "for nobody).")


def cmd_span(a):
    """One hand-made span into its period in periods.json, in the shape the checkers' spans have (`gaps --apply`):
    on/off {start, end, player} (a player seen on the ice whose track was lost / kept on after he left), extra
    {start, end} (our goalie pulled), ps {start, end} (a penalty shot against us), appended as a hand edit would
    append it; and a line in W/hand_spans.txt (when, what, why), which archive keeps. Sessions used to write these
    with inline Python or sed and no record of why (Y's Nov 9 game was solved three more times from such spans).
    Penalty kills have their own command. --list prints the log."""
    W = os.path.abspath(a.W); logf = f"{W}/hand_spans.txt"
    if a.list:
        print(open(logf, encoding="utf-8").read().rstrip() if os.path.exists(logf) else f"no hand-made spans in {logf}")
        return
    want = 3 if a.kind in ("on", "off") else 2
    if not a.kind or len(a.vals) != want:
        sys.exit("span: give on|off PLAYER T0 T1, or extra|ps T0 T1 (seconds of video), with --note \"why\"")
    if not a.note:
        sys.exit("span: --note \"why\" is needed: W/hand_spans.txt is the only record of why the span is there")
    try:
        vals = [float(v) for v in a.vals]
    except ValueError:
        sys.exit(f"span: not numbers: {' '.join(a.vals)}")
    vals = [int(v) if v.is_integer() else v for v in vals]
    player, (t0, t1) = (int(vals[0]) if want == 3 else None), vals[-2:]
    if t1 <= t0:
        sys.exit(f"span: it ends ({t1}) before it starts ({t0})")
    if player is not None:
        from roster import SKATERS, ABSENT
        solved = set(pd.read_csv(f"{W}/shifts_all.csv").player) if os.path.exists(f"{W}/shifts_all.csv") else set()
        if player not in SKATERS and player not in solved:
            sys.exit(f"span: #{player} is {'marked absent' if player in ABSENT else 'not on the roster'} this game")
    p = f"{W}/periods.json"
    Ps = periods(W)
    P = next((P for P in Ps if P["start"] <= t0 < P["end"]), None)
    if P is None:
        sys.exit(f"span: {t0} is in no period (" + ", ".join(f"{Q['label']} {Q['start']}-{Q['end']}" for Q in Ps) + ")")
    if t1 > P["end"]:
        sys.exit(f"span: {t0}-{t1} crosses the end of {P['label']} at {P['end']}: one span per period")
    if any(same_span(e, t0, t1, player) for e in P.get(a.kind, [])):
        sys.exit(f"span: {P['label']} already has {a.kind} {f'#{player} ' if player is not None else ''}{t0}-{t1}")
    for k in ("on", "off") if player is not None else ():
        for e in P.get(k, []):
            if e.get("player") == player and e["start"] < t1 and t0 < e["end"]:
                print(f"  note: it overlaps #{player}'s {k} span {e['start']}-{e['end']} in {P['label']}")
    add_span(P, a.kind, t0, t1, player)
    save_periods(W, Ps)
    line = log_span(W, P, a.kind, t0, t1, player, a.note)
    print(f"+ {line}\n  added to {p} (logged in {logf}); solve again")


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
        if a.batch:
            opt["batch"] = a.batch
        json.dump(opt, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    return opt


def _chunk_ids(sheets, chunk):
    """A period's sheets in chunks of `chunk`: [(cid, sheets)], the one layout for prompts and check --wait."""
    sheets = sorted(sheets)
    return [(f"c{k // chunk:02d}", sheets[k:k + chunk]) for k in range(0, len(sheets), chunk)]


def _review_coverage(W, P):
    """Per sheet of a period: rows in the manifest, rows missing an answer, whether the reviewer's file mentions a
    failed read, and when it was last written. Returns (manifest, dict sheet -> info, dict row_id -> (player,
    player2)), each row's answer as solve applies it: the last file's (review_zfix.txt sorts last)."""
    from apply_review import parse_review
    rv = f"{W}/rev_{P['label'].lower()}"
    man = pd.read_csv(f"{rv}/manifest.csv")
    ans, trouble = {}, {}
    for f in sorted(glob.glob(f"{rv}/review_*.txt")):
        try:
            txt = open(f, encoding="utf-8", errors="replace").read()
        except OSError:   # being written or moved right now (check --wait polls while reviewers write)
            continue
        for _, r in parse_review(txt).iterrows():
            ans[r.row_id] = (r.player, r.player2)
        if re.search(r"(fail|could not|couldn't|unable|error|not load|timed out)", txt, re.I):
            trouble[os.path.basename(f)] = True
    info = {}
    for sheet, g in man.groupby("sheet", sort=True):
        rows = list(g.row_id)
        fn = f"review_s{sheet[6:9]}.txt"
        try:
            mtime = os.path.getmtime(f"{rv}/{fn}")
        except OSError:
            mtime = None
        info[sheet] = dict(rows=len(rows), missing=[r for r in rows if r not in ans], file=fn, trouble=trouble.get(fn, False),
                           mtime=mtime)
    ids = set(man.row_id)
    return man, info, {r: v for r, v in ans.items() if r in ids}


def _review_numbers(cov):
    """Numbers the reviewers gave that aren't on this game's roster or are marked absent, with the rows. run2.py
    takes a reviewer's number as a player of ours, so one off the roster (a misread, or a sub not in roster.json)
    would get shifts unseen; an absent player's number is dropped there."""
    from roster import ALL_SKATERS, GOALIE_NAMES, ABSENT
    off, absent = {}, {}
    for P, man, info, ans in cov:
        for rid, ps in ans.items():
            for p in {x for x in ps if x.isdigit()}:
                n = int(p)
                if n in ABSENT:
                    absent.setdefault(n, []).append((P["label"], rid))
                elif n not in ALL_SKATERS and n not in GOALIE_NAMES:
                    off.setdefault(n, []).append((P["label"], rid))
    lines = []
    for what, d in (("not on the roster (solve takes each as a new player of ours: a misread, or a sub to add to "
                     "roster.json? a review_zfix.txt line with \"?\" keeps a misread out)", off),
                    ("of players marked absent (solve ignores them: did he play after all?)", absent)):
        if d:
            lines.append(f"numbers reviewers gave {what}:")
            for n, rows in sorted(d.items(), key=lambda x: (-len(x[1]), x[0])):
                shown = {}
                for lab, rid in rows[:12]:
                    shown.setdefault(lab, []).append(rid)
                lines.append(f"  #{n} x{len(rows)}: " + "; ".join(f"{lab} {' '.join(r)}" for lab, r in shown.items())
                             + (" ..." if len(rows) > 12 else ""))
    return lines


def _review_prompts(W, opt):
    """Fill pipeline/review_prompt.md once per chunk of sheets and write it to W/rev_pN/prompt_cNN.md, with the
    roster (minus absent players), our jersey, the goalie, empty roster-card rows (point at another period's card,
    or say the player probably didn't play), the opponents' look, any notes and the zoom command. A chunk with
    sheets still to answer lists only those. Returns the chunks (period, id, sheets, sheets left, rows left, prompt,
    whether its sheet images exist) and what the prompts say beyond the template (the goalie line, card notes)."""
    from roster import SKATERS, GOALIES, GOALIE_NAMES
    from reads import load_reads
    chunk = int(opt.get("chunk", 3))
    cfg = json.load(open(f"{W}/full/rink.json")) if os.path.exists(f"{W}/full/rink.json") else {}
    jersey = cfg.get("jersey", "light blue")
    jersey_desc = "white jerseys with blue numbers and blue trim" if jersey.startswith("white") else "light-blue jerseys"
    opp_desc = _opp_look(jersey, opt)
    tmpl = open(f"{HERE}/review_prompt.md", encoding="utf-8").read()
    roster = ", ".join(f"#{n} {v.upper()}" for n, v in sorted(SKATERS.items()))
    # "G" for either goalie: apply_review drops a "G" row, which is right for theirs too (reviewers marked the other
    # goalie "G" in ~50 rows of BT's Oct 25 game; "N" would keep his track as an unlabeled segment)
    ours = (f"Ours is #{GOALIES[0]} {GOALIE_NAMES.get(GOALIES[0], '').upper()}, in a {jersey.split(' vs ')[0]} "
            f"jersey like our skaters unless a note says otherwise." if GOALIES else
            "Ours is not on the card; a note may say what he wears.")
    goalie_line = f'A goalie (big leg pads, at a net) is "G", ours or the opponents\', never a number. {ours}'
    Ps = periods(W)
    empty = {}
    for P in Ps:
        p = f"{W}/rev_{P['label'].lower()}/card_empty.json"
        empty[P["label"]] = set(json.load(open(p))) if os.path.exists(p) else set()
    reads, _ = load_reads(f"{W}/full")
    nreads = reads.num.value_counts()
    notes = "".join(f" {n.rstrip('.')}." for n in opt.get("notes", []))
    chunks, cards = [], {}
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
        cards[lab] = card_notes.strip()
        man, info, _ = _review_coverage(W, P)
        for cid, cs in _chunk_ids(info, chunk):
            left = [x for x in cs if info[x]["missing"]]
            scratch = f"{W}/scratch/{lab.lower()}_{cid}"
            text = tmpl.format(rev=rv, scratch=scratch, jersey_desc=jersey_desc,
                               roster=roster, card_notes=card_notes, notes=notes, goalie_line=goalie_line,
                               sheets=", ".join(left or cs), opp_desc=opp_desc,
                               PY=PY.replace("\\", "/"), zoom=f"{HERE}/zoom.py".replace("\\", "/"))
            pf = f"{rv}/prompt_{cid}.md"
            open(pf, "w", encoding="utf-8").write(text)
            chunks.append(dict(lab=lab, cid=cid, sheets=cs, left=left, prompt=pf,
                               rows=sum(len(info[x]["missing"]) for x in left),
                               ready=all(os.path.exists(f"{rv}/{x}") for x in left + ["roster_card.jpg"])))
    return chunks, dict(goalie_line=goalie_line, cards=cards)


def cmd_review(a):
    """Write the reviewer prompts (_review_prompts) and print the next launch: the prompts of the first --batch
    chunks (20) with rows still to answer, one per line (also in W/review_todo.txt, which `check --wait` waits on;
    W/review_plan.txt has every chunk), then what the prompts say beyond the template, for a look before launching:
    the goalie line, empty card rows, --opp and --note. A batch bounds how many reviewers run at once (17 is the most
    seen to work); a chunk launched before and still open comes first in the next batch, marked."""
    from roster import ABSENT, ALL_SKATERS
    W = os.path.abspath(a.W).replace("\\", "/")
    opt = _review_options(W, a)
    chunks, said = _review_prompts(W, opt)
    plan = [f"{c['lab']} {c['cid']} {' '.join(x[:-4] for x in c['sheets'])} -> {c['prompt']}  "
            f"[{'todo (%d rows)' % c['rows'] if c['left'] else 'done'}]" for c in chunks]
    open(f"{W}/review_plan.txt", "w", encoding="utf-8").write("\n".join(plan) + "\n")
    ready = [c for c in chunks if c["left"] and c["ready"]]
    gone = [c for c in chunks if c["left"] and not c["ready"]]
    done = sum(not c["left"] for c in chunks)
    todo = ready[:int(opt.get("batch", 20))]; more = len(ready) - len(todo)
    tf = f"{W}/review_todo.txt"
    before = set(open(tf, encoding="utf-8").read().split()) if os.path.exists(tf) else set()
    open(tf, "w", encoding="utf-8").write("".join(c["prompt"] + "\n" for c in todo))
    print((f"{len(todo)} of {len(ready)} chunks to launch now; {more} more after these: run `review` again when "
           f"`check --wait` returns" if more else f"{len(todo)} chunk(s) to launch") +
          (f" ({done} of {len(chunks)} done already)" if done else "") +
          (f". The prompts, also in {W}/review_todo.txt:" if todo else ""))
    for c in todo:
        print(c["prompt"] + ("   (listed before: if its reviewer hasn't reported back, leave it out)"
                             if c["prompt"] in before else ""))
    if gone:   # an archived folder keeps manifests and reviews but not the images
        print(f"{len(gone)} chunk(s) with rows to answer have no sheet images or roster card (archived? prepare makes "
              f"them), not listed: " + ", ".join(f"{c['lab']} {c['cid']}" for c in gone))
    print("Goalie line in every prompt:", said["goalie_line"])
    for lab, t in said["cards"].items():
        if t:
            print(f"{lab} card rows:", t.replace(W + "/", "W/"))
    if opt.get("opp"):
        print("Opponents (--opp):", opt["opp"])
    for n in opt.get("notes", []):
        print("Note (--note):", n)
    if ABSENT:
        print("Absent (left out of the prompts' roster):", ", ".join(f"#{n} {ALL_SKATERS.get(n, '?')}" for n in sorted(ABSENT)))
    if todo:
        print(f"Launch all {len(todo)} in one message (but none whose earlier reviewer is still working), one "
              f"general-purpose subagent each, whose whole prompt is \"Read <prompt file> and do exactly what it says. "
              f"Reply with one line: how many rows you wrote.\"; then run `run_game.py check {a.W} --wait` once, in the "
              f"foreground with the Bash tool's timeout set to 600000 ms (it waits up to 540 s).")
    else:
        print("Nothing to launch." + ("" if gone else f" `run_game.py check {a.W}` confirms every row is answered."))


def cmd_check(a):
    """Review coverage: every manifest row needs an answer in some review_*.txt (apply_review.parse_review, as solve
    reads them). Lists missing rows per sheet, files whose notes mention failed image reads, and the numbers reviewers
    gave that aren't on this game's roster or are marked absent.
    --wait [SECONDS] first blocks until the chunks of the last launch (W/review_todo.txt, from `review`) are answered
    or the time is up (540 s fits one 10-minute foreground command), so that reviewers launched together hand back
    together instead of each waking the session; then it prints the rows answered per period, that launch's chunks
    still open, the sheets to redo, the numbers, and whether `review` has a next batch. Exit status 0 when every row
    of the game is answered, 1 otherwise."""
    W = os.path.abspath(a.W).replace("\\", "/")
    wait, t0 = a.wait, time.time()
    if wait is not None and not glob.glob(f"{W}/rev_p*/prompt_c*.md"):
        print(f"no reviewer prompts yet: `run_game.py review {a.W}` writes them"); sys.exit(1)
    chunk = int(_review_options(W).get("chunk", 3))
    tf = f"{W}/review_todo.txt"   # the last launch; without the file, the whole game
    launch = ({tuple(m.groups()) for m in (re.search(r"/rev_([^/]+)/prompt_(c\d+)\.md$", l) for l in
               open(tf, encoding="utf-8").read().split()) if m} if os.path.exists(tf) else None)
    while True:
        cov = [(P, *_review_coverage(W, P)) for P in periods(W)
               if os.path.exists(f"{W}/rev_{P['label'].lower()}/manifest.csv")]
        sheets = [i for _, _, info, _ in cov for i in info.values()]
        missing_total = sum(len(i["missing"]) for i in sheets)
        # every chunk with rows to answer: whether the last launch had it, its sheets
        open_ = [(P["label"], cid, {s: info[s] for s in cs}, launch is None or (P["label"].lower(), cid) in launch)
                 for P, _, info, _ in cov for cid, cs in _chunk_ids(info, chunk) if any(info[s]["missing"] for s in cs)]
        waited = [i for P, _, info, _ in cov for cid, cs in _chunk_ids(info, chunk)
                  if launch is None or (P["label"].lower(), cid) in launch for i in (info[s] for s in cs)]
        if wait is None or time.time() - t0 >= wait:
            break
        if not any(c[3] for c in open_) and time.time() - max((i["mtime"] or 0 for i in waited), default=0) > 3:
            break   # the launch is answered, and no file written in the last seconds (one may still be growing)
        time.sleep(5)
    mmss = _mm
    if wait is not None:
        print(f"waited {mmss(time.time() - t0)}")
    for P, man, info, ans in cov:
        lab = P["label"]
        miss = {s: i["missing"] for s, i in info.items() if i["missing"]}
        n_miss = sum(len(m) for m in miss.values())
        if wait is not None:
            print(f"{lab}: {len(man) - n_miss} of {len(man)} rows answered")
        else:
            print(f"{lab}: {len(man)} rows in {len(info)} sheets, {len(man) - n_miss} answered" +
                  (f", {n_miss} missing" if n_miss else ""))
            for s, m in miss.items():
                print(f"  {s}: missing {', '.join(m)}" + ("  (whole sheet)" if len(m) == info[s]["rows"] else ""))
        for s, i in info.items():
            if i["trouble"]:
                print(f"  rev_{lab.lower()}/{i['file']} mentions a failed read: look, and redo the sheet with a fresh "
                      f"reviewer if so (move the old file to old_{i['file']}, then `review` lists its chunk)")
    for line in _review_numbers(cov):
        print(line)
    if missing_total and wait is not None:
        late = [c for c in open_ if c[3]]; rest = len(open_) - len(late)
        rows = lambda m, n: f"all {n} rows" if len(m) == n else " ".join(m[:4]) + (" ..." if len(m) > 4 else "")
        if late:
            print(f"time is up with {len(late)} chunk(s) of the last launch still open:")
        for lab, cid, info, _ in late:
            last = max((i["mtime"] or 0 for i in info.values()), default=0)
            print(f"  {lab} {cid}: " + ", ".join(f"{s[:-4]} ({rows(i['missing'], i['rows'])})" for s, i in info.items()
                                                 if i["missing"]) +
                  (f"; last answer {mmss(time.time() - last)} ago" if last else "; no answer yet"))
        print(("The last launch is answered" if not late else "Next") +
              (f"; {rest} chunk(s) not launched yet" if rest else "") +
              f": `run_game.py review {a.W}` lists " + ("the next batch" if not late else
              "these again first (with only their missing sheets)" + (", then the next" if rest else "") +
              "; relaunch one only if its reviewer has reported back (a recent answer means it is still writing: "
              "leave it out, `check --wait` waits for it)") + ". Run each `check --wait` with the Bash tool's timeout "
              "set to 600000 ms.")
        sys.exit(1)
    if missing_total:
        print(f"{missing_total} rows still missing: `run_game.py review {a.W}` lists the chunks to launch")
        sys.exit(1)
    print("every review row is answered")


def cmd_prepare(a):
    W = os.path.abspath(a.W)
    setup_check.bench_check(W)
    # stop on nets that go against both the bench rule and the opening faceoff while a period is still to prepare
    todo = [P for P in periods(W) if not os.path.exists(f"{W}/rev_{P['label'].lower()}/manifest.csv")]
    setup_check.check_nets(W, stop=bool(todo) and not a.force)
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
    setup_check.bench_check(W)
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
    lineup_check(W)   # with the ice time collapses, which no window shows: the solver keeps five on with the others
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


LONG_SHIFT = 300   # s: a shift this long gets a look (one in 190 shifts; a seated stretch has hidden in one)


def _undone_spans(W, Ps, A, T):
    """Hand-made on/off spans that the solver followed (pN/shifts_final.csv) but the published sheet (shifts_all.csv,
    the one publish copies) undoes: final_stats.py drops shifts under MIN_SHIFT s and joins a player's shifts across
    rests under MERGE_GAP s. On BT's Nov 7 game a 17 s "on" span for #24 left a 4-on window listed through publish,
    and every later checker could only confirm it. Returns (fix, undone): fix[t] = skaters the sheet lost (+) or
    kept (-) against the spans at second t; undone = [(t0, t1, text)]."""
    from final_stats import MIN_SHIFT, MERGE_GAP
    fix, undone = np.zeros(T), []
    for P in Ps:
        fp = f"{W}/{P['label'].lower()}/shifts_final.csv"
        if not os.path.exists(fp) or not (P.get("on") or P.get("off")):
            continue
        F = pd.read_csv(fp)
        def cover(S, pl, a, b):   # per second of [a, b): is the player on in these shifts?
            c = np.zeros(b - a, bool)
            for r in S[S.player == pl].itertuples():
                c[max(int(np.ceil(r.t0)), a) - a:max(min(int(np.ceil(r.t1)), b) - a, 0)] = True
            return c
        mine = A[A.period == P["label"]]
        for kind, sign in (("on", 1), ("off", -1)):
            for e in P.get(kind, []):
                pl, a, b = int(e["player"]), int(np.ceil(e["start"])), min(int(np.ceil(e["end"])), T)
                if b <= a:
                    continue
                solver, sheet = cover(F, pl, a, b), cover(mine, pl, a, b)
                lost = (solver & ~sheet) if kind == "on" else (~solver & sheet)
                if lost.sum() < 0.5 * (b - a):
                    continue
                fix[a:b] += sign * lost
                undone.append((a, b, f"#{pl}'s \"{kind}\" span {a}-{b} is in the solve, but the sheet "
                               + (f"drops shifts under {MIN_SHIFT} s" if kind == "on" else f"joins rests under {MERGE_GAP} s")))
    return fix, undone


COLLAPSE_SHARE, COLLAPSE_GAP = 0.5, 480   # see _collapses


def _collapses(W, Ps, A):
    """Players whose ice time collapses in one period: under COLLAPSE_SHARE of their mean share of the other periods,
    with COLLAPSE_GAP+ s of it without a shift. The lineup check's windows can't show one (the solver keeps five on
    with the others), so seven sessions from Nov 1 to 15 briefed such a stretch by hand: three found missing shifts
    (BW Nov 7 #36 in P2, BT Nov 7 #24 in P3, DF Nov 8 #38 in P3), four found the player really sat or came late. On
    those 14 games solved without hand-made spans (Nov 18) this flags 10 stretches: the three, two of the four (the
    other two show no collapse there) and five more. Gates on his number's reads in the stretch, his linemates
    playing on, or unlabeled pieces of ours kept the three and dropped the rest only by a hair (one read; 0.97
    against 0.92 of the game's rate; 0.50 against 0.49), so every collapse gets a window. Returns
    [{period, t0, t1, player, toi, others, line}]."""
    L = {P["label"]: P["end"] - P["start"] for P in Ps}
    m = _mm
    out = []
    for pl, g in A.groupby("player"):
        toi = {k: g[g.period == k].dur.sum() for k in L}
        for P in Ps:
            k = P["label"]
            oth = [toi[o] / L[o] for o in L if o != k]
            if not oth or toi[k] / L[k] >= COLLAPSE_SHARE * np.mean(oth):
                continue
            t, gaps_ = P["start"], []   # the longest stretch of the period without a shift of his
            for r in g[g.period == k].sort_values("t0").itertuples():
                gaps_.append((t, r.t0)); t = max(t, r.t1)
            a, b = max(gaps_ + [(t, P["end"])], key=lambda x: x[1] - x[0])
            if b - a >= COLLAPSE_GAP:
                out.append(dict(period=k, t0=int(a), t1=int(b), player=int(pl), toi=toi[k],
                                others={o: toi[o] for o in L if o != k},
                                line=f"#{pl} has {m(toi[k])} in {k} against " + " and ".join(f"{m(toi[o])} in {o}" for o in L if o != k)
                                     + f", and no shift for {int(b - a) // 60} minutes"))
    return out


def lineup_windows(W, min_len=15):
    """Stretches of min_len+ seconds where the published shifts (shifts_all.csv) don't put the expected number of us
    on the ice, and goals in highlights.json with the wrong count, a credited player off the ice, or one the goal
    checker saw on the ice off it (on_ice). Returns
    (windows, goal_notes, extra): each window a dict with period, t0, t1, n_on, expected, mid, on_mid (who the shifts
    have on at the midpoint) and live (seconds of the window outside the estimated stoppages, None without
    stoppages.json), and `settled` where hand-made spans the sheet's cleaning undid explain it (_undone_spans: no
    checker can fix it, so it is reported, not briefed); goal_notes are strings; extra are windows for the gap
    briefs only, with a `why`: the 20 s
    around each flagged goal, and every shift of LONG_SHIFT+ s (with `player`), which the briefs used to leave out
    (on Y's Oct 19 game both goal lines were added to a brief by hand; at Kirkland a second pass over the long
    shifts found a player sitting through a timeout)."""
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
    fix, undone = _undone_spans(W, Ps, A, T)
    windows = []
    for P in Ps:
        run = None
        for t in range(P["start"], P["end"] + 1):
            d = (cnt[t] - tgt[t]) if t < P["end"] else None
            if run and d != run[1]:
                if t - run[0] >= min_len:
                    mid = (run[0] + t) // 2
                    w = dict(period=P["label"], t0=run[0], t1=t, n_on=int(tgt[run[0]] + run[1]),
                             expected=int(tgt[run[0]]), mid=mid, on_mid=on(mid),
                             live=int(live[run[0]:t].sum()) if live is not None else None)
                    # settled by hand if the spans the sheet undid account for all but a few of its seconds
                    off_by = (cnt + fix - tgt)[run[0]:t] != 0
                    why = [u for a, b, u in undone if a < t and b > run[0]]
                    if why and off_by.sum() < min_len:
                        w["settled"] = "; ".join(why)
                    windows.append(w)
                run = None
            if d and not run:
                run = (t, d)
    notes, extra = [], []
    hp = f"{W}/highlights.json"
    for h in (json.load(open(hp)) if os.path.exists(hp) else []):
        if h["type"] != "goal":
            continue
        t = int(h["t"])
        why = []
        if len(on(t)) != tgt[t]:
            notes.append(f"  goal at {t}: on the ice {on(t)}, expected {int(tgt[t])} skaters")
            why.append(f"the solver has {len(on(t))} on, expected {int(tgt[t])}")
        # the game sheet's scorer and assists (optional "scorer": 54, "assists": [36]) must be on the ice
        credited = [int(h["scorer"])] if h.get("scorer") else []
        credited += [int(x) for x in h.get("assists", [])]
        for p in credited:
            if h.get("team", "for") == "for" and p not in on(t):
                notes.append(f"  goal at {t}: #{p} is credited on the game sheet but not on the ice ({on(t)})")
                why.append(f"#{p} is credited on the game sheet but not on the ice")
        for p in seen_off(h, on(t)):   # the goal checker's on_ice (highlights --write)
            notes.append(f"  goal at {h['t']}: the goal check saw #{p} on the ice, the solver has him off ({on(t)})")
            why.append(f"the goal check saw #{p} on the ice, the solver has him off")
        P = next((P for P in Ps if P["start"] <= t <= P["end"]), None)
        if why and P:
            extra.append(dict(period=P["label"], t0=t - 10, t1=t + 10, n_on=len(on(t)), expected=int(tgt[t]), mid=t,
                              on_mid=on(t), live=None,
                              why=f"{'our' if h.get('team', 'for') == 'for' else 'their'} goal at {t}: " + "; ".join(why)
                                  + ". Who of ours was on the ice at the goal (the stepping-on and off around it to the second)?"))
    for r in A.itertuples():
        if r.dur >= LONG_SHIFT:
            mid = int((r.t0 + r.t1) // 2)
            extra.append(dict(period=r.period, t0=int(r.t0), t1=int(r.t1), n_on=None, expected=None, mid=mid,
                              on_mid=on(mid), live=None, player=int(r.player),
                              why=f"#{int(r.player)}'s shift runs {int(r.dur)} s, far longer than a rec-hockey shift. "
                                  f"Frames 30 s apart suffice: was he on the ice all through it, or seated at the bench "
                                  f"for part of it (then an off span over the seated stretch)?"))
    return windows, notes, extra


def _window_line(w):
    s = (f"  {w['period']} {w['t0']}-{w['t1']} ({w['t1'] - w['t0']} s): {w['n_on']} on the ice, expected "
         f"{w['expected']}; on at {w['mid']}: {w['on_mid']}")
    if w["live"] is not None:
        s += "; all of it in a stoppage" if w["live"] == 0 else f"; {w['live']} s of it live"
    if w.get("settled"):
        s += f"; settled by hand: {w['settled']}"
    return s


def lineup_check(W, min_len=15):
    """Print the lineup check (see lineup_windows), with the players whose ice time collapses in a period
    (_collapses), which no window can show, and last the windows settled by hand. Each window is a missed player, an
    unlisted penalty, a bad label or a slow line change during a stoppage; `run_game.py gaps` writes the briefs for
    checking them by eye (solve and publish print this)."""
    windows, notes, extra = lineup_windows(W, min_len)
    settled = [_window_line(w) for w in windows if w.get("settled")]
    windows = [w for w in windows if not w.get("settled")]
    collapses = _collapses(W, periods(W), pd.read_csv(f"{W}/shifts_all.csv"))
    bad = [_window_line(w) for w in windows] + notes   # goals: count, credited, seen on the ice
    bad += [f"  {w['period']} {w['t0']}-{w['t1']}: #{w['player']} on for {w['t1'] - w['t0']} s in one shift" for w in extra if "player" in w]
    bad += [f"  ice time collapse, {c['period']} {c['t0']}-{c['t1']}: {c['line']}" for c in collapses]
    log("lineup check: " + ("OK" if not bad else f"{len(bad)} to look at")
        + (f" ({len(settled)} window(s) settled by hand, which the sheet can't show)" if settled else ""))
    for b in bad:
        print(b)
    if windows or extra or collapses:
        print(f"  -> `run_game.py gaps {W}` writes the by-eye check briefs for these")
    for b in settled:
        print(b)
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


def _clock_line(W, P):
    """One line for period P's gap brief from clock.json: does the board's clock stop at whistles or run through
    stoppages? Six checkers in four games called a stretch live because "the game clock keeps running" in a period
    whose clock runs through them. On the 20 games with clock.json (Nov 18), before its last 2 minutes the clock of
    every 1st and 2nd stood still 0-9% of the time in 0-3 stops of 3+ s, and of every 3rd 19-35% in 9-28 stops."""
    import clock as clock_
    lap = lambda C: min(C["end"], P["end"]) - max(C["start"], P["start"])
    C = max((clock_.load(W) or {}).get("periods", []), key=lap, default=None)
    if C is None or lap(C) <= 0:
        return ""
    t, c, early, still, stops = _clock_still(C)
    nums = f"before its last 2 minutes it stood still {int((early & still).sum())} of {int(early.sum())} s, in {stops} stops of 3+ s"
    if stops >= CLOCK_STOPS:
        return f"The board's clock in {P['label']} stops at whistles ({nums}): a frozen clock is a stoppage.\n"
    late = int((~early & still).sum())
    return (f"The board's clock in {P['label']} runs through stoppages ({nums}): a running clock says nothing about play "
            f"here, so judge a stoppage from the play itself (a faceoff being set up, players standing or gliding to the "
            f"benches)." + (f" From {int(t[np.argmax(c <= 120)])} s (2:00 left) it stopped at whistles too ({late} s still)."
                            if late >= 10 else "") + "\n")


def _gap_answers(gdir):
    """Every entry earlier rounds' checkers wrote (W/scratch/gaps/answers.json, kept by `gaps --apply`), with the round,
    the brief and the item it answered as the brief listed it (P, t0, t1, what, tid, player_item)."""
    p = f"{gdir}/answers.json"
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []


def _collapse_why(c, A, notes, first, last):
    """A collapse window's text (_collapses), carrying what the hand-made ones did: his look, his usual linemates'
    shifts in the stretch, and an "off" span for whoever the solver had on in his place."""
    from roster import SKATERS
    pl, lab, a, b = c["player"], c["period"], c["t0"], c["t1"]
    m = _mm
    mine, ov = A[A.player == pl], {}
    for r in mine[mine.period != lab].itertuples():   # who is on with him in the other periods
        for q in A[(A.player != pl) & (A.period == r.period) & (A.t1 > r.t0) & (A.t0 < r.t1)].itertuples():
            ov[q.player] = ov.get(q.player, 0) + min(r.t1, q.t1) - max(r.t0, q.t0)
    mates = sorted(ov, key=ov.get, reverse=True)[:2]
    def shifts(q):
        s = A[(A.player == q) & (A.period == lab) & (A.t1 > a) & (A.t0 < b)].sort_values("t0")
        return ", ".join(f"{int(r.t0)}-{int(r.t1)}" for r in s.itertuples()) or "none"
    if a <= first + 5:
        cause = "He has no shift from the opening faceoff: did he come late? Then say when he first came over the boards."
    elif b >= last - 5:
        cause = "He has no shift to the end of the game: did he leave (hurt?), or play on in tracks that carry no number?"
    else:
        cause = "His tracks may carry no number or someone else's; he may also have sat the stretch out."
    look = " ".join(n for n in notes if re.search(rf"#{pl}\b", n))
    return (f"#{pl} {SKATERS.get(pl, '').upper()} has {m(c['toi'])} of ice time in {lab} against "
            + " and ".join(f"{m(v)} in {o}" for o, v in c["others"].items()) + f", and no shift from {a} to {b}. {cause} "
            f"His look: his row on the roster card{'; ' + look if look else ''}. "
            + ("His usual linemates' shifts in the stretch: " + "; ".join(f"#{q} {shifts(q)}" for q in mates) + ". " if mates else "")
            + "Look for him at their changes (the bench door, frames every 5 s) and write an \"on\" span for each shift of his "
              "you find, with an \"off\" span for whoever the solver had on in his place then (shifts_final.csv); if he "
              "really wasn't on, an \"ok\" saying from when to when.")


def cmd_gaps(a):
    """From the lineup check write one filled checker prompt per period (W/scratch/gaps/prompt_pN.md from
    pipeline/gap_prompt.md, and prompt_pN.json listing its items for `--apply`): the team's look, the rink, the board's
    clock, the roster, the known events, numbered windows (the lineup check's, the goals it flags, shifts of 5+ minutes,
    players whose ice time collapses in a period, and leads earlier checkers left open) with the tracked pieces behind
    each and the spans already merged near it, and the long pieces that sit at our bench (B1, B2, ...). Items an
    earlier round settled (a window answered "ok" with the same seconds, a bench piece answered "on" or "fix", a
    collapse answered at all) are not briefed again. Each prompt is one general-purpose subagent's whole job; it
    writes fixes.json in its scratch folder. `gaps W --apply` then merges every fixes.json into periods.json."""
    from roster import ABSENT
    W = os.path.abspath(a.W).replace("\\", "/")
    gdir = f"{W}/scratch/gaps"; os.makedirs(gdir, exist_ok=True)
    if a.apply is not None:
        return apply_fixes(W, a.apply or sorted(glob.glob(f"{gdir}/*/fixes.json")))
    if not os.path.exists(f"{W}/shifts_all.csv"):
        sys.exit("no shifts_all.csv: solve first")
    R = rink(f"{W}/full")
    Ps = periods(W)
    A = pd.read_csv(f"{W}/shifts_all.csv")
    windows, notes, extra = lineup_windows(W, a.min_len)
    settled = [w for w in windows if w.get("settled")]
    windows = [w for w in windows if not w.get("settled")]
    answers = _gap_answers(gdir)
    rnd = 1 + max((e.get("round", 0) for e in answers), default=0)
    closed = {e.get("closes") for e in answers}
    leads = [e for e in answers if e.get("lead_id") and e["lead_id"] not in closed]
    pending = sorted(glob.glob(f"{gdir}/*/fixes.json"))
    if pending:
        print("fixes not yet applied (`gaps --apply` merges them into periods.json):", ", ".join(pending))
    opt = _review_options(W)
    hl = json.load(open(f"{W}/highlights.json")) if os.path.exists(f"{W}/highlights.json") else []
    sheet_ = json.load(open(f"{W}/sheet.json", encoding="utf-8")) if os.path.exists(f"{W}/sheet.json") else {}
    clk = None
    if not any(h.get("type") == "goal" for h in hl):
        # without highlights.json, the sheet's goals at the seconds the goal briefs give them (_sheet_t): sheet.json's
        # video_t is missing or stale when the sheet came before fetch
        import clock as clock_
        clk = clock_.load(W)
    tmpl = open(f"{HERE}/gap_prompt.md", encoding="utf-8").read()
    man = {}
    for P in Ps:
        mp = f"{W}/rev_{P['label'].lower()}/manifest.csv"
        if os.path.exists(mp):
            m = pd.read_csv(mp); man[P["label"]] = dict(zip(m.tid, m.row_id))
    on = lambda t: sorted(int(x) for x in A[(A.t0 <= t) & (A.t1 > t)].player)
    whys = _logged_whys(W)   # spans added by `span` or `highlights --write`, with the reason logged for each
    whys.update({(e.get("P"), e.get("kind"), int(e["player"]), *e["span"]): e.get("why", "") for e in answers if e.get("span")})

    same_secs = lambda e, w: e.get("t0") is not None and abs(e["t0"] - w["t0"]) <= 5 and abs(e["t1"] - w["t1"]) <= 5

    def done_before(lab, w):
        """Settled in an earlier round: a window answered "ok" with the same seconds (5 s either way) and the same
        count on and expected (one wrong in a new way is briefed again; answers from before the counts were kept
        match on the seconds), a bench piece (its track and seconds) answered "on" or "fix", a collapse answered with
        anything but "unsure"."""
        for e in answers:
            if e.get("P") != lab or e.get("unsure") or e.get("bench") == "unsure":
                continue
            if w["what"] == "bench" and e.get("what") == "bench" and e.get("tid") == w["tid"] and same_secs(e, w) \
                    and e.get("bench") in ("on", "fix"):
                return True
            if w["what"] == "collapse" and e.get("what") == "collapse" and e.get("player_item") == w["player"]:
                return True
            if w["what"] not in ("bench", "collapse") and e.get("ok") and same_secs(e, w) \
                    and ("n_on" not in e or (e["n_on"], e.get("expected")) == (w.get("n_on"), w.get("expected"))):
                return True
        return False

    def history(P, w):
        """The spans already merged within a minute of a window, and earlier checkers' open notes on it."""
        lab, out, mg = P["label"], [], []
        for k in ("on", "off") if w["what"] != "bench" else ():
            for e in P.get(k, []):
                if e["start"] < w["t1"] + 60 and e["end"] > w["t0"] - 60:
                    why = whys.get((lab, k, int(e["player"]), float(e["start"]), float(e["end"])))
                    mg.append((e["start"], f"#{e['player']} {k} {e['start']:.0f}-{e['end']:.0f}" + (f" ({why})" if why else "")))
        if mg:
            out.append("merged: " + "; ".join(s for _, s in sorted(mg)))
        er = [f"round {e['round']}: {e.get('unsure') or e.get('why') or e.get('lead')}" for e in answers
              if e.get("P") == lab and (e.get("unsure") or e.get("bench") == "unsure" or e.get("lead"))
              and ((w["what"] == "bench" and e.get("tid") == w.get("tid") and same_secs(e, w)) or
                   (w["what"] != "bench" and e.get("what") != "bench" and e.get("t0") is not None
                    and e["t0"] < w["t1"] and e["t1"] > w["t0"] and e.get("lead_id") != w.get("lead_id")))]
        if er:
            out.append("earlier: " + "; ".join(er))
        return "".join(f"\n   {s}" for s in out)

    plan, skipped, collapses = [], 0, _collapses(W, Ps, A)
    for P in Ps:
        lab = P["label"]; p = lab.lower()
        ws = [dict(w, what="window") for w in windows if w["period"] == lab]
        ws += [dict(w, what="long" if "player" in w else "goal") for w in extra if w["period"] == lab]
        for c in collapses:
            if c["period"] == lab:
                ws.append(dict(c, what="collapse", mid=None, live=None,
                               why=_collapse_why(c, A, opt.get("notes", []), Ps[0]["start"], Ps[-1]["end"])))
        for e in leads:
            if e.get("P") == lab and e.get("t0") is not None:
                t0, t1 = int(e["t0"]), int(max(e["t1"], e["t0"] + 10))
                ws.append(dict(period=lab, t0=t0, t1=t1, what="lead", lead_id=e["lead_id"], mid=(t0 + t1) // 2,
                               on_mid=on((t0 + t1) // 2), live=None,
                               why=f"Round {e['round']}'s checker left this open: {e['lead']}"
                                   + (f" (#{e['player']})" if e.get("player") else "") + ". Settle it."))
        sitters = _bench_sitters(W, P, R) if os.path.exists(f"{W}/{p}/tracks_v1.csv") else []
        bench = [dict(what="bench", player=pl, tid=tid, t0=t0, t1=t1, frac=fr) for pl, tid, t0, t1, fr in sitters]
        n0 = len(ws) + len(bench)
        ws = [w for w in ws if not done_before(lab, w)]
        bench = [w for w in bench if not done_before(lab, w)]
        skipped += n0 - len(ws) - len(bench)
        if not ws and not bench:
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
                [(_sheet_t(clk, Ps, g["period"], _mmss(g["clock"])), g["team"], g.get("scorer")) for g in sheet_.get("goals", [])
                 if g["period"] in [Q["label"] for Q in Ps]]
        for t, team, sc in sorted(goals):
            if P["start"] <= t <= P["end"]:
                ev.append(f"goal {'for us' if team == 'for' else 'against us'} at about {t}" + (f" (#{sc})" if team == "for" and sc else ""))
        ev_txt = (f"\nKnown events in {lab} ({P['start']}-{P['end']} s of video): " + "; ".join(ev) + ".\n") if ev else ""
        S = pd.read_csv(f"{W}/{p}/segs_final.csv") if os.path.exists(f"{W}/{p}/segs_final.csv") else None
        wl, items = [], []
        for k, w in enumerate(ws, 1):
            live = "" if w["live"] is None else (" all of it in a stoppage;" if w["live"] == 0 else f" {w['live']} s of it live;")
            if w["what"] == "collapse":
                line = f"{k}. {lab} {w['t0']}-{w['t1']} ({w['t1'] - w['t0']} s): {w['why']}"
            elif w.get("why"):
                line = f"{k}. {lab} {w['t0']}-{w['t1']} ({w['t1'] - w['t0']} s): {w['why']} The solver's lineup at {w['mid']}: {w['on_mid']}."
            else:
                line = (f"{k}. {lab} {w['t0']}-{w['t1']} ({w['t1'] - w['t0']} s;{live} the solver has {w['n_on']} on, "
                        f"expected {w['expected']}): {w['on_mid']}.")
            if S is not None:
                ov = S[(S.t1 > w["t0"] - 3) & (S.t0 < w["t1"] + 3)]
                head = "pieces"
                if w["what"] == "long":   # a long shift: only his own pieces matter
                    ov = ov[ov.plabel == w["player"]]
                elif w["what"] == "collapse":   # his pieces, and unlabeled ones of ours changing at our bench
                    ov = ov[(ov.plabel == w["player"]) | ((ov.plabel < 0) & (ov.t1 - ov.t0 >= 10) & (ov.bench0 | ov.bench1))]
                    head = "pieces (his, and unlabeled ones that start or end at our bench: one of ours with no number?)"
                else:
                    ov = ov[(ov.plabel >= 0) | (ov.t1 - ov.t0 >= 5)]
                pieces = []
                for s_ in ov.sort_values("t0").itertuples():
                    who = f"#{int(s_.plabel)}" if s_.plabel >= 0 else "unlabeled"
                    src = f", label {'reviewed' if s_.src == 'review' else 'read'}" if s_.num >= 0 else ""
                    row = man.get(lab, {}).get(s_.tid)
                    ends = (" starts at the bench" if s_.bench0 else "") + (" ends at the bench" if s_.bench1 else "")
                    pieces.append(f"{who} tid {int(s_.tid)}{f' ({row})' if row else ''} {s_.t0:.0f}-{s_.t1:.0f}{src}{ends}")
                if pieces:
                    line += f"\n   {head}: " + "; ".join(pieces)
            wl.append(line + history(P, w))
            items.append((str(k), dict(P=lab, t0=int(w["t0"]), t1=int(w["t1"]), what=w["what"], player=w.get("player"),
                                       lead_id=w.get("lead_id"), n_on=w.get("n_on"), expected=w.get("expected"))))
        st_txt, bitems = "", []
        for j, w in enumerate(bench, 1):
            row = man.get(lab, {}).get(w["tid"])
            st_txt += (f"- B{j}. #{w['player']} tid {w['tid']}{f' ({row})' if row else ''} {w['t0']:.0f}-{w['t1']:.0f}, "
                       f"{w['frac']:.0%} of its frames at the bench{history(P, w)}\n")
            bitems.append((f"B{j}", dict(P=lab, t0=int(round(w["t0"])), t1=int(round(w["t1"])), what="bench", player=w["player"], tid=w["tid"])))
        if bench:
            st_txt = ("\nLong tracked pieces that stay in our bench zone (a player sitting at the bench whom the tracker "
                      "counted as on the ice? check each: if he was sitting, that is an \"off\" span over the piece "
                      "until he climbs over the boards):\n" + st_txt)
        hist = any("\n   merged: " in s or "\n   earlier: " in s for s in wl) or "earlier: " in st_txt
        round_note = (f" This is round {rnd}: the on/off spans already in periods.json (earlier checkers', and any added "
                      f"by hand or by `highlights --write`) are in the solve. \"merged\" under a window lists those "
                      f"within a minute of it: build on them, and contradict one only with a frame that shows it. "
                      f"\"earlier\" is a note an earlier checker left open.") if hist else ""
        chunk = max(1, a.chunk)
        # the look, roster, goalie, nets, the period's own roster card, rink, bench, box and clock line, worded as in
        # the goal and penalty briefs
        ctx = _brief_context(W, P)
        for c in range(0, max(len(wl), 1), chunk):
            k = c // chunk   # a, b, ... z, aa, ab, ...
            suffix = "" if len(wl) <= chunk else (chr(96 + k // 26) if k >= 26 else "") + chr(97 + k % 26)
            scratch = f"{gdir}/{p}{suffix}"
            text = tmpl.format(**ctx, scratch=scratch, events=ev_txt, round_note=round_note,
                               windows="\n".join(wl[c:c + chunk]) or "(none this period; only the bench pieces below)",
                               sitters=st_txt if c == 0 else "", out_file=f"{scratch}/fixes.json", period=lab, p=p)
            pf = f"{gdir}/prompt_{p}{suffix}.md"
            open(pf, "w", encoding="utf-8").write(text)
            # what this brief asks about, for `--apply` to list what got no answer
            json.dump(dict(round=rnd, items=dict(items[c:c + chunk] + (bitems if c == 0 else []))),
                      open(f"{gdir}/prompt_{p}{suffix}.json", "w"), indent=1)
            plan.append(f"{lab}{suffix}: {len(wl[c:c + chunk])} window(s)" + (f", {len(bench)} bench piece(s)" if bench and c == 0 else "") + f" -> {pf}")
    for n in notes:
        print(n)
    for w in settled:
        print(f"not briefed:{_window_line(w)[1:]}")
    if skipped:
        print(f"{skipped} item(s) settled in an earlier round, not briefed again (`{gdir}/answers.json`)")
    if not plan:
        print("lineup check: OK; nothing to brief" + (f"; {len(notes)} goal note(s) above" if notes else ""))
        return
    print(f"round {rnd}:\n" + "\n".join(plan))
    print(f"{len(plan)} prompt(s): for each, one general-purpose subagent whose whole prompt is\n"
          f"  'Read <prompt file> and do exactly what it says. Reply with one line per window and bench piece.'\n"
          f"  Then `run_game.py gaps {a.W} --apply` merges their fixes.json files into periods.json, and solve again.")
    if ABSENT:
        print("absent (not on the roster above):", ", ".join(f"#{n}" for n in sorted(ABSENT)))


def _match_item(items, e):
    """The brief item an entry without a usable "item" answers: its "window" seconds, its "tid", or the first window
    its span overlaps (10 s either way)."""
    w = str(e.get("window", ""))
    if re.fullmatch(r"\s*\d+(\.\d+)?\s*-\s*\d+(\.\d+)?\s*", w):
        a, b = (float(x) for x in w.split("-"))
        return next((k for k, i in items.items() if abs(i["t0"] - a) <= 2 and abs(i["t1"] - b) <= 2), None)
    if e.get("tid") is not None:   # two bench pieces of one track each need their own answer: the seconds tell them apart
        tid = int(e["tid"])
        cands = [k for k, i in items.items() if i["what"] == "bench" and i.get("tid") == tid]
        try:
            a, b = float(e["start"]), float(e["end"])
            cands = [k for k in cands if items[k]["t0"] - 10 < b and items[k]["t1"] + 10 > a] if len(cands) > 1 else cands
        except (KeyError, TypeError, ValueError):
            pass
        return cands[0] if len(cands) == 1 else None
    try:
        a, b = float(e["start"]), float(e["end"])
    except (KeyError, TypeError, ValueError):
        return None
    return next((k for k, i in items.items() if i["what"] != "bench" and i["t0"] - 10 < b and i["t1"] + 10 > a), None)


def apply_fixes(W, files):
    """Merge gap checkers' fixes.json files ([{"item", "period", "kind": "on"|"off", "player", "start", "end", "why"},
    ...]) into periods.json, and keep every entry in W/scratch/gaps/answers.json for the next round's briefs. "ok",
    "unsure" and bench answers are printed; a "lead" becomes a window in the next `gaps`; a penalty kill called 5 on
    5 is reported loudly and not applied (the pk is the session's call). The items each brief listed that got no
    answer are named; an entry that can't be read (no player, a tid like "571/912" and no item) is printed and its
    item counts as unanswered. periods.json and answers.json are written first, then the applied files renamed
    fixes.rN.json (N = the brief's round), so a failure leaves every file for the next run."""
    gdir = f"{W}/scratch/gaps"
    Ps = periods(W)
    answers = _gap_answers(gdir)
    added, loud, new, done = 0, [], [], []
    if not files:
        print("no fixes.json to apply (checkers write W/scratch/gaps/<period>/fixes.json)")
        return
    for f in files:
        try:
            fixes = json.load(open(f, encoding="utf-8"))
        except ValueError as e:
            print(f"{f}: not JSON ({e}); skipped"); continue
        name = os.path.basename(os.path.dirname(os.path.abspath(f)))   # the brief's scratch folder: p1, p2a, ...
        mp = f"{gdir}/prompt_{name}.json"
        brief = json.load(open(mp)) if os.path.exists(mp) else {}
        items, rnd = brief.get("items", {}), brief.get("round") or 1 + max((e.get("round", 0) for e in answers), default=0)
        answered = set()
        print(f"{f}:")
        for e in fixes if isinstance(fixes, list) else [fixes]:
            if not isinstance(e, dict):
                print(f"  not an entry, taken as no answer: {e!r}"[:240]); continue
            try:
                it = str(e.get("item", "")).strip().lstrip("#").upper()
                it = it if it in items else _match_item(items, e)
                rec = dict(e, round=rnd, brief=name, P=e.get("period"))
                if it:
                    i = items[it]
                    rec.update(item=it, P=i["P"], t0=i["t0"], t1=i["t1"], what=i["what"], tid=i.get("tid"),
                               player_item=i.get("player"), n_on=i.get("n_on"), expected=i.get("expected"))
                    if i.get("lead_id"):
                        rec["closes"] = i["lead_id"]
                added += _fix_entry(W, e, rec, it, Ps, loud, answers + new)
            except (KeyError, TypeError, ValueError, AttributeError, IndexError) as x:
                print(f"  can't read this entry, so its item counts as unanswered: {json.dumps(e, ensure_ascii=False)[:200]} "
                      f"({type(x).__name__}: {x})")
                continue
            if it:
                answered.add(it)
            new.append(rec)
        missing = [(k, i) for k, i in items.items() if k not in answered]
        if missing:
            print("  NO ANSWER for: " + "; ".join(
                (f"bench piece {k} (#{i['player']} tid {i['tid']}, {i['t0']}-{i['t1']})" if i["what"] == "bench"
                 else f"window {k} ({i['P']} {i['t0']}-{i['t1']})") for k, i in missing)
                  + ": the next `gaps` lists them again")
        done.append((f, f"{f[:-5]}.r{rnd}.json"))
    if new:
        json.dump(answers + new, open(f"{gdir}/answers.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if added:
        save_periods(W, Ps, sort=("on", "off"))
    for f, g in done:   # last: a run that failed before this point leaves every fixes.json to be applied again
        os.replace(f, g)
    print(f"{added} span(s) added to {W}/periods.json" + ("; solve again" if added else ""))
    closed = {e.get("closes") for e in answers + new}
    nopen = sum(1 for e in answers + new if e.get("lead_id") and e["lead_id"] not in closed)
    if nopen:
        print(f"{nopen} open lead(s): after the solve, `gaps` makes each a window")
    for s in loud:
        print(s)


def _fix_entry(W, e, rec, it, Ps, loud, earlier):
    """One gap checker's entry (apply_fixes): a pk played 5 on 5 is reported, a lead numbered, an ok / unsure /
    bench answer printed, an on/off span added to its period (add_span). Returns the spans added (0 or 1); raises
    ValueError for an entry that can't be read."""
    if e.get("pk") is not None or e.get("even"):
        k = next((k for P in Ps for k in P.get("pk", []) if f"{k['start']}-{k['end']}" == str(e.get("pk")).replace(" ", "")), None)
        pl = k.get("player") if k else None
        loud.append(f"!! {rec.get('P') or ''} penalty kill {e.get('pk')}" + (f" (#{pl} in the box)" if pl else "")
                    + f": the checker says it was played 5 on 5 ({e.get('even') or e.get('why', '')}). Not applied. If one "
                    f"of theirs sat in their box over the same stretch (coincident minors), do both of what `highlights "
                    f"--write` does by itself for coincident minors: take that pk out of {W}/periods.json (or cut it to "
                    f"the part that was 4 on 5), and keep the boxed player off the ice while he sat, `run_game.py span "
                    f"{W} off {pl if pl else '<player>'} {k['start'] if k else '<box in>'} {k['end'] if k else '<box out>'} "
                    f"--note \"in the box, coincident minors\"` (his seconds in the box); then solve again.")
        print(f"  {loud[-1]}")
        return 0
    if e.get("lead"):
        rec["lead_id"] = f"L{1 + sum(1 for x in earlier if x.get('lead_id'))}"
        try:   # the lead's own seconds, else its item's
            rec["t0"], rec["t1"] = float(e["start"]), float(e["end"])
            rec["P"] = next((P["label"] for P in Ps if P["start"] <= rec["t0"] <= P["end"]), rec["P"])
        except (KeyError, TypeError, ValueError):
            pass
        print(f"  lead {rec.get('P') or ''} {rec.get('t0', '')}-{rec.get('t1', '')}"
              + (f" #{e['player']}" if e.get("player") else "") + f": {e['lead']} (the next `gaps` makes it a window)")
        return 0
    if e.get("kind") not in ("on", "off"):
        what = next((f"{k}: {e[k]}" for k in ("ok", "unsure") if e.get(k)), None) or \
            (f"bench {e['bench']}: {e.get('why', '')}" if e.get("bench") else None)
        if what is None:
            raise ValueError("no kind, ok, unsure, bench, lead or pk")
        print(f"  noted {rec.get('P') or ''} {('item ' + it) if it else e.get('window', '')}: {what}")
        return 0
    player, t0, t1 = int(e["player"]), float(e["start"]), float(e["end"])
    # the times decide the period (a checker may copy a label from the brief's template); the label only places a
    # span that starts in a break
    P = next((P for P in Ps if P["start"] <= t0 <= P["end"]), None) or \
        next((P for P in Ps if P["label"] == e.get("period")), None)
    if P is None or t1 <= t0:
        raise ValueError(f"{t0}-{t1} is in no period")
    t0, t1 = max(t0, P["start"]), min(t1, P["end"])
    rec.update(P=P["label"], span=[float(t0), float(t1)])
    if add_span(P, e["kind"], t0, t1, player) is None:
        print(f"  already in periods.json: {P['label']} {e['kind']} #{player} {t0}-{t1}")
        return 0
    print(f"  + {P['label']} {e['kind']:3s} #{player} {t0}-{t1}: {e.get('why') or e.get('note', '')}")
    return 1


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
        if not g.get("date") and rec.get("dayTime"):   # records added by hand without one (TK's 32943, 32944, ...)
            g["date"] = rec["dayTime"][:19]             # sorted first and rewrote the file on every run
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
    """(SportNinja game id, LADA game id) for our game on `date`. The SportNinja id is the last part of LADA's
    boxscoreLink: from LADA's record of `lada_id` when given, else from the LADA cache by date. A record of `lada_id`
    that is our team's game and not cached yet joins teams/<slug>/lada_games.json, as references/lada.md had the
    sessions do by hand, so publish, schedule and the lines in `absent --suggest` find it by date."""
    from roster import LADA_TEAM_ID
    if lada_id:
        try:
            rec = _lada_get(f"game/{lada_id}")
        except Exception as e:
            log(f"LADA game {lada_id} unavailable ({e})")
            return None, lada_id
        if date and (rec.get("dayTime") or date)[:10] != date:
            log(f"LADA game {lada_id} was played on {rec['dayTime'][:10]}, not {date}: is it the right id?")
        p = lada_games_path()
        games = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
        if rec.get("teamId") == LADA_TEAM_ID and str(lada_id) not in games and rec.get("dayTime"):
            cur = games.setdefault(str(lada_id), {"date": rec["dayTime"][:19]})
            for k in ("playHome", "rinkId", "lines", "teamGoals", "opponentGoals", "boxscoreLink"):
                if rec.get(k) is not None:
                    cur[k] = rec[k]
            games = dict(sorted(games.items(), key=lambda kv: kv[1].get("date", "")))
            json.dump(games, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
            log(f"LADA game {lada_id} ({cur['date'][:10]}) added to {p}")
        link = rec.get("boxscoreLink") or ""
        return link.rstrip("/").rsplit("/", 1)[-1] or None, int(lada_id)
    for i, g in update_lada_games().items():
        if str(g.get("date", ""))[:10] == date and g.get("boxscoreLink"):
            return g["boxscoreLink"].rstrip("/").rsplit("/", 1)[-1], int(i)
    return None, None


def cmd_scores(a):
    """Each published game's final score from its SportNinja game sheet (game.json's sportninja_id, else the end of
    LADA's boxscoreLink) into game.json's sheet_score, the score the site shows. Scorekeepers correct sheets after
    the game (Blue Wings' Nov 7 went from 5-5 to 6-5), so run it before rebuilding. Every team, or --team."""
    import urllib.request
    from lada_ids import fold
    slugs = [a.team] if a.team else sorted(t for t in os.listdir(f"{ROOT}/teams")
                                           if os.path.exists(f"{ROOT}/teams/{t}/roster.json"))
    changed = 0
    for t in slugs:
        r = json.load(open(f"{ROOT}/teams/{t}/roster.json", encoding="utf-8"))
        name = r.get("team_name", r["team"])
        lp = f"{ROOT}/teams/{t}/lada_games.json"
        lada = json.load(open(lp, encoding="utf-8")) if os.path.exists(lp) else {}
        for gj in sorted(glob.glob(f"{ROOT}/teams/{t}/games/*/game.json")):
            game = json.load(open(gj, encoding="utf-8"))
            link = lada.get(str(game.get("lada_game_id")), {}).get("boxscoreLink") or ""
            sn = game.get("sportninja_id") or link.rstrip("/").rsplit("/", 1)[-1] or None
            if not sn:
                print(f"  {t} {game['id']}: no game sheet (no sportninja_id, no LADA boxscoreLink)")
                continue
            try:
                with urllib.request.urlopen(f"{SN_API}/games/{sn}", timeout=30) as resp:
                    g = json.load(resp)["data"]
            except Exception as e:
                print(f"  {t} {game['id']}: game sheet {sn} unavailable ({e})")
                continue
            home, vis = g["homeTeam"], g["visitingTeam"]
            mine = [x for x in (home, vis) if fold(name) in fold(x["name"]) or fold(x["name"]) in fold(name)]
            if len(mine) != 1 or g.get("home_team_score") is None or g.get("visiting_team_score") is None:
                print(f"  {t} {game['id']}: game sheet {sn} has no score for {name} ({home['name']} vs {vis['name']})")
                continue
            ours, theirs = ((g["home_team_score"], g["visiting_team_score"]) if mine[0]["id"] == home["id"]
                            else (g["visiting_team_score"], g["home_team_score"]))
            new = {"for": ours, "against": theirs}
            if game.get("sheet_score") == new and game.get("sportninja_id") == sn:
                continue
            old = game.get("sheet_score")
            was = f"{old['for']}-{old['against']}" if old else "none"
            print(f"  {t} {game['id']}: {was} -> {ours}-{theirs}")
            game["sheet_score"], game["sportninja_id"] = new, sn
            json.dump(game, open(gj, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
            changed += 1
    print(f"{changed} game(s) updated" + ("; rebuild the site: build_site.py" if changed else ""))


def cmd_sheet(a):
    """SportNinja's game sheet, public at metal-api.sportninja.net: which side we were, the score, shots per period,
    every goal with its period clock, scorer and assists, every penalty with the player, type and minutes, and who
    played. Prints it and writes W/sheet.json. Each goal and penalty gets a video time: the second the board's clock
    first showed its clock time (clock.json; a goal stops the clock there), or without clock.json, once periods.json
    is in place, period start + what the clock had run (exact only where the clock runs through stoppages)."""
    import urllib.request
    from roster import TEAM_NAME, TEAM, ALL_SKATERS, GOALIE_NAMES, SKATERS
    from lada_ids import fold
    W = os.path.abspath(a.W) if a.W else None
    m = re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(W or ""))
    date = a.date or (m.group(0) if m else None)
    # the ids an earlier run found (with --lada or --sn, or by date) are kept in sheet.json: the run after
    # periods.json exists, for the goals' video times, used to need --lada again
    old = json.load(open(f"{W}/sheet.json", encoding="utf-8")) if W and os.path.exists(f"{W}/sheet.json") else {}
    lada = a.lada or old.get("lada_game_id")
    sn = a.sn or (None if a.lada else old.get("sportninja_id"))
    if not sn and (date or lada):
        sn, lada = sportninja_id(date, lada)
    if not lada and date and os.path.exists(lada_games_path()):   # --sn alone: the cache may still know the game
        lada = next((int(i) for i, x in json.load(open(lada_games_path(), encoding="utf-8")).items()
                     if str(x.get("date", ""))[:10] == date), None)
    if not sn:
        sys.exit("no SportNinja game found: give --sn <id> (the end of LADA's boxscoreLink) or --lada <LADA game id>")
    with urllib.request.urlopen(f"{SN_API}/games/{sn}", timeout=30) as r:
        g = json.load(r)["data"]
    home, vis = g["homeTeam"], g["visitingTeam"]
    names = {home["id"]: home["name"], vis["id"]: vis["name"]}
    mine = [t for t in (home, vis) if fold(TEAM_NAME) in fold(t["name"]) or fold(t["name"]) in fold(TEAM_NAME)]
    if not mine:
        sys.exit(f"neither {home['name']!r} nor {vis['name']!r} looks like {TEAM_NAME!r}: whose game is it? "
                 f"(--team <slug>, or name the folder <slug>-<date>-vs-<opp>)")
    us = mine[0]["id"]; side = "home" if us == home["id"] else "visiting"; them = vis["id"] if side == "home" else home["id"]
    ros = {r["team_id"]: {p["id"]: p for p in r["players"]} for r in g.get("playerRosters", [])}
    def who(team, pid_):
        p = ros.get(team, {}).get(pid_)
        return (p["player_number"], p["name_last"]) if p else (None, pid_)
    pname = {p["id"]: p["period_type"]["name"] for p in g["periods"]}
    plabel = {p["id"]: f"P{p['period_type']['sort_order']}" for p in g["periods"]}
    pdur = {p["id"]: int(p["duration"] / 1000) for p in g["periods"]}
    Ps = {P["label"]: P for P in periods(W)} if W and os.path.exists(f"{W}/periods.json") else {}
    import clock as clock_
    clk = clock_.load(W) if W else None
    def video_t(period_id, clock):
        P = Ps.get(plabel[period_id])
        C = next((C for C in clk["periods"] if C["label"] == plabel[period_id]), None) if clk else None
        if C and (not P or (C["start"] < P["end"] and P["start"] < C["end"])):   # the same period by both counts
            return clock_.video_t(clk, plabel[period_id], _clock_s(clock))
        if not P:
            return None
        return int(P["start"] + pdur[period_id] - _clock_s(clock))
    out = dict(sportninja_id=sn, lada_game_id=int(lada) if lada else None, us=side, home=home["name"], visiting=vis["name"],
               score=[g["home_team_score"] if side == "home" else g["visiting_team_score"],
                      g["visiting_team_score"] if side == "home" else g["home_team_score"]],
               rink=f"{(g.get('venue') or {}).get('name', '')} {(g.get('facility') or {}).get('name', '')}".strip(),
               shots={}, goals=[], penalties=[], played=[], played_names=[], not_marked_playing=[],
               period_lengths={plabel[p["id"]]: pdur[p["id"]] for p in g["periods"]})   # an overtime is 5:00
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
        print(f"wrote {W}/sheet.json" + ("" if Ps or clk else "; video times appear once periods.json exists")
              + (" (video times from the board's clock)" if clk else "")
              + f". SportNinja game {sn}, LADA game {out['lada_game_id'] or 'unknown'}: kept there, so later runs need "
                "neither --sn nor --lada")


def cmd_schedule(a):
    """The team's games LADA knows (the cache plus a fresh look): date, opponent, home or away, rink, LADA id,
    whether its game page exists, and the planned lines' players who have no LADA id in roster.json yet."""
    from roster import GAMES_DIR, LADA_IDS, TEAM
    games = update_lada_games()
    have = {os.path.basename(d)[:10] for d in glob.glob(f"{GAMES_DIR}/*")}
    known = {v: k for k, v in LADA_IDS.items()}
    print(f"{TEAM}: {len(games)} games in LADA's view (* = published on the site)")
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


def _lada_record(lada_id, date):
    """This game's record in the team's lada_games.json (by id, else by date), {} if the cache doesn't know it.
    Games found by probing have no rinkName: it comes from another cached game at the same rinkId."""
    from roster import REPO
    p = lada_games_path()
    games = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    rec = dict(games.get(str(lada_id)) or next((g for g in games.values() if str(g.get("date", ""))[:10] == date), {}))
    if rec.get("rinkId") and not rec.get("rinkName"):
        rec["rinkName"] = next((g["rinkName"] for f in glob.glob(f"{REPO}/teams/*/lada_games.json")
                                for g in json.load(open(f, encoding="utf-8")).values()
                                if g.get("rinkId") == rec["rinkId"] and g.get("rinkName")), None)
    return rec


# the start time's sources, the first found wins: over the 53 published eyebrows (Nov 18) the title's time matched the
# typed one on 43 and LADA's schedule's on 42 (TK's Oct 25: the title 9:25 PM, LADA 8:25 PM); whole eyebrows 40 either way
EYEBROW_TIME_FROM = ("the video's title", "LADA's schedule")


def game_eyebrow(W, d, rec, sheet_):
    """The game page's header line in the site's format, 'Sun Nov 15, 2026 · 6:25 PM · Renton', for a publish without
    --eyebrow (sessions used to copy the last game's and edit it): the day from the game's date, the start time from
    the video's title (Turbo Kings': 'LTKvsSO 10:40 PM PDT - NOV 15, 2026 (Renton) - wide cut'), else LADA's schedule
    (EYEBROW_TIME_FROM), the rink from LADA's schedule, else the title, else the game sheet's venue ('Snoqualmie
    Arena Rink A'). The sources have
    disagreed (TK's Oct 25: LADA 8:25 PM, the title 9:25 PM), so any disagreement is printed. Exits without a time
    or a rink: the feed reads both out of the eyebrow."""
    vi = f"{W}/video_info.json"
    title = (json.load(open(vi, encoding="utf-8")).get("title") or "") if os.path.exists(vi) else ""
    times, rinks = {}, {}
    if str(rec.get("date", ""))[:10] == d.isoformat() and len(rec["date"]) >= 16:
        h, mi = int(rec["date"][11:13]), int(rec["date"][14:16])
        times["LADA's schedule"] = f"{(h - 1) % 12 + 1}:{mi:02d} {'AM' if h < 12 else 'PM'}"
    if rec.get("rinkName"):
        rinks["LADA's schedule"] = rec["rinkName"]
    m = re.search(r"\b(\d{1,2}):(\d{2})\s*([AP]M)\b", title, re.I)
    if m:
        times["the video's title"] = f"{int(m.group(1))}:{m.group(2)} {m.group(3).upper()}"
    m = re.search(r"\(([A-Za-z][^)]*)\)", title)
    if m:
        rinks["the video's title"] = m.group(1).strip()
    venue = sheet_.get("rink") or ""
    if venue:
        m = re.search(r"\bRink ([A-Z])\b", venue)
        rinks["the game sheet"] = venue.split()[0] + (f" {m.group(1)}" if m else "")
    if not times or not rinks:
        sys.exit(f"publish: no {'start time' if not times else 'rink'} for this game in LADA's schedule, the video's "
                 f"title or the game sheet: give --eyebrow \"{d:%a} {d:%b} {d.day}, {d.year} · <h:mm PM> · <rink>\"")
    tsrc = next(k for k in EYEBROW_TIME_FROM if k in times)
    t, (rsrc, r) = times[tsrc], next(iter(rinks.items()))
    eyebrow = f"{d:%a} {d:%b} {d.day}, {d.year} · {t} · {r}"
    print(f"eyebrow: {eyebrow} (the time from {tsrc}, the rink from {rsrc}; --eyebrow to change it)")
    for what, got in (("time", times), ("rink", rinks)):
        if len(set(got.values())) > 1:
            print(f"  the {what} differs between sources: " + "; ".join(f"{k} {v}" for k, v in got.items()))
    return eyebrow


def add_opponent(code, rec, sheet_):
    """A new opponent code joins the team's opponents.json, after the others (a script that re-sorted the keys had to
    be reverted), with LADA's spelling, which finds the logo in the LADA app; SportNinja's can differ ('Best Vibes HC',
    'Chill Vibes HC', 'Hosers D' where opponents.json has LADA's), so the game sheet's name is only the fallback."""
    from roster import TEAM_DIR, OPPONENTS
    if code in OPPONENTS:
        return
    p = f"{TEAM_DIR}/opponents.json"
    name = rec.get("opponentName") or sheet_.get({"home": "visiting", "visiting": "home"}.get(sheet_.get("us"), ""))
    if not name:
        print(f"opponent {code} is new, and neither LADA's schedule nor sheet.json names them: add \"{code}\": "
              f"\"<full name>\" to {p} (the site shows {code} until then), then build_site.py")
        return
    raw = open(p, encoding="utf-8").read() if os.path.exists(p) else "{}"
    ops = json.loads(raw); ops[code] = OPPONENTS[code] = name
    open(p, "w", encoding="utf-8").write(json.dumps(ops, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
    print(f"opponents.json: added \"{code}\": \"{name}\" ({'LADA' if rec.get('opponentName') else 'the game sheet'}'s "
          f"spelling); the user's spelling wins: change it in {p} if they want another, then build_site.py")


def publish_notes(a):
    """The game's notes from --notes-file (a blank line between notes) and each --notes, in that order; they replace
    game.json's. None when neither is given: game.json keeps the notes it has. Sessions used to write them with a
    one-off script after publish (three of 14 needed a second edit for the JSON's formatting or line endings)."""
    if not a.notes and not a.notes_file:
        return None
    paras = re.split(r"\n\s*\n", open(a.notes_file, encoding="utf-8-sig").read()) if a.notes_file else []
    return [" ".join(p.split()) for p in paras + (a.notes or []) if p.strip()]


def print_game(gd):
    """The game's player table, the facts strip and the fun stats as plain text, from the data the page is built from
    (build_report.page_data), for the session to show the user: sessions used to scrape them out of the built page."""
    import math
    from build_report import page_data
    from roster import final_score
    game, A, data = page_data(gd)
    fmt = lambda s: "-" if s is None else f"{math.floor(s + 0.5) // 60}:{math.floor(s + 0.5) % 60:02d}"   # the page's
    P, F, players = data["periods"], data["fun"], sorted(data["players"], key=lambda p: -p["toi"])
    name = lambda n: next((p["name"] for p in players if p["num"] == n), "")
    who = lambda n: f"#{n} {name(n)}".rstrip()
    pm = lambda x: f"{x:+d}" if x else "0"
    play = any(p["play"] is not None for p in players)
    sc = final_score(game)
    print(f"\n{game['title']} ({sc['gf']}-{sc['ga']}{'' if sc['official'] else ', goals on video'}) · {game['eyebrow']}")
    print(f"{'#':>3}  {'player':<18}{'shifts':>6}{'ice':>7}" + (f"{'live':>7}" if play else "") +
          f"{'+/-':>5}{'avg':>6}{'median':>7}{'long':>6}{'short':>6}  " + "".join(f"{p['label']:>6}" for p in P))
    for p in players:
        print(f"{p['num']:>3}  {(p['name'] + (' (sub)' if p['sub'] else '')):<18}{p['shifts']:>6}{fmt(p['toi']):>7}" +
              (f"{fmt(p['play']):>7}" if play else "") + f"{pm(p['plus_minus']):>5}{fmt(p['avg']):>6}{fmt(p['median']):>7}"
              f"{fmt(p['longest']):>6}{fmt(p['shortest']):>6}  " + "".join(f"{fmt(x[1]) if x else '-':>6}" for x in p["per"]))
    nsh, tot = sum(p["shifts"] for p in players), sum(p["toi"] for p in players)
    facts = [f"{len(players)} skaters", "periods " + " · ".join(fmt(p["end"] - p["start"]) for p in P),
             f"{nsh} shifts", f"average shift {fmt(tot / nsh)}"]
    S = data.get("shots")
    if S:
        per = [S[p["label"]] for p in P if p["label"] in S]
        facts.append(f"shots {sum(x[0] for x in per)}-{sum(x[1] for x in per)} ({', '.join(f'{x[0]}-{x[1]}' for x in per)})")
    ls = max(data["shifts"], key=lambda s: s["t1"] - s["t0"])
    sp = min((p for p in players if p["shortest"] is not None), key=lambda p: p["shortest"], default=None)
    print(" · ".join(facts))
    print(f"most ice time {who(players[0]['num'])} {fmt(players[0]['toi'])} · longest shift {who(ls['player'])} "
          f"{fmt(ls['t1'] - ls['t0'])}" + (f" · shortest shift {who(sp['num'])} {fmt(sp['shortest'])}" if sp else ""))
    print("Fun stats:")
    if F.get("pairs"):
        print("  best duos: " + "; ".join(f"{who(x['a'])} + {who(x['b'])} {fmt(x['sec'])}" for x in F["pairs"]))
    if F.get("unit"):
        print(f"  most-used five: {', '.join(who(n) for n in F['unit']['players'])}, together {fmt(F['unit']['sec'])}")
    if F.get("periods"):
        print("  shift length by period: " + ", ".join(f"{x['label']} {fmt(x['avg'])} avg ({x['n']} shifts)" for x in F["periods"]))
    if F.get("quickest"):
        print(f"  quickest changer: {who(F['quickest']['num'])}, {fmt(F['quickest']['avg'])} average shift; most shifts: "
              f"{', '.join(who(n) for n in F['most']['nums'])} ({F['most']['n']} each)")
    for k in F.get("pk") or []:
        print(f"  penalty kill {k['period']} {fmt(k['from'])}-{fmt(k['to'])}" + (f", {who(k['player'])} in the box" if k.get("player") else "")
              + ": " + (", ".join(f"{who(c['num'])} {fmt(c['sec'])}" for c in k["crew"]) or "-"))
    if len(F.get("reads") or []) > 1:
        top, low = F["reads"][0], F["reads"][-1]
        print(f"  most readable jersey: {who(top['num'])}, name read {top['n']:,} times; hardest to read: {who(low['num'])}, {low['n']} times")
    if F.get("pipeline"):
        it = [(F["pipeline"].get(k), t) for k, t in (("detections", "player detections"), ("crops", "close-ups of our players"),
                                                    ("reads", "number and name reads"), ("reviewed", "tracks checked by eye"))]
        print("  " + ", ".join(f"{v:,} {t}" for v, t in it if v))


def cmd_publish(a):
    W = os.path.abspath(a.W)
    from reads import load_reads
    from roster import GAMES_DIR, SITE_DIR
    import datetime
    date = a.date or a.game_id[:10]
    d = datetime.date.fromisoformat(date)
    gd = f"{GAMES_DIR}/{a.game_id}"; gj = f"{gd}/game.json"
    old = json.load(open(gj)) if os.path.exists(gj) else {}
    sheet_ = json.load(open(f"{W}/sheet.json", encoding="utf-8")) if os.path.exists(f"{W}/sheet.json") else {}
    notes = publish_notes(a)
    # before anything is written (the eyebrow exits when nothing gives a time): LADA's id links the game to the LADA
    # app's schedule and scores, and its record names a new opponent and gives the start time and rink
    lada_id = old.get("lada_game_id") or sheet_.get("lada_game_id") or lada_game_id(date)
    rec = _lada_record(lada_id, date)
    eyebrow = a.eyebrow or old.get("eyebrow") or game_eyebrow(W, d, rec, sheet_)
    if not a.eyebrow and old.get("eyebrow"):
        print(f"eyebrow: {eyebrow} (the earlier publish's; --eyebrow to change it)")
    add_opponent(a.opponent, rec, sheet_)
    os.makedirs(gd, exist_ok=True)
    shutil.copy(f"{W}/shifts_all.csv", f"{gd}/shifts.csv")
    Ps = periods(W)
    from roster import TEAM, OPPONENTS
    reads, names = load_reads(f"{W}/full")
    played = set(pd.read_csv(f"{W}/shifts_all.csv").player)
    lineup_check(W)
    video = a.video or open(f"{W}/url.txt").read().strip()
    if not video.startswith("http"):   # a local recording (BW's Oct 25 came from LiveBarn): no link until --video
        video = ""
    game = dict(
        id=a.game_id, date=date, title=a.title or f"{TEAM} vs {OPPONENTS.get(a.opponent, a.opponent)}, {d:%b} {d.day}",
        eyebrow=eyebrow, opponent=a.opponent, video=video,
        periods=[dict(label=P["label"], start=P["start"], end=P["end"]) for P in Ps],
        nets={P["label"]: P["net"] for P in Ps},
        penalty_kills=[dict(period=P["label"], **k) for P in Ps for k in P.get("pk", [])],
        notes=[], video_ends_early=bool(a.video_ends_early),
        fun=dict(name_reads={str(k): int(v) for k, v in names.num.value_counts().items() if k in played}),
        pipeline=dict(detections=sum(1 for _ in open(f"{W}/full/dets.csv")),
                      crops=len(os.listdir(f"{W}/full/crops")) if os.path.isdir(f"{W}/full/crops") else None,
                      reads=int(len(reads)),
                      reviewed=int(sum(len(pd.read_csv(m)) for m in glob.glob(f"{W}/rev_p*/manifest.csv")))))
    if old:  # keep hand-written fields (notes, title tweaks) from an earlier publish
        for k in ("notes", "title", "eyebrow", "highlights", "video_ends_early", "lada_game_id", "opponent_name", "zones",
                  "shots", "shots_source", "guests", "ice", "sheet_score", "sportninja_id"):
            if old.get(k):
                game[k] = old[k]
        if game["pipeline"]["crops"] is None and (old.get("pipeline") or {}).get("crops"):
            game["pipeline"]["crops"] = old["pipeline"]["crops"]   # an archived folder has no crops any more
    # what is given on the command line wins over the earlier publish's (--eyebrow and --title used to lose)
    game["eyebrow"] = eyebrow
    if a.title:
        game["title"] = a.title
    if notes is not None:
        game["notes"] = notes
    if not game.get("lada_game_id"):  # links the game to the LADA app's schedule and scores
        game["lada_game_id"] = lada_id
    if os.path.exists(f"{W}/stoppages.json"):
        game["stoppages"] = json.load(open(f"{W}/stoppages.json"))
    if os.path.exists(f"{W}/highlights.json"):  # [{type, team|player, t, clip, poster, note}] from the clips step
        # without the goal checker's shot, pass and on_ice (HL_WORK): the clips' and the lineup check's, not the page's
        game["highlights"] = [{k: v for k, v in h.items() if k not in HL_WORK}
                              for h in json.load(open(f"{W}/highlights.json", encoding="utf-8"))]
    if os.path.exists(f"{W}/shots.json") and json.load(open(f"{W}/shots.json")).get("checked"):
        game["shots"] = json.load(open(f"{W}/shots.json"))["periods"]   # shots.py, once checked against the board
        game["shots_source"] = "board"
    elif (not game.get("shots") or game.get("shots_source") == "sheet") and os.path.exists(f"{W}/sheet.json"):
        # the game sheet's shots per period (SportNinja); the board's OCR is wrong more often than not. Shots that
        # came from the sheet follow the folder's sheet.json on a republish: scorekeepers correct sheets after the
        # game (Blue Wings' Nov 7 gained a goal and a shot), and an earlier publish's shots used to stay
        sh_shots = json.load(open(f"{W}/sheet.json", encoding="utf-8")).get("shots") or {}
        if all(P["label"] in sh_shots for P in Ps):
            game["shots"] = {P["label"]: sh_shots[P["label"]] for P in Ps}
            game["shots_source"] = "sheet"
    if os.path.exists(f"{W}/sheet.json"):   # the game sheet's final score is the site's (`scores` refreshes it)
        sheet_ = json.load(open(f"{W}/sheet.json", encoding="utf-8"))
        if sheet_.get("score"):
            game["sheet_score"] = {"for": sheet_["score"][0], "against": sheet_["score"][1]}
            game["sportninja_id"] = sheet_.get("sportninja_id")
    from zones import zone_shares   # time in offence / defence for the trends page (needs the detections)
    game["zones"] = zone_shares(f"{W}/full", game) or game.get("zones")
    from ice import ice_maps   # where each skater was, for the game page's ice maps (rinks with a calibration)
    game["ice"] = ice_maps(W) or game.get("ice")
    json.dump(game, open(gj, "w"), indent=2, ensure_ascii=False)
    # every team, not just $TEAM: the root page counts each team's games, and each team's menu lists the teams with games
    sh(PY, f"{HERE}/build_site.py", env={k: v for k, v in os.environ.items() if k not in ("TEAM", "ROSTER_ABSENT")})
    where = "game.json only: the game page, the trends page and the feed don't show them"
    print(f"notes: {len(notes)} written to {gj} ({where})" if notes is not None else
          f"notes: {len(game['notes'])} kept from the earlier publish ({where}; --notes/--notes-file replace them)"
          if game["notes"] else f"notes: none yet; --notes TEXT (repeatable) or --notes-file F write them ({where})")
    print_game(gd)
    import pathlib
    page = f"{SITE_DIR}/games/{a.game_id}/index.html"
    url = pathlib.Path(page).resolve().as_uri()
    # sessions were asked to open it in 8 of 14 games, on its first publish; a republish opens it only with --open
    if (a.open or not old) and not a.no_open:
        import webbrowser
        webbrowser.open(url)
    log(f"wrote {gd}; the sites rebuilt in docs/. The page: {url}" + (" (opened)" if (a.open or not old) and not a.no_open
        else "") + ". Review, then commit and push to publish.")


def _size(path):
    n = 0
    for d, _, fs in os.walk(path):
        n += sum(os.lstat(os.path.join(d, f)).st_size for f in fs)
    return n


SCRATCH_KEEP = ("goals", "gaps", "clips")   # scratch/ folders whose text archive keeps (_scratch_text)


def _scratch_text(W):
    """The .md and .json files under W/scratch/goals, gaps and clips: the generated briefs and the checkers' answers
    (goals.json, pens.json, fixes.rN.json, answers.json, prompt_pN.json, generated.json, the clip checker's prompt and
    answers). A few hundred kB a game: `highlights` tells hand edits from generated fields by generated.json, `gaps`
    goes on from answers.json, and a pipeline review reads what the checkers said without the session transcripts."""
    S = os.path.normpath(f"{W}/scratch")
    return {os.path.relpath(os.path.join(d, f), S) for k in SCRATCH_KEEP for d, _, fs in os.walk(os.path.join(S, k))
            for f in fs if f.lower().endswith((".md", ".json"))}   # paths under scratch/, os.sep-separated


def cmd_archive(a):
    """Keep a finished game's data so it can be re-solved later (as ~/hockey-work/2026-09-27-vs-rr): detections, OCR
    reads, tracks, segments, reviews, periods, results, rink, what a clip is cut again from (clip_args.json,
    clips_check.json, hand traces outside scratch/), why a span is there (hand_spans.txt), and the checkers' briefs
    and answers in scratch/ (_scratch_text). Drop what is big and can be downloaded or regenerated: the video and
    audio, crops, overview frames, the scoreboard frames, contact sheets and charts, and the rest of scratch/ (the
    reviewers' folders, the checkers' frames and zooms)."""
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
    S = os.path.normpath(f"{W}/scratch")
    keep = _scratch_text(W)
    kept = {k: [os.path.getsize(os.path.join(S, f)) for f in keep if f.split(os.sep)[0] == k] for k in SCRATCH_KEEP}
    drop += [os.path.join(d, f) for d, _, fs in os.walk(S) for f in fs
             if os.path.relpath(os.path.join(d, f), S) not in keep]
    for p in drop:
        if os.path.islink(p) or os.path.isfile(p):
            os.remove(p)
        elif os.path.isdir(p):
            shutil.rmtree(p)
    for d, _, _ in sorted(os.walk(S), key=lambda x: -len(x[0])):   # folders left empty go too
        if not os.listdir(d):
            os.rmdir(d)
    log(f"archived {W}: {before / 1e9:.1f} GB -> {_size(W) / 1e6:.0f} MB")
    print("kept from scratch/, the checkers' briefs and answers: " + (", ".join(
        f"{k}/ {len(v)} file(s), {sum(v) / 1e3:.0f} kB" for k, v in kept.items() if v) or "nothing (no checker wrote there)")
        + "; the rest of scratch/ dropped")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    dl = sub.add_parser("download"); dl.add_argument("url"); dl.add_argument("W")
    dl.add_argument("--cookies", metavar="BROWSER", help="yt-dlp's --cookies-from-browser, e.g. firefox (the user runs this)")
    f = sub.add_parser("fetch"); f.add_argument("url"); f.add_argument("W"); f.add_argument("--limit", type=float)
    f.add_argument("--team", help="whose game: a folder in teams/ (tk, bw, bt, df, y, r); default the work folder's, else tk")
    f.add_argument("--rink", help="camera geometry (see rink.py); default renton")
    f.add_argument("--jersey", help="our jersey that game (rink.JERSEYS); default light blue")
    f.add_argument("--bench", help="left or right: the side of the frame our bench is on (rink.py); default the "
                   "jersey's side where the rink's bench follows it (rink.bench_by_jersey), else the rink's usual one")
    j = sub.add_parser("jersey"); j.add_argument("W"); j.add_argument("name")
    s = sub.add_parser("skaters"); s.add_argument("W"); s.add_argument("T0", type=float); s.add_argument("T1", type=float)
    pr = sub.add_parser("prepare"); pr.add_argument("W")
    pr.add_argument("--force", action="store_true", help="prepare even where a period's net goes against both the "
                    "bench rule and the opening faceoff (setup_check.check_nets)")
    # goals, kills and highlights: the checkers' briefs, the kills from the sheet, highlights.json from the answers
    go = sub.add_parser("goals"); go.add_argument("W")
    go.add_argument("--brief", action="store_true", help="write the goal and penalty checkers' briefs (W/scratch/goals/prompt_*.md)")
    pk_ = sub.add_parser("pk"); pk_.add_argument("W")
    pk_.add_argument("--write", action="store_true", help="merge the kills into periods.json")
    pk_.add_argument("--rough", action="store_true", help="with --write, also the kills in periods without a board "
                     "clock read, whose start is only the earliest it can be")
    hl_ = sub.add_parser("highlights"); hl_.add_argument("W")
    hl_.add_argument("--write", action="store_true", help="write highlights.json and the checker's kills into periods.json")
    sub.add_parser("unknown").add_argument("W")
    sub.add_parser("archive").add_argument("W")
    sc = sub.add_parser("schedule"); sc.add_argument("W", nargs="?", help="a work folder (its team), or --team")
    sc.add_argument("--team", help="the team's slug when there is no work folder yet")
    sub.add_parser("scores").add_argument("--team", help="one team's games (default: every team)")
    sh_ = sub.add_parser("sheet"); sh_.add_argument("W", nargs="?", help="work folder (named <...>YYYY-MM-DD<...>)")
    sh_.add_argument("--team"); sh_.add_argument("--date", help="YYYY-MM-DD when the folder name lacks it")
    sh_.add_argument("--sn", help="SportNinja game id (the end of LADA's boxscoreLink)")
    sh_.add_argument("--lada", help="LADA game id, to look the SportNinja id up")
    ab = sub.add_parser("absent"); ab.add_argument("W"); ab.add_argument("numbers", type=int, nargs="*")
    ab.add_argument("--clear", action="store_true", help="forget the absent list")
    ab.add_argument("--suggest", action="store_true", help="table the evidence per player: sheet, LADA lines, reads, card rows")
    rv = sub.add_parser("review"); rv.add_argument("W")
    rv.add_argument("--opp", help="the opponents' look, e.g. 'white jerseys; they also wear #11 and #43'")
    rv.add_argument("--note", action="append", help="a sentence for every reviewer, e.g. a player's look (repeatable)")
    rv.add_argument("--chunk", type=int, help="sheets per reviewer (3)")
    rv.add_argument("--batch", type=int, help="chunks listed per launch (20), so that many reviewers run at once")
    ck = sub.add_parser("check"); ck.add_argument("W")
    ck.add_argument("--wait", type=int, nargs="?", const=540, metavar="SECONDS",
                    help="block until the last launch (W/review_todo.txt) is answered or SECONDS pass (540: one "
                         "10-minute foreground command), then print what is still open")
    fr = sub.add_parser("frames"); fr.add_argument("W"); fr.add_argument("out")
    fr.add_argument("--view", help="rink, left-net or right-net (rink.py views) instead of X0 X1 Y0 Y1 TILE_W COLS")
    fr.add_argument("--tile", type=int, help="tile width in px (1000 for the rink, 660 for a net)")
    fr.add_argument("--cols", type=int, help="tiles per row (2 for the rink, 3 for a net)")
    fr.add_argument("--range", type=float, nargs=3, metavar=("T0", "T1", "STEP"), help="times T0, T0+STEP, ... T1")
    fr.add_argument("rest", nargs="*", help="[X0 X1 Y0 Y1 TILE_W COLS] t1 t2 ...")
    c = sub.add_parser("clip"); c.add_argument("W"); c.add_argument("game_id"); c.add_argument("name")
    c.add_argument("t0"); c.add_argument("t1"); c.add_argument("poster"); c.add_argument("focus", nargs="?")
    c.add_argument("--net", choices=("for", "against"), help="a goal clip: close in on the net it went into at POSTER")
    c.add_argument("--replay-from", help="a goal clip's replay starts this many seconds before POSTER (4, or 1.5 s before --shot)")
    c.add_argument("--shot", metavar="T,X,Y", help="a goal clip: when the puck left the scorer's stick and where his skates were (source px), from the goal check")
    c.add_argument("--pass", dest="pass_", metavar="T,X,Y", help="a goal clip: when the puck left the passer's stick and where his skates were; the passer stays in the frame until then and the replay starts 2 s before it")
    c.add_argument("--tracks", metavar="TIDS|CSV[:TIDS]", help="follow these tracks instead of the labeled ones: 'TID,TID;TID' in the period's tracks_v1.csv (each player's, scorer first), or a tracks file of its own (run_period.py into a scratch folder, or t,x,y rows traced by hand)")
    c.add_argument("--dry-run", action="store_true", help="compute and check the camera's path and print it; cut nothing (no video needed)")
    cl = sub.add_parser("clips"); cl.add_argument("W"); cl.add_argument("game_id")
    cl.add_argument("--only", metavar="NAME,...", help="re-cut just these clips (highlights.json's names; penalty-97 takes every penalty-97-*)")
    cl.add_argument("--dry-run", action="store_true", help="compute and check every clip's camera path; cut nothing (no video needed)")
    cs = sub.add_parser("clipsheet"); cs.add_argument("mp4"); cs.add_argument("out")
    cs.add_argument("--W", help="a work folder: mark the shot, goal and pass from its clips_check.json entry for this clip")
    cs.add_argument("--mark", action="append", metavar="LABEL=SEC", help="frame the tile nearest this clip second (repeatable)")
    cs.add_argument("--step", type=float, default=1.0, help="seconds of clip between tiles (1)")
    cs.add_argument("--from", dest="from_", type=float, metavar="SEC"); cs.add_argument("--to", type=float, metavar="SEC")
    sub.add_parser("solve").add_argument("W")
    gp = sub.add_parser("gaps"); gp.add_argument("W")
    gp.add_argument("--apply", nargs="*", metavar="FIXES.json", help="merge checkers' fixes into periods.json (default: every scratch/gaps/*/fixes.json)")
    gp.add_argument("--chunk", type=int, default=6, help="windows per checker prompt (6)")
    gp.add_argument("--min-len", type=int, default=15, help="shortest window to list, in seconds (15)")
    # the gap checkers' tools: tracked boxes on frames, one piece over time
    fr.add_argument("--tracks", action="store_true", help="draw our tracked boxes with track id and the solver's label")
    fo = sub.add_parser("follow"); fo.add_argument("W"); fo.add_argument("out"); fo.add_argument("period", help="P1, P2, ...")
    fo.add_argument("tids", type=int, nargs="+", help="track ids (segs_final.csv's tid), one row each")
    fo.add_argument("--range", type=float, nargs=3, metavar=("T0", "T1", "STEP"), help="crops at T0, T0+STEP, ... T1 (default: the piece's span, ~10 crops)")
    p = sub.add_parser("publish"); p.add_argument("W"); p.add_argument("game_id")
    p.add_argument("--opponent", required=True)
    p.add_argument("--date"); p.add_argument("--title"); p.add_argument("--video")
    p.add_argument("--video-ends-early", action="store_true", help="recording stops before the final horn")
    # publish's eyebrow (built when not given), notes and page, then span
    p.add_argument("--eyebrow", help="the page's header line, 'Sun Sep 27, 2026 · 7:50 PM · Renton' (default: an earlier "
                   "publish's, else built from LADA's schedule, the video's title and the game sheet)")
    p.add_argument("--notes", action="append", help="one of the game's notes (repeatable); with --notes-file they "
                   "replace game.json's notes, which nothing on the site shows")
    p.add_argument("--notes-file", help="a text file of notes, a blank line between them")
    p.add_argument("--no-open", action="store_true", help="don't open the game page in the browser (a first publish "
                   "opens it)")
    p.add_argument("--open", action="store_true", help="open the game page on a republish too")
    spn = sub.add_parser("span"); spn.add_argument("W")
    spn.add_argument("kind", nargs="?", choices=("on", "off", "extra", "ps"))
    spn.add_argument("vals", nargs="*", help="PLAYER T0 T1 for on/off, T0 T1 for extra/ps (seconds of video)")
    spn.add_argument("--note", help="why: the line kept in W/hand_spans.txt")
    spn.add_argument("--list", action="store_true", help="print W/hand_spans.txt")
    a = ap.parse_args()
    # Git Bash sessions pass /c/Users/... and quoted ~ paths, which Windows Python can't open
    for k in PATH_ARGS:
        v = getattr(a, k, None)
        if isinstance(v, str) and v:   # strings only: frames --tracks is a flag
            setattr(a, k, norm_path(v))
        elif isinstance(v, list):
            setattr(a, k, [norm_path(x) for x in v])
    if sys.platform == "win32":   # keep Windows awake while this runs (caffeinate does it on the Mac)
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    if a.cmd in ("fetch", "sheet", "download") and a.W:   # sheet usually runs before fetch has made the folder
        os.makedirs(a.W, exist_ok=True)
    if a.cmd == "fetch":
        open(f"{a.W}/url.txt", "w").write(a.url)
    # the team, before anything imports roster.py: --team, else the one fetch stored, else the folder's name (before
    # fetch), else Turbo Kings
    cfg = f"{a.W}/full/rink.json" if getattr(a, "W", None) else ""
    team = getattr(a, "team", None) or (json.load(open(cfg)).get("team") if os.path.exists(cfg) else None) or \
        (team_of_folder(a.W) if getattr(a, "W", None) else None) or "tk"
    if not os.path.exists(f"{ROOT}/teams/{team}/roster.json"):
        sys.exit(f"unknown team {team!r}: no teams/{team}/roster.json")
    os.environ["TEAM"] = team
    # players marked absent (run_game.py absent) stay out of the roster for every step but the site build
    absent = json.load(open(cfg)).get("absent", []) if os.path.exists(cfg) else []
    os.environ["ROSTER_ABSENT"] = ",".join(str(n) for n in absent)
    {"fetch": cmd_fetch, "skaters": cmd_skaters, "prepare": cmd_prepare, "solve": cmd_solve, "goals": cmd_goals,
     "frames": cmd_frames, "clip": cmd_clip, "publish": cmd_publish, "unknown": cmd_unknown,
     "archive": cmd_archive, "jersey": cmd_jersey, "absent": cmd_absent, "review": cmd_review, "check": cmd_check,
     "schedule": cmd_schedule, "sheet": cmd_sheet, "scores": cmd_scores, "gaps": cmd_gaps, "download": cmd_download,
     "span": cmd_span, "follow": cmd_follow, "pk": cmd_pk, "highlights": cmd_highlights, "clips": cmd_clips,
     "clipsheet": cmd_clipsheet}[a.cmd](a)
