# Goals, penalties and clips

## Finding the goals

`run_game.py goals $W` first prints the game sheet's goals (`sheet.json`, from `run_game.py sheet`) with the
video time each period clock implies: period start plus the clock's elapsed time, exact where the clock runs
through stoppages and otherwise the earliest the goal can be (every stoppage before it pushes it later). Then it
lists candidate goals from the video: center-ice faceoff formations that aren't period starts, and long stoppages
with where play restarted (a goal is always followed by a center faceoff). It prints which net is ours each
period, so goals for and against can be told apart. The scoreboard narrows each candidate: the clock stops a
second or two after the goal and the score changes soon after (on Oct 3 the board changed about 12 s after the
game sheet's time).

Check each by eye:

```sh
$PY pipeline/run_game.py frames $W $W/g.jpg --view rink --range <t-60> <t> 3      # the minute before the faceoff
$PY pipeline/run_game.py frames $W $W/gz.jpg --view left-net <t1> <t2> ...        # or right-net, 1 s apart
```

A real goal shows a scramble or shot at one net, the referee pointing at it, and one team celebrating before the
players drift to center. Most candidates without that are false alarms (icings, offsides, a timeout). The
scorekeeper can also be slow or wrong: on Sep 14 the board first credited our goal to the other team and fixed it
minutes later.
The game sheet can put a goal in the wrong period: on LADA R's Sep 21 game it had Moshchuk's goal at 17:26 of
the 2nd, but nothing happened then, and 34 s into the 3rd the board's clock stopped at 17:26 and the home score
and shots went up. A sheet goal with no candidate near its time is worth looking for at the same clock in the
next or previous period.

## Delegating the check

The frames are mechanical and cost the main session a few thousand tokens each, so hand a batch of candidates to
one general-purpose subagent:

> Verify candidate goals in a rec-hockey video. Work folder: $W. Python: $PY. For each candidate time below, run
> `$PY pipeline/run_game.py frames $W <your scratch>/g_<t>.jpg --view rink --range <t-60> <t> 3`, Read it, and if
> play ended at a net run the matching `--view left-net` or `--view right-net` 1 s apart over the last 10 s.
> A goal shows a shot or scramble at a net, the referee pointing at it, and one team celebrating before everyone
> drifts to center. Our net this period is on the <left|right>. Write `<your scratch>/goals.json`: one object per
> candidate with `t` (the candidate), `goal` (true/false), `at` (seconds of video of the goal itself), `net`
> (left/right), `team` (for/against), and a one-line `note` of what you saw. Candidates: <list>. Reply with one
> line per candidate.

Give it the scoresheet's times when you have them and tell it which net is ours.

## Penalties

A bench minor (too many players) is served by a skater: find who sat by zooming on the box as the panel goes
dark (he climbs out and his number shows), and put him as the `pk`'s `player` so the solver keeps him off. Two
penalties at once are two overlapping `pk` entries; the solver and the lineup check expect 3 skaters then.

The game sheet can name the wrong player: on Doofers' Sep 19 game it gave the last penalty to #31 Sourov, but the
board's panel showed 37 and Akulov #37 went to the box. And a minor late in a period can wait for the next one:
Sourov's coincidental tripping with 1:06 left in the 2nd wasn't served then (5 on 4 to the end, our box empty); he
went in during the intermission and sat the first 2:00 of the 3rd, so the `pk` is in the 3rd only.

A minor the game sheet gives at the same clock as a power-play goal against may never be served: on BW's Oct 11
game #54's high-sticking at 15:09 never lit the panel and we had 5 skaters again from the faceoff. Check
`run_game.py skaters` across the span before adding its `pk`.
On LADA R's Sep 21 game two penalties on the sheet were never served at all (our #39's slashing and their #0's
tripping): no panel, an empty box, and the player kept playing. A coincidental pair (one each) leaves 4-on-4 with
a `pk` for ours. A major or misconduct can have another player serve the minor: Sep 21's #81 got boarding plus a
10-minute misconduct, #10 sat the minor (the `pk`'s `player`), and #81 never came back (an `off` to the end).

For each of our penalties, find the infraction: the referee raises an arm right after it (a delayed penalty),
play goes on until our team touches the puck, then the whistle and the penalty-kill faceoff. The clock stops at
the whistle, so start 10–20 s before it. The referee may signal from the far end, so look where the penalized
player was in the seconds before the arm went up: his track in `$W/pN/segs_final.csv` (`plabel` = his number) and
full-rink frames 1 s apart. An opponent going down near him is the usual sign.

## Clips

```sh
$PY pipeline/run_game.py clip $W <game-id> goal-1 <t-12> <t+10> <t> [focus]
```

About 22 s per event, ending a few seconds after the goal or call, with a poster frame at the last time given.
The default framing follows the main group of players. A focus x (about 500 = left corner, 3300 = right; a net x
from `rink.py`) keeps the virtual camera on one end. For a penalty pass `#<number>` to follow the player who took
it, starting a few seconds before the infraction. A focus x can lock onto someone right by the camera (at
Kirkland a referee in the near corner filled the frame), so start with the default and check a few frames of each
clip (cv2 can read the mp4). Clips land in the team site's `games/<id>/clips/`, about 5 MB each, served by GitHub
Pages. The recordings' audio is silent, so clips have no sound.

## `highlights.json`

```json
[{"type": "goal", "team": "for", "t": 3828, "scorer": 54, "assists": [36], "clip": "clips/goal-3.mp4",
  "poster": "clips/goal-3.jpg", "note": "3rd period, clock 9:06: in alone on the goalie, 4-2"},
 {"type": "penalty", "player": 4, "t": 3580, "clip": "clips/penalty-4.mp4", "poster": "clips/penalty-4.jpg",
  "note": "1st period, clock 3:40: 3 minutes, ended by their power-play goal at 0:38"}]
```

`t` is seconds of video at the goal or infraction. `scorer` and `assists` are optional and come from the
scoresheet; the lineup check in solve and publish then flags a credited player who isn't on the ice at `t`, which
catches a shift the solver ran on past a line change (on Oct 3, #43's track ended mid-ice, his shift ran through
the goal, and the scorer lost 10 s at the net; an `"off"` entry in `periods.json` fixed it). The page shows who
was on the ice for each goal.
