# LADA Analytics

Game analytics for LADA's rec hockey teams: scores, shifts, ice time and average shift length for every skater, measured from the wide-cut game video on YouTube.

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
| `pipeline/` | The scripts that turn a game video into `shifts.csv`, and `build_site.py`, which renders `docs/`. They work on one team at a time, picked by `TEAM` (`tk` unless set). `regress.py` re-solves every archived game and diffs the published sheets, for checking a pipeline change; `backfill.py` brings every published game up to what publish now writes (stoppages after goals, time in offence and defence, roles and positioning) from its archived work folder, and rebuilds the sites. |
| `RUNBOOK.md` | The manual steps behind the skill, for debugging or running by hand. |
| `WINDOWS.md`, `setup_windows.ps1` | Setting up a Windows PC with an NVIDIA GPU to run the pipeline (one command). |
| `.claude/skills/process-game/` | The Claude Code skill for the weekly run. |

## Adding a game

The weekly run is driven by Claude Code. Open this repo and run the project skill:

> /process-game https://youtu.be/XXXXXXXXXXX vs RR

for Turbo Kings, or name the team: `/process-game https://youtu.be/XXXXXXXXXXX bw vs DB`.

The skill (`.claude/skills/process-game/SKILL.md`, with its `references/`) reads the SportNinja game sheet, asks
for the opponent and any new players, and runs `pipeline/run_game.py`: fetch → goals --brief (the goal and penalty
checkers, beside the next steps) → pk → absent → prepare → review → solve, and highlights once the checkers are
back → gaps, round by round → clips → publish. The by-eye work goes to subagents on briefs the code writes. It asks
before pushing; only the score confirmation and the push wait for you.

On the 14 games since Nov 1 a game took a median 109 minutes from start to "ready to publish" on the Windows PC (65
to 149, leaving out two broken by outside events): 28 minutes of active session time and 77 of waiting on background
work (fetch 26, the lineup checkers 26, the goal checker 12, the reviewers 6, the clips 4). By stage: fetch 29 (24
to 38), prepare to the first solve 16 (6 to 35), the lineup loop 47 (20 to 79, a median two rounds), the last solve
to ready 8. A median game was 142 M tokens: the lineup checkers 28%, the reviewers 27%, the main session 26%, the
goal and penalty checks 16%. On an M-series Mac it takes a few hours more, where detection alone is about two hours.
YouTube's bot block has added anything from nothing to hours: three of the four games fetched on Oct 31 needed the
user's browser cookies (`run_game.py download --cookies firefox`, which the user runs), and one waited nearly three
hours for the block to lift; Beerteam's Nov 14 video met it on Nov 19, and the user's cookies line took 1.6 minutes.

The first game under the Nov 18 rework, Beerteam's Nov 14 (processed Nov 19), is one game, with one unusual skater:
our #54 skated in a dark green jersey the tracker can't see and was traced by eye, about 22.5 minutes and 39.4 M
tokens of it (seven tracers 33.7 M, the main session 5.7 M). Against the medians above, in parentheses: 129.7 minutes
to "ready to publish", about 107 without that skater (109); 36.9 active and 91.0 waiting (28 and 77); fetch 19.6
with its 1.6-minute download (29); 9.5 minutes waiting on reviewers, 7.2 of them on 3 reviewers the harness refused (6);
1.05 on the goal and penalty checkers, run beside prepare and the review (12); the lineup loop one round, 3
checkers, 11 spans and 7.4 M tokens (two rounds and 37 M); the clips 51 minutes and about 31 M tokens from the first
clip command to the second checker's return, with 2 checker rounds and 3 hand-briefed helpers (4 minutes of waiting
on clips); 134.2 M tokens in all, 94.8 M without the untracked skater and 89.8 M also without the reviewers' A/B
(142 M); the main session 30.4 M, the review 4.6% of it (40.9 M and 39%); 49 subagents; and one clip the user
complained about, their goal 2, "doesn't have actual scorer in the slow-mo replay" (a clip complaint in 7 of the 14
games).

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
5. The LADA app shows a team's game analytics once its feed URL (`<site_url>api`) is in `shiftSheetFeeds` in the
   app's `lib/src/shared/api_constants.dart`, keyed by LADA team id, and that app version is released.

## How the numbers are made

1. Detect every person on the rink in the 4K video (YOLO, 8 fps) and split teams by jersey color.
2. Track our skaters frame to frame, and read jersey numbers and names from close-up crops (OCR).
3. Check uncertain or swapped tracks by eye against a reference card of each player's gear.
4. Solve for who is on the ice every second, assuming 5 skaters (4 on a penalty kill), with changes happening at the bench.
5. Clean up: gaps under 15 s are merged, and hops under 20 s don't count as shifts.
6. Estimate stoppages from player motion (a still faceoff setup, then the puck-drop burst) for live play time.
7. Find goals and penalties from the game sheet and the board's period clock, pin each down by eye, and cut zoomed
   highlight clips with a virtual camera that follows the play or a chosen player. A goal inside an estimated
   stoppage moves that stoppage's start to just after the goal: the players slow down before the whistle, so the
   motion estimate starts it too early (209 of 304 goals on the 49 archived games fell inside one, a median 7 s after
   its start).
