# Rinks, benches, jerseys, scoreboards

Each rink films from a different spot, so the camera geometry lives in a class in `pipeline/rink.py`: the detection
crop, where the far boards are, the ice polygon, our bench, the nets, the scoreboard box, the shots digits, and the
`views` that `run_game.py frames --view` crops. `fetch --rink` records the rink in `$W/full/rink.json`; a folder
without one is Renton. Pick the rink by the frame size and view of `frame600.png`, not by LADA's `rinkName` alone.

## Conventions so far

- Home wears white (blue numbers and trim), away light blue. The home bench at Renton and Kirkland is right of
  center, the away bench left; at Snoqualmie home is left, away right.
- Our bench decides which track ends count as line changes (solve) and which detections are tracked at the bench
  (prepare). `--bench left|right` on fetch, or `"bench"` in `rink.json` before prepare, mirrors the rink's usual
  side. Check it on `frame600.png`: our jerseys sit at our bench.
- Our goalie's net (`net` per period in `periods.json`) switches each period; prepare drops our goalie's detections
  in that crease. The proposal had all three backwards on BW's Oct 3 game, so check a crease zoom per period.
- The arena scoreboard is in frame at every rink: period clock, score, shots, and the home and guest penalty panels
  with the player's number and time left. Its LEDs flicker (at Renton most single frames show it dark), so
  `scoreboard.py` keeps the brightest frame of each second; fetch scans it into `$W/scoreboard.npy` and `$W/sb.jpg`.
- Which side we are: usually LADA's `playHome`, but go by the final score on the board. LADA Y were away in LADA
  but HOME on Kirkland's board on Sep 14; Doofers were away and guests on Sep 27 but had the home-side bench.
- Scorekeepers put penalties on the wrong panel (Kirkland: ours on the guest panel while the score sat on the home
  side), so the penalty box decides whose a penalty is.

## Renton (`renton`, 3840x1702)

Camera high on the near side. Both benches are behind the far boards: away left of center, home right. The
away team's penalty box is the glassed compartment just right of the away bench (frame x about 1740–1770, past
the glass post at x 1712), so a boxed player is tracked as "at the bench"; a player serving a penalty climbs over
the boards there and skates off when it ends, with his number readable on the way. Nets at x 540 (left) and 3245
(right). The empty-ice period proposal is often right to a few seconds here, but check every edge against the
clock: on Doofers' Sep 13 game (the same night as Beerteam's, 9:15 PM) the board ran a 1:00 intermission
countdown after the 1st and the 2nd with the old period still lit, and the proposal was 19–36 s off at four of
the five edges (the 1st ended at 18:16 of video, at the board's first 00.0, not 18:41; the 2nd and 3rd started at
the faceoff, 36 s and 19 s after it). BW's Oct 3 video came as 3600x1596; fetch
scales such a video up to 3840x1702 and keeps the original as `video_<W>x<H>.webm`. The clock stops at whistles
in some periods and runs through them in others. On Sep 13 (Beerteam) the operator let the 2nd period's clock hit
00.0, then ran an extra minute on an empty rink: the period ends at the first 00.0, and `break_*.jpg` shows whether
anyone was still playing. The board has run 3:00 for penalties the game sheet calls 2-minute minors; go by the
panel. A penalty's clock time on the game sheet is the clock when the scorekeeper entered it, which can be 20 s
after the whistle.
The home team's penalty box is the matching compartment left of the home bench (x about 1945–2055, a boxed
player at about 2000). On LADA R's Sep 21 game the empty-ice proposal merged the 1st and 2nd periods into one (the
break wasn't empty enough), so check it against the board's clock even here. That video came as 3246x1440. The
board's shot count fell well behind the game sheet in the 3rd (about 20–29 against the sheet's 22–39) and
`shots.py`'s OCR read nonsense, so the shots came from the sheet; the board also showed the guests a goal too many
for a while and fixed it later. On LADA R's Sep 14 game (10:15 PM) the proposal merged the 2nd and 3rd instead, and
the board again ran a 1:00 intermission countdown after the 1st and 2nd: periods are 18:00, and every edge came from
the clock (18:00 starting to count, the first 00.0). `shots.py` read 25-5 there while the board plainly said 29-38;
read `shots_check.jpg` yourself every time. Doofers' Oct 4 game (9:15 PM, 3246x1440 again) had the 1:00 countdown
after the 1st and 2nd too; the proposal started the 3rd 90 s early, inside the countdown and the empty-board wait
after it, and put the 3rd at the same net as the 2nd. Every edge came from the clock again, and the shots OCR read
the 3rd as 9 where the board went from 19 to 35. Beerteam's Sep 27 game (9:15 PM, 3246x1440, away) went the same way:
the proposal merged the 2nd and 3rd into one period and put it at the 1st's net, the board ran the 1:00 countdown after
the 1st and 2nd, the clock ran through stoppages in the 1st and 2nd and stopped at whistles in the 3rd, and the shots
OCR read 1-5, 1-9, 15-11 for the board's 9-5, 11-8, 19-12. On the one-a-minute `sb.jpg` the last minute's tenths
read like minutes ("43.1" looks like 4:31), and the board was dark (flicker) for the seconds around the 2nd period's
0.0: a 2 s sheet over the last minute pins the end.

