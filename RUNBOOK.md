# Runbook: processing a new game

Normally you run `/process-game <link>` in Claude Code, and `pipeline/run_game.py`'s subcommands do each step (its
docstring lists them in the order a game runs). This page is the manual version, useful when something needs fixing;
the skill (`.claude/skills/process-game/`) has the order of operations, the checks and the lessons per rink.

Written for Claude Code (or anyone patient). Commands assume the repo root as the working directory,
`PY` = a Python ≥ 3.10 with `pipeline/requirements.txt` installed, and `W` = a per-game work folder
**outside** the repo (the video and crops take ~5 GB).

```sh
# one-time: macOS system python is 3.9, which is too old for current yt-dlp
uv venv --python 3.12 ~/.venvs/hockey && uv pip install --python ~/.venvs/hockey/bin/python -r pipeline/requirements.txt
PY=~/.venvs/hockey/bin/python
W=~/hockey-work/2026-10-04-vs-XX      # other teams than Turbo Kings: bw-2026-09-13-vs-db
export TEAM=tk                        # the team whose game it is: a folder in teams/ (tk, bw, bt, df, y, r)
```

Each team's roster, opponents and published games live in `teams/<slug>/` (`roster.json`, `opponents.json`,
`games/`), and its site in `docs/<slug>/`. The scripts read the team from `TEAM`; `run_game.py` records it in
`$W/full/rink.json` (`fetch --team`), takes it from the folder's name before that, and sets it for everything it runs.

