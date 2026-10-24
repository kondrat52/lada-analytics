"""Camera geometry per rink. The pipeline was built on Renton's wide cut; other rinks film from other spots.

`run_game.py fetch --rink NAME` writes {"rink": NAME} to W/full/rink.json, next to dets.csv, and every later step
finds it there (a folder without one is Renton). Pixels are in the full 4K frame (3840 wide).

Positions are a detection's foot x and `rel` = foot y minus the far-boards curve y at that x (boards_poly.npy from
boards.py; > 0 is below the boards line in the image). Bench rules work in "bench depth": how far a foot is past
the boards between the ice and our bench, in Renton pixels (a Renton player at the bench is ~65 px tall), so the
thresholds in shifts.py and run2.py hold at every rink. Negative = on the ice side.
"""
import json, os
import numpy as np
from matplotlib.path import Path


class Renton:
    """Camera high on the near side; both benches behind the far boards, one left of center and its mirror image
    right of center, with the penalty boxes between them. So far the away team (we wear light blue) has had the
    left one and the home team (white) the right one."""
    crop_top = 560 / 1702         # detection band starts here (fraction of frame height); ceiling above
    board_band = (0.41, 0.76)     # rows where boards.py looks for the far boards' yellow kick plate (fractions)
    board_lowest = False          # boards.py: per column, only the lowest yellow run (yellow signs above the boards)
    size = (3840, 1702)           # fetch scales a smaller video of this view up to it (BW's Oct 3 came as 3600x1596)
    center_x = 1880
    nets = {"left": 540, "right": 3245}
    ocr_skip_depth = None         # OCR skips crops this deep in our bench (None: read everything)
    min_break = 25                # seconds of empty open ice that make an intermission
    bench_side = "left"           # our usual bench; rink.json "bench" can pick the other one
    scoreboard = (3290, 690, 130, 80)  # x, y, w, h of the arena scoreboard (scoreboard.py)
    shots_boxes = {"home": (47, 39, 59, 50), "guest": (65, 40, 78, 51)}   # shots-on-goal digits, in that crop (shots.py)
    clock_box, clock_tilt = (50, 3, 84, 19), 0   # period clock digits in that crop, levelled by the tilt (clock.py)
    white_v, dark_v = 160, 60     # process.py's torso colours: "white" = unsaturated and at least this bright, "dark" below
    jerseys = {}                  # this rink's own colour tests for a jersey, in place of JERSEYS'
    # crops of the 4K frame for checking goals and penalties by eye (run_game.py frames --view): x0, x1, y0, y1
    views = {"rink": (0, 3840, 700, 1500), "left-net": (150, 1450, 720, 1070), "right-net": (2500, 3800, 720, 1070)}

    def __init__(self, board_poly, bench=None):
        self.P = board_poly
        self.mirror = bool(bench) and bench != self.bench_side

    def _bench_x(self, x):
        """x as if we sat on the left bench: the right one is its mirror image about center ice."""
        return 2 * self.center_x - x if self.mirror else x

    def onice(self, x, rel):
        return rel > 5

    def open_ice(self, x, rel):
        """Out on the ice, away from the boards: nobody here for min_break seconds means an intermission."""
        return self.onice(x, rel) & (rel > 60)

    def bench_depth(self, x, rel):
        return -rel

    def at_bench(self, x, rel):
        """At our bench: standing at its boards or behind them."""
        x = self._bench_x(x)
        return (x > 1340) & (x < 1760) & (rel < 15)

    def bench_zone(self, x, rel):
        """Off the ice but tracked anyway, to see players come and go."""
        x = self._bench_x(x)
        return (x > 1300) & (x < 1800) & (rel > -80)

    def in_crease(self, x, rel, net_x):
        """Our goalie's spot in front of net_x (the goalie's detections are dropped from skater tracking)."""
        return (np.abs(x - net_x) < 110) & (rel > 0) & (rel < 75)

    # where our bench and penalty box are in the picture, by the side we sit on (run_game.py gaps tells the checkers)
    bench_where = {"left": "behind the far boards, left of center (only heads show above the boards; line changes "
                           "are tracks ending or starting at those boards)",
                   "right": "behind the far boards, right of center (only heads show above the boards; line changes "
                            "are tracks ending or starting at those boards)"}
    box_where = {"left": "the glassed compartment just right of our bench (x about 1740-1770)",
                 "right": "the compartment just left of our bench (x about 1945-2055)"}

    @property
    def side(self):
        return ("right" if self.bench_side == "left" else "left") if self.mirror else self.bench_side

    def bench_view(self):
        """A crop of our bench and its door for `run_game.py frames --view bench`: x0, x1, y0, y1 in the frame."""
        x0, x1 = sorted((self._bench_x(1300), self._bench_x(1800)))
        y = float(np.polyval(self.P, (x0 + x1) / 2)) if self.P is not None else 1000.0
        return int(x0) - 100, int(x1) + 100, int(y) - 170, int(y) + 60


