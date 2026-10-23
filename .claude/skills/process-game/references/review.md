# The visual review

Prepare picks every tracked segment that isn't strongly and unambiguously read by OCR, plus every long one (a swap
check), and renders them as sheets of 8 rows, one row per segment with up to 10 crops spread over its time
(`review_sheets.py`; `manifest.csv` maps row ids to segments). The roster card (`roster_card.py`) shows each roster
player in several views, half of them with a confident number or name read. Reviewer subagents label the rows;
`apply_review.py` merges their answers into the segments before the solve.

Over the last four games the reviewers handled 3042 rows on 387 sheets. Where OCR had a label they disagreed with
it on 23% of rows and reported a switch on 28% of the long rows that were there only for the swap check; on
unlabeled rows they named a player 48% of the time. So the selection isn't padding: don't trim it to save
reviewers.

## Prompts

`run_game.py review $W` fills `pipeline/review_prompt.md` once per chunk of sheets and writes
`$W/rev_pN/prompt_cNN.md`. Edit the template, not the prompts. It fills in:

- the roster (minus absent players), our jersey's look, and the goalie line ("#58 is the goalie" or "our goalie
  is not on the card");
- empty roster-card rows: a player with a row on another period's card gets a pointer to it (wingers swap sides, so
  a back turned away all period is common); one empty everywhere with under 30 reads "probably did not play"; one
  empty everywhere but read often "may have played; report the number if you see it";
- the opponents' look (`--opp`, saved in `$W/review.json`; default by our jersey) and your notes (`--note`,
  repeatable, e.g. a player's distinctive look, a borrowed jersey with someone else's nameplate, opponents who wear
  the same numbers as ours in their colour);
- a private scratch folder per reviewer under `$W/scratch/` (two reviewers once wrote to the same temp file).

The reviewer reads the roster card, then its sheets, and writes one CSV per sheet as soon as that sheet is decided,
so whatever finished survives a stall. Three sheets per reviewer and about six reviewers at a time is the size that
has worked; bigger chunks or many more at once tended to stall before writing anything.

Launch each `[todo]` chunk as one general-purpose subagent whose whole prompt is: "Read <prompt file> and do
exactly what it says. Reply with one line: how many rows you wrote." Start the next as each finishes. The
subagent's report comes back as a one-line message; nothing in the main context grows with the sheets.

## Coverage and relaunches

`run_game.py check $W` parses every `review_*.txt` exactly as solve does (`apply_review.parse_review`, which
tolerates a missing "R" and a "#") and lists the manifest rows without an answer, per sheet, plus any file whose
notes mention a failed image read. `review` then prints only the chunks still `[todo]`, with just the missing sheets
in each prompt. A reviewer that reported failed loads gets a fresh one: move its file to `old_review_sNNN.txt`
first (solve and check read only `review_*.txt`).

## A second opinion on specific rows

When a batch of rows needs re-checking (the roster in the prompt was wrong, a player was declared absent who
played, a swap looks doubtful), write a re-check prompt that lists the row ids with their sheet and the first
answer including the switch fields: re-checkers shown only the player column silently drop switches. Have the
re-checker write to its own file in its scratch folder, not into `rev_pN/`. Then merge by hand: dry-run the
changes (which rows change from what to what), and apply them one by one as lines in `review_zfix.txt`, which sorts
last and wins. On BW's Sep 20 game a 93-row re-check pass fixed a roster mistake this way.

## `review_zfix.txt`

Your own labels, in the review CSV format, with a note starting "checked by hand":

```
row_id,player,confidence,switch_time,player2,confidence2,note
R326,69,med,3776,90,med,checked by hand: 69 looks at the net for the goal; 90 white helmet from 3779
```

A later file overrides an earlier answer for the same row, so a zfix line replaces a reviewer's "?" (or a wrong
number). Tell the user which rows you labeled by hand, and say so in `game.json`'s notes.

## What went wrong before

- **A late arrival looks absent.** On BW's Sep 20 game #55 Lisenko arrived mid-second period; her P1 card row was
  empty and OCR had read her number 29 times (a ponytail hides it), so 30+ reviewers were told she hadn't played.
  One reviewer caught the LISENKO nameplate. Keep anyone LADA's lines list on the roster unless every period's
  card and the reads are empty; `review` now words the empty-row note by read count.
- **The empty-row line contradicts a note.** On BW's Oct 11 game #55 Lisenko again had no card row (7 reads), and
  `review` wrote "#55 probably did not play" right before the `--note` saying she was on the lineup; the line was
  reworded by hand in every prompt. This time she really hadn't played: no reviewer found her, and the other 10
  filled 102% of the spots in every period. Solve's shift-seconds line is the cleanest test of a missing player.
- **A non-player's number soaks up partial reads.** On Oct 3, #3 Ilinskaya didn't play, but "3" read off 43, 53
  and 35 labeled ~35 rows as #3, and a reviewer's "?" keeps the OCR label. That's what `run_game.py absent` is
  for; set it before prepare.