Views: `rink` 0–3840 × 700–1500; `left-net` 150–1450 × 720–1070; `right-net` 2500–3800 × 720–1070.

## Renton, new camera (`renton2`, the whole fisheye frame, 3840x1920)

From Turbo Kings' Oct 17 game (9:15 PM) Renton's video comes from a new camera low at center ice on the near side,
behind the netting, with a fisheye lens: fetch stops with "video is 3840x1920 ... new framing". The far boards bow
up to y ~340 at center and drop to ~1030 at the frame edges; the near boards run along the bottom. The rink is the
same, so the benches are still behind the far boards: away (light blue) from the glass post at x 1380 to ~1735,
then the away box (1735–1865), the scorekeeper's window at center (the scorekeeper wore light blue and passes our
jersey test; he is outside the bench zone, so he isn't tracked), the home box (2020–2150) and the home bench to
~2500. A player at the far boards is ~75 px tall, as with the old camera, so the bench rules are Kirkland's,
unscaled. Bench sitters show only their heads above the boards and don't pass the jersey test; line changes come
from on-ice tracks ending at the boards, as before. The nets sit at about (560, 755) and (3345, 755), right in front
of the end boards' kick plate, where the boards curve is steep: the crease is a box in the frame (`in_crease`).
The scoreboard is small and tilted in the right corner (x 3456–3606, y 576–702), readable on `sb.jpg` but not by
`shots.py`'s OCR (it read 30-6 for 38-16): read the shots at each period's end yourself. Players near the camera are
~500 px tall. Unlike the old camera's, this video has real audio: the referees' whistles are audible, which pins
goals and penalty calls to a fraction of a second, and clips keep the sound.

On Oct 17 the clock ran through stoppages in the 1st and 2nd and stopped at whistles in the 3rd; the board counted a
1:00 intermission after the 1st and 2nd (period ends at the first 00.0, starts when 18:00 starts counting). The
empty-ice proposal had the 1st period's net backwards and its edges 5–26 s off. The board ran 3:00 for a minor the sheet
calls 2:00, lit the panel during the stoppage and started it at the faceoff, and cleared it at a power-play goal.

Views: `rink` 0–3840 × 220–1920; `left-net` 100–1300 × 480–1080; `right-net` 2600–3800 × 470–1070.

## Snoqualmie A (`snoqualmie`, a 3840x1536 strip)

Blue Wings' home rink. Camera high on the near side at center, very wide. Both benches are on the near side at the
frame edges: home left, away right, so the bench sitters are close to the camera and make over half of all crops
(their reads are skipped: `ocr_skip_depth`). Nets at 630 and 3260. Intermissions are short (`min_break` 10 s):
players stand at the bench doors, then skate out to warm up. Videos have come as 3440x1376 and get scaled up.