class Snoqualmie(Renton):
    """Rink A: camera high on the near side at center, very wide (3840x1536). Both benches are on the near side at
    the frame edges: away right (Turbo Kings in light blue), home left (Blue Wings in white). The far boards sit at
    y 450-610."""
    crop_top = 340 / 1536
    board_band = (0.27, 0.45)
    size = (3840, 1536)
    center_x = 1890
    nets = {"left": 630, "right": 3260}          # where the goalies stand (same crease size as Renton's)
    # the ice, with the near boards and both benches' boards as its left, right and bottom sides (the far boards
    # curve is the top)
    ICE = Path([(130, 0), (3720, 0), (3720, 598), (3395, 1195), (3360, 1200), (3140, 1390), (2970, 1536),
                (910, 1536), (700, 1290), (410, 990), (130, 545)])
    # top of the boards between the ice and each bench, ordered so that bench_depth's normal points into the bench,
    # and the bench's extent down the frame
    BENCHES = {"right": ((3720, 598), (3395, 1195)), "left": ((410, 990), (130, 545))}
    BENCH_YS = {"right": (560, 1260), "left": (510, 1260)}   # down past the bench doors
    SCALE = 1.6                           # a skater at our bench's boards is ~123 px tall; at Renton's, ~75
    # the bench is close to the camera, so its sitters make over half of all crops; their reads are never used
    ocr_skip_depth = 60
    # intermissions are short (~1.5 min): players stand at their bench doors, then skate out to warm up
    min_break = 10
    bench_side = "right"
    scoreboard = (1790, 262, 280, 116)
    shots_boxes = {"home": (136, 76, 157, 95), "guest": (171, 76, 197, 95)}
    clock_box = (115, 18, 166, 43)        # the usual framing; ~50 px lower on Oct 12 and 18 (clock.py finds it)
    views = {"rink": (0, 3840, 380, 1536), "left-net": (200, 1400, 380, 760), "right-net": (2600, 3800, 380, 760)}

    bench_where = {"left": "on the near side at the LEFT edge of the frame, right by the camera (players sitting "
                           "there are big, often get tracked as if on the ice, and climb over the boards to go on)",
                   "right": "on the near side at the RIGHT edge of the frame, right by the camera (players sitting "
                            "there are big, often get tracked as if on the ice, and climb over the boards to go on)"}
    box_where = {"left": "on the near side just right of our bench, at the bottom of the frame",
                 "right": "on the near side just left of our bench (x about 3450-3700)"}
    BENCH_VIEWS = {"left": (0, 900, 700, 1536), "right": (2940, 3840, 700, 1536)}

    def __init__(self, board_poly, bench=None):
        super().__init__(board_poly)
        side = bench or self.bench_side
        self._side = side
        self.BENCH, self.BENCH_Y = self.BENCHES[side], self.BENCH_YS[side]

    @property
    def side(self):
        return self._side

    def bench_view(self):
        return self.BENCH_VIEWS[self._side]

    def _xy(self, x, rel):
        x = np.asarray(x, float); rel = np.asarray(rel, float)
        return x, rel + np.polyval(self.P, x)

    def onice(self, x, rel):
        x, y = self._xy(x, rel)
        inside = self.ICE.contains_points(np.c_[x.ravel(), y.ravel()]).reshape(x.shape)
        return (np.asarray(rel) > 5) & inside

    def open_ice(self, x, rel):
        x = np.asarray(x, float)
        return super().open_ice(x, rel) & (x > 700) & (x < 3150)   # clear of both bench doors

    def bench_depth(self, x, rel):
        x, y = self._xy(x, rel)
        (ax, ay), (bx, by) = self.BENCH
        nx, ny = by - ay, ax - bx          # normal pointing into the bench
        d = ((x - ax) * nx + (y - ay) * ny) / np.hypot(nx, ny) / self.SCALE
        return np.where((y > self.BENCH_Y[0]) & (y < self.BENCH_Y[1]), d, -999.0)

    def at_bench(self, x, rel):
        return self.bench_depth(x, rel) > -15

    def bench_zone(self, x, rel):
        return self.at_bench(x, rel)


