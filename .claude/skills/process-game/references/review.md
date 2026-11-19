# Reviewers and gap checkers

The visual review labels tracked segments before the solve; the gap checkers fix the lineup after it. Both are
subagents on briefs the code writes (`pipeline/review_prompt.md`, `pipeline/gap_prompt.md`): edit the templates, not
the briefs. Contents: the review; `review_zfix.txt`; a second opinion on rows; the gap checkers; what went wrong before
(roster and goalies, then the lineup check's cases).

## The review

Prepare picks every tracked segment that isn't strongly and unambiguously read by OCR, plus every long one (a swap
check), and renders them as sheets of 8 rows, one row per segment with up to 10 crops spread over its time
(`review_sheets.py`; `manifest.csv` maps row ids to segments). The roster card (`roster_card.py`) shows each roster
player in several views. On four October games reviewers disagreed with OCR's label on 23% of the rows that had one,
reported a switch on 28% of the long rows there only for the swap check, and named a player on 48% of the unlabeled
ones: the selection isn't padding, so don't trim it to save reviewers.

`run_game.py review $W` fills the template once per chunk of three sheets (`$W/rev_pN/prompt_cNN.md`) with the roster
minus absent players, our jersey, the goalie line ("G" for any goalie's row, ours or theirs, which the solve drops),
each period's empty card rows (a pointer to another period's card, or "probably did not play" under 30 reads, "may
have played" above), the opponents' look (`--opp`, default by our jersey), the notes (`--note`, repeatable; both kept
in `$W/review.json`, so a note is removed there), a private scratch folder per reviewer, and the `zoom.py` command
for a closer look. It lists at most 20 chunks per call (`--batch`; 17 at once is the most seen to work) and prints
what the prompts say beyond the template. Three sheets per reviewer and one CSV per sheet, written as soon as that
sheet is decided, are deliberate: bigger chunks stalled before writing anything.

`check $W` parses every `review_*.txt` exactly as solve does and lists the rows without an answer, the files whose
notes mention a failed image read, and the numbers reviewers gave that are off the roster or absent; `--wait` first
blocks until the last launch is answered (540 s at most). A reviewer that reported failed loads gets a fresh one:
move its file to `old_review_sNNN.txt` first (solve and check read only `review_*.txt`). A chunk `review` lists
again while its reviewer is still writing is marked: relaunch it only once that reviewer has reported back.

## `review_zfix.txt`

Your own labels for review rows, in the review CSV format, with a note starting "checked by hand":

```
row_id,player,confidence,switch_time,player2,confidence2,note
R326,69,med,3776,90,med,checked by hand: 69 looks at the net for the goal; 90 white helmet from 3779
```

It sorts last, so it overrides every reviewer's answer for the same row: a "?" for a misread number `check` lists,
the player a gap checker saw on a piece that is a review row (`manifest.csv` maps `tid` to `row_id`), a switch where
two rows carry the same label at once. Tell the user which rows you labeled by hand, and say so in the notes.

## A second opinion on specific rows

When a batch of rows needs re-checking (the roster in the prompt was wrong, a player was declared absent who played,
a swap looks doubtful), write a re-check prompt that lists the row ids with their sheet and the first answer
including the switch fields: re-checkers shown only the player column silently drop switches. Have the re-checker
write to its own file in its scratch folder, not into `rev_pN/`. Then dry-run the changes (which rows change from
what to what) and apply them as `review_zfix.txt` lines. On BW's Sep 20 game a 93-row re-check fixed a roster mistake.

## The gap checkers