- **Borrowed jerseys.** Dukhno #50 played in a jersey with the DERKACHEV nameplate; a `--note` tells reviewers.
- **Two jerseys of ours at once.** On Beerteam's Oct 4 game four regulars (#10, #34, #41, #87) wore a white jersey with
  teal and black trim ("Lada Family XV") and the rest the usual royal-blue trim. Both passed the white test. A
  `--note` naming the four kept reviewers from calling them noise. The roster card shows such a split at a glance.
- **Prompt wording versus a `--note`.** The template asks for "G" on goalie rows. A note that said "mark him '-'"
  contradicted it and had to be fixed with sed in all 37 prompts (and in `review.json`, escaping the quotes). Word
  notes to match the template's codes.
- **A timeout late in the 3rd.** Beerteam's Oct 4 game had one at 2:34 of the 3rd (3687–3767 of video), which the
  lineup check showed as 3 on. The gap checker found it on the board's frozen clock and gave the time to the five who
  came out, as on Sep 20.
- **Opponents with our numbers.** Night Owls wore white #11, #35 and #43 against our light blue; the `--opp` text
  said a white jersey is an opponent whatever its number.
- **Our goalie as a skater.** At Snoqualmie A our goalie (light blue, red pads) was sometimes tracked as a skater
  away from the crease and kept a skater's shift running (Oct 11: a track labeled #11 parked by our net). Whoever
  checks the lineup gaps should be told which net is ours each period.
- **Referees as ours.** In Snoqualmie B's dim video referees' stripes passed the white-jersey test; reviewers
  mark them noise.
- **A number that never faces the camera.** Prozhogin #61 was labeled by hand in ten stretches from black shorts,
  banded socks and red gloves and the fact that no other defenceman was out with his partner. Gear plus who is
  accounted for settles most "?" rows.
- **A track that breaks at the bench door.** Several Beerteam gaps were a player's track ending at the bench
  boards and restarting a second later under a new id that the reviewers labeled: the unlabeled piece is the same
  player (compare positions and times in `segs_final.csv`), and a zfix line closes the gap. Conversely, a segment
  that starts behind the bench boards counts as on-ice from its first frame, so players stepping on during a
  goal can be listed as on; an `"off"` entry until the goal fixes it. Trimming segments to their first on-ice
  detection in shifts.py would fix this for every line change, but changes every game's numbers, so it waits for a
  regression pass over the archived folders.