class Snoqualmie2(Snoqualmie):
    """Snoqualmie from Oct 2026: the same camera spot, but the video is its whole fisheye frame (3824x2160), not a
    3840x1536 strip. The far boards bow up to y ~870 at center and dip to ~1170 at the frame edges; the near boards
    run along the bottom (y ~2100 at center). Benches at the frame edges as before: home left (we wore white), away
    right."""
    crop_top = 720 / 2160
    board_band = (0.38, 0.57)
    size = (3824, 2160)
    center_x = 1935
    nets = {"left": 680, "right": 3270}
    ICE = Path([(100, 0), (3750, 0), (3750, 1200), (3664, 1220), (3254, 1600), (3000, 1840), (2500, 2040),
                (1935, 2095), (1500, 2040), (1000, 1840), (560, 1500), (195, 1160), (100, 1150)])
    # top of the boards between the ice and each bench, ordered so that bench_depth's normal points into the bench
    BENCHES = {"left": ((560, 1500), (195, 1160)), "right": ((3664, 1220), (3254, 1600))}
    BENCH_Y = (1100, 1750)
    SCALE = 3.3                           # a skater at the bench boards is ~250 px tall
    # the video is dim and grey: the ice is V ~150, white jerseys no brighter, and blue numbers barely show. So
    # "white" counts the ice behind a player too, and what tells our white jerseys from TTT's navy is how little
    # dark there is (referees' stripes pass as ours; reviewers drop them)
    white_v, dark_v = 115, 45
    jerseys = {"white": dict(ours=lambda c: (c["white"] >= 0.15) & (c["dark"] < 0.4) & (c["red"] < 0.1),
                             crop=lambda c: (c["white"] >= 0.1) & (c["dark"] < 0.5) & (c["red"] < 0.1))}
    scoreboard = (1810, 640, 270, 110)
    shots_boxes = {"home": (124, 68, 156, 91), "guest": (168, 68, 200, 91)}
    clock_box = (110, 7, 169, 32)
    # the whole fisheye frame: ice from the far boards (y ~870 at center) to the near boards (~2100). The nets sit at
    # about (645, 1015) and (3250, 1020) in the frame (checked on the Oct 10 video), centered in the net views
    views = {"rink": (0, 3824, 800, 2160), "left-net": (80, 1280, 820, 1370), "right-net": (2620, 3820, 820, 1370)}

    BENCH_VIEWS = {"left": (100, 1100, 1250, 2160), "right": (2724, 3724, 1250, 2160)}

    def __init__(self, board_poly, bench=None):
        self.P = board_poly
        self._side = bench or self.bench_side
        self.BENCH = self.BENCHES[self._side]

    def open_ice(self, x, rel):
        x = np.asarray(x, float)
        return Renton.open_ice(self, x, rel) & (x > 750) & (x < 3100)   # clear of both bench doors


