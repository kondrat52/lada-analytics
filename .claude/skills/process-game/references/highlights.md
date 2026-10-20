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
minutes later. The sheet's clock lags the goal itself: on Doofers' Sep 13 game all five goals were 6–13 s of video
before the time the sheet's clock implies, even in a period whose clock ran through stoppages.
The game sheet can put a goal in the wrong period: on LADA R's Sep 21 game it had Moshchuk's goal at 17:26 of
the 2nd, but nothing happened then, and 34 s into the 3rd the board's clock stopped at 17:26 and the home score
and shots went up. A sheet goal with no candidate near its time is worth looking for at the same clock in the
next or previous period. The credited scorer can be wrong too: on Doofers' Sep 27 game the sheet gave the first goal to
Babkin #26, who wasn't on the ice (two frame checks agreed; he came on for the faceoff after it, and Albantov #29 was
at the crease). The reverse slips through: on Beerteam's Sep 27 game the sheet credited the winner to Shikhanov #70,
unassisted, while the video plainly shows Kleiman #69 carrying in alone and scoring. #70 was on the ice, so the
lineup check passed and only the frame check caught it; read the scorer's number on every goal. When the video
plainly shows who scored, credit that player in `highlights.json` (the user asked for Kleiman) and say in the goal's
note and `game.json`'s notes what the sheet credits; when the video doesn't settle it, keep the sheet's credit. A
credited scorer who wasn't on the ice stays in the lineup check's list, which is expected. A clock time can lose a digit too: that sheet put Bogdanov's goal at 17:17 of the 3rd, where nothing
happened, and the board's clock stopped at 7:17 for it. The sheet's time for a power-play goal can be the penalty's, not the goal's: on TK's Oct 17
game it had Roadrunners' goal at 12:25, but the board's clock read 11:48 when it went in, 37 s later, and the penalty
panel went dark then. Where the video has sound (Renton's new camera), the whistle after a goal is audible and pins
it to a fraction of a second.

The board can also count a goal that never happened. On Beerteam's Oct 4 game the clock froze at 18.6 for Jackalopes'
3rd goal; 15 s later the guest score went to 4 and their shots up by one, while the players were only lining up at
center. The sheet and LADA had 1-3. A score change while the clock is stopped and nobody is playing is the
operator's slip: the sheet's score stands, and the shot that came with it comes off `shots.json` (and off its guest
`series`). That sheet didn't mark the last goal as empty-net either. The frame check found our net empty, and a
crease zoom 1 s apart found our goalie out from 3851 to 4026 (an `extra` span, about 1:30 of clock with stoppages).

The recording itself can skip. LADA R's Sep 14 video loses about two minutes of the 3rd at 44:37: from one second to
the next the board's clock jumps from 13:59 to 11:58, the home score and shots go up during live play, and every
player is somewhere else (three tracks end at 2677.4 s and two begin at 2677.5 s). The sheet's 13:11 goal fell in
the gap. A board score change with no stoppage or center faceoff before it is the sign; frames half a second apart
confirm the cut. Such a goal stays out of `highlights.json` (the page counts goals on video, and there is nothing to
clip), and the notes give the final score and the gap. In that game the clock ran through most goals and each goal
came 1–6 s before the board's score changed, not 6–13 s before the sheet's time.

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

A penalty shot replaces the minor, and SportNinja's game sheet doesn't record it: on BW's Oct 18 game it still listed
#88's hooking as a 2-minute minor. The board gives it away: the panel posts "88 2:00" while the clock is stopped, then
goes dark before the faceoff, the clock stays frozen for about a minute, and `run_game.py skaters` drops to our goalie
alone while their shooter skates in from center. There's no `pk`. Put the stretch with all our skaters at the bench
in the period's `"ps"` (solve puts nobody on, so the clip's card lists no one), clip the infraction as a `penalty`, and
clip the shot as a `"moment"` titled "Penalty shot". With one skater on the ice the default framing wanders off to
center ice and misses the save, so pass the net's x as the focus (630 or 3260 at Snoqualmie A). A penalty shot for us
leaves our shooter on the ice, which `ps` doesn't model yet: `ps` plus an `on` for the shooter would conflict.

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

A play worth a clip that is neither (the user asked for TK's 3-on-0 that didn't score on Oct 17) is a
`"moment"` with a `"title"`, the card's heading: `{"type": "moment", "title": "3 on 0, no goal", "t": 1234,
"clip": "clips/moment-1.mp4", "poster": "clips/moment-1.jpg", "note": "..."}`. The page lists who was on the ice
for it as for a goal; it doesn't count toward goals and the lineup check skips it. The user's "around 3:00 in the
1st" was the clock (3:11 left, video 898), not 3:00 into the video: try both. A detection scan for 3+ of ours past
every opponent finds too many runs to use alone (the white test misses opponents), so look at the frames.

`t` is seconds of video at the goal or infraction. `scorer` and `assists` are optional and come from the
scoresheet; the lineup check in solve and publish then flags a credited player who isn't on the ice at `t`, which
catches a shift the solver ran on past a line change (on Oct 3, #43's track ended mid-ice, his shift ran through
the goal, and the scorer lost 10 s at the net; an `"off"` entry in `periods.json` fixed it). The page shows who
was on the ice for each goal.
