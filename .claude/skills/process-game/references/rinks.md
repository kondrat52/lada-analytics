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
  but HOME on Kirkland's board on Sep 14.
- Scorekeepers put penalties on the wrong panel (Kirkland: ours on the guest panel while the score sat on the home
  side), so the penalty box decides whose a penalty is.

## Renton (`renton`, 3840x1702)

Camera high on the near side. Both benches are behind the far boards: away left of center, home right. The
away team's penalty box is the glassed compartment just right of the away bench (frame x about 1740–1770, past
the glass post at x 1712), so a boxed player is tracked as "at the bench"; a player serving a penalty climbs over
the boards there and skates off when it ends, with his number readable on the way. Nets at x 540 (left) and 3245
(right). The empty-ice period proposal is right to a few seconds here. BW's Oct 3 video came as 3600x1596; fetch
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
for a while and fixed it later.

Views: `rink` 0–3840 × 700–1500; `left-net` 150–1450 × 720–1070; `right-net` 2500–3800 × 720–1070.

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

Views: `rink` 0–3840 × 380–1536; `left-net` 200–1400 × 380–760; `right-net` 2600–3800 × 380–760.

## Snoqualmie B (`snoqualmie2`, the whole fisheye frame, 3824x2160)

The same camera spot, but since Oct 2026 the video is the camera's whole fisheye frame: the far boards bow up to
y ~870 at center and dip to ~1170 at the edges, the near boards run along the bottom. Benches as at rink A (home
left). Nets at 680 and 3270. The picture is dim and grey: the ice is V ~150 and white jerseys no brighter, blue
numbers barely show, so the rink has its own brightness levels (`white_v`, `dark_v`) and its own white-jersey test
(little dark in the torso tells our white from TTT's navy); referees' stripes pass as ours and the reviewers drop
them. LADA's schedule calls it "Snoqualmie B".

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
band, the ice polygon, the benches, the nets, `scoreboard` (x, y, w, h), `shots_boxes` (the home and guest shot
digits inside that crop), `views`, and `board_lowest` if there's yellow lettering above the boards. Run
`boards.py` on the frame and draw its curve over it; check it all the way to the frame edges. Then YOLO on a few
frames and the jersey test under that lighting, and only then detection. Register the class in `RINKS`.
