---
name: process-game
description: Turn a LADA team's game video (Turbo Kings, Blue Wings, Beerteam, Doofers, Y or R; the YouTube wide cut) into a game analytics page (score, shifts, goals, penalties and shots), and publish it on that team's site. Use it whenever the user wants a game processed, analyzed, added or published, gives a YouTube link to a game, mentions a shift sheet or a scoresheet for a game, or asks to re-solve or archive a game's work folder, e.g. "/process-game https://youtu.be/... vs RR", "/process-game https://youtu.be/... bw vs DB", "process Saturday's game", "here's the game sheet PDF".
---

# Process a LADA team's game

One wide-cut game video becomes per-player shift stats, goals, penalties and shots on the team's GitHub Pages site
in `docs/<slug>/`. `pipeline/run_game.py` does the work (its docstring lists the commands in run order); this file
is the order of operations and the checks. Every by-eye job goes to a subagent whose brief the code writes from a
template in `pipeline/*_prompt.md`: edit the template, never a generated brief. Read these when a step says so:

| File | When |
|---|---|
| `references/rinks.md` | the rink's camera, bench and clock; a camera that moved; a rink that isn't in `rink.py` |
| `references/review.md` | reviewers and gap checkers: relaunches, re-checks, `review_zfix.txt`, what went wrong before |
| `references/highlights.md` | penalty-kill exceptions, `highlights.json`, clip situations and their flags |
| `references/lada.md` | LADA's API, SportNinja game sheets, player ids, `roster.json`, a game between two LADA teams |
| `references/ice.md` | the ice maps publish adds; calibrating a camera that has none |
| `RUNBOOK.md` | the same pipeline step by step, for running pieces by hand |

Teams: `tk` LADA Turbo Kings (LADA team 24), `bw` Blue Wings (10), `bt` Beerteam (5), `df` Doofers (17), `y` LADA Y
(20), `r` LADA R (2). Each has `teams/<slug>/` with `roster.json`, `opponents.json`, `games/` and `lada_games.json`,
and its site in `docs/<slug>/`. "We", "our" and "the roster" mean the team whose game it is. The work folder's name
says whose game it is until `fetch --team` records it in `$W/full/rink.json`; every command follows it.

## Machine, budget, and what blocks on the user

```sh
PY=~/.venvs/hockey/Scripts/python.exe; [ -x $PY ] || PY=~/.venvs/hockey/bin/python   # the Windows PC, else the Mac
[ -x $PY ] || sh pipeline/setup_env.sh
W=~/hockey-work/<slug>-<YYYY-MM-DD>-vs-<opp>      # outside the repo, ~5 GB; all lower case; Turbo Kings' have no slug prefix
```

Detection needs the local GPU, so none of this runs in the cloud. On the Windows PC (RTX 5090, `WINDOWS.md`) fetch
took 24 to 38 minutes (median 29) on the 13 fetches from Nov 2 to 17: download 1.5 to 4, detection 12 to 17 with OCR
beside it, and the scoreboard scan, which finished last, 5 to 12 minutes after detection. Since Nov 19 the scan runs
on the GPU and ends well before detection, and OCR (six single-threaded workers) ended 1.7 to 2.7 minutes after it
on TK's Nov 15 video (204k crops, among the most), which took 18.5 to 22 minutes after its download against 25.3
before. A smaller video's scaling re-encode adds 5 to 7. A game
has taken a median 109 minutes from start to "ready to publish" (65 to 149), 28 of them active and 77 waiting on
background work (fetch 26, lineup checkers 26, the goal checker 12, reviewers 6, clips 4); the lineup loop alone
took 20 to 79 (median two rounds). `run_game.py` keeps Windows awake. On the Mac fetch takes about 2 hours and needs
`nohup caffeinate -dims -t 28800 >/dev/null 2>&1 &` first: a sleeping Mac stalls detection and kills reviewers; its
background shell jobs stop after 2 hours, so run fetch again when one does. Keep the user posted with one line per
stage.

The user often leaves during a run. Only two points need them: confirming the score and highlights before
publish, and the push itself. Everything else runs to "ready to publish" on sensible assumptions, with each
assumption written down for the summary. Don't stop to ask about a new player, a sub, a spelling or a penalty.