8. Map every detection onto the ice in feet through the rink's camera calibration (`pipeline/rinkcam.py`). Where the
   play is each second is the median position of everyone detected on the ice (6 or more): time in offence is live
   play with it past their blue line, time in defence behind ours (`pipeline/zones.py`). A rink without a calibration
   falls back to thirds of the camera picture, which reach past the blue lines and count 4 to 8 points more time in
   both ends; the trends page draws those games as rings.
9. Each skater's role in a game, from his tracked positions (`pipeline/positioning.py`): over live play outside our
   penalty kills (our power plays included) with 4 or more of ours tracked, the share of the time he was one of our
   two deepest. D at 0.6 and up, F at 0.4 and under, no role in between. The game page tags it.
10. Positioning, season numbers only (a single game doesn't repeat well enough): for defensemen their side, from the
    share of their time on the left side with the play in our end (worked out for each end of the camera picture and
    averaged, since the camera puts a skater on one side more at one end), and with the play in their end the share
    inside their blue line and the share 15 ft or more past it; for forwards their depth with the play in our end, the
    share as our highest forward in their end, goal side of the play on rushes against, their lane with the play in
    their end (the share in the left and in the right third of the ice, each end of the picture averaged) and, with
    the play in our end, the share outside our blue line and the share low in our zone (from the tops of the circles
    down). Each game keeps the seconds they rest on; the trends page shows the average of his games in a role, for a
    skater with 4 or more games in it: a small rink per defenseman and per forward, its bands and lanes shaded by the
    share of his time there, and a table of the forwards' other numbers.

Ice time is real elapsed time on the ice, including stoppages; live play time comes from the stoppage estimate.

## TODO

What's left from the reviews of the processed games (Oct 22, 2026: the first 29; Nov 1: 39; Nov 18: 53 published,
47 archived, 14 of them since Nov 1, with every stage log and session timed and every hand-made lineup fix counted).
The by-eye lineup checks are still the biggest cost: 13 to 70 on/off spans a game (median 28.5; Renton's re-aimed
camera a median 27.5, with about 10 bench pieces a game), and no measured change has beaten the checkers at it yet.
What they contribute, measured by solving every archived game without its hand-made spans (`regress.py
--strip-spans`): the solver alone leaves a median of 7 lineup windows and 7.3 minutes of ice time per game moved
against the published sheet, and inside the checkers' `off` spans it has the player on for 90% of the seconds (the
56% of Nov 1 was dragged down by three long spans for players who had left). The regress baseline on Nov 19: 46 of
48 archived games identical, the same two Blue Wings games as since Oct 22.

Fetch, on the 13 full fetches made with the Nov 2 code: 24.3 to 38.0 minutes, median 28.6; downloads 1.4 to 3.9
(one of 14.5 with no error logged), and no bot block or cookies on any of them; the clock read in 1.1 to 1.4. Since
Nov 19 the board scan decodes on the GPU and OCR runs in six single-threaded workers (items 1 and 4): TK's Nov 15
video (204k crops), fetched again from its download on a quiet machine, took 18.5 minutes from the stages' start to
done, against 25.3 with the code before (27.2 in its own fetch log). On other games the scan's part should be what it
led OCR by on the 13 fetches (0.6 to 6.7 minutes, median 5.0), and the OCR part smaller with fewer crops. The first
fetch since, Beerteam's Nov 14 (about 116k crops): 18.0 minutes after a 1.6-minute download, the board scan 5.7 on
the GPU and ending 10.4 minutes before detection, the last of the six OCR workers 14 s after detection (fetch now
logs that line).

1. **OCR alongside detection: made Nov 2, delivered in part.** `run_game.ocr_alongside` starts the workers (four
   until Nov 19, six since) with detection; they read each crop as it lands (`ocr_worker.py` leaves the newest 2 s of crops alone). On full games
   OCR finished 0.1 to 2.6 minutes after detection under 160k crops, and 6.1 to 8.8 after on the five with 204k to
   262k (white jerseys at `renton2nov`, `snoqualmie2` and `renton2thin`), against 6.7 to 14.2 minutes after it
   before Nov 2. On the Mac OCR stays after detection (the workers starved its decoder); `OCR_AFTER=1` does the same
   on the PC. **Six single-threaded workers on the PC: made Nov 19.** Each worker had 2 onnxruntime threads; with 1
   they read the same rows (the union of the csv rows identical on 27 slice runs and 8 full fetches) with less
   waiting. Full fetches of TK's Nov 15 video with the board scan on the GPU, quiet machine: 4 x 2 detection 14.8
   minutes, OCR done 4.9 after it, fetch 20.9; 6 x 1 15.6, 1.7, 18.5; 8 x 1 17.2, 0.2, 18.6 (and with
   Steam and Firefox busy: 4 x 2 15.7, 5.7, 22.7; 6 x 1 18.1, 2.7, 22.2; 8 x 1 18.1, 0.2, 19.6). With the scan on the
   GPU, 6 x 1 and 8 x 1 tie on fetch (18.5 and 18.6 quiet) and both beat 4 x 2 (20.9), because OCR no longer ends 5
   minutes after detection; 6 x 1 was taken over 8 x 1 because it slows detection less (15.6 against 17.2). 4 x 2
   detects fastest (14.8), and 8 x 2 starved detection on the slice (24 to 27 frames a second). Not measured: more
   than one run per setting under each condition (the outside load differed between the runs); a game with few crops,
   where detection sets the pace and may come out a little slower with 6 x 1 than with 4 x 2; and `jersey`'s OCR,
   `OCR_AFTER=1` and the `ocr()` tail after detection, which now run 6 x 1 too. A worker now writes its `ocr_N.csv`
   with its first row, so one that reads nothing leaves no empty file; every reader globs `ocr_*.csv`, so a folder
   resumed at another worker count works. The Mac keeps 4 x 2.
