# LADA Analytics

Shift sheets for LADA's rec hockey teams: shifts, ice time and average shift length for every skater, measured from the wide-cut game video on YouTube.

| Team | Folder | Site |
|---|---|---|
| LADA Turbo Kings (LADA team 24) | `teams/tk/` | https://kondrat52.github.io/lada-analytics/tk/ |
| LADA Blue Wings (LADA team 10) | `teams/bw/` | https://kondrat52.github.io/lada-analytics/bw/ |
| LADA Beerteam (LADA team 5) | `teams/bt/` | https://kondrat52.github.io/lada-analytics/bt/ |
| LADA Doofers (LADA team 17) | `teams/df/` | https://kondrat52.github.io/lada-analytics/df/ |
| LADA Y (LADA team 20) | `teams/y/` | https://kondrat52.github.io/lada-analytics/y/ |
| LADA R (LADA team 2) | `teams/r/` | https://kondrat52.github.io/lada-analytics/r/ |

## What's here

| Path | What it is |
|---|---|
| `docs/` | The published sites (GitHub Pages): each team's in `docs/<slug>/`, with game pages, a trends page (`trends.html`) and a JSON feed in `api/`, and a list of the teams at the root. Generated; don't edit by hand. |
| `API.md` | The JSON feed for apps (e.g. the LADA app): URLs, fields, conventions. |
| `teams/<slug>/games/<date>-vs-<opp>/` | One folder per game: `game.json` (periods, penalty kills, video link, notes) and `shifts.csv` (one row per shift). |
| `teams/<slug>/roster.json` | Jersey number → surname, LADA player ids, team name, LADA team id and where its site goes. Add new players here. |
| `teams/<slug>/opponents.json` | Opponent code → full name. |
| `teams/<slug>/lada_games.json` | The team's games as LADA's API has shown them (ids, home/away, rink, lines, scores); the pipeline keeps it current and takes each game's LADA id from it. |
| `pipeline/` | The scripts that turn a game video into `shifts.csv`, and `build_site.py`, which renders `docs/`. They work on one team at a time, picked by `TEAM` (`tk` unless set). `regress.py` re-solves every archived game and diffs the published sheets, for checking a pipeline change. |
| `RUNBOOK.md` | The manual steps behind the skill, for debugging or running by hand. |
| `WINDOWS.md`, `setup_windows.ps1` | Setting up a Windows PC with an NVIDIA GPU to run the pipeline (one command). |
| `.claude/skills/process-game/` | The Claude Code skill for the weekly run. |

## Adding a game

The weekly run is driven by Claude Code. Open this repo and run the project skill:

> /process-game https://youtu.be/XXXXXXXXXXX vs RR

for Turbo Kings, or name the team: `/process-game https://youtu.be/XXXXXXXXXXX bw vs DB`.

The skill (`.claude/skills/process-game/SKILL.md`, with its `references/`) reads the SportNinja scoresheet if you
give it one, asks for the opponent and any new players, finds periods, goals, penalties and shots from the arena
scoreboard and the video, then runs `pipeline/run_game.py` (fetch → absent → prepare → review → solve → publish)
and asks before pushing. Only the score confirmation and the push wait for you.

It takes two to four hours of session time on the Windows PC (fetch 25–45 minutes when YouTube serves the video,
prepare and review 15–25, the by-eye lineup checks 20–70, then goals, clips and publish 10–30), or a few hours more
on an M-series Mac, where detection alone is about two hours. YouTube's bot block adds anything from nothing to
hours: three of the four games fetched on Oct 31 needed the user's browser cookies (`run_game.py download
--cookies firefox`, which the user runs), and one waited nearly three hours for the block to lift. The Nov 2
changes to detection and OCR (TODO 1–3) should take about 10 minutes off a fetch; they are measured on a slice so
far, and the first full fetch will tell.

On a Windows PC with an NVIDIA GPU, detection runs on CUDA and should be much faster. To set one up, run this in
PowerShell; `WINDOWS.md` has the details and the steps by hand:

```powershell
irm https://raw.githubusercontent.com/kondrat52/lada-analytics/main/setup_windows.ps1 | iex
```

To rebuild the sites after editing a game's files or a roster (`TEAM=bw` for one team only):

```sh
python pipeline/build_site.py
```

## Adding a team

1. `teams/<slug>/roster.json`: copy another team's, empty its `skaters`, `subs`, `goalies` and `lada_player_ids`
   (`{}`), and change the team name, `team_short`, `lada_team_id` (LADA's public `https://api.ladaseattle.com/api/v1/Team/<id>` gives a team's name)
   and `site_url` (`https://kondrat52.github.io/lada-analytics/<slug>/`). `teams/<slug>/opponents.json`: `{}`.