Keep the main session small. A median game is 142 M tokens: lineup checkers 28%, reviewers 27%, the main session
26%, goal and penalty checkers 16%. Every subagent's hand-back wakes the main session (reviewers did it 22 to 132
times a game, 39% of its tokens), so launch a whole batch in one message, then wait with one blocking command
(`check --wait`) or Yield, with no status lines in between. Every frames job has a generated brief; delegate it. Read
an image you need yourself once, cropped tight, and the Gantt charts only when the lineup check lists something.

**Subagent models (a trial since Nov 18, 2026).** Launch every reviewer (step 5) with `model: "opus"` and
`effort: "medium"`, and every checker (the goal and penalty checkers of step 2, the lineup checkers of step 6, the clip
checker of step 7) with `model: "opus"` and `effort: "high"`. Subagents were about 70% of a game's tokens on the
session's own model. Reviewers have "?" to fall back on and the lineup check catches what they miss; a checker's
answer goes into the sheet or a clip without a second look, hence the higher effort. Nobody has measured Opus on these
sheets, so on the first game run this way, once `check` says the review is complete, copy the review files of three
chunks (the first of each period) to `$W/scratch/ab/opus/`, launch those three prompts again on the session's own
model with "but write each sheet's CSV into `$W/scratch/ab/session/`, not into the review folder" added, and compare
row by row: the share of "?" in each set (README's TODO 13 has 15.8% at high effort and 7.2% at xhigh on the session's
model), and the rows where both give a number at high or med confidence and the numbers differ. Give the user the
counts and add them to TODO 13; the user decides whether reviewers move to `effort: "high"`. Once a game has done
this, replace these sentences with the result.

**One game per session.** In the two sessions that processed several games, the fourth and fifth games ran at 432 k
and 521 k tokens of context per call, against 195 k for a median game. Compaction (7 of 14 games) came each time
while idle, waiting on the user after "ready to publish": write the notes file and the summary before you stop.

## 0. Inputs (one message, then start)

```sh
$PY pipeline/run_game.py schedule --team <slug>     # LADA's view: date, time, opponent, home/away, rink, id, planned lines
$PY pipeline/run_game.py sheet $W                   # the game sheet: score, shots, goals with scorers, penalties, who played
```

`sheet` reads SportNinja's public API (the folder's name gives the team and the date; `--lada <id>` or `--sn <id>`
once when LADA's cache doesn't have the game, `references/lada.md` has where to find one, and `sheet.json` keeps both)
and writes `$W/sheet.json`, which the later steps read. A scoresheet PDF from the user says the same things; its file
name is the SportNinja id.

Then ask, in one message, only for what's still missing: whose game if the link or title doesn't say (Blue Wings'
titles name the team, Turbo Kings' start with LTK; "LADA R vs LADA Y" is both teams', `references/lada.md`), the
opponent's short code (`opponents.json` has the known ones), and for each new player whether he is on the team or
a sub (the schedule's "LADA ids not in roster.json" and the sheet's "marked playing but not in roster.json"). Don't
ask about the score, goal times or penalties. Start fetch as soon as you know whose game it is (`--team`; home or
away gives `--jersey`); the other answers matter from step 4.

## 1. Fetch (background)

```sh
$PY pipeline/run_game.py fetch "<url>" $W --team <slug> --rink <renton|renton2|renton2band|renton2thin|renton2nov|snoqualmie|snoqualmie2|kirkland> [--jersey white] [--bench left|right] > $W.fetch.log 2>&1
```

