# Rinks, benches, jerseys, scoreboards

Each rink films from a different spot, so the camera geometry lives in a class in `pipeline/rink.py`: the detection
crop, where the far boards are, the ice polygon, our bench, the nets, the scoreboard box, the shots digits, and the
`views` that `run_game.py frames --view` crops (`rink`, `left-net`, `right-net`, and `bench`: our bench and its
door, mirrored to the side we sit on). `fetch --rink` records the rink in `$W/full/rink.json`; a folder without one
is Renton. Pick the rink by the frame size and view of `frame600.png`, not by LADA's `rinkName` alone.

## What has held at every rink so far (29 games)

- **Jerseys and benches.** Home wears white (blue numbers and trim), away light blue. The home bench at Renton and
  Kirkland is right of center, the away bench left; at Snoqualmie home is left, away right. Set the bench from
  `frame600.png` (our jerseys sit at our bench), never from home/away: Doofers were LADA's away team and the board's
  guests at Kirkland on Sep 27 and still sat at the home-side bench. Fetch defaults to each rink's usual side
  (`bench_side`), so a home game at Snoqualmie needs `--bench left`.
- **Which side of the board we are.** Usually LADA's `playHome`, but go by the final score: LADA Y were away in LADA
  and HOME on Kirkland's board on Sep 14.
- **The period clock is the only reliable period source.** The empty-ice proposal has been wrong at nearly every
  game: periods merged (two into one, or the whole video as one), a 3rd started 90 s early inside the intermission
  countdown, nets reversed, edges 11–40 s off. Take every edge from the clock on `sb.jpg`, then a 2 s sheet around
  it (`scoreboard.py $W out.jpg $(seq a 2 b)`): a period starts when the clock first counts down from 18:00 (the
  opening faceoff; the board can sit at 18:00 through a minute of play first, see Kirkland) and ends at its first
  0.0, or earlier where play stopped and the operator ran the rest off on an empty rink (`run_game.py skaters`
  drops from 6, `break_*.jpg` shows nobody playing). After the 1st and 2nd the board counts a 1:00 intermission
  down (1:30 and 2:00 seen) with the old period still lit, which looks like a last minute of play: play's last
  minute shows tenths ("45.9"), a countdown shows m:ss. On the one-a-minute `sb.jpg` the tenths read like minutes
  ("43.1" looks like 4:31).
- **The clock runs through stoppages in the 1st and 2nd and stops at whistles in the 3rd**, in every game so far
  (Kirkland: it also stops in the last minute or two of the 1st and 2nd). So "period start + 18:00 minus the clock"
  gives a 1st or 2nd period event's video time to a second or two, until the operator takes a minute off (LADA R's
  Oct 5: 3:00 to 2:00 with play going on).
- **Minors run 3:00 on the board in the 1st and 2nd and 2:00 in the 3rd**, whatever the game sheet says (it calls
  them all 2:00), at every rink; 4:00 and 6:00 seen at Kirkland. The panel lights 12–30 s after the whistle (the
  scorekeeper posts it at the next faceoff, once stopping the running clock to do it) and counts from the faceoff,
  so a kill runs from the whistle the box trip shows to the panel going dark, and the sheet's clock time is the
  posting's or the faceoff's. A box attendant has kept a player in 22 s after the panel went dark (the kill ends
  when he steps out), and referees have sent one back for 4 s at the next whistle (a second `pk` span, with an `on`
  span for him in between).
- **Scorekeepers slip.** Penalties on the wrong team's panel (Kirkland: ours on the guest panel while the score sat
  on the home side), a penalty posted and removed at the same stoppage, the guests shown a goal too many for a
  while, a goal counted that never happened (Beerteam's Oct 4: the score and a shot went up with the clock frozen
  and the players lining up), the clock run on an empty rink after play ended. The penalty box decides whose a
  penalty is; the sheet's score stands over the board's.
- **Our goalie's net** switches each period, and the proposal gets it backwards often. At Snoqualmie (both cameras)
  every home game had him in the left net in the 1st and 3rd and every away game in the right; at Renton home games
  had him right in the 1st and 3rd and away games left. Check a crease zoom per period anyway, for pads, a blocker
  and a mask rather than a body at the net (Doofers skated without a goalie for two periods on Oct 4), or go by
  where the goals went in when both goalies wear white.