2. Players and LADA player ids: `python pipeline/lada_ids.py --write <slug>` (several slugs at once is fine). It signs
   in to LADA as you (LADA has to show you the team's roster) and fills in `skaters`, `subs` (LADA's Sub status),
   `goalies` (LADA's Goalie position) and `lada_player_ids`; the surname is the last word of LADA's name, so check
   them against the jerseys. It never changes what's already there. A spare who isn't on LADA's roster goes under
   `subs` by hand (the team's SportNinja roster has them; screenshots work). A player LADA lists under another number
   than his jersey's (Y's #87 Beregovoy is #67 on LADA) goes under his jersey number, with `"lada_numbers": {"87": 67}`
   so `lada_ids.py` matches him and doesn't add LADA's number. A player who wears two numbers (Beregovoy wears 67
   on the white jersey) is under both, with the same LADA id, and `"aliases": {"87": 67}` lists him once, under 67,
   on the season table, trends page and feed. Without `--write` it only compares.
3. `python pipeline/build_site.py`: the team gets its site, listed at the root, and its feed (empty until the first
   game) right away.
4. Process a game with `--team <slug>`. Check the jerseys and benches on a frame first: `rink.py` knows our two
   jerseys (light blue, white with blue trim) and each rink's benches.
5. The LADA app shows a team's shift sheets once its feed URL (`<site_url>api`) is in `shiftSheetFeeds` in the
   app's `lib/src/shared/api_constants.dart`, keyed by LADA team id, and that app version is released.

## How the numbers are made

1. Detect every person on the rink in the 4K video (YOLO, 8 fps) and split teams by jersey color.
2. Track our skaters frame to frame, and read jersey numbers and names from close-up crops (OCR).
3. Check uncertain or swapped tracks by eye against a reference card of each player's gear.
4. Solve for who is on the ice every second, assuming 5 skaters (4 on a penalty kill), with changes happening at the bench.
5. Clean up: gaps under 15 s are merged, and hops under 20 s don't count as shifts.
6. Estimate stoppages from player motion (a still faceoff setup, then the puck-drop burst) for live play time.
7. Find goals (every non-period-start center-ice faceoff follows one) and cut zoomed highlight clips with a
   virtual camera that follows the play or a chosen player.

Ice time is real elapsed time on the ice, including stoppages, because the video has no game clock. The
recordings' audio is silent, so nothing relies on sound.

## TODO

What's left from the reviews of the processed games (Oct 22, 2026: the first 29; Nov 1: the 39 so far, 7 of them
since Oct 22, with every stage log and session timed and every hand-made lineup fix counted). Fetch is 25–45
minutes of a game's 2–4 hours; the by-eye lineup checks, 20–70 minutes and 19–56 on/off spans per game at
Snoqualmie's two cameras (6 per game at Renton), are the biggest cost left, and no measured change has beaten
the checkers at it yet. What they contribute, measured by solving every archived game without its hand-made
spans (`regress.py --strip-spans`): the solver alone leaves a median of 7 lineup windows and 6 minutes of
ice time per game moved against the published sheet, and inside the checkers' `off` spans it still has the
player on for 56% of the seconds.

1. **OCR alongside detection: made Nov 2.** `run_game.ocr_alongside` starts the four workers with detection; they
   read each crop as it lands (`ocr_worker.py` leaves the newest 2 s of crops alone, which may still be being
   written) and finish seconds after detection instead of 8–14 minutes after it. On a 4-minute slice of TK's Nov 1
   game: detection 52.6 s then OCR 46 s, against 77 s for both at once (detection itself a fifth slower with the
   workers beside it). On the Mac OCR stays after detection (the workers starved its decoder); `OCR_AFTER=1` does
   the same on the PC. Not yet measured on a full fetch, where the scoreboard scan runs alongside too: the next
   game's fetch log will say.
2. **Detection in three processes: made Nov 2.** A thread for the post-processing gained nothing (52.3 s against
   52.6 s on the slice): the pipe reader, the model's Python wrapper and the colour statistics all hold the GIL,
   about 24 s of the 53 (ffmpeg alone 21 s, reader 29, reader and model 40). `process.py` now runs the pipe reader
   and the post-processing in their own processes over a ring of 48 frames in shared memory: 34.3 s on the slice
   with the same detections and crops, the model now the limit (36 s with nothing else running). Detection of a
   game should drop from 13 minutes to about 9. A restart from a frame and a kill of the main process (the children
   exit within 5 s) are tested on the slice.
3. **GPU decode: measured Nov 2, not used; nvenc's p1 preset made.** `-hwaccel cuda` decodes the VP9 (14.0 s
   against 18.2 s for the slice) but made detection slower (57.9 s against 52.3 s, the GPU being busy with the
   model) and the scaling re-encode no faster (42.9 s against 43.2 s): that encode is NVENC-bound. Its p1 preset
   instead of p5 does it in 18.6 s (PSNR 50.4 dB against 50.5 for p5 against the scaled source, a 15% larger
   file), so `fit_size`'s 10 minutes should be 4 or 5.
4. **One decode of the video for detection and the scoreboard.** Measured over six fetches since Oct 26: the board
   scan alongside detection takes 6.7–11.4 minutes and detection 12.5–17.5 with it (11–16 before), so about 2–3
   minutes per fetch are saved and a minute or two is left to gain from a `split` off `process.py`'s ffmpeg graph
   (a named pipe on Windows, per-second picks that survive `detect()`'s restarts). Not worth it.
5. **The solver and seated players: measured Nov 1, not made.** 173 of the 328 hand-made `off` spans on the 33
   archived games cover seconds where the player's own track stood at the bench (`rink.at_bench`, or off the ice),
   which the solver scores as "on" because a labeled piece counts from its first second to its last. Counting
   those seconds as "off" evidence, in runs of 8 s and more, moved every archived game by 1–6 minutes of ice time
   and left more lineup windows on 15 of 28 games (8 of the 14 that had been checked to OK): of all such runs at
   Snoqualmie only
   12–27% lie inside a hand-confirmed off span (0–11% at Renton and Kirkland), so a player standing at the bench
   door or along the boards reads the same as a seated one. Position and duration don't tell them apart (nor
   does the box height); the checkers' eyes do, and `gaps` now lists the long bench pieces, the flagged goals and
   shifts of 5+ minutes for them. `regress.py --strip-spans` measures the next attempt the same way.