Periods can end before the clock does. On BW's Oct 11 game the 1st and 2nd periods stopped with about 1:25 and 1:03
on the clock; the teams changed ends while the board ran the rest off on an empty rink, and the next period began
about 25 s after the board hit 0:00. So a period ends where `run_game.py skaters` drops from 6, not at 0:00, and
starts at the faceoff (the clock leaves 18:00), not at the skate-out the proposal picks. The proposal also split
the 3rd period at a long power-play-goal stoppage into two. Y's Sep 21 game did the same (both periods stopped with
about 55 s left): it looks like the rule here, so expect it. On that game the clock ran through stoppages in the
1st and 2nd (period start + 18:00 minus the clock is the video time, to a second or two) and stopped at whistles
in the 3rd. In the last minute the board shows seconds and tenths ("45.9"), easy to misread as minutes.
Beerteam's Sep 20 game (home, white, left bench) broke both rules: play ran to 0:00 in every period, and the board
then counted a 1:00 intermission down before resetting to 18:00. Players warm up through that minute, so the
empty-ice proposal merged the 1st and 2nd into one period; take every period from the clock (start when it leaves
18:00, end at 0:00), as at Kirkland. The clock again ran through stoppages in the 1st and 2nd and stopped at whistles
in the 3rd. A player of ours (home) going to the box skates to the near-left corner and climbs in at the bottom-left
of the frame, next to our bench. The board ran 3:00 for a minor in the 2nd and 2:00 for one in the 3rd.
BW's Oct 18 game (home, 4:30 PM) followed Beerteam's pattern: every period ran to 0.0, followed by a 1:00 intermission
countdown, the clock ran through stoppages in the 1st and 2nd and stopped at whistles in the 3rd, and the board ran
3:00 for the 1st period's minor and 2:00 for the 3rd's. The proposal merged the 1st and 2nd and had every net
backwards. Snoqualmie A's period ends haven't followed one rule, so read the clock every time. Fetch defaults to the
away bench here (`bench_side = "right"`), so a home game needs `--bench left`. That video was a recording of
LiveBarn's player (3438x1374): LiveBarn's score panel sits in the top-left corner and a timeline bar along the
bottom, both outside the ice, and detection was unaffected.

Views: `rink` 0–3840 × 380–1536; `left-net` 200–1400 × 380–760; `right-net` 2600–3800 × 380–760.

## Snoqualmie B (`snoqualmie2`, the whole fisheye frame, 3824x2160)

