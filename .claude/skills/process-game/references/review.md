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