- **The board's shot digits are a few pixels tall**, and `shots.py`'s OCR was wrong at most games (nearly always at
  Renton, Kirkland and Snoqualmie B; Snoqualmie A's board showed no shots at all for the away side on Oct 12), so
  the game sheet's shots are the default and `shots_check.jpg` a cross-check. The board itself lags the sheet by a
  shot or two at period ends.
- **The board flickers.** Its LEDs are dark in most single frames at Renton, and dark for whole stretches on Oct 12
  (1196–1250 s, right across a faceoff), so `scoreboard.py` keeps the brightest frame of each second; fetch scans
  it into `$W/scoreboard.npy` and `$W/sb.jpg`, and archive keeps the frames as `scoreboard_jpg.npz`.
- **Sound.** The original wide cuts are silent. LiveBarn recordings (3438x1374, LiveBarn's score panel top-left and
  a timeline bar along the bottom, both outside the ice) and Renton's new camera have audio: the whistles (about
  2.4 kHz) pin goals and calls to a fraction of a second and the clips keep the sound. Check each recording.
- **Frame sizes.** Every rink's class has a usual `size`; fetch scales a smaller video of the same view up to it
  and keeps the original as `video_<W>x<H>.webm`. Seen: Renton 3600x1596 and 3246x1440 (the late games),
  Snoqualmie A 3440x1376 and 3438x1374, Snoqualmie B only 2548x1440 on YouTube, Kirkland 3600x1440 and 3438x1374.

## Renton (`renton`, 3840x1702)

Camera high on the near side. Both benches are behind the far boards: away left of center, home right. The away
team's penalty box is the glassed compartment just right of the away bench (frame x about 1740–1770, past the glass
post at x 1712), the home team's the matching compartment left of the home bench (x about 1945–2055, a boxed player
at about 2000). A boxed player is tracked as "at the bench": he climbs over the boards there and skates off when it
ends, with his number readable on the way. Nets at x 540 (left) and 3245 (right).