`run_game.py gaps $W` turns solve's lineup check into one brief per period (`W/scratch/gaps/prompt_pN.md`, split
after 6 windows), with numbered items: the windows with the tracked pieces behind them, the 20 s around each flagged
goal, every shift of 5+ minutes, each ice-time collapse (a player under half his share of the other periods with 8+
minutes without a shift: a whole stretch, his look and his usual linemates' shifts), the leads earlier checkers left
open, and the long pieces in our bench zone (B1, B2, ...). Each brief also gives the board's clock for that period
(whether it stops at whistles or runs through stoppages: six checkers in four games had called a stretch live
because the clock kept running), our net, the bench and box, the period's own roster card and the tools (`frames`,
`--tracks` to draw our tracked boxes with track id and label, `follow` for one piece over time). Every item needs an
answer; `gaps --apply` merges the spans, keeps every answer in `scratch/gaps/answers.json`, names the items left
unanswered (an entry it can't read counts as none; the next round lists them again), turns leads into windows, and
prints a kill reported as 5 on 5 with `!!` and the two steps to take, without applying it. It saves before it renames
the fixes files, so a run that fails can be repeated. Later rounds show the spans already merged near each window and
skip what was settled (a window answered "ok" only while its seconds and its count on the ice are the same).
A window that the sheet's cleaning of hand-made spans explains (an `on` span under the 20 s minimum shift dropped, an
`off` rest under 15 s joined) is reported as settled, not briefed.

The Nov 1 additions found real errors (14 of 15 goal items, 10 of 10 long shifts, 39 of 81 bench pieces led to
spans) without cutting spans or rounds. A checker's cost is per item (a median 12.6 minutes and 35 images), and spans
under 5 s are 22% of the spans but 2.5% of the seconds moved, so nothing is gained by asking checkers to skip short
ones.

## What went wrong before

### Roster, numbers and goalies (before and during the review)

- **A late arrival looks absent.** BW's Sep 20: #55 Lisenko arrived mid-2nd, her P1 card row was empty and OCR had read
  her 29 times (a ponytail hides the number), so 30+ reviewers were told she hadn't played; one caught the LISENKO
  nameplate. Keep anyone LADA's lines list unless every card and the reads are empty. Solve's shift-seconds line is
  the cleanest test of a missing player (BW's Oct 11: the other ten filled 102% of every period).
- **A non-player's number soaks up partial reads.** Oct 3: "3" read off 43, 53 and 35 labeled ~35 rows as absent #3 —
  `absent` is for that, before prepare. The sheet can mark such a player playing: Doofers' Oct 25 #6 Zaychikov had 670
  reads of "6", all partials of 26/46/61/76, no nameplate read, and 3:10 after the first solve. `absent` set after the
  review still applies at solve.
- **A number OCR reads as another.** Y's Sep 21: #14 Ber had no card row anywhere (his 14 taken for Sokolov's 4)
  though 112 confident "14" reads were his; Y's Nov 9: `unknown` listed #27 with 285 reads, every crop AKULOV 37, and
  `absent --suggest` said Sokolov #4 played on reads that were Ber #14 and Bronnikov #74. Tislenok #98's sleeve read
  "91". Sheet a few crops of a regular whose card row is empty everywhere but whose number is read often, and give
  the reviewers a `--note` for each.
- **Borrowed and mixed jerseys.** Dukhno #50 played in a DERKACHEV jersey; on Beerteam's Oct 4 four regulars (#10,
  #34, #41, #87) wore a white "Lada Family XV" jersey with teal and black trim, the rest the usual royal-blue trim, and
  both passed the white test. A `--note` each; the roster card shows such a split at a glance.
- **A number that rarely faces the camera.** Prozhogin #61 (TK: black shorts, banded socks, red gloves) and Kleiman
  #69 (Beerteam: KLEIMAN nameplate, black helmet). Gear plus who else is accounted for settles most "?" rows: Prozhogin
  was labeled by hand in ten stretches because no other defenceman was out with his partner.
- **Opponents with our numbers.** Night Owls wore white #11, #35 and #43 against our light blue; on Doofers' Nov 8
  Rainucks' navy #38 and #46 passed the white test, their #38 filled our #38's P3 card row, and the solver gave most
  of Tislenok's P3 shifts to others (a checker found them by his look, the only one of ours in long plain black
  pants). The template now treats a card row in the opponents' colours as theirs, and a collapse window catches the
  dropped player. Put their shared numbers in `--opp`.
- **An opponent who passes our jersey test triples the review.** LADA R's Oct 19: Teamy McTeamface's navy with sky-blue
  panels passed the white test on 89% of crops and the first prepare made 295 sheets (80-120 is usual). Measure a test
  that separates them (`rinks.md`, "Jersey tests"), set `jersey` in `full/rink.json`, move `p*` and `rev_p*` aside and
  prepare again (222 sheets).