On a Windows PC with an NVIDIA GPU, detection runs several times faster (CUDA; `process.py` picks it up by
itself). Install Git for Windows (Claude Code's Bash tool needs its bash, and these commands are sh), the NVIDIA
driver and Claude Code, then run `powershell -ExecutionPolicy Bypass -File pipeline\setup_env.ps1` once: it makes
the same environment with PyTorch for CUDA, sets `PYTHONUTF8=1`, and checks that symlinks are allowed (turn on
Developer Mode if not). There `PY=~/.venvs/hockey/Scripts/python.exe`; no `caffeinate` is needed, because
`run_game.py` keeps Windows awake while it runs. `WINDOWS.md` has the setup step by step. `run_game.py` accepts Git
Bash's `/c/Users/...` paths.

`run_game.py fetch "<url>" $W --team <slug> --rink <class> [--jersey white] [--bench left|right]` does steps 1 to 5
in one go (24 to 38 minutes on the PC on the 13 fetches since Nov 2) and resumes after any interruption.

## 1. Download (1.5 to 4 min on the PC)

```sh
mkdir -p $W/full
$PY -m yt_dlp -f 313 -o "$W/video.webm" "https://youtu.be/VIDEO_ID"   # 313 = 2160p VP9; fetch takes the best webm there is
$PY pipeline/run_game.py download "https://youtu.be/VIDEO_ID" $W --cookies firefox   # the same, plus the audio and
#   title, with the browser's YouTube cookies when YouTube answers "Sign in to confirm you're not a bot" (the user
#   runs this line; fetch then skips the downloads)
```

YouTube's bot block refuses every client alike. It has cleared by itself after 25 and 50 minutes (Oct 19) and not in
three hours (Beerteam's Oct 25 video, Oct 31, when three of four games needed cookies); none of the 13 fetches since
Nov 2 met it. During a block oEmbed still answers with the title (`curl "https://www.youtube.com/oembed?url=<url>&format=json"`),
and a background loop that runs `$PY -m yt_dlp -F <url>` every 5 minutes and starts fetch once format 313 is listed
gets through without cookies. Reading the browser's cookies is the user's to run.

Every rink in `rink.py` has its usual frame `size` (Renton's new camera 3840x1920, Kirkland 3840x1536), and `fetch`
scales a smaller video of the same view up to it (`run_game.fit_size`, nvenc's p1 preset on the PC: 5 to 7 minutes).
The original stays as `video_<W>x<H>.webm`. Before that encode, fetch calibrates the far boards on a frame scaled to
the rink's size and compares the curve with the rink's usual one (`ref_boards` in `rink.py`): at Kirkland and
Snoqualmie B (`reframe`) a late upload sitting low under a black band is shifted into place in the same encode;
elsewhere the offset is logged, and at Renton the log names the class that fits or the turn onto the class given
(`references/rinks.md`, "A camera that moved"). A fetch run again keeps a `periods.json` you have edited and writes
its proposal to `periods.proposed.json`.

## 2. Calibrate the far boards (1 min)

```sh
FF=$($PY -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
$FF -loglevel error -ss 600 -i $W/video.webm -frames:v 1 $W/frame600.png
echo '{"team": "tk", "rink": "renton2nov"}' > $W/full/rink.json   # without "rink" a folder is `renton`, the old camera (to Oct 4)
# Renton's camera since Nov 7, home in white (white sits right there): {"rink": "renton2nov", "jersey": "white", "bench": "right"}
# Snoqualmie A (a 3840x1536 strip; white sits left, light blue right): {"rink": "snoqualmie", "jersey": "white", "bench": "left"}
# Snoqualmie B (the camera's whole fisheye frame, 3824x2160): {"rink": "snoqualmie2", "jersey": "white", "bench": "left"}
# Kirkland (fisheye, benches behind the far boards; no jersey rule, look): {"rink": "kirkland", "jersey": "white", "bench": "right"}
$PY pipeline/boards.py $W/frame600.png $W/full     # writes boards_poly.npy
```

The camera geometry per rink (detection crop, board band, ice area, benches, boxes, nets, frame views) lives in
`pipeline/rink.py`; `references/rinks.md` has a table of the classes. Fetch sets `"bench"` from the jersey where the
bench follows it (Renton and Snoqualmie) and writes `frame600_small.jpg`, `bench_left.jpg` and `bench_right.jpg` to
check it on: our jerseys sit at our bench. Check the fitted boards line on the frame to its edges. Yellow lettering
above the boards pulls the fit up; a rink's `board_lowest = True` keeps only the lowest yellow run in each column
(Kirkland). If the camera moved, or it's a new rink, adjust or add a class before detecting: the detection crop
(`crop_top`) must include the heads of players standing at the far boards.

Our players are told apart by jersey colour (`JERSEYS` in `rink.py`: light blue by default, white with blue numbers,
and tests against particular opponents, `rinks.md`). Detection only saves crops of players who pass the jersey's
crop test, so set the jersey before detecting. If it was wrong, `run_game.py jersey $W white` fixes it afterwards:
`crops.py` cuts the missing crops from the video using the detections already in `dets.csv`, then OCR reads them,
and a bench set from the jersey moves with it. The bench (`"bench"` in `rink.json`) decides which track ends count as
line changes.

## 3. Detect (~80 min on an M3; 12 to 17 on the PC)

```sh
nohup $PY pipeline/process.py $W/video.webm $W/full 8 > $W/full/log.txt 2>&1 &
```

- Progress lines go to `log.txt`; it ends with `DONE`.
- If it slows down badly (memory grows, swap), kill it, delete rows of the last frame from `dets.csv`,
  and restart from that time: `process.py $W/video.webm $W/full 8 <last t>` (frame numbers stay global).
- `process.py` is three processes since Nov 2 (the pipe reader, the model, the post-processing) over a ring of
  frames in shared memory; a kill of the main one takes the other two with it within 5 s. On a full game it runs at
  31 to 44 frames a second (by the height of the rink's detection band), as before Nov 2.
- On the Mac don't run OCR at the same time: it starves the video decoder. On the PC `fetch` starts the four OCR
  workers alongside detection (`run_game.ocr_alongside`): they finish 0.1 to 2.6 minutes after it under 160k crops,
  6 to 9 minutes after with 204k to 262k (white jerseys).
- `fetch` also scans the scoreboard beside detection (`scoreboard.py`, at below-normal priority). On the PC it takes
  18 to 28 minutes there and finishes last on every fetch, 5 to 12 minutes after detection (2.6 to 4.7 run alone).

## 4. Read numbers (10–15 min)

```sh
for k in 0 1 2 3; do PYTHONHASHSEED=0 $PY pipeline/ocr_worker.py $W/full 1000000000 1 $k 4 > $W/full/ocr_$k.log 2>&1 & done
```

## 5. Find the periods and the nets

The arena scoreboard is in frame at every rink: `pipeline/scoreboard.py $W` keeps its brightest frame per second
(the LEDs flicker) and `pipeline/scoreboard.py $W out.jpg t1 t2 ...` sheets it at any seconds (`$W/sb.jpg` is the
board every 60 s). It shows the period clock, the score, the shots, and each penalty with the player's number and
time left. `pipeline/clock.py $W` reads the period clock off every second of the board (`clock_box` in `rink.py`)
into `$W/clock.json`: each period from the last second at 18:00 to the first 00.0, and the video second of every
clock time, which `sheet`, `goals`, `pk` and the briefs use. Fetch runs it, logs per period whether the clock ran
out, warns where a clock edge and the empty ice differ by over 100 s, and writes `periods.json` (from the empty ice
when the clock gives none, which it logs); check it on
`$W/clock_check.jpg` (`clock.py --write` puts the clock's periods into `periods.json` by hand). Where the clock doesn't
give three periods, read them off `sb.jpg` (00.0, a 1:00 intermission countdown, then 18:00).

```sh
$PY pipeline/ovsheet.py $W/full/ov $W/ov.jpg 0 4000 30 3     # the 10-second overview frames, to see the breaks
```

Each period's `net` is our goalie's (`nets` in `pipeline/rink.py`). Fetch proposes it by three reads: our bench's end
in the 1st, switching each period (141 of 141 published periods); the half our skaters line up in at the opening
faceoff; our jersey in each crease. `prepare` stops on a net that goes against both the first two (`--force` once
you have seen it is right).

`run_game.py sheet $W` prints SportNinja's game sheet (score, shots, goals with scorers, penalties, who played) and
writes `$W/sheet.json`. Publish takes the score (`sheet_score`) and the shots per period from it (`shots_source:
sheet`). `pipeline/shots.py $W --us home|guest` reads the shots off the board into `$W/shots.json` instead (its OCR
is wrong at most rinks); check it against `$W/shots_check.jpg`, fix the per-period counts and set `"checked": true`
so publish prefers the board's.

## 6. Goals, penalties and spans

```sh
$PY pipeline/run_game.py goals $W --brief        # the goal and penalty checkers' briefs, W/scratch/goals/prompt_*.md
$PY pipeline/run_game.py pk $W --write           # our penalty kills from the sheet and the clock, into periods.json
#   (not a ROUGH one, in a period without a clock read, unless --rough; not one the penalty checker has answered)
$PY pipeline/run_game.py highlights $W --write   # once the checkers have answered: highlights.json, their kills
$PY pipeline/run_game.py span $W ps 3724 3765 --note "penalty shot against: all ours at the bench"
$PY pipeline/run_game.py span $W extra 3666 3754 --note "goalie pulled"
$PY pipeline/run_game.py span $W off 18 2410 2442 --note "sat at the bench, his track ran on"   # on|off PLAYER T0 T1
$PY pipeline/run_game.py span $W --list          # every hand-made span and why (W/hand_spans.txt)
```

Each brief is one subagent's whole job; the answers land in `W/scratch/goals/pN/goals.json` and `pens/pens.json`.
`highlights` prints what doesn't add up before `--write`. `periods.json` per period then holds `pk` (`{start, end,
player}`), `ps` and `extra` (`{start, end}`) and the `on`/`off` spans (`{start, end, player}`); `span` is the hand
writer for the last four, so each has a logged reason.

## 7. Track each period

```sh
$PY pipeline/run_game.py unknown $W              # numbers read hundreds of times that aren't on the roster
$PY pipeline/run_game.py absent $W 3 15          # roster numbers that didn't play (--suggest: the evidence; --clear)
$PY pipeline/run_game.py prepare $W              # the bench and nets checks, then per period:
#   run_period.py $W/full $W/p1 <P1 start> <P1 end> <net x>; review_sheets.py $W/p1 $W/rev_p1 8;
#   roster_card.py $W/p1 $W/rev_p1/roster_card.jpg 8
```

Finish OCR (step 4) before this step, and never re-run `run_period.py` for a period after its review (step 8) has
started: review rows point at segment numbers, and a new segmentation scrambles them. Look at `roster_card.jpg`:
every row should be one player. The card only has roster numbers, so add new or sub players `unknown` finds to the
team's `roster.json` first (team members under `skaters`, subs under `subs`); other teams' jerseys are opponents.
The absent list is stored in `$W/full/rink.json` (by hand, `ROSTER_ABSENT=3,15` in the environment of every
script): a number that didn't play soaks up partial reads of other numbers. Don't edit `roster.json` for that. A
change to it after prepare means preparing again before the review starts; once the review has started, solve alone
picks it up.

## 8. Visual review (Claude subagents)

```sh
$PY pipeline/run_game.py review $W [--opp "white jerseys"] [--note "#55 LISENKO: a ponytail hides her number"]
$PY pipeline/run_game.py check $W --wait   # up to 540 s until the batch is answered (Bash timeout 600000 ms)
```

`review` fills `pipeline/review_prompt.md` once per chunk of 3 sheets into `$W/rev_pN/prompt_cNN.md` (roster minus
absent players, jersey, goalie, empty roster-card rows, the opponents' look, your notes) and lists up to 20 to launch
(`$W/review_todo.txt`). Each is one general-purpose subagent told to read its prompt file and do what it says; all of
a batch at once. Each reviewer writes one `review_sNNN.txt` per sheet, CSV with the header
`row_id,player,confidence,switch_time,player2,confidence2,note`. `check` also lists numbers reviewers gave that are
off the roster or absent. The skill's `references/review.md` has the relaunch and re-check protocol and
`review_zfix.txt`, your own labels, which override the reviewers'.

## 9. Solve and check

```sh
$PY pipeline/run_game.py solve $W   # per period run2.py and gantt.py, then final_stats.py, stoppages.py, the lineup check
# by hand: run2.py $W/p1 $W/rev_p1 <P1 end> '[[<P1 start>,<P1 end>]]' '[[<pk start>,<pk end>,4,<player>]]'
#          gantt.py $W/p1/shifts_final.csv $W/p1/segs_final.csv $W/gantt_p1.png <P1 start> <P1 end>
$PY pipeline/run_game.py gaps $W           # one by-eye checker brief per period, W/scratch/gaps/prompt_pN.md
$PY pipeline/run_game.py gaps $W --apply   # their fixes.json into periods.json as on/off spans; then solve again
```

In the Gantt chart the bottom panel should sit at 5 (4 on a PK). Long stretches at 4 or 6 mean a missed player, a
penalty, or a bad label. `solve` passes `periods.json`'s spans to `run2.py` as `[start, end, 4, player]` (a kill),
`[start, end, 5, player]` (`off`), `[start, end, 5, player, "on"]` (`on`) and `[start, end, 6]` (`extra`), and a `ps`
as a gap in the live spans. It prints each period's shift seconds against 5 × its length and the lineup check: who
was on in each gap and how much of it was live play, flagged goals, shifts of 5+ minutes and ice-time collapses.
`gaps` writes a brief per period from `pipeline/gap_prompt.md` for those items and the long pieces in our bench zone;
`--apply` names the items left unanswered and turns leads into the next round's windows.

## 10. Play time and clips

`run_game.py solve` runs `pipeline/stoppages.py`, which adds a `play` column to `shifts_all.csv` and writes
`stoppages.json`. After the last solve:

```sh
$PY pipeline/run_game.py clips $W <game-id> --dry-run    # every clip in highlights.json: the camera path, checked
$PY pipeline/run_game.py clips $W <game-id>              # cut into the team site's games/<id>/clips/, contact sheets
$PY pipeline/run_game.py clipsheet <clip.mp4> out.jpg --from 20 --to 26 --step 0.25    # any stretch of a clip, tiled
```

`$W/clip_args.json` overrides one clip's arguments (`t0`, `t1`, `focus`, `shot`, `pass`, `replay_from`, `tracks`);
`run_game.py clip` cuts a single clip by hand. `clips` writes `W/scratch/clips/prompt.md` for the subagent that
checks every contact sheet; a clip that fails doesn't stop the rest, and `clips` exits 1 with the `--only` line that
retries it. `run_game.py frames $W out.jpg --view rink|left-net|right-net|bench --range T0 T1 STEP`
renders frames (`--tracks` draws our tracked boxes); `follow` crops one tracked piece over time.

## 11. Publish

```sh
$PY pipeline/run_game.py publish $W <date>-vs-<opp> --opponent <OPP> --notes-file $W/notes.txt
git add -A && git commit -m "Add <date> vs <opp>" && git push
```

Publish copies `$W/shifts_all.csv` to `teams/$TEAM/games/<date>-vs-<opp>/shifts.csv` and writes its `game.json`:
periods, nets, penalty kills, the video link (`--video` for a local recording), the header line (`--eyebrow`, else
the time from the video's title or LADA's schedule and the rink from the schedule, the title or the sheet),
stoppages, `highlights.json` without its working keys, the sheet's score and shots, the LADA id, time in offence and
defence (`zones.py`), the ice maps (`ice.py`, where the camera is calibrated), the fun stats and pipeline counts, and
the notes (in `game.json` only). A republish keeps the hand-written fields. Then it rebuilds every team's site
(`build_site.py`; unset `TEAM` for every team), prints the table and the page's `file:///` address, and opens the page
on a first publish (`--open` on a republish, `--no-open` never). Don't make a `game.json` by copying another game's:
its score, ids, highlights, shots and ice maps would come along, and the site shows the copied score.

GitHub Pages redeploys in 4 to 5 minutes. Then `run_game.py archive $W` drops the video, crops and sheets and keeps
the game's data (~100 MB, the scoreboard frames as JPEGs, the hand spans, the clips' arguments and the checkers'
briefs and answers among it), so it can be re-solved later. Keep every game's archive: `pipeline/regress.py`
re-solves all of them and diffs each against its published `shifts.csv`, which is how a change to the solve is
checked before any site is rebuilt.
