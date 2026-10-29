---
name: process-game
description: Turn a LADA team's game video (Turbo Kings, Blue Wings, Beerteam, Doofers, Y or R; the YouTube wide cut) into a shift sheet with goals, penalties and shots, and publish it on that team's site. Use it whenever the user wants a game processed, analyzed, added or published, gives a YouTube link to a game, mentions a shift sheet or a scoresheet for a game, or asks to re-solve or archive a game's work folder, e.g. "/process-game https://youtu.be/... vs RR", "/process-game https://youtu.be/... bw vs DB", "process Saturday's game", "here's the game sheet PDF".
---

# Process a LADA team's game

One wide-cut game video becomes per-player shift stats, goals, penalties and shots on the team's GitHub Pages site
in `docs/<slug>/`. `pipeline/run_game.py` does the work; this file is the order of operations and the checks.
Details that only matter sometimes live next to it, read them when their step says so:

| File | When |
|---|---|
| `references/rinks.md` | the rink's camera, benches, jerseys, scoreboard quirks; a rink that isn't in `rink.py` |
| `references/review.md` | the visual review: how reviewers work, relaunching, re-checks, lessons |
| `references/highlights.md` | finding goals and penalties by eye, clips, `highlights.json` |
| `references/lada.md` | LADA's API, SportNinja game sheets, player ids, `roster.json` fields |
| `RUNBOOK.md` | the same pipeline step by step, for running pieces by hand |
| `pipeline/regress.py` | before changing anything the solve depends on: it re-solves every archived game and diffs the published sheets |

Teams: `tk` LADA Turbo Kings (LADA team 24), `bw` Blue Wings (10), `bt` Beerteam (5), `df` Doofers (17), `y` LADA Y
(20), `r` LADA R (2). Each has `teams/<slug>/` with `roster.json`, `opponents.json`, `games/` and `lada_games.json`,
and its site in `docs/<slug>/`. "We", "our" and "the roster" mean the team whose game it is. `fetch --team` records
the team in the work folder and every later command follows it; a script run by hand takes it from `TEAM`.

## Machine, budget, and what blocks on the user

```sh
PY=~/.venvs/hockey/Scripts/python.exe; [ -x $PY ] || PY=~/.venvs/hockey/bin/python   # the Windows PC, else the Mac
[ -x $PY ] || sh pipeline/setup_env.sh
W=~/hockey-work/<slug>-<YYYY-MM-DD>-vs-<opp>      # outside the repo, ~5 GB; Turbo Kings' folders have no slug prefix
```

Detection needs the local GPU, so none of this runs in the cloud. On the Windows PC (RTX 5090, set up with
`pipeline\setup_env.ps1`, see `WINDOWS.md`) fetch takes 30 to 40 minutes (download 3 to 15, detection 11 to 17
with the scoreboard scan running beside it, OCR 5 to 11, reading the board's clock about 1.5), prepare 6 to 11, the review 15 to 25, and
the lineup checks after the first solve anywhere from 15 minutes to two hours (the 29 games so far needed 0 to 76
on/off spans each, most of them found by eye), so a game is one and a half to three hours of session time;
`run_game.py` keeps Windows awake.
On the Mac fetch takes about 2 hours and needs `nohup caffeinate -dims -t 28800 >/dev/null 2>&1 &` first: a sleeping Mac stalls detection and kills reviewers
mid-sheet. Keep the user posted with one line per stage.

The user often leaves during a run. Only two points need them: confirming the score and highlights before
publish, and the push itself. Everything else runs to "ready to publish" on sensible assumptions, with each
assumption written down for the summary. Don't stop to ask about a new player, a sub, a spelling or a penalty.

Keep the main session small: half of the game sessions so far were compacted mid-game, and the by-eye work is what
grows them. Read a sheet once, crop tight, and delegate every frames job: the goals and penalties
(`references/highlights.md` has the brief) and the lineup windows (`run_game.py gaps` writes those briefs). Read
the Gantt charts only when the lineup check lists something, and start a new session for each game.

## 0. Inputs (one message, then start)

```sh
$PY pipeline/run_game.py schedule --team <slug>     # LADA's view: date, time, opponent, home/away, rink, id, planned lines
$PY pipeline/run_game.py sheet $W                   # the game sheet: score, shots, goals with scorers, penalties, who played
```

The game sheet comes from SportNinja's public API (the work folder's name gives the date; `--lada <id>` or
`--sn <id>` when LADA's cache doesn't have the game yet). It answers the score, each goal's period and clock with
scorer and assists, every penalty with player, type and minutes, shots per period and who the scorekeeper marked
as playing, and it writes `$W/sheet.json`, which `goals` and the lineup check use later. A scoresheet PDF from the
user says the same things; read it only when the API has nothing.