Pick `--rink` by the frame size and view (`references/rinks.md`; Renton's current camera is `renton2nov`). Home has
worn white, away light blue; `--jersey` picks our colour test (default light blue). Fetch sets the bench from the
jersey at Renton and Snoqualmie (Renton: light blue left, white right; Snoqualmie: white left, light blue right; every
archived game) and keeps Kirkland's usual right bench with a line to check it; `--bench` overrides.

Start it with Bash `run_in_background` (you are told when it exits) and one Monitor on
`tail -F $W.fetch.log | grep -E --line-buffered "bench:|jersey and bench|framing|WARNING|Traceback|Error|fetch done"`
at its longest timeout (30 minutes), armed again if it expires and stopped when fetch exits; no foreground polling or
`sleep` (sessions lost 24 minutes that way). Fetch resumes after an interruption: run it again (a `periods.json` you
have edited stays; its new proposal goes to `periods.proposed.json`). Nothing heavy meanwhile.

As soon as the log names `frame600_small.jpg`, `bench_left.jpg` and `bench_right.jpg`, look: our jerseys sit at our
bench. A wrong jersey seen that early is cheapest fixed by stopping fetch, moving `$W/full` aside and running the
same fetch with `--jersey`; after detection (the sign: a handful of review rows and a nearly empty roster card),
`run_game.py jersey $W white` cuts and reads the missing crops without detecting again. A wrong bench: `--bench`, or
`"bench"` in `$W/full/rink.json` before prepare. Framing: at Kirkland and Snoqualmie B a late upload under a black band
is shifted into place; at Renton the `framing` line names the class that fits (stop fetch and run it again with that
`--rink`), or the turn onto the class given: up to 1.5 degrees is a roll and runs as that class, more is a re-aim
(`references/rinks.md`, "A camera that moved", has both). A "new framing" exit, or a rink not in `rink.py`: stop
before detection (`references/rinks.md`).

If YouTube answers "Sign in to confirm you're not a bot" (last on Nov 1), the user runs this line with `!` (written
with forward slashes and `~`, since `!` runs bash), then fetch skips the downloads. Reading the browser's cookies is
theirs to run, not the session's; RUNBOOK §1 has the wait-it-out loop.

```sh
~/.venvs/hockey/Scripts/python.exe pipeline/run_game.py download "<url>" ~/hockey-work/<folder> --cookies firefox
```

## 2. Periods and nets, then the goal and penalty checkers

Fetch writes `$W/periods.json` from the board's clock: each period from the last second it shows 18:00 to its first
00.0. Its `clock:` lines say per period whether the clock ran out, how many reads agree and whether the board was
dark at an edge (then that edge is an estimate: check it on `break_*.jpg`, the overview frames around each
intermission, and with `skaters`). Read `$W/sb.jpg` (the board every minute) and `$W/clock_check.jpg` (per period
the board 1 s before, at and after its start and its end). The clock knows nothing about play: correct `start` or
`end` in `periods.json` where they part (a board left at 18:00 through play, a clock run off on an empty rink or set
back; `references/rinks.md`).
- `periods from the empty ice`: the clock gave no period; the empty ice has merged periods and missed edges by 30 to
  90 s, so take the periods from `sb.jpg` by eye. Fewer than three on the clock: the same.
- The sheet has a period `periods.json` lacks (`goals`, `pk` and `highlights` say so; an overtime is P4, 5:00 of
  clock): add it with its start, end and net.
- `WARNING periods`: a clock edge and the empty ice differ by over 100 s; run the `skaters` command it gives before
  moving the edge (LADA R's Nov 2: "1:02" with an unlit 1 read as 0:02 ended the 3rd 148 s early).
- `WARNING clock` on the 3rd: if the recording stops before the horn (`video_end.jpg`), publish with
  `--video-ends-early`.
- End tiles that aren't 00.0 after tenths, or show 0:0x without tenths: sheet the board 2 s apart to the video's end,
  `$PY pipeline/scoreboard.py $W $W/sb2.jpg $(seq <t0> 2 <t1>)`.

`net` is where our goalie plays each period. Fetch proposes it by three reads (our bench's end in the 1st, then
switching, held on 47 of 47 games; the half our skaters line up in at the opening faceoff; our jersey in each crease)
and warns where they disagree. Where all three agree, leave the nets: on TK's Nov 8 fetch had them right and a
misread frame reversed them. Where they disagree, look by play, not by jersey (a sub goalie can wear anything): where
our skaters crowd during our kill, the net where our score went up, a crease zoom with pads and a mask (`frames $W
out.jpg --view left-net <t> ...`). Fix the bench first if that is what's wrong; prepare stops on a net that goes
against both the rule and the faceoff (`--force` once you have seen it is right).

As soon as the periods and nets are set, brief the goal and penalty checkers and launch them all in one message;
they need no tracks and run beside prepare and the review (a median 28 minutes: run after the review, they left the
session idle 12 to 26 minutes in 11 of 14 games):

```sh
$PY pipeline/run_game.py goals $W --brief           # W/scratch/goals/prompt_pN.md per period with goals, prompt_pens.md
```

One general-purpose subagent per brief (`model: "opus"`, `effort: "high"`), whose whole prompt is "Read <brief> and
do exactly what it says. Reply with one line per goal or penalty." Each writes a JSON answer that step 6 reads; don't wait for them, go on with step 3.
The briefs name the players the sheet marks playing who aren't in `roster.json` yet, so they needn't wait for step 4.

The score and shots come from the game sheet: publish copies its final score (`sheet_score`, what the site shows) and
its shots per period. Scorekeepers correct sheets later: `$PY pipeline/run_game.py scores`, then `build_site.py`.
`shots.py` only when the sheet has no shots (RUNBOOK §5).

## 3. Penalty kills

```sh
$PY pipeline/run_game.py pk $W --write              # our kills from the sheet and the clock, into periods.json
```

Run it before the first solve; without `--write` it only prints. Each of our penalties starts at the second the
clock showed its time; a 2-minute minor runs 3:00 where the clock runs through stoppages (the 1st and 2nd so far,
starting 30 s before the sheet's time there); a power-play goal against ends it, an intermission splits it,
coincident minors get none. On 16 archived games 32 of 36 kills started and 32 ended within 15 s of the published
ones. A kill in a period without a board clock read is marked ROUGH and left to the penalty checker (`--rough` writes
it anyway). The penalty checker's kills replace these at `highlights --write`, and `pk --write` skips a penalty the
checker has answered, so running it again is harmless; where they part, `references/highlights.md` ("Penalties")
has the cases. A penalty shot against us and a pulled goalie are spans, each with a note on why:

```sh
$PY pipeline/run_game.py span $W ps <t0> <t1> --note "penalty shot: all of ours at the bench"   # solve puts nobody on
$PY pipeline/run_game.py span $W extra <t0> <t1> --note "goalie pulled"   # 6 expected, crease empty to crease again
```

A team with no goalie skates six with someone standing in: an `extra` over the whole stretch (`references/review.md`).

## 4. The roster for this game

```sh
$PY pipeline/run_game.py unknown $W                 # numbers read hundreds of times that aren't on the roster
$PY pipeline/run_game.py absent $W --suggest        # the evidence per player: sheet, LADA's lines, reads, card rows
$PY pipeline/run_game.py absent $W 3 15 26          # roster numbers that didn't play (adds to the list; --clear empties it)
```

`unknown` sheets each candidate (`$W/unknown_<N>.jpg`): our jersey means a new player or sub, another team's jersey
that passes our colour test is an opponent to ignore. Add ours to `roster.json`, team members under `skaters` and
subs under `subs` (number → surname as on the back; tell the user the spelling); when unsure, `subs`: moving him later
changes only the site (a number of ours missing from `roster.json` isn't always a sub: the captain's was once). Then
mark absent everyone on the roster who didn't play, subs and goalies included: a number that didn't play soaks up
partial reads of others. Keep anyone LADA's lines list unless every period's card and the
reads are empty for them: a late arrival or a covered number looks like absence, and the sheet is the scorekeeper's.
A surname two players share counts for neither, so if only one played, mark the other absent.

```sh
$PY pipeline/run_game.py prepare $W                 # bench and nets checks, then per period: tracks, review sheets, roster card
```

Read one `roster_card.jpg`: each row should be one player with a consistent look. A player empty on every card most
likely didn't play (mark absent, then prepare again); empty in one period only is a back turned to the camera. A
change to the roster or the absent list after prepare: before the review starts, move `$W/p*` and `$W/rev_p*` aside
and prepare again; once it has started (its rows point at prepare's segments), never prepare again, and solve alone
picks the change up (an absent player gets no shifts; the pieces prepare labeled with his number count for nobody).

## 5. Visual review (subagents)

```sh
$PY pipeline/run_game.py review $W [--opp "white jerseys; they also wear #11 and #43"] [--note "#55 LISENKO: a ponytail hides her number"]
$PY pipeline/run_game.py check $W --wait            # Bash timeout 600000: blocks until the batch is answered
```

`review` writes one prompt per chunk of three sheets, lists up to 20 to launch now and prints what they say beyond
the template: the goalie line, each period's empty card rows, `--opp` and `--note`. Read those first; a note that
contradicts them misleads every reviewer (change the note, kept in `$W/review.json`, or the absent list, and run
`review` again). `--opp` gives the opponents' look and any of our numbers they wear. Launch every listed prompt in one
message, one general-purpose subagent each (`model: "opus"`, `effort: "medium"`), whose whole prompt is "Read
<prompt file> and do exactly what it says.
Reply with one line: how many rows you wrote." Then `check --wait` once; repeat `review` and `check --wait` until
`review` lists nothing, leaving out a prompt it marks "listed before" while that reviewer hasn't reported back.

`check` also lists numbers reviewers gave that are off the roster (solve would take each as a new player of ours) or
belong to absent players. Settle each: a sub to add to `roster.json`, a player who did play, or a misread kept out by
a `review_zfix.txt` line (`references/review.md`). A reviewer whose notes say images failed gets replaced: move its
file to `old_review_sNNN.txt` and `review` lists the chunk again.

## 6. Highlights, solve and the lineup loop

Solve (below) as soon as the review is answered. `highlights` comes once the goal and penalty checkers are back, and
always before the first `gaps`; solve again if `--write` changed the kills:

```sh
$PY pipeline/run_game.py highlights $W              # the entries, and a "!" line for whatever doesn't add up
$PY pipeline/run_game.py highlights $W --write      # highlights.json, and the checker's kills in place of pk's
```

Our goals always take the sheet's scorer and assists; theirs name the sheet's scorer in the note. Act on each `!`:
a scorer the checker saw differently, or a goal the board counts and the sheet doesn't, goes to the user in the
summary (the sheet stands until the team says otherwise); a penalty shot becomes a `ps` span and a goalie the checker
saw pulled an `extra` one (step 3); a missing answer means relaunching that checker. A play worth a clip that is
neither goal nor penalty is a hand-added `"moment"` (`references/highlights.md`).

```sh
$PY pipeline/run_game.py solve $W
$PY pipeline/run_game.py gaps $W                    # after every solve: the checker briefs, W/scratch/gaps/prompt_pN.md
$PY pipeline/run_game.py gaps $W --apply            # the checkers' fixes.json into periods.json; then solve again
```

Solve applies the reviews, infers who is on the ice every second, estimates stoppages from player motion, and prints
the stats table, each period's shift seconds against 5 × its length (minus kills; about 100%) and the lineup check:
stretches of 15+ s without 5 of us on (4 in a kill, 6 with the goalie pulled), goals with the wrong count or a
credited or seen player off the ice, shifts of 5+ minutes, ice-time collapses, and windows hand spans already explain.
`gaps` briefs those with our long pieces in the bench zone (seated players counted as on, most at Snoqualmie) and the
leads earlier checkers left; later rounds show the spans already merged and skip what was settled. Launch one
general-purpose subagent per brief (`model: "opus"`, `effort: "high"`), all in one message, whose whole prompt is
"Read <file> and do exactly what it says. Reply with one line per window and bench piece.", then Yield until all are back. `--apply` prints each span it
merges and names every item left unanswered (the next `gaps` lists it again). A `!!` line is a listed kill a checker
saw played 5 on 5: do the two things it says (take that `pk` out of `periods.json` or cut it to the part that was
short, and run the `span ... off` line it prints for our boxed player). Repeat solve, `gaps`, the checkers and
`--apply` until `gaps` has nothing to brief (a median two rounds); after a round that merges no span and opens no
lead, stop and put what it left unsure in the notes and the summary. A window a checker calls a slow change in a stoppage stays as it is.

Hand-made spans go in only through `span`, with a note: `span $W on|off <player> <t0> <t1> --note "why"`, and
`span $W --list` shows them. A wrong label on a review row is a `review_zfix.txt` line (`references/review.md`).
Tell the user how many spans the checkers added and what you decided by hand.

## 7. Clips, after the last solve

```sh
$PY pipeline/run_game.py clips $W <game-id> --dry-run   # every camera path in highlights.json, checked; nothing cut
$PY pipeline/run_game.py clips $W <game-id>             # cut, a contact sheet each, and the clip checker's brief
```

The clips frame the solver's tracks, so they come after the last solve; `<game-id>` is publish's,
`<YYYY-MM-DD>-vs-<opp>`. Fix what the dry run warns about first: the times in `highlights.json`, or a clip's own
arguments in `$W/clip_args.json` (`references/highlights.md` has the situations and flags). After the cut, one
general-purpose subagent on the brief it names (`model: "opus"`, `effort: "high"`), whose whole prompt is "Read
<brief> and do exactly what it says.
Reply with one line per clip." It writes
`$W/scratch/clips/answers.json`: for each clip not ok, fix what it points at (`t`, `shot` or `pass` in
`highlights.json`, or `clip_args.json`), re-cut with `clips --only <names>` and give the new brief to a fresh checker.
A clip that fails doesn't stop the others: `clips` exits 1 and prints the `--only` line that retries those.
Show the user nothing until it has answered: the user complained about a clip in 7 of 14 games, and each time the
session's own look had passed it. That is "ready to publish": write `$W/notes.txt` (step 8) and the summary, then
tell the user the score and the highlights and ask them to confirm.

## 8. Publish

```sh
$PY pipeline/run_game.py publish $W <YYYY-MM-DD>-vs-<opp> --opponent <OPP> --notes-file $W/notes.txt [--video-ends-early]
```

It writes `teams/<slug>/games/<id>/game.json` and `shifts.csv` (play time, stoppages, highlights, the sheet's score
and shots, time in offence and defence, and the ice maps where the camera is calibrated, every rink so far:
`references/ice.md`), finds the LADA id, builds the page's header line (the time from the video's title, else LADA's
schedule; the rink from LADA's schedule, the title or the sheet; it prints where they differ; `--eyebrow` overrides),
adds a new opponent to `opponents.json` in LADA's spelling (the user's spelling wins: change it there, then
`build_site.py`), rebuilds every site and the feed, prints the player table, the fun stats and `The page:
file:///...`, and opens the page on a game's first publish (`--open` on a republish, `--no-open` never). Show the
user the table and the notable stats.

`$W/notes.txt` holds the notes, a blank line between them: the rink if new, who sat and when, the subs and absent
players, where the goal times came from, anything decided by hand, and what the sheet credits that the video shows
otherwise. They stay in `game.json` (no page and no feed shows them) and survive a republish. A new player needs a
LADA id, which only the user can fetch: give them the `lada_ids.py` line for their own PowerShell (`references/lada.md`).

Ask before committing and pushing: the site is public. Pages then takes 4 to 5 minutes, and `gh` isn't installed
on the PC, so poll in a background Bash command (the domain is `docs/CNAME`'s; a new page answers 404 until live):

```sh
until curl -sfL -o /dev/null "https://analytics.ladaseattle.com/<slug>/games/<id>/?v=$RANDOM"; do sleep 30; done
```

## 9. Archive, and record what you learned

```sh
$PY pipeline/run_game.py archive $W                 # drops the video, crops and sheets (~5 GB), keeps the data (~100 MB)
```

Offer it once the user is happy. It keeps what a re-solve or a re-cut needs, `hand_spans.txt`, `clip_args.json`,
`clips_check.json` and the briefs and answers under `scratch/` (a hand trace for a clip belongs outside `scratch/`).
Never `rm -rf` a work folder: `$PY pipeline/regress.py` re-solves every archived game and diffs each against its
published `shifts.csv` (45 of 47 identical on Nov 18; Blue Wings' Sep 20 and Sep 27 predate the Oct 15 solver
fixes). Run it after any change to `shifts.py`, `apply_review.py`, `solver.py`, `run2.py`, `final_stats.py` or
`stoppages.py`, before rebuilding a site, and say in the commit what moved; `--strip-spans --keep` weighs a solver
change against the checkers' spans. README's TODO lists what was measured. Anything this game taught about a rink,
a jersey, the scoreboard or the checkers goes into the matching `references/*.md` now, not into memory: memory stays
on one machine, the skill travels.

To redo an archived game (Y's Sep 21, published on the wrong bench, was redone on Nov 19), first run
`regress.py --only <folder>` with `--out` in a scratch folder: it must come out identical. `download` brings the video
back, and YouTube's bot check needs the user's `--cookies firefox` line from step 1. Scale it to the size `dets.csv`
was detected at with `run_game.fit_size` (the old size is in `$W.fetch.log`), never with `fetch`, which goes on to
detect, and check on one frame that a box from `dets.csv` sits on a player. Change `full/rink.json` through
`set_config` (`set_config(W, bench=None)` sets the bench from the jersey as fetch does), never by `prepare`, then
solve and run step 6's lineup loop. Publish with one `--notes-file` holding every old note unchanged plus one on what
was redone and what moved: `--notes` and `--notes-file` replace the notes. On an old folder the gap briefs have no
clock line (no `clock.json`), the first checker to run `scoreboard.py` scans the whole video (a few minutes), and
publish recounts the name reads against today's `roster.json`, so `fun.name_reads` and `pipeline.reads` move a little.