- **A two-digit number OCR keeps reading as one.** On Y's Sep 21 game #14 Ber had no card row in any period
  (OCR took his 14 for Sokolov's 4), though 112 confident "14" reads were all him on the ice. A `--note` that he
  played all game, and to read 14 against 4 carefully, got him labeled. Before review, sheet a few crops of any
  regular whose card row is empty everywhere but whose number is read often.
- **The lineup check finds wrong labels, not just gaps.** On Sep 21 a 4-on stretch was a false line change: the
  solver had #14 off and #32 on at 48:00, but the "32" piece had one OCR read and started where #14's track ended,
  and two pieces labeled 70 and 37 were #18. A gap's subagent should judge who was on from full frames and the
  bench door, not trust the labels; the fixes go in as `on`/`off` spans, or as zfix lines when the piece is a
  review row (`manifest.csv` maps `tid` to row). When a reviewer and a full-frame check disagree, a zoom on the
  player at the bench door settles it.
- **A long row whose number shows only late.** On Y's Oct 12 game a 98 s row was labeled #18 "high" from its
  later crops, while #18's own row ran in parallel until 3531.6; the early crops showed no number, and the gap check
  read 97 on that player three times after he climbed over the bench boards. The tracker had swapped identities when
  #18's track ended. Two rows with the same label overlapping in time is the sign: the zfix line gives the early
  player with a switch to the late one at the other track's end.
- **Shifts under 20 s are dropped** (`final_stats.py`'s `MIN_SHIFT`), including a real shift cut short by the final
  horn: Sep 21's last 16 s show 3 skaters because Ber and Beregovoy came on 17–19 s before the end. That flag stays.
- **A timeout with the goalie pulled.** On Beerteam's Sep 20 game Cluster Pucks called a timeout the moment our
  goalie left the net; both teams stood at their benches for 36 s, and the solver had seven of ours "on" (6 were
  expected, with an `extra` span). The six who came out of the timeout get it (`on` entries), the rest are `off`.
- **A regular lost for minutes.** On the same game Kleiman #69 (KLEIMAN nameplate, black helmet; his number rarely
  faces the camera) was missing from four 2nd-period stretches, and the period came to 94% of its shift seconds.
  The gap subagent found him at the bench door each time, including a 225 s shift through a penalty kill. A period
  under ~97% with one player's time far below his other periods points at him.
- **A player who leaves hurt.** The opposite sign: on Beerteam's Sep 27 game Khristoforov #7 went down injured early in
  the 3rd and never came back, the 3rd still came to 101% (Volkov #94 moved back to defence), and #7's 3rd-period time
  was one shift. A period at ~100% with one regular's time far below his other periods means he left: a frame check
  at a few later line changes confirms it, and an `off` span from the injury to the period's end keeps him off.
- **The goalie who played isn't the roster's first.** Mark the goalies who didn't play absent too: the first goalie
  not absent is the one the prompts' goalie line and shifts.py use (Doofers' Sep 19: Wheeler #0 in goal, #1 and #20
  absent, no hand edits).
- **A number no one wears.** On Doofers' Sep 19 game two rows were labeled 19 off a sleeve; a reviewer's number
  joins the solve's roster, so it would have become a phantom player. Before solving, grep the reviews for numbers
  not on the roster; a zfix "?" keeps them out (the gap check later found one was Kleiman #69).
- **No goalie.** Doofers' Oct 4 game had no goalie until 51:40 of video (10:50 left in the 3rd): they skated six,
  with a skater (#52, #61 or #13 at different times) standing or kneeling in our net, and a padded goalie in a navy
  jersey came on through our bench then (the game sheet named Wheeler #0 in goal all game). Nothing before solve
  showed it: the crease zooms for `net` saw "someone in light blue at our net". The first solve said 103-104% of
  five, and its lineup check listed eight windows, most of them "6 on". The gap-check subagent counted six of ours
  by eye again and again and found the goalie's entrance. `extra` spans for the whole of P1 and P2 and P3 up to
  3100 brought it to 101-102% with one window left. Prepare had already dropped the stand-in's detections in our
  crease (the `net` filter), and the review had started, so prepare couldn't be redone; solve filled him in from
  the gaps between his tracks (a choppy track, on for 19 of 20 minutes). On a crease zoom, check for pads, a
  blocker and a goalie mask, not just a body at the net.
- **A sub in goal, again.** Doofers' Sep 27 game had David Pfeifer #54 (under `subs`) in goal in a red goalie
  jersey: #0, #1, #20 and #54 all went on the absent list, so the prompts' goalie line read "Our goalie is not on the
  card" and a `--note` named him and his colour; no prompt needed editing and no reviewer labeled anyone 54. The
  first gap check also gets the bench right only half the time at Kirkland's staggered changes: a second pass over
  the gaps it left (and over any shift over ~5 minutes) found #52 sitting a whole timeout and the next shift.
- **A sub in goal.** On LADA R's Sep 21 game Perry #99, listed under `subs`, played goal instead of #35, but
  the prompts' goalie line comes from the roster's first goalie and an empty-row line said #79 (a regular who
  played all game, number rarely readable) probably hadn't played. Both were fixed by hand in every prompt
  before launch, with `--note`s saying the same. Mark a sub who played goal absent (he isn't a skater) and read the
  goalie and empty-row lines of one prompt before launching any. On Oct 5 (Perry in goal again) marking the
  regular goalie #35 absent along with #99 made `review` write "Our goalie is not on the card" by itself. A
  `--note` named Perry, so the prompts needed no hand edits. On Beerteam's Sep 20 game the goalie was a spare
  not on `roster.json` at all (David Pfeifer, number never readable), and the prompts' "#1 is the goalie" line was
  replaced in every prompt with sed before launch.
- **"Noise" doesn't clear a label.** The template's answer format allows a number, "?" or "G", so most reviewers
  mark an opponent or referee row "?" with "noise" in the note, and a few write "noise" as the player.
  `apply_review` leaves an OCR label in place for "noise" and only weakens it for "?". On Doofers' Oct 10 game
  (opponents' yokes passing the white test) 50 of P1's 538 rows were opponents or referees still carrying one of our
  numbers from OCR. Solve still came to 100–102% per period, and the gap check fixed what it put on the ice. A
  "noise" code in the template plus clearing the label in `apply_review` would fix it, but it changes re-solves of
  archived folders, so it waits for the regression pass.
- **Seated players counted as on.** On LADA R's Oct 12 game at Snoqualmie A (our bench at the frame edge, right by
  the camera) the first lineup check listed eight "6 on" windows, and almost every one was a player sitting at our
  bench: his track, full of confident number reads, started there and the solver counted it as on the ice. The gap
  subagent found each by the nameplate on the bench and the moment he went over the boards. Because the solver keeps
  5 on, such tracks rarely show as a window, so a second pass over P2's segments that start at our bench and stay
  there found nine more. 25 on/off entries took the periods from 104/104/102% to 102/103/102%. At a rink like this,
  ask the gap subagent for that scan from the start.
- **A quick rest gets joined into one shift.** `final_stats.py` joins a player's shifts across gaps under 15 s
  (`MERGE_GAP`, meant for tracking loss), so a real 8 s rest at a goal shows him on for it. On Oct 10, #29 went off
  about 185 and came back at 193, and the goal at 191 listed six. An `off` span of 15 s (178–193) kept the shifts
  apart at the cost of 7 s of his time.
