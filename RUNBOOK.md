# Runbook: processing a new game

Normally you run `/process-game <link>` in Claude Code, and `pipeline/run_game.py` chains these steps
(`fetch`, `sheet`, `absent`, `prepare`, `review`, `check`, `solve`, `gaps`, `publish`). This page is the manual version, useful when
something needs fixing; the skill (`.claude/skills/process-game/`) has the checks and the lessons per rink.

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
`games/`), and its site in `docs/<slug>/`. The scripts read the team from `TEAM`;
`run_game.py` records it in `$W/full/rink.json` (`fetch --team`) and sets it for everything it runs.

On a Windows PC with an NVIDIA GPU, detection runs several times faster (CUDA; `process.py` picks it up by
itself). Install Git for Windows (Claude Code's Bash tool needs its bash, and these commands are sh), the NVIDIA
driver and Claude Code, then run `powershell -ExecutionPolicy Bypass -File pipeline\setup_env.ps1` once: it makes
the same environment with PyTorch for CUDA, sets `PYTHONUTF8=1`, and checks that symlinks are allowed (turn on
Developer Mode if not). There `PY=~/.venvs/hockey/Scripts/python.exe`; no `caffeinate` is needed, because
`run_game.py` keeps Windows awake while it runs. `WINDOWS.md` has the setup step by step.

## 1. Download (5 min)

```sh
mkdir -p $W/full
$PY -m yt_dlp -f 313 -o "$W/video.webm" "https://youtu.be/VIDEO_ID"   # 313 = 2160p VP9; the pipeline expects 3840 px wide
```

Every rink in `rink.py` has its usual frame `size` (Renton 3840x1702, Kirkland 3840x1536), and `fetch` scales a
smaller video of the same view up to it (`run_game.fit_size`; Y's Sep 14 game came as 3600x1440, BW's Oct 3 at
Renton as 3600x1596). The original stays as `video_<W>x<H>.webm`.

## 2. Calibrate the far boards (1 min)

```sh
FF=$($PY -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
$FF -loglevel error -ss 600 -i $W/video.webm -frames:v 1 $W/frame600.png
echo '{"team": "tk", "rink": "snoqualmie"}' > $W/full/rink.json   # rink: not for Renton, the default
# Snoqualmie A (a 3840x1536 strip; away bench right, home left): {"rink": "snoqualmie", "jersey": "white", "bench": "left"}
# Snoqualmie B (the camera's whole fisheye frame, 3824x2160; home bench left):
#   {"rink": "snoqualmie2", "jersey": "white", "bench": "left"}
# home games (white jerseys, right bench at Renton): {"rink": "renton", "jersey": "white", "bench": "right"}
# Kirkland (fisheye, benches behind the far boards, home right): {"rink": "kirkland", "jersey": "white", "bench": "right"}
$PY pipeline/boards.py $W/frame600.png $W/full     # writes boards_poly.npy
```

The camera geometry per rink (detection crop, board band, ice area, our bench, nets, frame views) lives in `pipeline/rink.py`.
Check the fitted boards line on the frame all the way to its edges, and that the benches are where the rink's class
expects them, by viewing a crop of the frame. Yellow lettering on signs above the boards pulls the fit up; a rink's
`board_lowest = True` makes `boards.py` keep only the lowest yellow run in each column (Kirkland). If the camera moved, or it's a new rink, adjust or add a class there before detecting: the
detection crop (`crop_top`) must include the heads of players standing at the far boards.

Our players are told apart by jersey colour (`JERSEYS` in `rink.py`: light blue by default, or white with blue
numbers). Against white jerseys with big sky-blue panels (Teamy McTeamface) half of theirs pass for light blue; use
`light blue vs sky blue`, which also checks the hue (`bhue` in `dets.csv`: ours ~113, theirs ~107 at Kirkland). Detection only saves crops of players in that jersey, so set it before detecting. The bench we had
(`"bench": "right"` mirrors Renton's left bench about center ice) decides which track ends count as line changes. If it was wrong,
`run_game.py jersey $W white` fixes it afterwards: `crops.py` cuts the missing crops from the video using the
detections already in `dets.csv`, then OCR reads them.

## 3. Detect (~80 min on an M3)

```sh
nohup $PY pipeline/process.py $W/video.webm $W/full 8 > $W/full/log.txt 2>&1 &
```

- Progress lines go to `log.txt`; it ends with `DONE`.
- If it slows down badly (memory grows, swap), kill it, delete rows of the last frame from `dets.csv`,
  and restart from that time: `process.py $W/video.webm $W/full 8 <last t>` (frame numbers stay global).
- Don't run OCR at the same time: it starves the video decoder.

## 4. Read numbers (10–15 min)

```sh
for k in 0 1 2 3; do PYTHONHASHSEED=0 $PY pipeline/ocr_worker.py $W/full 1000000000 1 $k 4 > $W/full/ocr_$k.log 2>&1 & done
```

## 5. Find the periods

The arena scoreboard is in frame at every rink: `pipeline/scoreboard.py $W` keeps its brightest frame per second
(the LEDs flicker; `run_game.py fetch` does this pass alongside detection and writes `$W/sb.jpg`, the board every 60 s), and
`pipeline/scoreboard.py $W out.jpg t1 t2 ...` sheets it at any seconds. It shows the period clock, the score, the
shots, and each penalty with the player's number and time left, so periods, goals and penalties come from it; don't
ask the team about penalties. Check which team each penalty belongs to by who skates into a penalty box:
scorekeepers have put penalties on the wrong panel. `pipeline/clock.py $W` reads the period clock off every second
of the board (`clock_box` in `rink.py`) into `$W/clock.json`: each period from the last second at 18:00 to the first
00.0, and the video second of every clock time, which `run_game.py sheet` and `goals` use for the game sheet's goals
and penalties. Fetch runs it and proposes the periods from it; check them on `$W/clock_check.jpg` (`--write` puts
the clock's periods into `periods.json` by hand). Where the clock doesn't give three periods, take them from the clock
by eye (00.0, a 1:00 intermission countdown, then 18:00). A penalty carried over an intermission is a penalty kill
in both periods.

```sh
$PY pipeline/ovsheet.py $W/full/ov $W/ov.jpg 0 4000 30 3     # the 10-second overview frames, to see the breaks
```

Breaks show the ice empty with both teams at the benches for about a minute. Our goalie switches ends each
period. Net x: see `nets` in `pipeline/rink.py` (Renton ≈ 540 left, ≈ 3245 right).
Publish takes the game sheet's shots per period from `sheet.json` (`shots_source: sheet` in game.json).
`pipeline/shots.py $W --us home|guest` reads them off the board into `$W/shots.json` instead (its OCR is wrong at
most rinks); check it against `$W/shots_check.jpg`, fix the per-period counts, and set `"checked": true` so publish
prefers the board's.
`run_game.py sheet $W` prints SportNinja's game sheet (score, shots, goals with scorers, penalties, who played) and
writes `$W/sheet.json`; `run_game.py goals` then shows each goal's video time from the period clock (`clock.json`).

## 6. Track each period

```sh
$PY pipeline/run_period.py $W/full $W/p1 <P1 start> <P1 end> <net x>
$PY pipeline/review_sheets.py $W/p1 $W/rev_p1 8
$PY pipeline/roster_card.py $W/p1 $W/rev_p1/roster_card.jpg 8
```

Repeat for p2 and p3. Finish OCR (step 4) before this step, and never re-run `run_period.py` for a period
after its review (step 7) has started: review rows point at segment numbers, and a new segmentation scrambles
them. Look at `roster_card.jpg`. Every row should be one player. The card only has roster numbers, so run
`run_game.py unknown $W` before tracking to find new or sub players (numbers read hundreds of times that aren't
in the team's `roster.json`, with a crop sheet each): add ours to it, team members under `skaters` and subs under
`subs` (ask which); other teams' jerseys are opponents. Roster numbers that didn't play are marked with
`run_game.py absent $W 3 15 ...` (stored in `$W/full/rink.json`; by hand, `ROSTER_ABSENT=3,15` in the environment
of every script; `absent $W --suggest` tables the evidence per player): a number that didn't play soaks up partial reads of other numbers. Don't edit `roster.json` for
that.

## 7. Visual review (Claude subagents, ~15 min in parallel)

```sh
$PY pipeline/run_game.py review $W [--opp "white jerseys"] [--note "#55 LISENKO: a ponytail hides her number"]
$PY pipeline/run_game.py check $W        # afterwards: every manifest row answered?
```

`review` fills `pipeline/review_prompt.md` once per chunk of 3 sheets into `$W/rev_pN/prompt_cNN.md` (roster
minus absent players, jersey, goalie, empty roster-card rows, the opponents' look, your notes) and prints which
chunks are still to do. Each chunk is one general-purpose subagent told to read its prompt file and do what it says;
about six at a time. Each reviewer writes one `review_sNNN.txt` per sheet, CSV with the header
`row_id,player,confidence,switch_time,player2,confidence2,note`. The skill's `references/review.md` has the
relaunch and re-check protocol.

## 8. Solve and check

```sh
$PY pipeline/run2.py $W/p1 $W/rev_p1 <P1 end> '[[<P1 start>,<P1 end>]]'
$PY pipeline/run2.py $W/p3 $W/rev_p3 <P3 end> '[[<P3 start>,<P3 end>]]' '[[<pk start>,<pk end>,4]]'  # with a penalty kill
$PY pipeline/gantt.py $W/p1/shifts_final.csv $W/p1/segs_final.csv $W/gantt_p1.png <P1 start> <P1 end>
```

In the Gantt chart the bottom panel should sit at 5 (4 on a PK). Long stretches at 4 or 6 mean a missed
player, a penalty, or a bad label: inspect with crop sheets before trusting the numbers. `run_game.py solve` lists
them (and goals without 5 of us on the ice) as a lineup check. Labels you decide by hand go in
`$W/rev_pN/review_zfix.txt` (same CSV), which overrides the reviewers' "?" answers. A player you saw go off
whose shift runs on (his track ends mid-ice) goes in that period's `"off"` list in `periods.json`
(`{"start", "end", "player"}`): `run_game.py solve` passes it to `run2.py` as `[start, end, 5, player]`; a player seen on the ice whose track was
lost goes in the period's `"on"` list the same way (`[start, end, 5, player, "on"]`). `solve` also prints each period's shift
seconds against 5 × its length, and the lineup check names who was on the ice in each gap and how much of it was
live play. `run_game.py gaps $W` writes one by-eye check brief per period for those gaps
(`$W/scratch/gaps/prompt_pN.md`, filled from `pipeline/gap_prompt.md`: the windows, the segments behind them, the
known events, the bench and box), each one subagent's job; `gaps $W --apply` merges their `fixes.json` into
`periods.json` as on/off spans.

## 9. Play time and highlights

`run_game.py solve` runs `pipeline/stoppages.py`, which adds a `play` column to `shifts_all.csv` and writes
`stoppages.json`. For highlights: `run_game.py goals` lists candidate goals, `run_game.py frames --view rink|left-net|right-net` renders frames
to check them (`--range T0 T1 STEP`, or the crop by hand), and `run_game.py clip` cuts a zoomed clip into the team
site's `games/<id>/clips/` (last argument: an x position or `#N` to follow player N). List the clips in
`$W/highlights.json`, with the scoresheet's `scorer` and `assists` so the lineup check can verify them; see the
skill's `references/highlights.md` for the format.

## 10. Publish

```sh
(cd $W && $PY $OLDPWD/pipeline/final_stats.py p1:P1 p2:P2 p3:P3)    # writes $W/shifts_all.csv, prints the table
G=teams/$TEAM/games/<date>-vs-<opp>
mkdir -p $G && cp $W/shifts_all.csv $G/shifts.csv
# write $G/game.json (copy the previous game's and edit periods, video, PKs, notes).
# Optional extras for the Fun stats section: "fun": {"name_reads": {number: count}} from load_reads()'s
# name reads, and "pipeline": {"detections", "crops", "reads", "reviewed"} counts from this run.
$PY pipeline/zones.py $W $G/game.json   # time in offence/defence: add as "zones" in game.json
$PY pipeline/build_site.py              # this team's site, with its trends.html (unset TEAM: every team)
git add -A && git commit -m "Add <date> vs <opp>" && git push
```

GitHub Pages redeploys in about a minute. Then `run_game.py archive $W` drops the video, crops and sheets and keeps
the game's data (~100 MB, the scoreboard frames as JPEGs among it), so it can be re-solved later. Keep every game's
archive: `pipeline/regress.py` re-solves all of them and diffs each against its published `shifts.csv`, which is how
a change to the solve is checked before any site is rebuilt.
