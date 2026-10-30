# Ice maps

Where each of our skaters was on the ice during their shifts: the game page's "Ice map" section (the team's map
beside a picked player's, zone shares written on the ice) and `ice` in the feed's game file (`API.md`). Publish
makes them (`pipeline/ice.py`) for a game at a rink whose camera is calibrated in `pipeline/cams/<rink>.json`; any
other game has none, and its page leaves the section out. To add or refresh one game's maps without republishing:

```sh
$PY pipeline/ice.py $W teams/<slug>/games/<id>/game.json     # prints each player's zone shares, writes "ice"
TEAM=<slug> $PY pipeline/build_site.py
```

An archived work folder has everything this needs (tracks, segments, shifts, periods, `boards_poly.npy`).

How a position is made: a player's labeled tracks (`segs_final.csv`) inside his shifts (`shifts_all.csv`), each foot
point mapped onto the ice by the rink's calibration (`pipeline/rinkcam.py`), our net always at the bottom. A
labeled piece that spends most of its time in their crease is dropped: on TK's Oct 25 their goalie's white passed
our jersey test and 23 pieces of his track carried our numbers by chaining. About 70–85% of a player's ice time has
a labeled position; scrums and the far boards count less.

Read the zone shares once per game: defencemen at 45–60% in our zone and centers' hot spots on the faceoff dots
have held on both calibrated games. A map with a hot spot in their crease, or everyone's share far off what the play
looked like, means a bad label or a calibration that no longer fits (a camera moved or re-aimed).

## Calibrated rinks

| Rink (`rink.py`) | Model | Fitted on | Fit |
|---|---|---|---|
| `snoqualmie` (A) | pano | BW Oct 25, the LiveBarn file | markings 0.3 ft median; their goalie at X +-83-84 |
| `snoqualmie2` (B) | fisheye + warp | TK Oct 25, YouTube 3824x2160 | markings 0.4 ft median, 1.4 ft 90%; their goalie at X +-83-88 |

Snoqualmie A's videos come framed two ways, 52 px apart (the YouTube cuts higher than the LiveBarn files and two
games from Oct 12 and 18); each game's own boards curve (`boards_poly.npy`) says which, and `rinkcam.camera` shifts
the calibration by the difference. Renton (both cameras) and Kirkland have no calibration yet.

## Calibrating a rink

Needs one game's work folder at that rink with its video still in it (an archived folder has none: fetch it again,
or wait for the next game there). About half an hour of session time, most of it the landmark reader.

```sh
D=~/hockey-work/cal-<rink>
$PY pipeline/rinkcal.py frame $W $D            # the empty rink (median of 41 frames), enhanced, with gridded halves
```

Then one general-purpose subagent reads the painted markings into `$D/landmarks.json`, with this brief (fill in the
frame's size and where things are from `$D/half.jpg`):

> You are reading pixel positions of an ice rink's painted markings off one camera image, to calibrate a camera
> model; aim for ±5 source px (±3 for dots). `$D/half.jpg` is the whole frame at half size with rulers in source
> coordinates; `$D/left.jpg` and `$D/right.jpg` are its halves at 1:1 with a 50 px grid;
> `$PY pipeline/rinkcal.py crop $D X0 X1 Y0 Y1 [ZOOM] [plain]` writes `$D/lm/crop_X0_Y0.jpg`, a zoomed crop with a
> 10 px grid labeled in source px (`plain` crops the unenhanced median; the enhanced one exaggerates scuff marks).
> Keep crops to about 900x500 source px at zoom 2. [Describe the view: where the camera is, where the far boards,
> the nets, the center line, the blue lines and the near side are, with rough coordinates.] Write
> `$D/landmarks.json`, each key a list of [x, y] points on the painted line's middle (boards: where the ice meets
> them), an empty list if not visible: "center", "blue_left", "blue_right" (8-12 points each, spread along their
> whole length), "goal_left", "goal_right" (as many as visible), "net_left", "net_right" (the goal mouth's middle on
> the goal line), "dot_center", "dot_neutral_far_left/right", "dot_neutral_near_left/right",
> "dot_end_far_left/right", "dot_end_near_left/right" (one point each), "boards_far" (10-14 points, straight stretch
> only), "boards_near" (if the base is visible), "boards_end_left", "boards_end_right" (3-6 points behind each net),
> "circle_center" (14-20 points all around, near half included), "circle_end_near_left/right",
> "circle_end_far_left/right" (8-16 points of whatever arc is visible), "ref_crease" (the referee's 10 ft semicircle
> at the near boards, if that's what the arc there is), "center_far_crossing", "center_near_crossing" (where the
> center circle crosses the center line), and "notes" (anything uncertain). Left/right are the image's; far is away
> from the camera. Reply with one line per key: the key and its number of points.

The near side decides the fit: on rink A the first fit had nothing nearer than the neutral dots and put them 75 px
off; the near end circles, the referee's crease and the center circle's near half fixed it.

```sh
$PY pipeline/rinkcal.py fit $D $W pano         # or fisheye; writes pipeline/cams/<rink>.json and $D/check.jpg
```

`pano` suits a strip that the camera has already unrolled (lines curve gently, the far boards bow down at center);
`fisheye` a whole fisheye frame (the far boards bow up at center, the roof fills the top half). Look at
`$D/check.jpg` (every marking drawn back onto the frame: it should sit on the paint across the ice) and the printed
checks: markings within about half a foot (median), their goalie at X +-82..88 in each period, under 0.2% of our
on-ice track points off the ice. Then add the rink to the table above, run `ice.py` on the rink's games and rebuild.