2. **Detection in three processes: made Nov 2, not delivered on a full game.** `process.py` runs the pipe reader and
   the post-processing in their own processes over a ring of 48 frames in shared memory: 34.3 s against 52.6 s on a
   4-minute slice of TK's Nov 1 game, with the same detections and crops (a thread had gained nothing: the reader,
   the model's Python wrapper and the colour statistics all hold the GIL). On full games detection took 12.2 to 16.9
   minutes, median 14.9 (31 to 44 frames a second, by the height of the rink's detection band): per hour of video
   what it was before Nov 2, not the 9 minutes predicted. Each change was measured on the slice alone, and all of
   them needed the same CPU headroom. On Nov 19 TK's Nov 15 video detected in 14.2 minutes with the old fetch (36.6
   frames a second, quiet machine; 14.8 in its own fetch log), 14.8 with the board scan on the GPU and 4 x 2 OCR,
   15.6 with 6 x 1 (OCR takes more of the CPU and ends sooner), and 0.8 to 2.5 minutes slower again with Steam and
   Firefox busy beside it.
3. **GPU decode: measured Nov 2, not used; nvenc's p1 preset made and delivered.** `-hwaccel cuda` decoded the VP9
   faster but made detection slower (the GPU busy with the model) and the scaling re-encode no faster: that encode
   is NVENC-bound. Its p1 preset instead of p5 (PSNR 50.4 dB against 50.5 on the slice, a 15% larger file) took
   5.2 to 7.2 minutes on full fetches against 11.2 to 16.9 before: 3.0, 2.3 and 1.9 times faster at the three sizes
   seen (6.3 minutes at 3840x1536 against the 4 to 5 predicted). The board scan's decode on NVDEC (item 4) costs
   detection little (14.8 against 14.2 minutes with the same OCR): the slowdown found here was for detection's own
   decode moved to the GPU.
