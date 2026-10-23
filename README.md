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

It takes one and a half to three hours on the Windows PC (30–40 minutes of fetch, 15–25 of visual review, then
the by-eye checks of the lineup, goals and penalties), or a few hours more on an M-series Mac, where detection alone
is about two hours.

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

Two pipeline changes measured as worth making in the Oct 22, 2026 review of the first 29 processed games, not made
yet:

1. **One decode of the video for detection and the scoreboard.** `fetch` decodes the 4K video three times:
   `process.py` (8 fps, cropped to the rink, for YOLO), `crops.py` (8 fps again, for the jersey crops) and
   `scoreboard.py scan` (every frame, cropped to the board, keeping the brightest of each second; 3–5 minutes per
   game, run after OCR). Detection is GPU-bound, so the cheapest version runs the scan in a thread or process
   alongside `detect()` and joins it before `ocr()`; the tidier one adds the board crop to `process.py`'s ffmpeg
   graph (`split` into the 8 fps rink crop and a full-rate board crop) so the video is read once. Either needs a
   game video to test (archives keep none): at the next game run the old scan too and compare `scoreboard.npy`
   frame by frame, and time the fetch.
2. **Periods and a game clock from the board, by OCR.** The empty-ice proposal (`periods_proposed.json`) has been
   wrong at nearly every game, so the period edges are read by eye off `sb.jpg` every time (`references/rinks.md`
   has the rules: the clock counts down from 18:00, runs through stoppages in the 1st and 2nd and stops at whistles
   in the 3rd, an intermission countdown of 1:00–2:00 between periods, operators who reset or run the clock on an
   empty rink). Reading the clock digits off every second of the board, the way `shots.py` reads the shots digits
   (RapidOCR on an upscaled crop, then a fit that allows only the moves a clock makes), gives the period spans
   directly and a video time for every clock time, which also places the game sheet's goals and penalties in the
   video without a frame hunt. It needs a clock box per rink next to `shots_boxes` in `rink.py`, and data to
   develop on: `archive` keeps the board as JPEGs (`scoreboard_jpg.npz`) since Oct 22, so every game from then on
   provides a test case; the hand-read periods in each archived `periods.json` are the ground truth.