class Kirkland(Renton):
    """Camera low at center ice on the near side with a fisheye lens (3840x1536): the far boards bow up to y ~430
    at center and dip to ~700 at the frame edges, where the end boards run down the sides. Both benches are behind
    the far boards like Renton's, but not mirror images: the home one (we wore white) right of center, the away
    one left; the doors are at the blue posts (x 1612 and 2265). The near-side corners at the bottom of the frame are
    off the ice (timekeeper and penalty boxes)."""
    crop_top = 320 / 1536
    board_band = (0.25, 0.49)
    board_lowest = True           # the HOCKEY sign at the right has yellow letters
    size = (3840, 1536)           # fetch scales a smaller video of this view up to it (run_game.fit_size)
    center_x = 1930
    nets = {"left": 605, "right": 3255}
    min_break = 25
    bench_side = "right"
    BENCHES = {"left": (1340, 1720), "right": (2160, 2560)}   # x at the boards, with Renton's ~30 px margins
    scoreboard = (358, 396, 136, 82)
    shots_boxes = {"home": (55, 54, 71, 68), "guest": (73, 52, 90, 65)}
    clock_box = (50, 18, 87, 35)
    views = {"rink": (0, 3840, 320, 1536), "left-net": (150, 1350, 400, 800), "right-net": (2600, 3800, 400, 800)}
    # the ice inside the end and near boards (the far boards curve is the top)
    ICE = Path([(0, 0), (3840, 0), (3840, 690), (3800, 717), (3707, 917), (3653, 1037), (3560, 1277),
                (3440, 1450), (3400, 1536), (560, 1536), (400, 1317), (333, 1183), (260, 1090), (150, 870),
                (40, 650), (0, 640)])

    bench_where = {"left": "behind the far boards, left of center, its door at the blue post (x 1612); only heads "
                           "show above the boards",
                   "right": "behind the far boards, right of center, its door at the blue post (x 2265); only heads "
                            "show above the boards"}
    box_where = {"right": "the near corner at the bottom-RIGHT of the frame (a player drops out of the frame as he sits)",
                 "left": "the near corner at the bottom-LEFT of the frame (a player drops out of the frame as he sits)"}

    def __init__(self, board_poly, bench=None):
        self.P = board_poly
        self._side = bench or self.bench_side
        self.bench_x = self.BENCHES[self._side]

    @property
    def side(self):
        return self._side

    def bench_view(self):
        x0, x1 = self.bench_x
        y = float(np.polyval(self.P, (x0 + x1) / 2)) if self.P is not None else 600.0
        return x0 - 200, x1 + 200, int(y) - 170, int(y) + 60

    def onice(self, x, rel):
        x = np.asarray(x, float); rel = np.asarray(rel, float)
        y = rel + np.polyval(self.P, x)
        inside = self.ICE.contains_points(np.c_[x.ravel(), y.ravel()]).reshape(x.shape)
        return (rel > 5) & inside

    def at_bench(self, x, rel):
        x0, x1 = self.bench_x
        return (x > x0) & (x < x1) & (rel < 15)

    def bench_zone(self, x, rel):
        x0, x1 = self.bench_x
        return (x > x0 - 40) & (x < x1 + 40) & (rel > -80)


