# Rinks, benches, jerseys, scoreboards

Each camera's geometry is a class in `pipeline/rink.py`: the detection crop, the far boards, the ice, the benches and
boxes, the nets, the scoreboard box with the clock and shots digits, the `views` that `run_game.py frames --view`
crops (`rink`, `left-net`, `right-net`, `bench`), the bench our jersey puts us on (`bench_by_jersey`) and the one
sentence the checkers' briefs give for the rink (`brief`). `fetch --rink` records the class in `$W/full/rink.json`;
a folder without one is `renton`, the old camera. Pick the class by the frame size and view of `frame600.png`, not
by LADA's `rinkName` alone.

| Class | Video | Camera | Our bench (fetch sets it) | Boxes | Nets x | Clock |
|---|---|---|---|---|---|---|
| `renton` | Renton to Oct 4, 3840x1702 (3600x1596, 3246x1440 scaled) | high, near side | behind the far boards: light blue left (away), white right (home) | between the benches: away x 1740-1770, home 1945-2055 | 540, 3245 | runs through stoppages in the 1st and 2nd, stops at whistles in the 3rd |
| `renton2` | Renton from Oct 17, 3840x1920 | fisheye, low at center, near side | as `renton`: away from the post at x 1380, home to x 2500 | away 1735-1865, home 2020-2150 | 560, 3345 | as `renton` |
| `renton2band` | LADA Y's Oct 12, LiveBarn 3600x1800 with a black band over the top 264 rows | `renton2`, 266 px lower | as `renton2` | as `renton2` | as `renton2` | as `renton` |
| `renton2thin` | LADA R's Oct 19 and 26, 2560x1280 with a thin band | `renton2`, 62 px lower | as `renton2` | as `renton2` | as `renton2` | as `renton` |
| `renton2nov` | Renton from Nov 7 (re-aimed), 3840x1920 | `renton2` re-aimed, ~65 px left; rolled about 1 degree since Nov 15 | away from the post at ~1310 to 1665, home 2080 to ~2430 | away 1665-1795, home 1950-2080 | 500, 3285 | as `renton` |
| `snoqualmie` | Snoqualmie A, a 3840x1536 strip (3440x1376, 3438x1374) | high at center, near side, very wide | near side at the frame edges: white left (home), light blue right (away) | home: near-left corner, bottom-left; away: just left of our bench, x 3450-3700 | 630, 3260 | as `renton` |
| `snoqualmie2` | Snoqualmie B, the whole fisheye frame 3824x2160 (YouTube often 2548x1440) | as A, fisheye, dim and grey | as `snoqualmie` | on the near side next to each bench | 680, 3270 | as `renton` |
| `kirkland` | Kirkland, 3840x1536 (3600x1440, 3438x1374) | fisheye, low at center, near side | behind the far boards, doors at the blue posts (x 1612, 2265); no jersey rule: fetch keeps its right side, check `bench_left.jpg`/`bench_right.jpg` | the near corners at the bottom, on each bench's side | 605, 3255 | as `renton`, and it also stops in the last minute or two of the 1st and 2nd |

The bench rules held on every archived game (Renton: light blue left 15 of 15, white right 6 of 6; Snoqualmie A and
B: white left 14 of 14, light blue right 7 of 7). At Kirkland we sat left in white once and right twice, left and
right once each in light blue; Doofers were LADA's away team there on Sep 27 and sat at the home bench.

## What has held at every rink (53 games by Nov 18)

- **Which side of the board we are.** Usually LADA's `playHome`, but go by the final score: LADA Y were away in LADA
  and HOME on Kirkland's board on Sep 14. The goal and penalty briefs tell the checkers which side the sheet gives us.