Then ask, in one message, only for what's still missing: whose game if the link or title doesn't say (Blue Wings'
titles name the team, Turbo Kings' start with LTK; "LADA R vs LADA Y" is both teams', processed from one fetch as
`references/lada.md` describes), the opponent's short name (e.g. RR; `opponents.json` has the
known ones), and new players and whether each is on the team or a sub (the schedule's "LADA ids not in
roster.json" and the sheet's "marked playing but not in roster.json" are the candidates). Don't ask about the
score, goal times or penalties: the sheet and the scoreboard have them. Fetch prints the video's title, which
carries the date, time and rink for the page header ("LTKvsTTT 5:55 PM PDT - SEP 13, 2026 (Snoqualmie) - wide
cut"; Blue Wings' "2026/09/13 LADA Blue Wings vs Disco Bandoleros", rink in the description).

Home or away decides our jersey and bench: home has worn white (blue numbers and trim), away light blue, and
`references/rinks.md` says which bench at each rink. LADA's schedule says `playHome`, but go by the video: check
`frame600.png` once fetch has it. Start step 1 before the answers come; they matter from step 2 on.

## 1. Fetch (background)

```sh
$PY pipeline/run_game.py fetch "<url>" $W --team <slug> --rink <renton|renton2|renton2band|renton2thin|snoqualmie|snoqualmie2|kirkland> [--jersey white] [--bench right]
```

Run it in the background and watch `$W/full/log.txt` with a Monitor that also matches `Traceback|Error`. Fetch
downloads the 4K video (and scales a smaller one up to the rink's usual frame), calibrates the far boards, runs
detection (restarting itself if it slows down) with a pass over the arena scoreboard beside it, OCRs the crops,
sheets the board into `$W/sb.jpg` (one tile per minute), reads the period clock off it (`pipeline/clock.py`: `$W/clock.json`, `$W/clock_check.jpg`) and
proposes periods from the clock. It resumes after any interruption, so re-run it if a background job is
stopped (the Mac's shell jobs stop after 2 hours; detection alone can take longer there). Don't run anything heavy
meanwhile: OCR and other jobs starve the video decoder. YouTube sometimes answers "Sign in to confirm you're not a
bot" for every client (every `player_client` alike): on Oct 19 it cleared by itself after about 25 minutes, and
that night after 50 for a video uploaded that evening. oEmbed answers during a block and gives the title, which says
whose game it is (`curl "https://www.youtube.com/oembed?url=<url>&format=json"`). A background loop that runs
`$PY -m yt_dlp -F <url>` every 5 minutes and starts fetch once format 313 is listed gets through without cookies;
reading the user's browser cookies (`--cookies-from-browser`) needs their say-so.

Pick `--rink` by the frame size and view (`references/rinks.md`); for a rink that isn't in `rink.py`, stop before
detection and follow the new-rink steps there. `--jersey` picks our colour test (default light blue); if you learn
after detection that we wore the other jersey (prepare makes a handful of review rows and a nearly empty roster
card), `run_game.py jersey $W white` cuts the missing crops and OCRs them without detecting again. `--bench` says
which side of the frame our bench is on; check it on `frame600.png` (our jerseys sit at our bench) and fix it by
adding `"bench": "right"` to `$W/full/rink.json` before prepare, or at the latest before solve.

## 2. Periods, nets, shots

Read `$W/sb.jpg` first: the period clock, score, shots, and the home and guest penalty panels. From it: which
side we are (go by the final score, not LADA's `playHome`), every score change, every penalty, and whether the
clock ran out. Then check `$W/periods.json`. Fetch takes the periods from the board's clock (`clock.py` reads
every second of it): each runs from the last second the clock shows 18:00 to its first 00.0, and the log prints
the empty-ice proposal beside them. Read `$W/clock_check.jpg`, one row per period: the board 1 s before, at and
after its start (18:00, 18:00, 17:59) and its end (00.0 from the middle tile on). On the 13 archived games it was
tried on, 70 of 78 edges were within 2 s of the hand-read ones. The clock knows nothing about play: fix an edge
where play and the clock part (`references/rinks.md`: a board left at 18:00 through a minute of play, a clock run
off on an empty rink, an intermission set while play had stopped), or where the board was dark (the reader then
assumes the clock kept running; check with `break_*.jpg` and `run_game.py skaters`). When the clock doesn't give
three periods (fetch's log says so) take them from `sb.jpg` by eye; when it gives none (a board the reader can't make
out, a `clock_box` that misses the clock), fetch falls back on the empty-ice proposal, which has merged periods and
reversed nets before. A finer sheet is one command: `$PY pipeline/scoreboard.py $W $W/sb2.jpg $(seq 1090 2 1130)`.

`net` is where our goalie plays that period (`nets` in `rink.py`; Renton 540 = left, 3245 = right) and switches
each period. Prepare drops our goalie's detections at that net, so check it on a zoom of both creases in each
period (`frames --view left-net`).

Shots come from the game sheet: publish copies `sheet.json`'s per-period counts into `game.json` (`shots_source:
sheet`). The board's digits are a few pixels tall and `shots.py`'s OCR has been wrong at most games, so run it only
when the sheet has no shots or looks wrong, once `periods.json` is right:

```sh
$PY pipeline/shots.py $W --us <home|guest>      # ~5 min -> W/shots.json + W/shots_check.jpg
```

Read `shots_check.jpg` (the board 25 s after each period, when the scorekeeper has caught up), make `"periods"` in
`shots.json` match it, `[ours, theirs]` per period, not cumulative, and set `"checked": true`; publish then prefers
the board's. In the last minute the clock shows tenths, which tells whether the video reaches the final horn; if it
doesn't, publish with `--video-ends-early`.

## 3. Penalty kills

Each penalty lights a panel with the player's number and counts down; sheet the board every 1–2 s around it. The
kill runs from the whistle to the moment the panel goes dark (LADA minors have been 2 or 3 minutes of clock; a
power-play goal against ends one early, so end the `pk` just after the goal). Don't trust which panel: watch who
skates into a penalty box after the whistle (`frames --view rink` 1–3 s apart, then a zoom) and read the number on
the way in. A penalty that spans an intermission gets a `pk` in both periods. Without a readable board,
`run_game.py skaters $W t0 t1` shows where only 4 of our skaters are out (5 → 4 plus the goalie before prepare);
a 2-minute penalty on a stopped clock often takes 3+ minutes of video.

Add each to its period in `periods.json`: `"pk": [{"start": 3602, "end": 3798, "player": 4}]`. Solve keeps the
player off for that span, since the box isn't our bench.

A penalty shot against us sends all our skaters to the bench: `"ps": [{"start": 3724, "end": 3765}]` in its period
makes solve put nobody on and the lineup check expect 0 (`references/highlights.md` has how to find one; the game
sheet doesn't record it). A pulled goalie is the opposite: `"extra": [{"start": 3666, "end": 3754}]` in its period makes solve and the lineup
check expect 6 skaters from the moment he leaves the crease until he is back in it (through any goal against). An
empty-net goal on the sheet or our crease emptying late in a period gives it away. A team with no goalie at all
skates six with a skater standing in at the net: an `extra` span over the whole stretch (`references/review.md`,
"No goalie").

## 4. The roster for this game

```sh
$PY pipeline/run_game.py unknown $W                 # numbers read hundreds of times that aren't on the roster
$PY pipeline/run_game.py absent $W 3 15 26          # roster numbers that didn't play
$PY pipeline/run_game.py absent $W --suggest        # the evidence per player: sheet, LADA's lines, reads, card rows
```

`unknown` sheets each candidate (`$W/unknown_<N>.jpg`): our jersey means a new player or sub, another team's
jersey that passes our colour test is an opponent to ignore. Add ours to `roster.json`, team members under
`skaters` and subs under `subs` (number → surname as on the back; tell the user the spelling), and put a player in
`subs` when unsure: moving him later changes only the site. Don't assume a missing number is a sub: the captain's
was missing once. Then mark absent everyone on the roster who didn't
play, including the subs who didn't come (`absent --suggest` tables the evidence per player and prints a list to
start from): a number that didn't play soaks up partial reads of others (a "3" off
43, 53 and 35 gave #3 ice time she never had). Decide from the sheet's "not marked playing" list, LADA's lines,
`unknown`'s read counts and the roster cards, but keep anyone LADA's lines list unless every period's card and
the reads are empty for them: a late arrival or a covered number looks the same as absence, and the sheet is the
scorekeeper's (it has marked a player playing who never appeared, and one absent who played all game). A surname two players share (father and son)
counts for neither, so if only one played, mark the other absent.

```sh
$PY pipeline/run_game.py prepare $W                 # per period: tracks, review sheets, roster card
```

Read one `roster_card.jpg`: each row should be one player with a consistent look. A player empty on every card
most likely didn't play (mark absent, then prepare again); empty in one period only is a back turned to the camera,
which `review` handles. Changing the roster or the absent list after prepare means moving `$W/p*` and `$W/rev_p*`
aside and preparing again, but never once a period's review has started: its rows point at segment numbers.

## 5. Visual review (subagents)

```sh
$PY pipeline/run_game.py review $W [--opp "white jerseys; they also wear #11 and #43"] [--note "#55 LISENKO: a ponytail hides her number"]
```

This writes one filled prompt per chunk of three sheets (`$W/rev_pN/prompt_cNN.md`) with the roster, our jersey,
the goalie, empty card rows with where to look instead, the opponents' look and your notes, and prints the plan
with each chunk's state. For every `[todo]` line launch one general-purpose subagent whose whole prompt is
"Read <that file> and do exactly what it says. Reply with one line: how many rows you wrote.", about six at a time,
starting the next as each finishes. Three sheets per reviewer and one answer file per sheet is deliberate: bigger
chunks stall before writing anything. When they're back:

```sh
$PY pipeline/run_game.py check $W                   # every manifest row answered? which sheets to redo
```

`review` again prints only what's left. A reviewer whose notes say images failed to load gets replaced: move its
file to `old_review_sNNN.txt` (solve reads only `review_*.txt`) and relaunch. `references/review.md` has the
re-check protocol for rows worth a second opinion and what went wrong before.

## 6. Solve and check

```sh
$PY pipeline/run_game.py solve $W
```

Solve applies the reviews, infers who is on the ice every second, estimates stoppages from player motion for live
play time (the audio is silent, so no whistles), writes `$W/gantt_pN.png`, prints the stats table, each period's shift seconds against 5 × its length (minus penalty-kill seconds; expect about
100%), and a lineup check: stretches of 15+ s without 5 of us on (4 in a kill, 6 with the goalie pulled), with who
was on and how much of the stretch was live play, and goals in `highlights.json` without 5 on or with a credited player
off the ice. Each is a missed player, an unlisted penalty, a bad label, or a slow line change during a stoppage.
Seeing who was on is a frames job, and the briefs for it are generated:

```sh
$PY pipeline/run_game.py gaps $W                    # one checker brief per period: W/scratch/gaps/prompt_pN.md
$PY pipeline/run_game.py gaps $W --apply            # merge the checkers' fixes.json into periods.json, then solve again
```

Each brief has the team's look, the rink, the bench and box, our net, the roster, the known events (kills, goals,
a pulled goalie), every window with the tracked pieces behind it (`segs_final.csv` rows with their review row ids),
and any long piece that sits in our bench zone (a seated player the tracker counted as on; common at Snoqualmie,
where the bench is by the camera). Launch one general-purpose subagent per brief, all at once, with the prompt
"Read <file> and do exactly what it says. Reply with one line per window." Each writes `fixes.json`: `on` spans for
a player seen on the ice whose track was lost, `off` spans for one the solver kept on after he left (a track that
ends mid-ice stays on until the next bench activity, and the solver drops someone else to keep 5 on). `--apply`
prints each span as it merges it into `periods.json`, skips duplicates and renames the file; solve again. Two
passes are normal, and a window the checker calls a slow change in a stoppage stays as it is (the check says how
many of its seconds were live).

A wrong label rather than a lost track (a whole unit with one player missing usually means his tracks carry someone
else's number or none; the window's pieces show it) is a zfix line instead: write it to `$W/rev_pN/review_zfix.txt`
in the review CSV format with a note starting "checked by hand"; it sorts last and overrides the reviewers' answer,
e.g. `R326,69,med,3776,90,med,checked by hand: 69 looks at the net for the goal; 90 white helmet from 3779`. Tell
the user which rows you labeled by hand and how many spans the checkers added.

## 7. Highlights: goals and penalties

```sh
$PY pipeline/run_game.py goals $W                   # candidates: center-ice faceoffs that aren't period starts
```

With `sheet.json` in place it first prints the sheet's goals with the second the board's clock showed each one's
time (`clock.json`; 82 of 96 goals on the archived games came 2 s before to 8 s after the goal itself, since the
clock stops just after it; most of the rest were the sheet's time lagging by 15–25 s where the clock runs through
stoppages, or a power-play goal given the penalty's time; without `clock.json`, period start plus the elapsed clock, exact only where the clock runs
through stoppages). Every goal is followed by a center faceoff, and the board's score changes a few seconds after
the clock stops. Confirm each by eye, or hand the list to one subagent with the brief in
`references/highlights.md`, which also covers finding each of our penalties' infraction and framing the clips:

```sh
$PY pipeline/run_game.py frames $W $W/g.jpg --view rink --range <t-60> <t> 3        # the minute before the faceoff
$PY pipeline/run_game.py frames $W $W/gz.jpg --view left-net <t1> <t2> ...          # zoom on a net, 1 s apart
$PY pipeline/run_game.py clip $W <game-id> goal-1 <t-12> <t+10> <t> "#<scorer>,#<assist>" --net for|against
$PY pipeline/run_game.py clip $W <game-id> penalty-4 <t-12> <t+10> <t> [focus-x | #<number>]
```

A goal clip with `--net` keeps the credited players in the frame, closes in on the net at the goal and ends with a
zoomed half-speed replay, so `t` must be the goal to the second and the clips come after the last solve.

Write `$W/highlights.json` (format in the reference; include `"scorer"` and `"assists"` from `sheet.json` so the
lineup check can verify them). Tell the user the score you found and ask them to confirm it; that and the push are
the two things that wait for them.

## 8. Publish

```sh
$PY pipeline/run_game.py publish $W <YYYY-MM-DD>-vs-<opp> --opponent <OPP> --eyebrow "Sun Oct 4, 2026 · 7:50 PM · Renton" [--video-ends-early]
```

This writes `teams/<slug>/games/<id>/game.json` and `shifts.csv` (with play time, stoppages, highlights, the game
sheet's shots, or the board's once `shots.json` is checked, and time in offence and defence from the detections),
finds the game's LADA id in `lada_games.json` (fetch keeps it current; `references/lada.md` if it can't), and rebuilds every team's site: game pages, the trends page
and the JSON feed in `api/` (`API.md`). A new opponent's code
and full name go in `opponents.json` (the user's spelling wins; LADA's exact spelling finds the logo in the app).
A new player needs a LADA id, which only the user can fetch: give them the exact `lada_ids.py` line to run.

Write `notes` in `game.json` (they survive a republish): the rink if new, who sat and when, where the goal times
came from, the subs, absent players, and anything labeled by hand or read differently from the board. Open the
page locally (`docs/<slug>/games/<id>/index.html`), show the user the table and the notable fun stats, then ask
before committing and pushing: the site is public. After the push, check the page is live (Pages takes about a
minute; add `?v=<random>` to skip the cache; the github.io address answers 301 to the custom domain in `docs/CNAME`,
analytics.ladaseattle.com since Oct 26, so `curl -L`).

## 9. Archive, and record what you learned

```sh
$PY pipeline/run_game.py archive $W                 # drops the video, crops and sheets (~5 GB), keeps the data (~100 MB)
```

Offer it once the user is happy. Never `rm -rf` a work folder: the kept data (with the scoreboard frames as JPEGs)
re-solves with a later pipeline, and `$PY pipeline/regress.py` does that for every archived game and diffs each
against its published `shifts.csv`, game by game and player by player. Run it after any change to `shifts.py`,
`apply_review.py`, `solver.py`, `run2.py`, `final_stats.py` or `stoppages.py`, before rebuilding a site, and say in
the commit what moved. On Oct 22, 2026 the baseline was identical for 23 of 25 archived games (Blue Wings' Sep 20
and Sep 27 games predate the Oct 15 solver fixes and differ by up to a minute for one player), and the noise-label
fix made that day moved five more by up to 45 s of one player's time; those five were re-solved from their archives
and republished the same day, with a note in each `game.json` saying what moved. Larger changes measured as worth
making but not made yet are listed under TODO in `README.md`.
Anything this game taught about a rink, a jersey, the scoreboard or the reviewers
goes into the matching `references/*.md` now, not into memory: memory stays on one machine, the skill travels.