The same camera spot, but since Oct 2026 the video is the camera's whole fisheye frame: the far boards bow up to
y ~870 at center and dip to ~1170 at the edges, the near boards run along the bottom. Benches as at rink A (home
left). Nets at 680 and 3270. The picture is dim and grey: the ice is V ~150 and white jerseys no brighter, blue
numbers barely show, so the rink has its own brightness levels (`white_v`, `dark_v`) and its own white-jersey test
(little dark in the torso tells our white from TTT's navy); referees' stripes pass as ours and the reviewers drop
them. LADA's schedule calls it "Snoqualmie B".

Doofers' Sep 19 game (home, white, left bench) was already this whole frame, but YouTube had it only at 2548x1440:
fetch takes the best webm when there's no 4K and scales it up, and the geometry fit unchanged. The empty-ice
proposal merged the 1st and 2nd, and the board fooled me once: after the 1st it counted a 1:00 intermission
(period still 1, plain m:ss), which looks like the last minute of play. Play's last minute shows tenths ("12.9");
the period ends at 0.0, and after the 2nd the board counted a 2:00 intermission. The clock ran through stoppages in
the 1st and 2nd and stopped at whistles in the 3rd. Our (home) penalty box is on the near side just right of our
bench. Referees and Sentinels' black jerseys with a cream shoulder yoke passed the white test, so prepare made 210
review sheets (twice the usual) and `run_game.py skaters` read 8–10: check penalties at the box by eye. Our goalie
wore white with dark pads, theirs light blue; in a lopsided period the play sits at their net, which tells the nets
apart.

Views: `rink` 0–3824 × 800–2160; `left-net` 80–1280 × 820–1370; `right-net` 2620–3820 × 820–1370. The nets sit
at about (645, 1015) and (3250, 1020) in the frame, checked on the Oct 10 video; early in that video the right net
wasn't on the ice yet, so a check should use a frame from the game itself.

## Kirkland (`kirkland`, 3840x1536)

Camera low at center ice on the near side through a fisheye lens: the far boards bow up to y ~430 at center and
dip to ~700 at the edges, where the end boards run down the sides. Both benches are behind the far boards, home
right of center, away left; the doors are at the blue posts (x 1612 and 2265). The penalty boxes are the near
corners at the bottom of the frame, ours bottom-right and theirs bottom-left (as home), and a player drops out of
the bottom of the frame as he sits: read his number or name on the way in. Nets at 605 and 3255. Videos have come
as 3600x1440 and get scaled up.

- The HOCKEY sign at the right has yellow letters that pull the boards fit up; `board_lowest = True` keeps only the
  lowest yellow run per column.
- Intermissions are about a minute and a referee stays on the ice, so the empty-ice proposal finds a single period.
  Take the periods from the clock: it runs down to 00.0, shows a 1:00 intermission countdown, then resets to
  18:00; a period starts when the clock first counts down from 18:00. The clock runs through stoppages here,
  except in the last minute or two.
- The penalty clock jumped during an intermission (2:33 → 1:42): for a carried-over penalty use the moment the panel
  goes dark, not the time it showed at the break. Penalties have been 3 and 4 minutes; one 2:00 for the other team
  was posted and taken off again at the same stoppage.
- Teamy McTeamface's white jerseys have big sky-blue panels, so half of theirs pass the plain light-blue test.
  `--jersey "light blue vs sky blue"` adds a hue test (`bhue` in `dets.csv`: ours ~113, theirs ~107).
- Shots OCR is often wrong here: fix `shots.json` from `shots_check.jpg`.
- Doofers' Sep 27 game (3:00 PM; a recording of LiveBarn's player, 3438x1374) was away in LADA and the guests on the
  board, yet our light-blue jerseys sat at the home-side bench right of center: check `frame600.png` and set the bench
  from it, never from home/away. The empty-ice proposal found all three periods that time, but 20-40 s off at every
  edge; the clock rules above held (18:00 starting to count, 0.0, a 1:00 intermission countdown), with the clock
  running through stoppages in the 1st and 2nd and stopping at whistles in the 3rd. Both minors ran 3:00 on the board.
  Our player dropped into the near-right box. Rainucks' white jerseys with blue numbers and green-and-blue stripes
  passed the light-blue test (`unknown` listed six of their numbers, #96 with more reads than any of ours), and the
  goalies were told apart by colour (ours red, theirs white). Shots OCR read 20-20 for the board's 25-32.

Views: `rink` 0–3840 × 320–1536; `left-net` 150–1350 × 400–800; `right-net` 2600–3800 × 400–800.

## Jersey tests

`JERSEYS` in `rink.py` turns process.py's torso colour fractions into "ours" (tracked) and "crop" (saved for OCR
and review). Light blue is the default; `white` is a white torso with little dark in it and under 10% red (Sea
Otters' red with white stripes is 30–50% red); `light blue vs sky blue` adds the hue test. A rink can override a
test for its own lighting (`jerseys` on the class, as Snoqualmie B does). Whenever the picture looks different
from before, run YOLO on a few frames and check the test before detection: a wrong test loses our far-side
players silently. Detection only saves crops of players in our jersey, so a jersey set wrong after the fact means
`run_game.py jersey $W <name>` (~5 min, no detection rerun).

## A rink that isn't in `rink.py`

Stop before detection. You don't have to wait for the download to look at it:

```sh
U=$($PY -m yt_dlp -g -f 313 "<url>"); $FF -loglevel error -ss 600 -i "$U" -frames:v 1 $W/frame600.png   # FF: imageio_ffmpeg's ffmpeg
```

Add a class: `crop_top` above the heads of players at the far boards (a wrong crop silently loses them), the board
band, the ice polygon, the benches, the nets, `scoreboard` (x, y, w, h, all even: ffmpeg rounds an odd crop of
yuv420 video down, every raw frame read then drifts a row, and the scan shows two half boards and runs short of the
video, 3706 s for 3736), `shots_boxes` (the home and guest shot digits inside that crop), `views`, and `board_lowest` if there's yellow lettering above the boards. Run
`boards.py` on the frame and draw its curve over it; check it all the way to the frame edges. Then YOLO on a few
frames and the jersey test under that lighting, and only then detection. Register the class in `RINKS`.
