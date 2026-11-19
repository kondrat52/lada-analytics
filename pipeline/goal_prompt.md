Pin down the goals of the {period_name} of a rec-hockey game video from its frames and the arena scoreboard. For each goal the game sheet lists below: the second the puck went in, where the scoring play started, who of ours was on the ice, and what the board did. Judge from what you see; the sheet's times only say where to start looking.

Work folder: W={W}. Python: PY={PY} (run your own scripts with `-I`). Run pipeline commands from {ROOT}. Your scratch folder, the only place you write: {scratch}/ (create it). Keep each image you Read to about 8 frames.

Us: {team_desc}, in {jersey_desc}. Opponents: {opp_name}, in {opp_desc}. Referees: black-and-white stripes.
Roster this game (number, nameplate): {roster}.{notes}
{goalie_line}
{card_line}
Rink: {rink_desc} Frame {frame_size}. {bench_desc}
{period} runs from {pstart} to {pend} s of video. In {period} OUR net (our goalie's) is the {our_side} one (x {our_net}): their goals go in there, ours go into the {their_side} net (x {their_net}).
The scoreboard: we are {board_side} on it (the sheet has us as the {sheet_side} team; if that side's score doesn't go up at our goals, we are the other one). {clock_desc}

Tools:
- `$PY pipeline/run_game.py frames $W <out.jpg> --view rink --range <t0> <t1> <step>` renders full-rink frames at those seconds of video (or list times instead of --range). `--view left-net` / `--view right-net` zoom on a net. A custom crop: `$PY pipeline/run_game.py frames $W <out.jpg> X0 X1 Y0 Y1 TILE_W COLS t1 t2 ...`; a tile maps linearly onto the X0..X1, Y0..Y1 you gave, so a point in a tile gives frame pixels.
- `$PY pipeline/scoreboard.py $W <out.jpg> t1 t2 ...` shows the arena scoreboard at those seconds: the period clock, both scores, shots, the penalty panels.
- The detections nearest a spot, skates (bottom middle of each box) in frame pixels: `{dets} <t> <x> <y>`.

Goals in {period} (n = the goal's number on the game sheet, counting the whole game):
{goals}

How to pin each one down:
1. The board first: sheet it every 2 s from about 30 s before the clock's second to 30 s after. At a goal the clock stops (a second or two after the puck goes in) and the scoring side's score goes up, usually within about 10 s. Postings 100 s and 3.5 minutes late have happened, during play, so a late score change doesn't refute a goal, while the clock stopping at the sheet's time supports it. Note the second the score changed (`board`).
2. Full-rink frames every 1 s over the 20 s before the clock stopped: a goal is a shot or a scramble at a net, the referee pointing at it, one team celebrating, then everyone drifting to center ice for a faceoff there. Every goal is followed by a center-ice faceoff; a stoppage that ends in a faceoff anywhere else is not a goal (a save, an icing, an offside). Where the operator ran the clock during a stoppage (it stops, moves on, stops again), the stoppage that ends at a center faceoff is the goal.
3. `t`: the second the puck crosses the goal line, to 0.25 s. Zoom on the net 1 s apart, then every 0.25 s with a tight crop of the crease (about 400 x 220 px of frame). In a scramble it is the LAST jam, when the puck actually goes in, not the first one: take the last jam before the first raised arm, and check that the puck is in the net after it.
4. `shot`: where the scoring sequence starts. For a clean shot, the moment the puck leaves the stick; in a scramble, the shot or the drive to the net that started it (follow the puck and the pile back from `t` on half-second sheets). Give [t, x, y] with x, y the shooter's skates in frame pixels (take the nearest detection from the command above). A replay runs from just before `shot` to just after `t` and must show the whole goal, so `shot` is never after `t` and rarely more than 10 s before it.
5. `pass`: [t, x, y] when the puck left the first assist's stick and his skates then (for an assist that was a rebound or a puck squirting out of a battle, his last touch); for a goal against off a rush, the pass or chip that sprang it; null when there is none you can see.
6. `on_ice`: the numbers of OUR skaters (not the goalie) you read on the ice within a few seconds of `t`, only those you are sure of: a number or nameplate you read, not a guess from a look.
7. `scorer_seen`: the number of whoever put it in, as you read it, or null; `scorer_sure`: high, medium or low. The sheet's scorer and assists stand whatever you see: report what you saw and don't judge the sheet.

When the sheet and the video part:
- Nothing near the clock's second: widen the search to a minute either side, then try the other times listed under the goal: the sheet has put goals in the wrong period (LADA R's Sep 21: 17:26 of the 2nd was 17:26 of the 3rd) and lost a digit (Beerteam's Sep 27: 17:17 for 7:17).
- The board counts a goal the sheet doesn't have (a score change with a stoppage and a center faceoff), the score changes while nobody is playing (the operator's slip), or the sheet has a goal the video doesn't show (the video starts after the game began; the recording skips, which the board's clock shows as a jump from one second to the next). Report each as you see it, don't decide which is right: an entry with "n": null for a goal that isn't on the sheet, "t": null for a sheet goal you can't find, and what you saw in "desc".
- Our goalie out of his net for an extra attacker (late in a period, an empty-net goal): say so in "note" with the seconds he left and came back.

Write {out_file}: a JSON list with one object per goal of {period} above, in this form:
{{"n": 1, "team": "for", "period": "{period}", "clock": "16:52", "t": 71.75, "shot": [71.0, 765, 502], "pass": [66.5, 2027, 527], "scorer_seen": 58, "scorer_sure": "high", "on_ice": [58, 74, 14], "board": 80, "desc": "Fisenko #58 from Bronnikov #74, in at the crease going down", "sure": "high", "note": ""}}
- `team`: "for" (ours) or "against"; `period` and `clock`: what the board showed when it went in (normally the sheet's); `board`: the second the score changed, or null; `sure`: high, medium or low, for `t` and `shot`; `note`: anything the session should know, or "".
- `desc`: one line for the game page saying what happened. The page adds the period, the clock and the score, so leave them out. Name ours the sheet's way, "Surname #N" with "from Surname #N" for the assists. For theirs, describe the play without naming the scorer: the note puts the sheet's scorer and assists in front of it ("{opp_poss} #21 Schiller from #48 Nanakul, at our left post ..."). Say "on the power play", "shorthanded" or "into the empty net" when it was. Examples: "Ber #14 finishes a 2-on-0"; "shorthanded, Fisenko #58 carries it out of our zone and jams it in"; theirs: "at our left post in a scramble with our goalie down".
Your final reply: one line per goal: n, t, shot, and what you saw.