4. **The scoreboard scan on the GPU: made Nov 19.** It had finished last on 13 of 13 fetches: 18.2 to 27.5 minutes
   beside detection (6.7 to 8.2 before Nov 2 beside the old detection; 2.6 to 4.7 run alone), ending 4.9 to 12.1
   minutes after detection, median 7.9: the video was decoded twice in software while three detection processes and
   four OCR workers filled the CPU's 16 threads, and the scan at below-normal priority got the leftovers. Now
   `scoreboard.py` decodes on NVDEC (`-hwaccel cuda`: ffmpeg's own VP9 parser driving it) and cuts the board out on the
   GPU (`overlay_cuda` at minus the box's corner onto a box-sized frame: this ffmpeg has no crop for CUDA frames), at
   normal priority: 2.5 CPU-seconds per minute of 4K VP9 against 23.5 for the CPU decode at 4 threads. On full fetches
   of TK's Nov 15 video it took 5.5 to 6.8 minutes and ended 9 to 12 minutes before detection; its 3,880 boards are
   byte-identical to the CPU scan's (their JPEGs to the archive's), and so are the clock, the periods and `sb.jpg`.
   Where the first and middle seconds don't come out byte-identical to the CPU path (no NVDEC or CUDA filters, a
   container with no duration), or the GPU pass fails, stalls (no frame for 2 minutes) or comes up short, the scan runs
   on the CPU as before; so it does on the Mac, which skips the check, and with `SCOREBOARD_CPU=1`. Every rink's
   `scoreboard` box must have even sides and corner: an odd one fails the check and is wrong on the CPU path too
   (`crop` evens it, and the raw frames read then drift a row). Tried and
   not used: the `vp9_cuvid` decoder's own `-crop` (1.1 CPU-seconds a minute, but it drifted from the software decode
   by up to 28 levels within a GOP); the GPU scan at below-normal priority (starved: on an 8-minute slice it ended 50
   to 60 s after detection, against 60 to 80 s before it at normal); the scan alone after detection and OCR (on the
   slice no faster than beside them: 215 to 221 s against 206 to 221). Not built: a second output from detection's own
   decode (all it could save now is the GPU scan's 2.5 CPU-seconds a minute). Not measured: half precision and larger
   batches for the model (the GPU was 28 to 36% busy during detection, so the model waits on the CPU), and TensorRT (not
   installed; its install needs the network). The lesson of items 1 to 4 stands: measure a fetch change with
   detection, OCR and the scan running together, and confirm it on a full fetch before writing a prediction into the
   docs.
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
6. **The setup checks: made Nov 18.** Fetch sets our bench from the jersey where it follows it (Renton, every camera:
   light blue left 15 of 15, white right 6 of 6; Snoqualmie A and B: white left 14 of 14, light blue right 7 of 7;
   Snoqualmie's usual right side had been wrong for 14 of its 21 games) and keeps Kirkland's, which follows nothing.
   It proposes each period's net by three reads, our bench's end in the 1st and switching (47 of 47 games), the half
   our skaters line up in at the opening faceoff (139 of 140 periods) and the crease count (138 of 141), and prepare
   stops on a net that goes against the first two (TK's Nov 8, set backwards by hand, would have stopped). It logs per
   period whether the clock ran out and warns where a clock edge and the empty ice part by over 100 s (on 33
   archived clocks: the two wrong edges, no false alarm), says when publish needs `--video-ends-early` and when the
   periods came from the empty ice, writes the frame views the jersey and bench are checked on, and prints the turn
   where no Renton framing fits (a roll up to 1.5 degrees). A fetch run again keeps an edited `periods.json` (its
   proposal goes to `periods.proposed.json`). Solves are byte-identical.
7. **The goal and penalty checkers' briefs, kills from the sheet, highlights from the answers: made Nov 18.** `goals
   --brief` writes them from fetch's output and `periods.json`, so they run beside prepare and the review: the goal
   check took a median 27.6 minutes, and run after the review it had left the session idle 12 to 26 minutes in 11 of
   14 games. `pk` proposes our kills from the sheet and the clock: on the 16 archived games with a clock read, 32 of
   36 starts and 32 of 36 ends within 15 s of the published kills; a period without a clock read gives only a rough
   kill, left to the penalty checker, whose answers `pk --write` never overwrites. The briefs name the sheet's players
   not yet in `roster.json`, and an overtime runs its sheet's length. `highlights` builds `highlights.json` from the
   answers and the sheet (our scorers always the sheet's), matches its entries by the sheet's numbers so hand edits and
   deletions stay, and the goal checker's on-ice reads join the lineup check.
8. **Reviewers in batches with one wait: made Nov 18.** Each reviewer's hand-back woke the main session, 22 to 132
   times a game, which made the review 39% of the main session's tokens (4.6% on Beerteam's Nov 14, in two
   batches); `review` lists a batch and `check --wait` blocks until it is answered. `check` lists numbers reviewers
   gave that are off the roster; reviewers get `zoom.py` (106 of 198 in five sessions had written their own crop
   scripts); "G" is any goalie. **Batches of 16 and a wait that gives up: made Nov 19.** On Beerteam's Nov 14 3 of 20
   reviewers were refused (the harness runs 20 subagents at once, and three checkers were running) and `check --wait`
   sat out its 540 s on them, 7.2 of the 9.5 minutes spent waiting on reviewers. `review` now lists 16 (`--batch`),
   and `check --wait` returns once the batch is answered, after 180 s with no new answer or zoom crop (`--quiet`), or
   at 540 s, naming the prompts that never answered so that the next `review` lists them again. Reviewer durations
   from 1,355 transcripts: the 1,301 on Opus 5.5 a median 129 s, at most 438; the 51 on Fable 5.1 at high effort,
   all on one game (TK's Nov 1), a median 267 s, at most 599; with scratch writes counted as signs of life no launch
   was quiet for more than 102 s, hence 180.
9. **Gap briefs with an answer per item: made Nov 18.** Every window and bench piece needs an answer, `gaps --apply`
   names the unanswered, leads become the next round's windows, a kill reported as 5 on 5 is printed and not applied,
   each brief says whether the period's clock stops at whistles (the 3rds) or runs through stoppages (the 1sts and
   2nds, on all 20 games with a clock read), later rounds show the spans already merged and skip what was settled,
   and an ice-time collapse gets a window of its own (10 windows over the 14 games, the 3 real cases among them).
   The checkers get `frames --tracks` (our tracked boxes with track id and label) and `follow` (one piece over time),
   which ten checkers in four games had scripted for themselves.
   The Nov 1 additions found real errors (14 of 15 goal items, 10 of 10 long shifts and 39 of 81 bench pieces led to
   spans) without cutting spans or rounds. A checker's cost is per item (a median 12.6 minutes and 35 images), and
   spans under 5 s are 22% of the spans but 2.5% of the seconds moved, so nothing is gained by skipping short ones.
10. **Clips from `highlights.json`, checked: made Nov 18.** `clips` cuts every highlight with the sessions' arguments,
    checks each camera path first (`--dry-run` alone), tiles each clip into a contact sheet and briefs one checker;
    a clip that fails doesn't stop the rest.
    The user had complained about a clip in 7 of the 14 games, each one the session's own look had passed. On the
    archives the check flags the first cuts of TK Nov 1 #3, R Nov 2 #10, Y Nov 2 #4, BT Nov 7 #1 and DF Nov 15 #5,
    and 6 of the 87 accepted goal clips (all early-net, as their sheets show). **The scorer in the replay: made Nov
    19.** Both November complaints (Beerteam's Nov 14 goal-2, Blue Wings' Nov 7 goal-11) were a replay on someone
    else while the sheet's scorer shot from the far point or the far boards. The goal brief now has the checker find
    the sheet's scorer first; `shot` is his last touch and `start` where the play began; the penalty brief asks for
    `spot`; new dry-run checks (`shooter-edge`, `scorer-jump`, `player-jump`, `spot-track`); the clip checker's
    problems carry a kind, its rounds are numbered, and `clips --answers` sorts them. On the last approved cut of 221
    clips in 30 games 16 warned before and 20 after, and both bad first cuts (0 warnings before) warn now.
11. **The command line: made Nov 18.** Git Bash's `/c/...` paths work everywhere; `sheet` works before fetch for every
    team and keeps its ids; `absent --suggest` drops shared-surname pieces and shows what was read alongside a number;
    `span` writes a hand-made span with its reason into `hand_spans.txt`; `publish` builds the header line (the same
    as the typed one on 40 of 53 games), adds a new opponent, writes the notes from `--notes-file`, prints the table
    and opens the page on a first publish. `archive` now also keeps `hand_spans.txt`, `clip_args.json`,
    `clips_check.json` and, since Nov 19, the text files anywhere under `scratch/` (`.md`, `.json`, `.csv` and `.txt`
    up to 10 MB; it had kept only `scratch/goals`, `gaps` and `clips`, and lost Beerteam's Nov 7 goal-1 trace), and
    it goes into no linked folder or junction there. **`title <link>`: made Nov 19.** It reads the video's title from
    oEmbed, which the bot check doesn't block, and says the date, team, opponent's code and work folder.
12. **Gates for the collapse window: measured Nov 18, not made.** Of the seven stretches briefed by hand from Nov 1 to
    15, three had missing shifts; gates on the player's number reads in the gap, his linemates playing on, or
    unlabeled pieces of ours separated those from the rest only by a hair (one read; 0.97 against 0.92 of the game's
    rate; 0.50 against 0.49), so every collapse gets a window.
13. **The reviewers' effort level and model: measured Nov 18 and 19, open.** The 8 games reviewed at high effort
    against the 5 at xhigh, on the session's model: 1.0 against 3.2 minutes and 0.32 M against 1.41 M tokens per
    reviewer (19.6k against 64.7k a row), a game at 117 M against 145 M tokens and 99 against 125 minutes, and 15.8%
    against 7.2% of rows answered "?". The games differ and nobody checked which answers were right, so it is an open
    question, not a recommendation. Since Nov 18 the skill launches reviewers on Opus 5.5 at medium effort and the
    checkers on Opus 5.5 at high, as a trial (subagents were about 70% of a game's tokens on the session's own model).
    The first game run that way, Beerteam's Nov 14 (Nov 19): 27 Opus reviewers at medium, 0.5 to 1.9 minutes and
    0.66 M tokens each (0.24 to 0.92 M), 27.8k a row, left 60 of 619 rows "?" (9.7%; 13.3%, 11.8% and 5.0% by
    period). The first chunk of each period (72 rows) was reviewed again on the session's model (Fable 5.2 at high):
    Opus left 7 "?", the session's model 6; of the rows where both were confident (60 by the session's count, 62 by
    another) none differ; Opus reported a switch on 12 rows, the session's model on 21 (three of them a
    "?" start that Opus had named outright); a chunk took 0.62 to 0.74 M tokens on Opus against 1.04 to 1.62 M. So on
    the same chunks Opus at medium was cheaper, while its 27.8k a row on this game is more than the 19.6k of the high-
    effort games of Nov 18, which were other games. Token figures here are cumulative, by the Nov 18 method (Opus and
    Fable tokens counted alike), never an agent's final context. One game, and nobody checked the switches: still the
    user's call.
14. **A later checker contradicting an earlier round's span: found Nov 19, fixed Nov 19.** `gaps --apply` added the
    later span and kept the earlier one, so both stayed in `periods.json` and in later briefs' "merged" lines, and the
    solver added the same large cost to both states for those seconds, which left them to the tracks. On the redo of
    Y's Sep 21 round 1 had #29 off 2458-2478 and #12 on 2458-2467; round 2 saw the change at the bench door 4-5 s
    later (#29 on 2458-2463, #12 off 2458-2462). Fixed Nov 19: the newest span wins (`trim_opposite`): `gaps --apply`,
    `span`, `trace --apply`, and for a kill or a boxed player's `off` `pk --write` and `highlights --write`, cut its
    seconds out of the player's opposite spans and print it, and `answers.json` and `hand_spans.txt` keep what is
    left; two checkers of one round who disagree get a `!!` line and both stay. The Y Sep 21 replay keeps only round
    2's pair, and the solve then has #29 off at 2463 per that checker, 1 s later than the published 2462.
15. **Read counts on a republish: found Nov 19, open.** `publish` recounts `fun.name_reads` and `pipeline.reads` from
    the folder's OCR against today's `roster.json` (`reads.py` matches names against it), so an old game's read counts
    drift with every roster change since its first publish: on the redo of Y's Sep 21, #12 106 to 105, #72 86 to 82
    and the reads 5142 to 5149, with `reads.py` unchanged since Oct 16. The page's fun stats show them.
16. **Three more clip checks: measured Nov 19, not made.** An empty-net check on the replay fired on 22 approved
    clips; `EMPTY_N` 3 instead of 2 (the early-net check's "all but empty") gave 5 false alarms; the three label
    checks as counted warnings would have flagged 28 approved clips, since the solver's labels are often wrong at a
    goal while the spot is right, so they stay `clip note:` lines. Not caught by any dry-run check: a checker's shot
    on the wrong player (Blue Wings' Nov 7 goal-11's second cut); only the briefs address that.
17. **An absent player's surname in the name reads: made Nov 19; the tie on the full name: measured, not made.**
    `absent --suggest` now compares the sheet's surnames with `roster.json`'s (after transliteration) as well as the
    numbers, and prints the nameplates read on each played or check number's crops; the review card's line for a
    number with no card row says whose nameplates its reads carry. `reads.RIVALS`: a plate that scores strictly
    higher against an absent player's surname than against every playing player's is nobody's. Of 137,586 name reads in the 48 folders it drops 242 in 28 games and changes no
    owner; letting absent names join the margin instead would have dropped 3,111, nearly all of them players' own
    reads. On Beerteam's Nov 14 PIZANO's 70 reads had gone to #27: no piece, review row or shift was affected (the
    crops are not on our tracks), but the published page's name-read count for #27 says 546 where 476 are his (item
    15 has why a republish moves it). Not made: breaking a tie between a playing and an absent surname on the
    full-name ratio (DUTSENKO is DOTSENKO, not BELOUSENKO), which would let "about as well" count; it changes the
    scoring for every game.
18. **A guest's LADA id: found Nov 19, open (the user's call).** `"guests": {"54": "Pfeifer"}` in `game.json` holds a
    name only, so David Pfeifer's LADA id 20433 (no number on LADA's Beerteam roster) is nowhere in the feed: his row
    has `lada_player_id: null`. Where a guest's id goes is a question of the feed's format, not of the pipeline.
19. **What the next game must prove: open.** No game video was on disk during the Nov 19 fix round, so no clip was
    cut and no checker read the new briefs. Untested on a real game: the goal checker's scorer-first search and
    `start`, the clip checker's answer kinds and `clips --answers` on its new answers, the penalty checker's `spot`
    and the clip that follows it, and `trace` (its briefs, `pipeline/trace_prompt.md`, went to no tracer; `trace
    --apply` was fed the Nov 14 tracers' answers and gave the published solve). The next game's notes should say how
    each did.
20. **A skater of ours the tracker can't see: made Nov 19.** Beerteam's Nov 14 #54 in dark green had no track; 15
    `on` spans for him were dropped without a word, then he came out 96 s too long until 17 hand-made `off` spans
    held him. Now a player known only from `on` spans (under 20 s of labeled track) is held off wherever neither an
    `on` span nor a labeled piece of his is (`run2.py`): Beerteam's game with the 17 `off 54` spans deleted solves
    identical to the published sheet. A player still left out of a solve is named with why and his spans. The
    lineup check's first line names a roster skater the sheet has playing who has no shift (the sheet's name where
    it differs, "#54 PFEIFER (roster.json: SEMENOV)"); on the published states it fires once, on Blue Wings' Oct 11
    #55 Lisenko, whom the sheet marks playing and the session decided hadn't played without marking her absent.
    Without a sheet, a game with one of ours short in 15+ s windows over 15% of it while filled under 98% is flagged
    (`SHORT_SHARE`, `SHORT_FILL`): of the 48 archived games solved without their spans only Beerteam's Nov 14 passes
    both (816 s, 23.0%, at 96.8%); next come Doofers' Nov 8 (12.2%, 97.5%) and Beerteam's Nov 7 (10.7%, 98.4%), each
    a player lost for one period, and every other game is at 7.7% or less and filled 98.9% or more. `trace` writes
    the by-eye briefs for such a player (`pipeline/trace_prompt.md`, parts of at most 600 s) and `trace --apply` adds
    his shifts as `on` spans: the seven Nov 14 tracer answers give the same 15 shifts (2,026 s) and the published
    solve.
21. **Skating pace and distance per skater: measured Nov 24, tabled (the user's call).** From the ice maps'
    positions (`ice.positions`, feet on the ice), smoothed over about a second, live play only, on the six archived
    TK games: a skater's rank within the team repeats from game to game for the median pace (correlation 0.84) and
    the distance per minute (0.73), and #12's median came out 9.8 to 10.3 ft/s on four cameras (`renton2`,
    `snoqualmie2`, `snoqualmie`, `renton2nov`). Top speed does not: the 99th percentile ran 23 to 90 ft/s (0.06),
    track switches and box jumps reading as bursts, so no top speed, bursts or acceleration before those are
    cleaned out. Speed was usable on 55 to 69% of #12's ice time (labeled track in runs of 2+ s). No drop in pace
    late in a shift showed, for him or pooled. Before any figure in feet or mph is published: hand-time skates
    between the blue lines (50 ft) on each camera and compare, and compare within a role (defensemen with
    defensemen). Not wanted (the user, Nov 24): usage splits (5 on 5, kill and power-play minutes, how a shift
    starts). Measured the same day and too noisy per game: where the play is with a skater on the ice against
    off it (game-to-game correlation about 0; #12 pooled -0.04, 95% -0.14 to +0.06 over 68 shifts).
22. **What repeats from game to game: measured Nov 24, the reliable part made Nov 24.** The owner's rule is that
    nothing unreliable gets published, so a pass over the 49 archived games measured which candidate numbers repeat
    (a skater's game against his other games, split halves, a season mean's reliability) and which the camera or
    the tracking bends. Made, in publish and for every published game with `backfill.py`:
    - *Stoppages after goals.* 209 of the 304 goals fell inside an estimated stoppage, a median 7 s after its start:
      the players slow down before the whistle. A goal inside one now moves its start to just after the goal
      (`stoppages.after_goals`). On the 55 published games 224 stoppages moved; live play grew in 52 games, a median
      41 s (0 to 153), and 1,146 shifts' `play` changed; nothing else in any `shifts.csv` did. It is exact without a
      work folder (`play` comes out identical from `game.json` and `shifts.csv`), so the six early games got it too.
      `regress.py` before the change and after the backfill: 47 of 49 archived games identical both times (the same
      two Blue Wings games differ), and the re-solved sheets differ only in `play`, on 46 games. `game.json` keeps
      the motion estimate as `stoppages_raw` (the six early games' from their files before the change) and the
      correction always starts from it, so a goal's time changed later can move a start back. Its costs: a stoppage
      moves to after its latest goal, so with two goals inside one the whistle and faceoff between them count as live
      (once: Blue Wings' Oct 25, goals at 1537 and 1580 inside [1535, 1613)); and 26 of the 224 moves are 30 s or
      longer, which may be a missed faceoff rather than a slow whistle, so live play stays an upper bound.
    - *Time in offence and defence in feet.* The picture's thirds put the blue lines at 0.25-0.29 and 0.71-0.75 of the
      span between the nets, not at thirds, so they counted time in both ends 4 to 8 points too high. Now the play's
      median position in feet: on the 49 games, offence 36.6% to 30.8% and defence 37.8% to 32.1% on average (the
      moved stoppages included). By team, offence/defence before and after: Turbo Kings 40.1/36.1 to 33.7/30.1 (6
      games), Beerteam 36.0/37.4 to 30.6/31.5, Blue Wings 34.9/38.4 to 28.5/31.5 (8), Doofers 37.2/35.1 to 31.1/29.9,
      R 34.8/42.1 to 29.7/35.8, Y 37.5/37.0 to 31.9/32.9. Five games without a work folder stay on the picture
      (Turbo Kings' Sep 20 to Oct 10, Blue Wings' Sep 13; TK's Sep 13 has no zones), drawn as rings and left out of
      the trends page's tiles.
    - *Role per game* (share among our two deepest, D at 0.6+, F at 0.4 and under): a game against the skater's
      other games correlates 0.90; 44 of 561 player-games are in between or against his usual role.
    - *Positioning, season numbers only.* A single game's values correlate 0.43-0.57 with the same skater's other
      games, too little to show; a 4-6 game mean's reliability is 0.66-0.81: a D's share on the left side with the
      play in our end (0.81), worked out for each end of the picture and averaged, since with our net at the
      picture's left the camera puts a skater left 0.15 more often than at its right (+-0.075 on the raw share); a
      D's share inside their blue line with the play in their end (0.66); a forward's depth with the play in our end
      (0.78), share as our highest forward in their end (0.73) and goal side on rushes against (0.74). The trends
      page shows the plain mean of a skater's game values in a role, for 4+ games, each game counting once (a game
      needs 10 s of the moment, 5 s for rushes and for each end's left share; a D game with 5 s at only one end of
      the picture uses that end alone, 6 of 194): on the 27 defensemen with 4+ games, random split halves over games correlate
      0.79 (left) and 0.53 (inside) so, against 0.76 and 0.47 with the seconds pooled across games, and the
      reliabilities above were measured on it. #12 comes out at left 0.726 and inside 0.484 on Turbo Kings (5 games),
      0.710 and 0.454 on Y (6 games as a D).
    - *Power plays are in.* The role and positioning use live play outside our penalty kills (and the pulled-goalie
      and penalty-shot spans), not 5 on 5: the opponents' penalties are timed only in games published from Nov 23,
      so our power plays could be left out of a few games only. On Turbo Kings' Nov 22 (5 opponents' penalties,
      about 19% of the positioning frames) leaving them out moved single-game values by up to 0.07 (a D's inside
      share) and 0.14 (a forward's goal side).
    - *A defenseman deep on attack, and his side* (a second pass the same day, on the 49 archived games). `deep`: with
      the play in their end (the frames of `inside`, the same 10 s minimum a game), the share of his labeled frames
      15 ft or more past their blue line (V > 40). A season mean's reliability is 0.83, the most repeatable of the
      positioning numbers, and the ranks hold for cuts of 40 to 50 ft and for the 90th percentile of his depth
      instead of a share. It reads about 7% low from tracks lost deep in their end, and about 0.03 higher in games
      where the team wears white, so it compares teammates, not teams. Turbo Kings: #78 0.275 (4 games), #61 0.201
      (6), #12 0.197 (5), #13 0.187 (5). The left share gives his side: "Left" at 0.55 and up, "Right" at 0.45
      and under (each with how often he is there), "Both sides" in between.
    - *A rink per defenseman* (Nov 27, after a teammate read the tables' range bars, a dot between the team's lowest
      and highest, as his place in the zone). The trends page draws each defenseman's season as a small rink
      attacking up, each band shaded by the share of his time there and carrying its number: with the play in their
      end deep (`deep`), at their blue line (`inside - deep`) and not in their zone (`1 - inside`), with the play in
      our end the left and right halves of our zone (`left`, his stronger side larger). No number changed. Within
      each team the at-their-blue-line share spreads less than `deep` (Y: 31-39% against 4-20%), so `deep` is what
      tells teammates apart. A dot at each one's average spot was considered and not built: estimated from the
      published shares (taking his depth as normal), Y's six defensemen average within about 6 ft of each other,
      all near the blue line. The forwards' table lost its range bars the same day and is plain sortable numbers.
    - *A rink per forward* (Nov 27, a pass over the 51 games with positions: 363 forward-games, 46 forwards with 4+
      games). What repeats, as a season mean's reliability among teammates (each value less its team's mean; the
      same sums give the published depth 0.78, high forward 0.74 and goal side 0.73): his lane with the play in their
      end, the share in the left third of the ice (`lane_left`, 0.89) and in the right third (`lane_right`, 0.86), the
      thirds starting 14 ft from the middle; with the play in our end the share outside our blue line (`out`, 0.81)
      and low in our zone, from the tops of the circles down (`low`, V <= -54, 0.78). The rink draws the rest too:
      the centre lane (0.54: forwards differ little in it, sd 0.047 against 0.127 for the left third) and the top of
      our zone (0.70). The camera puts a forward in the left third 0.324 of the time with our net at one end of the
      picture and 0.258 at the other, so the lanes are worked out for each end and averaged, as a D's left. White
      games read within 0.012 of the others on all of them. By rink the pooled `low` runs 0.255-0.336 and `out`
      0.216-0.275, so they compare teammates, not teams. A forward is labeled 70% of his seconds on the ice with the
      play in our end (a defenseman 44%), but his track drops out more low in our zone (0.74 gap seconds per labeled
      second, 0.25-0.27 above it): `low` reads about 6 points low (0.285 against 0.349 with the gaps split between
      the bands before and after) and the top of our zone 4.5 high, the season means with and without the gaps
      correlating 0.98 (`low`), 0.97 (`out`) and 0.99 (the lanes). Measured and not built: his depth with the play
      in their end (the share below the dots 0.63, not in their zone 0.52, up to 20 ft past their blue line 0.47, his median depth
      0.58); his lane with the play in our end (0.91 and 0.92, but the season means correlate 0.88 with the lanes in
      their end, so the rink shows a lane once); lane by depth cells in our zone (0.67-0.92, ten numbers a rink).
      Backfilled for the 51 games; nothing else in a `game.json` or `shifts.csv` moved.

    Measured and not built: a D's share in front of our net (his track drops out there: 0.93 gap seconds per labeled
    second at the net-front spot, 0.41 elsewhere, and 45% of the last frames before a gap are there against 31% of
    all), the cushion on rushes (reliability 0.58, and it moves with the rink), D pairs (only 3 pairs had 3+ games of
    20 s together, and their spacing didn't repeat), and anything about changes on the fly, a shift's age, staying
    on through a whistle or rest. One team-level finding, not built: when two or more of ours change together with
    the play in our end, the next 20 s have 15 points more time in our end than matched moments without a change
    (132 events; game bootstrap +8 to +22 points; goals against in the next 30 s no different). It is an
    association only: a change may follow the pressure rather than cause it.

    Measured again in the second pass and not published: a D's time near our net. His labeled frames cover 44% of
    his time when we defend and miss about half of his time at the net. Filling his track's gaps within the shift
    brings the miss down to 3-10%, but then 45% of the number is interpolated, it reads 0.06 lower in white games and
    up to 0.1 off by rink, and on Turbo Kings and Y the spread between teammates is no larger than the noise.
    Publishing it needs the tracker to keep defensemen labeled at the net. Nor pinches per minute (reliability 0.57:
    it depends on how long a track holds unbroken).