- **The period clock is the only reliable period source.** The empty-ice proposal has merged periods, started a 3rd
  inside the intermission countdown and been 11-40 s off; fetch now uses it only as a cross-check (a warning past
  100 s), and as the periods when the clock gives none (it logs `periods from the empty ice`). A period starts when the clock first counts down from 18:00 (the opening faceoff; the board can sit at 18:00
  through a minute of play, see Kirkland) and ends at its first 0.0, or earlier where play stopped and the operator ran
  the rest off on an empty rink (`run_game.py skaters` drops from 6, `break_*.jpg` shows nobody playing). After the 1st
  and 2nd the board counts a 1:00 intermission down (1:30 and 2:00 seen) with the old period still lit: play's last
  minute shows tenths ("45.9"), a countdown 0:ss ("0:45"). On the one-a-minute `sb.jpg` tenths read like minutes
  ("43.1" looks like 4:31).
- **Reading the clock** (`clock.py`). The recogniser reads the seconds well and the minutes badly: it drops a thin
  leading 1, runs "16" into one character at Snoqualmie A and reads 18:00 as "800" at Snoqualmie B. The LEDs can stay
  dark for 15 s and more; the fit then assumes the clock kept running, so an edge in a dark stretch is an estimate
  (fetch's `clock:` line says so). Three period ends the reader got wrong, all at an end tile that wasn't a plain 00.0:
  Y's Oct 19 1st (Snoqualmie A) held at 1.2 for 4 s before running out (the end is the 0.0 after the hold); LADA R's
  Nov 2 3rd (Snoqualmie A) showed "1:02" with the 1 unlit, read as 0:02, and ended 148 s early; the Snoqualmie B Oct
  25 operator set the clock back from 1:05 to 1:09 and the reader ended the 3rd there, 134 s early. So when the end
  tiles of `clock_check.jpg` show the same non-zero digits, or 0:0x without tenths, sheet the board 2 s apart to the
  video's end. Fix an edge before prepare: prepare tracks only inside the periods, and on R's Nov 2 the last 2:24
  of the 3rd had to be given by a lineup checker as spans. An edge found wrong once the review has started is still
  corrected in `periods.json`, without preparing again: the lineup check lists the untracked seconds and the checkers
  give them as `on` spans (Y's Oct 5 at Kirkland: P1 moved back 50 s to the opening faceoff, and solve came to 100%).
  `clock.py $W` on an archived folder reads
  `scoreboard_jpg.npz` again and prints where `periods.json` differs.
- **The clock runs through stoppages in the 1st and 2nd and stops at whistles in the 3rd**, on all 20 games with a
  clock read (the gap briefs say which per period). So in the 1st and 2nd "period start + 18:00 minus the clock" gives
  an event's video second to a second or two, until the operator takes a minute off (LADA R's Oct 5: 3:00 to 2:00
  with play going on).
- **Minors run 3:00 on the board in the 1st and 2nd and 2:00 in the 3rd**, whatever the sheet says (2:00); `pk`
  proposes them so. 4:00 and 6:00 seen at Kirkland. The panel lights 12-30 s after the whistle (the scorekeeper posts
  it at the next faceoff) and counts from the faceoff, so a kill runs from the whistle the box trip shows to the panel
  going dark. A box attendant has kept a player in 22 s after the panel went dark (the kill ends when he steps out),
  and referees have sent one back for 4 s at the next whistle (a second `pk`, with an `on` span between). A
  power-play goal against ends the minor while the panel can stay lit (Doofers' Oct 18: frozen at 0:44 for 33 s). A
  minor carried into the 3rd is rescaled to the 2:00 length (1:14 left at the 2nd's buzzer showed 0:50).
- **Scorekeepers slip.** Penalties on the wrong team's panel, a penalty posted and removed at one stoppage, the guests
  shown a goal too many for a while, a goal counted that never happened (Beerteam's Oct 4: score and shot up with the
  clock frozen and the players lining up), a goal the sheet misses (Blue Wings' Nov 7: the board 6-5, the sheet 5-5,
  corrected to 6-5 days later), goals posted late (Blue Wings' Nov 7 one 3.5 minutes late; Y's Nov 9 one 100 s late in
  live play; R's Nov 2 one 8 s after the horn). The penalty box decides whose a penalty is; the sheet's score stands.
- **Our goalie's net** switches each period and starts at our bench's end (141 of 141 periods). Fetch proposes it by
  that rule, the opening faceoff and the crease count. Doofers skated without a goalie for two periods on Oct 4: a
  crease zoom needs pads, a blocker and a mask, not a body at the net.
- **The board's shot digits are a few pixels tall**: `shots.py` was wrong at most games (Snoqualmie A's board showed
  no away shots on Oct 12), so the sheet's shots are the default. The board lags the sheet by a shot or two at period
  ends.
- **The board flickers.** Its LEDs are dark in most single frames at Renton, so `scoreboard.py` keeps the brightest
  frame of each second (`$W/scoreboard.npy`, `$W/sb.jpg`; archive keeps `scoreboard_jpg.npz`). The camera isn't framed
  the same every game, so `clock.py` moves `clock_box` to where the board changes most before reading.
- **Sound.** The original wide cuts were silent; LiveBarn recordings (3438x1374, a score panel top-left and a timeline
  bar along the bottom, both outside the ice), Renton's new camera and TK's Nov 1 cut at Snoqualmie A have audio: the
  whistles (about 2.4 kHz) pin goals and calls, and the clips keep the sound. Check each recording.
- **Frame sizes and framing.** Fetch scales a smaller video of the same view up to the class's `size` (keeping
  `video_<W>x<H>.webm`) and measures the far-boards curve against `ref_boards` first. At Kirkland and Snoqualmie B
  (`reframe`) an offset over 20 px is shifted into place in the same encode (late LiveBarn uploads under a black band
  sat 53 to 70 px low); elsewhere it is logged (Snoqualmie A's 52 px lower framing is tolerated, and its `clock_box`
  is found anyway). A fetch that already detected on a misframed video stops with a message to move `full/` aside.

## A camera that moved (Renton)

Where the far boards sit more than 20 px (median) off the usual curve of the Renton class fetch was given, its
`framing` line names another class whose curve fits within 25 px, or prints the turn and shift onto the given class's
ice-map camera (`rinkcam.align`). A smaller offset prints nothing, whatever the curve's shape.

A class that fits: fetch starts the board scan seconds after that line under the class it was given, so stop fetch,
move `$W/scoreboard.npy` and `$W/clock_reads.json` aside if they exist (the clock's reads are cached by `clock_box`,
which most Renton classes share), and run the same fetch with that `--rink`. Detection and OCR carry on (the classes
share `crop_top`); the board is scanned and read again and the periods and nets proposed again (into `periods.json`
unless you have edited it, else into `periods.proposed.json`).

A turn of up to 1.5 degrees is a roll: run as the given class if the nets, the bench and the board crop hold on
`frame600.png`, and the ice maps correct it. Turbo Kings', Blue Wings' and Doofers' Nov 15 games were such a roll
against `renton2nov` (-0.96 degrees, a 19 px drop, residuals 3 px across the middle; the center line leans about 30 px over the frame's height) and ran as `renton2nov`.

A larger turn, with the center line upright, is a re-aim: TK's Nov 8 game against `renton2` (-2.62 degrees; the curve
55 px higher at the left end and 108 px lower at the right, everything about 65 px left). Measure a new class off
`frame600.png` before the scoreboard scan runs: the board, nets, box posts, near boards and center line, each with a
ruler crop (`renton2nov`'s values in `rink.py` are an example), then calibrate the ice maps (`references/ice.md`).
Under the wrong class the board crop catches only the board's edge, and the clock, the periods and `sb.jpg` with it.

## Renton

Both cameras look at the same rink: the benches behind the far boards, away left of center and home right, with the
penalty boxes between them. A boxed player is tracked as "at the bench": he climbs over the boards there and skates
off when it ends, with his number readable on the way.

- **Old camera (`renton`).** The proposal merged periods and reversed nets there more than once; the board was dark
  around a period's 0.0 more than once (a 2 s sheet over the last minute pins the end). The camera was fixed all game
  on Sep 28 whatever a checker says (phase correlation of `full/ov/` frames gave zero). Views: `rink` 0-3840 ×
  700-1500; `left-net` 150-1450 × 720-1070; `right-net` 2500-3800 × 720-1070.
- **New camera (`renton2`, `renton2nov`).** Fisheye from low at center behind the netting; the far boards bow up to
  y ~340 at center, the nets sit right in front of the end boards' kick plate, where the curve is steep (the crease
  is a box: `in_crease`). The scorekeeper's window is at center; he wore light blue and passes our test, but sits
  outside the bench zone. A player at the far boards is ~75 px tall, near the camera ~500 px. Bench sitters show only
  their heads; line changes are tracks ending at the boards. The board is small and tilted in the right corner
  (readable on `sb.jpg`, not by `shots.py`). The video has real audio. The board was often dark for stretches (Blue
  Wings' Nov 7 at four of six period edges; Blue Wings' Nov 15 across one goal each way): where it is blank across a
  penalty call, take the call's time from the frames (Doofers' Nov 15: the sheet-implied time was 20 s late). TK's
  Nov 8 video stopped at 3970 with 20 s or more on the clock: the 3rd ends at the video's end (`--video-ends-early`).
  Views `renton2`: `rink` 0-3840 × 220-1920; `left-net` 100-1300 × 480-1080; `right-net` 2600-3800 × 470-1070;
  `renton2nov`: `left-net` 40-1240 × 480-1080, `right-net` 2540-3740 × 470-1070.
- **The same camera framed lower.** LiveBarn's cuts: `renton2band` (a black band and logo over the top 264 rows,
  everything 266 px lower; the scoreboard crop under `renton2` showed the ceiling) and `renton2thin` (a thin band,
  62 px; no error under `renton2`, since the size matches: compare `full/boards_poly.npy` with a `renton2` game's).
  Any other shift is another class like them. Switching to one is in "A camera that moved" above.

## Snoqualmie A (`snoqualmie`)

Blue Wings' home rink. Both benches are on the near side at the frame edges, so bench sitters are close to the
camera, make over half of all crops (their reads are skipped: `ocr_skip_depth`) and get tracked as if on the ice:
`gaps` lists those long pieces and the checkers find each by the nameplate on the bench and the moment he climbs over.
Seated players are most of the by-eye work here. As away, a boxed player sat about 20 s after the whistle.
Intermissions are short (`min_break` 10 s): players stand at the bench doors, then skate out to warm up.

- Period ends haven't followed one rule: on BW's Oct 11 and Y's Sep 21 the 1st and 2nd stopped with 1:25, 1:03 and
  ~55 s left, the board ran the rest off on an empty rink and the next period began ~25 s after 0:00; later games ran
  each period to 0.0. On Oct 5 the 2nd ended on a goal against with 2 s left and the clock was then run out: end the
  period at the goal.
- On LADA R's Oct 12, Doofers' Oct 18 and Beerteam's Oct 25 the board sat about 50 px lower: the clock is still found,
  but the shots panel falls below the crop and `shots.py` reads nothing useful. `boards.py` there gives [569, 504,
  538, 560, 648] at x 200/1000/1920/2800/3640 against the usual [517, 453, 486, 509, 595]. To compare before fetch,
  run `boards.py` on a scaled frame into a scratch folder holding a `rink.json` with the rink (without one it uses
  Renton's band and the curve looks like a wild misfit).
- Players gathered at our bench late in a game may be in a timeout (a 30 s timer on the board): R's Nov 2 at
  3780-3805; on Y's Nov 9 one sat inside a 100 s stoppage that `stoppages.py` counted as live.
- Jerseys: Flounders' white with light-blue trim passed our light-blue test a little (their #12 BUSH read 47 times);
  Night Owls wear white #11, #35 and #43 (`review.md`). On Oct 4 both goalies wore white with white pads: where the
  goals went in settled the nets.
- Views: `rink` 0-3840 × 380-1536; `left-net` 200-1400 × 380-760; `right-net` 2600-3800 × 380-760; `bench` 0-900 ×
  700-1536 (left) or 2940-3840 × 700-1536 (right).

## Snoqualmie B (`snoqualmie2`)

The same camera spot, the camera's whole fisheye frame: the far boards bow up to y ~870 at center, the near boards
run along the bottom. The picture is dim and grey (the ice V ~150, white jerseys no brighter, blue numbers barely
show), so the class has its own brightness levels and jersey tests: white is little dark in the torso, light blue
counts blue from saturation 25 (`blue_s`), ours 5%+ against 0-2% for white jerseys and referees. That light-blue test
came from Doofers' Oct 25, the first light-blue game here: the plain test had passed 0.8 of our players a frame and
given whole players no time. Check a new jersey at a rink before prepare: our on-ice detections per frame
(`track.load(...)`: `ours & onice`) should be near 5, not 1.

- Referees' stripes and dark jerseys with a cream or white yoke (Sentinels, Frost Giants) pass the white test: twice
  the usual review sheets, `skaters` reading 8-10, and their numbers in `unknown` (their #13 and #16 read hundreds of
  times on Oct 10, so our absent #13 and #16 had to be on the absent list). Puck Buddies OG's red with white
  nameplates did too (#64, #7 LONGFELLOW; their #7 swelled our #7's reads): look at the crops before trusting a
  number's count. SEA Otters' red and black didn't.
- YouTube had these videos only at 2548x1440 on Sep 19, Oct 10 and Nov 7 (scaled up; the geometry fits); TK's Oct 25
  came at 3824x2160. A late upload sitting low (Doofers' Oct 25: 70 px) is shifted by fetch now.
- Seen here: the proposal merged the 1st and 2nd or put all three edges 11-40 s off; a 2:00 intermission; the board at
  18:00 until the opening faceoff at 0:11 (Oct 10); our goalie in white with dark pads against theirs in light blue
  (in a lopsided period the play sits at their net).
- Views: `rink` 0-3824 × 800-2160; `left-net` 80-1280 × 820-1370; `right-net` 2620-3820 × 820-1370; `bench` 100-1100 ×
  1250-2160 (left) or 2724-3724 × 1250-2160 (right). The nets sit at about (645, 1015) and (3250, 1020); early in a
  video a net may not be on the ice yet, so check on a frame from the game.

## Kirkland (`kirkland`)

Fisheye from low at center on the near side: the far boards bow up to y ~430 and dip to ~700 at the edges, where the
end boards run down the sides. A boxed player drops out of the bottom of the frame as he sits: read his number on the
way in.

- The HOCKEY sign at the right has yellow letters that pull the boards fit up; `board_lowest = True` keeps only the
  lowest yellow run per column.
- Intermissions are about a minute with a referee on the ice, so the empty ice finds one period or all three 20-40 s
  off. The penalty clock jumped during an intermission (2:33 to 1:42): for a carried-over penalty use the moment the
  panel goes dark.
- The operator can start the clock late: on LADA Y's Oct 5 the board sat at 18:00 for the first 55 s while the game
  went on (opening faceoff at 0:05, a goal against at 0:41). Before prepare, look at the first minute (`frames --view
  rink 0 4 8 ... 40`) for play under a frozen 18:00, and start P1 at the faceoff.
- Jerseys: Teamy McTeamface's white with big sky-blue panels needs `light blue vs sky blue`; Rainucks' white with blue
  numbers and green-and-blue stripes passed the light-blue test too (`unknown` listed six of their numbers); their
  goalies were told apart by colour. BladeRunners wear red.
- At Kirkland's staggered changes the first gap check has got the bench right only about half the time; a second
  round over what it left (and any shift over ~5 minutes) found #52 sitting a whole timeout.
- Views: `rink` 0-3840 × 320-1536; `left-net` 150-1350 × 400-800; `right-net` 2600-3800 × 400-800.

## Jersey tests

`JERSEYS` in `rink.py` turns `process.py`'s torso colour fractions into "ours" (tracked, applied at prepare) and
"crop" (cut and read; set before detection). A rink can override a test for its lighting (`jerseys` and `blue_s` on
the class, as Snoqualmie B does; a change to `blue_s` means detecting again).

| Test | When | Measured |
|---|---|---|
| `light blue` | the default: our light blue | |
| `white` | our white: a white torso with little dark, under 10% red | Sea Otters' red with white stripes is 30-50% red |
| `light blue vs sky blue` | against white jerseys with big sky-blue panels (Teamy McTeamface): adds a hue test | `bhue` ours ~113, theirs ~107 |
| `white vs light blue` | against LADA's other light-blue team (`lada.md`, "A game between two LADA teams") | 174 review sheets down to 114 |
| `white vs navy and sky blue` | against navy with sky-blue panels and white numbers (Teamy McTeamface, LADA R's Oct 19) | kept 90% of ours, 11% of theirs |
| `white vs royal blue` | against royal blue with red numbers (Weekday Benders, LADA R's Oct 26) | kept 89-100% of ours, 1-6% of theirs |

A wrong test loses our far-side players silently, so whenever the picture looks different from before, run YOLO on a
few frames and check the test before detection. Detection only saves crops of players who pass the crop test, so a
jersey set wrong afterwards means `run_game.py jersey $W <name>` (~5 min for a few crops, 22 min of decoding for 100k
on a 66-minute video). An opponent can pass our test on its trim alone (Roadrunners' #4 ORR in grey-white with
light-blue stripes made most of 88 reads of "4"), and a dark opponent can pass the white test wholesale on a fisheye
camera, where the ice behind a player fills the box (Weekday Benders: 75%, five of their numbers with 400-670 reads;
they also wear our #66 and #39, whose reads were mixed).
To measure a new test before prepare (no detection rerun: the "ours" test applies at prepare), join `dets.csv` (row
order within a frame = the crop's `_NN`) with the OCR reads, compare the colour fractions of crops read as our numbers
against crops read as theirs, and leave out numbers both teams wear.

## A rink that isn't in `rink.py`

Stop before detection. You don't have to wait for the download to look at it:

```sh
U=$($PY -m yt_dlp -g -f 313 "<url>"); $FF -loglevel error -ss 600 -i "$U" -frames:v 1 $W/frame600.png   # FF: imageio_ffmpeg's ffmpeg
```

Add a class: `crop_top` above the heads of players at the far boards (a wrong crop silently loses them), the board
band, the ice polygon, the benches (with `bench_where`, `box_where` and `bench_view` for the briefs, and
`bench_by_jersey` once a few games show a rule), `brief`, the nets, `scoreboard` (x, y, w, h, all even: ffmpeg rounds
an odd crop of yuv420 video down, every raw frame read then drifts a row, and the scan shows two half boards and runs
short of the video), `clock_box` (the period clock's four digit cells inside that crop, x0, y0, x1, y1, as a level
rectangle) with `clock_tilt` (degrees it is turned to lie on the digits, positive when they slope down to the right;
31 at Renton's new camera), `shots_boxes`, `views`, `ref_boards`, and `board_lowest` if there's yellow lettering above
the boards. Run `boards.py` on the frame and draw its curve over it to the frame edges. Then YOLO on a few frames and
the jersey test under that lighting, and only then detection. Register the class in `RINKS`. Once the board is
scanned, `clock.py $W` prints the box's offset (a few px is normal; tens of px means it was measured on another
framing) and writes `clock_check.jpg`: each row should show 18:00, 18:00, 17:59 and the period's last seconds to
00.0. Then calibrate the ice maps (`references/ice.md`).
