# Lada TK Analytics

Shift sheets for LADA's rec hockey teams: shifts, ice time and average shift length for every skater, measured from the wide-cut game video on YouTube.

| Team | Folder | Site |
|---|---|---|
| LADA Turbo Kings (LADA team 24) | `teams/tk/` | https://kondrat52.github.io/lada-tk-analytics/ |
| LADA Blue Wings (LADA team 10) | `teams/bw/` | https://kondrat52.github.io/lada-tk-analytics/bw/ |

## What's here

| Path | What it is |
|---|---|
| `docs/` | The published sites (GitHub Pages): Turbo Kings' at the root, other teams' in `docs/<slug>/`, each with game pages, a trends page (`trends.html`) and a JSON feed in `api/`. Generated; don't edit by hand. |
| `API.md` | The JSON feed for apps (e.g. the LADA app): URLs, fields, conventions. |
| `teams/<slug>/games/<date>-vs-<opp>/` | One folder per game: `game.json` (periods, penalty kills, video link, notes) and `shifts.csv` (one row per shift). |
| `teams/<slug>/roster.json` | Jersey number → surname, LADA player ids, team name, LADA team id and where its site goes. Add new players here. |
| `teams/<slug>/opponents.json` | Opponent code → full name. |
| `pipeline/` | The scripts that turn a game video into `shifts.csv`, and `build_site.py`, which renders `docs/`. They work on one team at a time, picked by `TEAM` (`tk` unless set). |
| `RUNBOOK.md` | The manual steps behind the skill, for debugging or running by hand. |
| `WINDOWS.md`, `setup_windows.ps1` | Setting up a Windows PC with an NVIDIA GPU to run the pipeline (one command). |
| `.claude/skills/process-game/` | The Claude Code skill for the weekly run. |

## Adding a game

The weekly run is driven by Claude Code. Open this repo and run the project skill:

> /process-game https://youtu.be/XXXXXXXXXXX vs RR

for Turbo Kings, or name the team: `/process-game https://youtu.be/XXXXXXXXXXX bw vs DB`.

The skill (`.claude/skills/process-game/SKILL.md`) asks for the opponent, start time, new players and the score,
finds periods, goals and penalties itself from the arena scoreboard and the video, then runs
`pipeline/run_game.py` (fetch → prepare → review → solve → publish) and asks before pushing.

It takes a few hours on an M-series Mac: about two hours of detection, then number reading, a visual review of the uncertain moments, and the final solve.

On a Windows PC with an NVIDIA GPU, detection runs on CUDA and should be much faster. To set one up, run this in
PowerShell; `WINDOWS.md` has the details and the steps by hand:

```powershell
irm https://raw.githubusercontent.com/kondrat52/lada-tk-analytics/main/setup_windows.ps1 | iex
```

To rebuild the sites after editing a game's files or a roster (`TEAM=bw` for one team only):

```sh
python pipeline/build_site.py
```

## Adding a team

1. `teams/<slug>/roster.json`: copy `teams/bw/roster.json` and change the team name, `lada_team_id` (LADA's public
   `https://api.ladaseattle.com/api/v1/Team/<id>` gives a team's name), `site_dir` and `site_url`, and the players.
   The players come from the team's SportNinja roster (screenshots of it work): spares go under `subs`, and the
   league's shared account (Agregat Dannikh) stays out.
2. LADA player ids: `TEAM=<slug> python pipeline/lada_ids.py` (signs in to LADA as you; LADA has to show you the
   team's roster).
3. Process a game with `--team <slug>`. Check the jerseys and benches on a frame first: `rink.py` knows our two
   jerseys (light blue, white with blue trim) and each rink's benches.
4. The LADA app shows a team's shift sheets once its feed URL (`<site_url>api`) is in `shiftSheetFeeds` in the
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