- **Goalies.** Mark every goalie who didn't play absent, and a sub who played goal absent too (he isn't a skater):
  the goalie line then says ours is not on the card, and a `--note` gives his look. Cases: Doofers' Sep 19 (Wheeler in
  goal, #1 and #20 absent), Sep 27 (Pfeifer #54 from `subs` in a red jersey), LADA R's Sep 21 and Oct 5 (Perry #99
  for #35), Beerteam's Sep 20 (a spare not on `roster.json` at all). Our goalie tracked as a skater away from his
  crease kept a skater's shift running at Snoqualmie A (Oct 11): the briefs give our net per period for that.
- **No goalie.** Doofers' Oct 4 had none until 51:40 of video: six skaters with one standing in our net. The first
  solve said 103-104% with eight mostly "6 on" windows; the checker counted six again and again and found the goalie's
  entrance. `extra` spans over the stretch brought it to 101-102%. Prepare had dropped the stand-in's detections in
  our crease, and solve filled him in from the gaps between his tracks.
- **Word notes to match the template's codes.** A note that said "mark him '-'" for a goalie contradicted the
  template's "G" and had to be fixed in all 37 prompts.
- **"N" clears an OCR label**, and so does a "?" whose note is about noise, opponents or referees in every part (how
  reviewers wrote it before "N" existed); a bare "?" keeps it. On Doofers' Oct 10 (opponents' yokes passing the white
  test) 50 of P1's 538 rows had been opponents or referees still carrying our numbers.
- **A stuttering stream.** LADA R's Oct 19 video carried only ~2 distinct frames a second from 45:30 to 66:00
  (YouTube's copy too): tracks fragmented and the stoppage estimate saw everyone still until `stoppages.py` learned to
  skip repeated frames. Check with ffmpeg's `mpdecimate` over 10 s (about 230 frames kept is normal at 24 fps), and
  give the checkers a `--note`: frames at least 0.5 s apart.

### The lineup check's cases

| What the check shows | What it was | The fix |
|---|---|---|
| "6 on" stretches; pieces that start at our bench and stay there | a seated player the tracker followed as on (most at Snoqualmie, by the camera: on LADA R's Oct 12, 25 spans) | `off` spans; `gaps` lists those pieces as bench items |
| 4 on at a "line change": a piece with one read starting where another's track ended | a false change: wrong labels (Y's Sep 21: "32" was #14, "70" and "37" were #18) | judge from full frames and the bench door; spans, or a zfix line when the piece is a review row |
| two rows with the same label overlapping in time | the tracker swapped identities at a track's end (Y's Oct 12: a 98 s row labeled #18 was #97 until late) | a zfix line with a switch to the other player at the other track's end |
| a gap at the bench boards, a new id a second later | one player's track broken at the door | a zfix line or an `on` span |
| a player's time far below his other periods, the period at ~94-97% | a regular lost for minutes (BW Sep 20: Kleiman #69, a 225 s shift through a kill) | the collapse window |
| a period at ~100%, one regular's time far below his other periods | he left (Beerteam's Sep 27: Khristoforov #7 hurt early in the 3rd) | an `off` span from then to the period's end |
| odd counts with a frozen clock, players at both benches | a timeout (Beerteam's Oct 4: 3 on; Sep 20: one when our goalie was pulled, 7 on) | the five (six) who came out get it; the template says so |
| a goal listing six of ours | a real rest under 15 s joined into one shift (`MERGE_GAP`; Oct 10: #29 off 185-193) | an `off` span of 15 s |
| 3 on in a period's last seconds | a real shift under 20 s dropped (`MIN_SHIFT`; Sep 21's last 16 s) | none: the sheet drops it; the checker's "ok" settles the window |
| a long shift hiding a seated stretch | a player sitting through a timeout (Kirkland) | the 5+ minute shift window |

Seated players are the biggest by-eye cost at Snoqualmie: on the 33 archived games of Nov 1, 27 spans a game at rink A
and 48 at rink B, and 173 of the 328 `off` spans covered seconds where the player's own track stood at the bench.
Counting such seconds as off in the solver was measured and dropped (README's TODO): a player standing at the door
reads the same as a seated one. Renton's re-aimed camera has needed a median 27.5 spans a game since Nov 7, with
about 10 bench pieces a game.