Seen here: the proposal merged the 1st and 2nd (LADA R Sep 21), the 2nd and 3rd (LADA R Sep 14, Beerteam Sep 27,
which it also put at the 1st's net), or the whole video into one period (LADA R vs LADA Y Sep 28), started the 3rd
90 s early inside the countdown and the empty-board wait after it (Doofers Oct 4, with its net reversed), and was
19–36 s off at four of five edges (Doofers Sep 13, whose 1st ended at 18:16 of video at the board's first 00.0, not
18:41, and whose 2nd and 3rd started at the faceoff, 36 s and 19 s after it). Beerteam Sep 13: the operator let
the 2nd period's clock hit 00.0, then ran an extra minute on an empty rink, and let the 1st's last 45 s run after
play had ended. LADA R Sep 21: the board's shot count fell behind the sheet in the 3rd (about 20–29 against the
sheet's 22–39), so the shots came from the sheet. The board was dark (flicker) for the seconds around a period's
0.0 more than once: a 2 s sheet over the last minute pins the end. The camera was fixed all game on Sep 28,
whatever a checker says: phase correlation of `full/ov/` frames gives the shift, and it was zero.

Views: `rink` 0–3840 × 700–1500; `left-net` 150–1450 × 720–1070; `right-net` 2500–3800 × 720–1070.

## Renton, new camera (`renton2`, the whole fisheye frame, 3840x1920)

From Turbo Kings' Oct 17 game (9:15 PM) Renton's video comes from a new camera low at center ice on the near side,
behind the netting, with a fisheye lens: fetch stops with "video is 3840x1920 ... new framing" under `renton`. The
far boards bow up to y ~340 at center and drop to ~1030 at the frame edges; the near boards run along the bottom.
The rink is the same, so the benches are still behind the far boards: away (light blue) from the glass post at
x 1380 to ~1735, then the away box (1735–1865), the scorekeeper's window at center (the scorekeeper wore light blue
and passes our jersey test; he is outside the bench zone, so he isn't tracked), the home box (2020–2150) and the
home bench to ~2500. A player at the far boards is ~75 px tall, as with the old camera, so the bench rules are
Kirkland's, unscaled. Bench sitters show only their heads above the boards and don't pass the jersey test; line
changes come from on-ice tracks ending at the boards, as before. The nets sit at about (560, 755) and (3345, 755),
right in front of the end boards' kick plate, where the boards curve is steep: the crease is a box in the frame
(`in_crease`). The scoreboard is small and tilted in the right corner (x 3456–3606, y 576–702), readable on `sb.jpg`
but not by `shots.py` (it read 30-6 for 38-16). Players near the camera are ~500 px tall. The video has real audio.

On Oct 17 the proposal had the 1st period's net backwards and its edges 5–26 s off; the board lit the penalty panel
during the stoppage, started it at the faceoff, and cleared it at the power-play goal.

Views: `rink` 0–3840 × 220–1920; `left-net` 100–1300 × 480–1080; `right-net` 2600–3800 × 470–1070.

### The same camera with a black band (`renton2band`)

LADA Y's Oct 12 game (8:45 PM) already came from this camera, five days before Oct 17, but as LiveBarn's 3600x1800
with a black band and the LiveBarn logo over the top 264 rows (of 1920 once scaled up): the picture is Oct 17's at
the same scale, 266 px lower (the far boards curve is Oct 17's plus 266 at every x) and cut off at the bottom by as
much. Under `renton2` detection ran fine (the band is above the ice), but the scoreboard crop showed the ceiling.
`renton2band` moves everything with a y down by 266 and puts the scoreboard at (3434, 838). Tell the two apart on
`frame600.png`: a black band across the top. If a fetch under `renton2` already ran, switch `rink` in
`$W/full/rink.json`, move `scoreboard.npy` aside and run `scoreboard.py $W` again; the detections and crops stay.
On Oct 12 the 2nd period's faceoff fell in a dark stretch of the board, so its start came from the clock counting
1:1 afterwards (16:47 at 1290) and a frame check of the drop; the board's shots matched the sheet's totals but lagged
a shot each at the 1st's end.

Views: `rink` 0–3840 × 486–1920; `left-net` 100–1300 × 746–1346; `right-net` 2600–3800 × 736–1336.

### A thin band (`renton2thin`)

LADA R's Oct 19 game (8:45 PM) came at 2560x1280 at best (no 4K on YouTube), with a thin black band over the top
~60 rows (of 1920 once scaled up) and LiveBarn's timeline bar along the bottom. Fetch under `renton2` raises no
error, since the size matches. Compare `full/boards_poly.npy` with an Oct 17 or later `renton2` game's: on Oct 19
it was Oct 17's plus 62 px at every x, so `renton2thin` shifts everything with a y by 62 and reads the scoreboard
at (3456, 638). Any other shift is another class like it (or `renton2band`'s 266). Switching `rink` in
`$W/full/rink.json` before fetch reaches the scoreboard scan saves rescanning the board; detection uses only
`crop_top`, so it doesn't care. That night the clock ran through stoppages in the 1st and 2nd and stopped at whistles
only in the 3rd, so the penalty panel lit about 25 s after the whistle (#9 was in the box at 936, the panel at 950):
take a kill's start from the frames, not the panel. The intermissions were a 1:00–1:30 countdown on the board with
players on the ice, so the empty-ice proposal found one period; the clock gave 12–1112, 1204–2285, 2391–4137.

Views: `rink` 0–3840 × 282–1920; `left-net` 100–1300 × 542–1142; `right-net` 2600–3800 × 532–1132.

## Snoqualmie A (`snoqualmie`, a 3840x1536 strip)

Blue Wings' home rink. Camera high on the near side at center, very wide. Both benches are on the near side at the
frame edges, home left, away right, so the bench sitters are close to the camera, make over half of all crops
(their reads are skipped: `ocr_skip_depth`), and get tracked as if they were on the ice: `run_game.py gaps` lists
the long pieces that sit in the bench zone, and the checkers find each by the nameplate on the bench and the moment
he goes over the boards (25 on/off entries on LADA R's Oct 12 game came from that). Our penalty box is on the near
side next to our bench: as home, a player skates to the near-left corner and climbs in at the bottom-left of the
frame; as away, the box is just left of our bench (x about 3450–3700) and he sat about 20 s after the whistle. Nets
at 630 and 3260. Intermissions are short (`min_break` 10 s): players stand at the bench doors, then skate out to
warm up, so the proposal merges periods here almost every time and once split the 3rd at a long power-play-goal
stoppage into two.

Period ends haven't followed one rule here, so read the clock every time: on BW's Oct 11 and Y's Sep 21 games the
1st and 2nd stopped with 1:25, 1:03 and about 55 s on the clock, the teams changed ends while the board ran the rest
off on an empty rink, and the next period began about 25 s after 0:00 (so a period ends where `run_game.py skaters`
drops from 6 and starts at the faceoff, not at the skate-out the proposal picks); every later game (Beerteam Sep 20
and Oct 4, BW Oct 18, LADA R Oct 5 and Oct 12) ran each period to 0.0, with the 1:00 countdown after the 1st and 2nd
(about 1:30 after the 2nd on Oct 5). On Oct 5 the 2nd ended on a goal against with about 2 s left and the operator
then ran the clock to 0.0 with no play: end the period at the goal. On Oct 4 both goalies wore white with white
pads, so where our goal and the goals against went in settled the nets. Flounders' white with light-blue trim passed
our light-blue test a little (their #12 BUSH read 47 times); Night Owls' white #11, #35 and #43 are in `review.md`.

Views: `rink` 0–3840 × 380–1536; `left-net` 200–1400 × 380–760; `right-net` 2600–3800 × 380–760; `bench` 0–900 ×
700–1536 (left) or 2940–3840 × 700–1536 (right).

## Snoqualmie B (`snoqualmie2`, the whole fisheye frame, 3824x2160)

The same camera spot, but since Oct 2026 the video is the camera's whole fisheye frame: the far boards bow up to
y ~870 at center and dip to ~1170 at the edges, the near boards run along the bottom. Benches as at rink A (home
left); our (home) penalty box is on the near side just right of our bench, the opponents' its mirror next to theirs. Nets at 680 and 3270. The picture
is dim and grey: the ice is V ~150 and white jerseys no brighter, blue numbers barely show, so the rink has its own
brightness levels (`white_v`, `dark_v`) and its own white-jersey test (little dark in the torso tells our white
from TTT's navy). Referees' stripes and dark jerseys with a cream or white shoulder yoke (Sentinels, Frost Giants)
pass that test: twice the usual review sheets (210–223), `run_game.py skaters` reading 8–10 (check penalties at the
box by eye), `unknown` listing their numbers, and their #13 and #16 read hundreds of times on Oct 10, so our own
absent #13 and #16 had to be on the absent list. LADA's schedule calls it "Snoqualmie B". YouTube has had these
videos only at 2548x1440 (Sep 19, Oct 10): fetch takes the best webm and scales it up, and the geometry fits.

Seen here: the proposal merged the 1st and 2nd (Sep 19) or found all three 11–40 s off (Oct 10, nets right); after
the 2nd on Sep 19 the board counted a 2:00 intermission; on Oct 10 the board sat at 18:00 until the opening faceoff
at 0:11, and the box attendant kept #61 in for 22 s after the panel went dark. Our goalie wore white with dark pads,
theirs light blue; in a lopsided period the play sits at their net, which tells the nets apart. Shots OCR was wrong
in every period of both games.

Views: `rink` 0–3824 × 800–2160; `left-net` 80–1280 × 820–1370; `right-net` 2620–3820 × 820–1370; `bench` 100–1100 ×
1250–2160 (left) or 2724–3724 × 1250–2160 (right). The nets sit at about (645, 1015) and (3250, 1020) in the frame,
checked on the Oct 10 video; early in that video the right net wasn't on the ice yet, so a check should use a frame
from the game itself.

## Kirkland (`kirkland`, 3840x1536)

Camera low at center ice on the near side through a fisheye lens: the far boards bow up to y ~430 at center and
dip to ~700 at the edges, where the end boards run down the sides. Both benches are behind the far boards, home
right of center, away left; the doors are at the blue posts (x 1612 and 2265). The penalty boxes are the near
corners at the bottom of the frame, ours bottom-right and theirs bottom-left (as home), and a player drops out of
the bottom of the frame as he sits: read his number or name on the way in. Nets at 605 and 3255.

- The HOCKEY sign at the right has yellow letters that pull the boards fit up; `board_lowest = True` keeps only the
  lowest yellow run per column.
- Intermissions are about a minute and a referee stays on the ice, so the proposal finds a single period (Sep 14,
  Oct 5: the 2nd and 3rd merged) or all three 20–40 s off (Sep 27). Take the periods from the clock.
- The penalty clock jumped during an intermission (2:33 → 1:42): for a carried-over penalty use the moment the panel
  goes dark, not the time it showed at the break. A 2:00 for the other team was posted and taken off again at the
  same stoppage.
- Teamy McTeamface's white jerseys have big sky-blue panels, so half of theirs pass the plain light-blue test:
  `--jersey "light blue vs sky blue"` adds a hue test (`bhue` in `dets.csv`: ours ~113, theirs ~107). Rainucks' white
  with blue numbers and green-and-blue stripes passed the light-blue test too (`unknown` listed six of their numbers,
  #96 with more reads than any of ours); the goalies were told apart by colour (ours red, theirs white). BladeRunners
  wear red; nothing of theirs passed the white test.
- The operator can start the clock late. On LADA Y's Oct 5 game the board sat at 18:00 for the first 55 s of video
  while the game went on: opening faceoff at 0:05, a goal against at 0:41 (the sheet's 17:50 is the scorekeeper's
  guess), and the clock first counted down at the faceoff after it. The "18:00 starting to count" rule put P1 at 55,
  prepare cut its segments from there, and only the goals check found the earlier goal. Before prepare, look at the
  first minute of video (`frames --view rink 0 4 8 ... 40`) for play under a frozen 18:00. Once the review had
  started, P1 was moved to 5 in `periods.json` without preparing again: `on` spans for the five seen from the opening
  faceoff (and the changes after the goal) filled the seconds before the first segment, and solve came to 100%.
- The first gap check gets the bench right only half the time at Kirkland's staggered changes: a second pass over
  the gaps it left (and over any shift over ~5 minutes) found #52 sitting a whole timeout and the next shift.

Views: `rink` 0–3840 × 320–1536; `left-net` 150–1350 × 400–800; `right-net` 2600–3800 × 400–800.

## Jersey tests

`JERSEYS` in `rink.py` turns process.py's torso colour fractions into "ours" (tracked) and "crop" (saved for OCR
and review). Light blue is the default; `white` is a white torso with little dark in it and under 10% red (Sea
Otters' red with white stripes is 30–50% red); `light blue vs sky blue` adds the hue test; `white vs light blue` is
the white test with under 30% blue, for a game against LADA's other light-blue team (`references/lada.md`, "A game
between two LADA teams"). A rink can override a test for its own lighting (`jerseys` on the class, as Snoqualmie B
does). Whenever the picture looks different from before, run YOLO on a few frames and check the test before
detection: a wrong test loses our far-side players silently. Detection only saves crops of players in our jersey,
so a jersey set wrong after the fact means `run_game.py jersey $W <name>` (no detection rerun; ~5 min for a few
crops, 22 min of decoding for 100k on a 66-minute video). An opponent's jersey can pass our test on its trim alone
(Roadrunners' #4 ORR in grey-white with light-blue stripes made most of the 88 reads of "4"); `unknown` shows them.

## A rink that isn't in `rink.py`

Stop before detection. You don't have to wait for the download to look at it:

```sh
U=$($PY -m yt_dlp -g -f 313 "<url>"); $FF -loglevel error -ss 600 -i "$U" -frames:v 1 $W/frame600.png   # FF: imageio_ffmpeg's ffmpeg
```

Add a class: `crop_top` above the heads of players at the far boards (a wrong crop silently loses them), the board
band, the ice polygon, the benches (with `bench_where`, `box_where` and `bench_view` for the checkers' briefs), the
nets, `scoreboard` (x, y, w, h, all even: ffmpeg rounds an odd crop of yuv420 video down, every raw frame read then
drifts a row, and the scan shows two half boards and runs short of the video, 3706 s for 3736), `shots_boxes` (the
home and guest shot digits inside that crop), `views`, and `board_lowest` if there's yellow lettering above the
boards. Run `boards.py` on the frame and draw its curve over it; check it all the way to the frame edges. Then YOLO
on a few frames and the jersey test under that lighting, and only then detection. Register the class in `RINKS`.
