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
| `pipeline/` | The scripts that turn a game video into `shifts.csv`, and `build_site.py`, which renders `docs/`. They work on one team at a time, picked by `TEAM` (`tk` unless set). `regress.py` re-solves every archived game and diffs the published sheets, for checking a pipeline change. |
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
hours for the block to lift; none of the 13 fetches since Nov 2 met it.

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
   highlight clips with a virtual camera that follows the play or a chosen player.

Ice time is real elapsed time on the ice, including stoppages; live play time comes from the stoppage estimate.

## TODO

What's left from the reviews of the processed games (Oct 22, 2026: the first 29; Nov 1: 39; Nov 18: 53 published,
47 archived, 14 of them since Nov 1, with every stage log and session timed and every hand-made lineup fix counted).
The by-eye lineup checks are still the biggest cost: 13 to 70 on/off spans a game (median 28.5; Renton's re-aimed
camera a median 27.5, with about 10 bench pieces a game), and no measured change has beaten the checkers at it yet.
What they contribute, measured by solving every archived game without its hand-made spans (`regress.py
--strip-spans`): the solver alone leaves a median of 7 lineup windows and 7.3 minutes of ice time per game moved
against the published sheet, and inside the checkers' `off` spans it has the player on for 90% of the seconds (the
56% of Nov 1 was dragged down by three long spans for players who had left). The regress baseline on Nov 18: 45 of
47 archived games identical, the same two Blue Wings games as since Oct 22.

Fetch, on the 13 full fetches made with the Nov 2 code: 24.3 to 38.0 minutes, median 28.6; downloads 1.4 to 3.9
(one of 14.5 with no error logged), and no bot block or cookies on any of them; the clock read in 1.1 to 1.4. Since
Nov 19 the board scan decodes on the GPU and OCR runs in six single-threaded workers (items 1 and 4): TK's Nov 15
video (204k crops), fetched again from its download on a quiet machine, took 18.5 minutes from the stages' start to
done, against 25.3 with the code before (27.2 in its own fetch log). On other games the scan's part should be what it
led OCR by on the 13 fetches (0.6 to 6.7 minutes, median 5.0), and the OCR part smaller with fewer crops; the next
fetch logs will say.

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
   times a game, which made the review 39% of the main session's tokens; `review` now lists at most 20 chunks and
   `check --wait` blocks until they are answered. `check` lists numbers reviewers gave that are off the roster;
   reviewers get `zoom.py` (106 of 198 in five sessions had written their own crop scripts); "G" is any goalie.
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
    and 6 of the 87 accepted goal clips (all early-net, as their sheets show).
11. **The command line: made Nov 18.** Git Bash's `/c/...` paths work everywhere; `sheet` works before fetch for every
    team and keeps its ids; `absent --suggest` drops shared-surname pieces and shows what was read alongside a number;
    `span` writes a hand-made span with its reason into `hand_spans.txt`; `publish` builds the header line (the same
    as the typed one on 40 of 53 games), adds a new opponent, writes the notes from `--notes-file`, prints the table
    and opens the page on a first publish. `archive` now also keeps `hand_spans.txt`, `clip_args.json`,
    `clips_check.json` and the checkers' briefs and answers under `scratch/goals`, `gaps` and `clips`.
12. **Gates for the collapse window: measured Nov 18, not made.** Of the seven stretches briefed by hand from Nov 1 to
    15, three had missing shifts; gates on the player's number reads in the gap, his linemates playing on, or
    unlabeled pieces of ours separated those from the rest only by a hair (one read; 0.97 against 0.92 of the game's
    rate; 0.50 against 0.49), so every collapse gets a window.
13. **The reviewers' effort level: measured Nov 18, open.** The 8 games reviewed at high effort against the 5 at xhigh:
    1.0 against 3.2 minutes and 0.32 M against 1.41 M tokens per reviewer, a game at 117 M against 145 M tokens and 99
    against 125 minutes, and 15.8% against 7.2% of rows answered "?". The games differ and nobody checked which
    answers were right, so it is an open question, not a recommendation. Since Nov 18 the skill launches reviewers
    on Opus 5.5 at medium effort and the checkers on Opus 5.5 at high, as a trial (subagents were about 70% of a
    game's tokens on the session's own model): the first game run that way reviews three chunks twice, on Opus and
    on the session's model, and its counts go here.
14. **A later checker contradicting an earlier round's span: found Nov 19, open.** `gaps --apply` adds the later span
    and keeps the earlier one, so both stay in `periods.json` and in later briefs' "merged" lines, and the solver adds
    the same large cost to both states for those seconds, which leaves them to the tracks. On the redo of Y's Sep 21
    round 1 had #29 off 2458-2478 and #12 on 2458-2467; round 2 saw the change at the bench door 4-5 s later (#29 on
    2458-2463, #12 off 2458-2462). The solve came out as round 2 saw it (#29 off and #12 on at 2462) and round 3
    confirmed it, but `periods.json` holds both pairs.
15. **Read counts on a republish: found Nov 19, open.** `publish` recounts `fun.name_reads` and `pipeline.reads` from
    the folder's OCR against today's `roster.json` (`reads.py` matches names against it), so an old game's read counts
    drift with every roster change since its first publish: on the redo of Y's Sep 21, #12 106 to 105, #72 86 to 82
    and the reads 5142 to 5149, with `reads.py` unchanged since Oct 16. The page's fun stats show them.
