# Goals, penalties and clips

## Finding the goals

`run_game.py goals $W` first prints the game sheet's goals (`sheet.json`, from `run_game.py sheet`) with the
video time each period clock implies: the second the board's clock first showed the goal's time (`clock.json`,
read by fetch), which the clock stops at in the 3rd too; without `clock.json`, period start plus the clock's elapsed
time, exact where the clock runs through stoppages and otherwise the earliest the goal can be. Then it
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
before the time the sheet's clock implies, even in a period whose clock ran through stoppages. It isn't always that
far: on Doofers' Oct 10 game (Snoqualmie B) the 1st period's three goals were 1–5 s before it and the 2nd's matched
it, so search from about 15 s before the implied time to 5 s after. On LADA Y's Oct 12 game (Renton, clock running
through stoppages in the 1st and 2nd) five goals were 2–7 s before it, but the 2nd period's last one was 7 s after:
widen the search to 10 s after when the first pass finds nothing.
The game sheet can put a goal in the wrong period: on LADA R's Sep 21 game it had Moshchuk's goal at 17:26 of
the 2nd, but nothing happened then, and 34 s into the 3rd the board's clock stopped at 17:26 and the home score
and shots went up. A sheet goal with no candidate near its time is worth looking for at the same clock in the
next or previous period. The credited scorer can be wrong too: on Doofers' Sep 27 game the sheet gave the first goal to
Babkin #26, who wasn't on the ice (two frame checks agreed; he came on for the faceoff after it, and Albantov #29 was
at the crease). The page keeps the sheet's credit, the goal's note and `game.json`'s notes say what the video shows,
and the lineup check keeps listing it, which is expected. A frame check can misread the scorer too: on Beerteam's
Sep 27 game it read the winner's scorer as Kleiman #69 where the sheet had Shikhanov #70, both were on the ice, and
the page credited Kleiman until the team confirmed Shikhanov, which the video shows as well. So `highlights.json`
always keeps the sheet's scorer. When a frame check names someone else who was also on the ice, the page doesn't
say so: ask the user in the summary to check with the team, and change the credit only on their word. A clock time can lose a digit too: on Beerteam's Sep 27 game the sheet put Bogdanov's goal at 17:17 of the 3rd, where nothing
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

Give it the scoresheet's times when you have them and tell it which net is ours. The lineup windows have their own
generated briefs (`run_game.py gaps`, step 6 of the skill); this one is for goals and penalties.

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
Doofers' Oct 18 game had the same: #61's boarding plus misconduct, #61 in the box for half a minute, then Panova #75
climbed in from the bench and sat the 2:00 (the panel still said 61).

A penalty shot replaces the minor, and SportNinja's game sheet doesn't record it: on BW's Oct 18 game it still listed
#88's hooking as a 2-minute minor. The board gives it away: the panel posts "88 2:00" while the clock is stopped, then
goes dark before the faceoff, the clock stays frozen for about a minute, and `run_game.py skaters` drops to our goalie
alone while their shooter skates in from center. There's no `pk`. Put the stretch with all our skaters at the bench
in the period's `"ps"` (solve puts nobody on, so the clip's card lists no one), clip the infraction as a `penalty`, and
clip the shot as a `"moment"` titled "Penalty shot". With one skater on the ice the default framing wanders off to
center ice and misses the save, so pass the net's x as the focus (630 or 3260 at Snoqualmie A). A penalty shot for us
leaves our shooter on the ice, which `ps` doesn't model yet: `ps` plus an `on` for the shooter would conflict.

For each of our penalties, find the infraction: the referee raises an arm right after it (a delayed penalty),
play goes on until our team touches the puck, then the whistle and the penalty-kill faceoff. In the 3rd the clock
stops at the whistle and the sheet's video time lands there, 1–10 s after the infraction, so start 10–20 s before
it. In the 1st and 2nd the clock runs through the stoppage, and the sheet's time is usually 20–50 s after the
infraction (up to 73 s on the archived games), so look back from there. The referee may signal from the far end, so look where the penalized
player was in the seconds before the arm went up: his track in `$W/pN/segs_final.csv` (`plabel` = his number) and
full-rink frames 1 s apart. An opponent going down near him is the usual sign.

## Clips

```sh
$PY pipeline/run_game.py clip $W <game-id> goal-1 <t-12> <t+10> <t> "#44,#2" --net for     # ours: scorer, then assists
$PY pipeline/run_game.py clip $W <game-id> goal-3 <t-12> <t+10> <t> --net against          # theirs aren't tracked
$PY pipeline/run_game.py clip $W <game-id> penalty-88 <t-12> <t+10> <t> "#88"
```

About 22 s per event, ending a few seconds after the goal or call, with a poster frame at the last time given.
Every goal clip gets `--net` and, for ours, the scorer and assists from `sheet.json`. The camera then keeps the
credited players in the frame on the build-up, closes in on the net the goal went into (and the slot) from 6 s
before `t` to 2 s after, keeping the scorer and any passer that fits that tight frame, and ends with an 11 s
half-speed replay zoomed in on the net (`t` −4 s to +1.5 s, about 580 px of the 3840). So `t` must be the goal
to the second. Following the main group alone had missed the scorers: on TK's Oct 25 game Belousenko shot from
the slot just outside the frame, and at Snoqualmie A's far nets a scramble is a few dozen pixels tall at any crop
the live camera holds (the replay is what shows the puck going in). The labels are the solver's, so cut clips
after the last solve; a mislabeled track only moves the build-up, not the replay.
The default framing (no `--net`) follows the main group of players. A focus x (about 500 = left corner, 3300 = right; a net x
from `rink.py`) keeps the virtual camera on one end. For a penalty pass `#<number>` to follow the player who took
it, starting a few seconds before the infraction. A focus x can lock onto someone right by the camera (at
Kirkland a referee in the near corner filled the frame), so start with the default and check a few frames of each
clip (cv2 can read the mp4). A focus x only weights where the players are, so it can't bring an empty net into
the frame: TK's Oct 25 empty-netter from center ice stayed out of view with 2700 and 3250 alike, and the clip
shows the shot, not the puck going in. Clips land in the team site's `games/<id>/clips/`, about 5 MB each, served by GitHub
Pages. Most recordings' audio is silent, so their clips have no sound; where it isn't (Renton's new camera, LADA R's
Oct 5 LiveBarn recording at Snoqualmie A), `clip` keeps it.

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
was on the ice for each goal. The check only covers the credited players and the count, so a wrong uncredited
skater gets through: on TK's Oct 25 game the empty-netter (scorer only) showed #33 in #89's place, because #89's
track was lost 9 s before the goal and the next piece was chained to #33. The frame check had read #89 in the
fist-bump line, and the user caught it on the page. So before publishing, compare the frame check's on-ice reads
with the solver's lineup at every goal (`pN/shifts_final.csv` rows with `t0 <= t < t1`).