class Renton2(Kirkland):
    """Renton from Oct 17, 2026: a new camera low at center ice on the near side with a fisheye lens, the whole
    frame (3840x1920). The far boards bow up to y ~340 at center and drop to ~1030 at the frame edges, where the end
    boards run down to the near boards along the bottom. Same rink as before, so the benches are still behind the far
    boards, away left (we wore light blue) and home right, with the penalty boxes between them; a player at the far
    boards is about as tall as with the old camera (~75 px), so the bench rules need no scaling."""
    crop_top = 220 / 1920
    board_band = (0.15, 0.56)
    board_lowest = True           # yellow signs above the end boards, and the scoreboard's digits
    size = (3840, 1920)
    center_x = 1940
    nets = {"left": 560, "right": 3345}
    NET_Y = 755                   # both nets sit at about this y, right in front of the end boards' kick plate
    min_break = 25
    bench_side = "left"
    # x at the boards: the away bench runs from the glass post at 1380 to its box (1735-1865, a boxed player is
    # "at the bench" as with the old camera), the home bench from its box (2020-2150) to 2500
    BENCHES = {"left": (1380, 1800), "right": (2080, 2500)}
    bench_where = {"left": "behind the far boards, from the glass post at x 1380 to about 1735 (only heads show "
                           "above the boards; the scorekeeper's window is at center)",
                   "right": "behind the far boards, from about 2150 to 2500 (only heads show above the boards; the "
                            "scorekeeper's window is at center)"}
    box_where = {"left": "between the benches, x 1735-1865", "right": "between the benches, x 2020-2150"}
    scoreboard = (3456, 576, 150, 126)    # even sides: ffmpeg rounds an odd crop of yuv420 video down, misaligning frames
    shots_boxes = {"home": (36, 57, 48, 69), "guest": (50, 66, 64, 79)}
    clock_box, clock_tilt = (51, 31, 87, 45), 31   # the board hangs at an angle
    views = {"rink": (0, 3840, 220, 1920), "left-net": (100, 1300, 480, 1080), "right-net": (2600, 3800, 470, 1070)}
    # the ice inside the near boards, which bow down to the frame's bottom edge at center (the far boards curve is the
    # top)
    ICE = Path([(0, 0), (3840, 0), (3840, 1000), (3790, 1030), (3600, 1240), (3400, 1440), (3200, 1600),
                (2880, 1770), (2600, 1850), (2200, 1910), (1920, 1920), (1600, 1910), (1400, 1880), (1200, 1830),
                (1000, 1760), (800, 1660), (600, 1540), (400, 1360), (200, 1120), (100, 1030), (0, 1000)])

    def in_crease(self, x, rel, net_x):
        """Near the end boards the boards curve is steep, so the crease is a box in the frame around the net."""
        x = np.asarray(x, float)
        y = np.asarray(rel, float) + np.polyval(self.P, x)
        return (np.abs(x - net_x) < 160) & (y > self.NET_Y - 50) & (y < self.NET_Y + 90)


class Renton2Band(Renton2):
    """Renton's new camera as LADA Y's Oct 12 video came (LiveBarn, 3600x1800, scaled up to 3840x1920): a black band
    with the LiveBarn logo over the top 264 rows, and the picture 266 px lower than Oct 17's at the same scale (the
    far boards curve fits Oct 17's plus 266 at every x), cut off at the bottom by as much. Everything with a y moves
    down by DY; crop_top stays, since crops.py finds the crops by it and the band is above the ice anyway."""
    DY = 266
    board_band = (0.29, 0.70)
    NET_Y = Renton2.NET_Y + DY
    scoreboard = (3434, 838, 150, 126)    # measured on the Oct 12 frame (the board at x 3445-3573, y 845-957)
    clock_box = (70, 30, 110, 44)
    views = {"rink": (0, 3840, 486, 1920), "left-net": (100, 1300, 746, 1346), "right-net": (2600, 3800, 736, 1336)}
    ICE = Path(Renton2.ICE.vertices + (0, DY))


class Renton2Thin(Renton2):
    """Renton's new camera as LADA R's Oct 19 video came (LiveBarn, 2560x1280 at best on YouTube, scaled up to
    3840x1920): a thin black band over the top ~60 rows and the picture 62 px lower than Oct 17's at the same scale
    (the far boards curve fits Oct 17's plus 62 at every x). Renton2Band's shift, smaller."""
    DY = 62
    board_band = (0.18, 0.59)
    NET_Y = Renton2.NET_Y + DY
    scoreboard = (3456, 638, 150, 126)
    views = {"rink": (0, 3840, 282, 1920), "left-net": (100, 1300, 542, 1142), "right-net": (2600, 3800, 532, 1132)}
    ICE = Path(Renton2.ICE.vertices + (0, DY))


RINKS = {"renton": Renton, "snoqualmie": Snoqualmie, "snoqualmie2": Snoqualmie2, "kirkland": Kirkland,
         "renton2": Renton2, "renton2band": Renton2Band, "renton2thin": Renton2Thin}

# Our jersey that game, as tests on process.py's torso colour fractions (the dets.csv columns, or a dict of them):
# `ours` picks our players for tracking, the looser `crop` which detections get a 4K crop for OCR and review.
# White (home) jerseys have blue numbers and trim, so the blue fraction is low; what tells them apart is a white
# torso with little dark in it. Referees' stripes are 25-55% dark, dark jerseys more. Red jerseys with white
# stripes (a Sea Otter's) are 25-60% white but 30-50% red; ours are under 10% red.
JERSEYS = {
    "light blue": dict(ours=lambda c: c["blue"] >= 0.3, crop=lambda c: c["blue"] >= 0.12),
    "white": dict(ours=lambda c: (c["red"] < 0.1) & (((c["white"] >= 0.35) & (c["dark"] < 0.3)) |
                                                    ((c["white"] >= 0.25) & (c["dark"] < 0.2) & (c["red"] < 0.05))),
                  crop=lambda c: (c["white"] >= 0.25) & (c["dark"] < 0.35) & (c["red"] < 0.1)),
    # our light blue against an opponent whose white jerseys have big sky-blue panels (Teamy McTeamface): half of
    # theirs pass the plain light-blue test. Hue tells them apart (bhue at Kirkland: ours ~113, theirs ~107)
    "light blue vs sky blue": dict(ours=lambda c: (c["blue"] >= 0.3) & (c["bhue"] >= 111),
                                   crop=lambda c: (c["blue"] >= 0.12) & (c["bhue"] >= 110)),
    # our white against LADA's own light blue (LADA R vs LADA Y): 9% of the light-blue torsos pass the white test on
    # their white numbers and trim; our blue numbers are rarely 30% of the torso
    "white vs light blue": dict(ours=lambda c: JERSEYS["white"]["ours"](c) & (c["blue"] < 0.3),
                                crop=lambda c: JERSEYS["white"]["crop"](c)),
    # our white against Teamy McTeamface's navy with sky-blue panels and white numbers (LADA R, Oct 19): 89% of
    # theirs pass the plain white test. Their blue is a greener hue (bhue ~107, ours ~118) and more of it; this kept
    # 90% of the crops read as our numbers and 11% of theirs
    "white vs navy and sky blue": dict(
        ours=lambda c: JERSEYS["white"]["ours"](c) & ~(((c["bhue"] >= 100) & (c["bhue"] <= 111)) &
                                                       (c["blue"] + c["lblue"] > 0.15)),
        crop=lambda c: JERSEYS["white"]["crop"](c)),
}


def _full_dir(folder):
    """W/full for a folder holding dets.csv itself or a link to it (period dirs)."""
    if os.path.exists(os.path.join(folder, "rink.json")) or not os.path.exists(os.path.join(folder, "dets.csv")):
        return folder
    return os.path.dirname(os.path.realpath(os.path.join(folder, "dets.csv")))


def _config(folder):
    p = os.path.join(_full_dir(folder), "rink.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def rink_name(folder):
    return _config(folder).get("rink", "renton")


def jersey(folder):
    """Our jersey's colour tests (JERSEYS) for this video: rink.json's "jersey", light blue unless set."""
    name = _config(folder).get("jersey", "light blue")
    return RINKS[rink_name(folder)].jerseys.get(name) or JERSEYS[name]


def rink(folder):
    """Geometry for the video whose detections live in `folder` (W/full, or a period dir linking into it)."""
    full = _full_dir(folder)
    bp = os.path.join(full, "boards_poly.npy")
    return RINKS[rink_name(folder)](np.load(bp) if os.path.exists(bp) else None, bench=_config(folder).get("bench"))
