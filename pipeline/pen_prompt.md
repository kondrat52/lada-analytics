Pin down the penalties of a rec-hockey game video from its frames and the arena scoreboard. For each penalty the game sheet lists below, ours and theirs: when the infraction and the whistle were, what the board's panel showed, who went into the box and when he came out, and for ours, the stretch we played a man short. Judge from what you see; the sheet's times only say where to start looking.

Work folder: W={W}. Python: PY={PY} (run your own scripts with `-I`). Run pipeline commands from {ROOT}. Your scratch folder, the only place you write: {scratch}/ (create it). Keep each image you Read to about 8 frames.

Us: {team_desc}, in {jersey_desc}. Opponents: {opp_name}, in {opp_desc}. Referees: black-and-white stripes.
Roster this game (number, nameplate): {roster}.{notes}
{goalie_line} {nets_line}
{card_line}
Rink: {rink_desc} Frame {frame_size}. {bench_desc} Our penalty box is {box_ours}; theirs is {box_theirs}.
The scoreboard: we are {board_side} on it (the sheet has us as the {sheet_side} team). Each penalty lights a panel on its team's side with the player's number and the time left, counting down with the game clock. {clock_desc} On the archived games the board ran a 2-minute minor for 3:00 wherever the clock ran through stoppages, and for 2:00 where it stopped at whistles; the sheet always says 2.

Tools:
- `$PY pipeline/run_game.py frames $W <out.jpg> --view rink --range <t0> <t1> <step>` renders full-rink frames at those seconds of video (or list times instead of --range). `--view bench` is a close-up of our bench and its door; `--view left-net` / `--view right-net` zoom on a net. A custom crop: `$PY pipeline/run_game.py frames $W <out.jpg> X0 X1 Y0 Y1 TILE_W COLS t1 t2 ...`; a tile maps linearly onto the X0..X1, Y0..Y1 you gave, so a point in a tile gives frame pixels. The whole ice in one wide tile, to count both teams' skaters on a faceoff: `$PY pipeline/run_game.py frames $W <out.jpg> {wide} <t>`.
- `$PY pipeline/scoreboard.py $W <out.jpg> t1 t2 ...` shows the arena scoreboard at those seconds: the period clock, both scores, shots, the penalty panels. Sheet it every 1-2 s around each penalty.
- The detections nearest a spot, skates (bottom middle of each box) in frame pixels: `{dets} <t> <x> <y>`.

Penalties (n = this list's order; minor and misconduct for one player at one clock are one item):
{pens}

For each one:
1. The board: the second the panel posts the number and time (`minutes`: what it showed, 2, 3, 5 or 10) and the second it goes dark.
2. The box: who skates into it after the whistle (full-rink frames 1-3 s apart, then a zoom on the box): read the number on the way in (`box_in`) and see when he climbs out (`box_out`, or the panel going dark if you can't see him leave). Don't trust which panel lit or the sheet's number: on Doofers' Sep 19 game the sheet named #31, the panel showed 37 and #37 went in. A bench minor (too many players) is served by a skater, and a teammate can serve a major's or a misconduct's minor: `sat` is who sat, when it isn't the sheet's player.
3. `t`, the infraction: the referee raises an arm right after it (a delayed penalty), play goes on until the penalized team touches the puck, then `whistle`. The referee may signal from the far end, so look where the penalized player was in the seconds before the arm went up; an opponent going down near him is the usual sign. Each item says where to start looking.
   `spot`, ours only: [t, x, y] with t the infraction's second and x, y the penalized player's skates then, in frame pixels (the nearest detection from the command above; read his number on a zoom first). The penalty's clip follows the tracked body at that spot: without it the clip follows the boxes labeled with his number, which on Beerteam's Nov 14 game were another player's at both penalties (#24's from 10 s before his infraction, #69's jumping onto #37 during it). null if you can't see him then.
4. `kill`, ours only: [start, end] in seconds of video, from the whistle to the moment we have five skaters again (the panel dark, the player out of the box), or 1 s after their power-play goal, which ends a minor early. A kill that runs across an intermission is one span; the script splits it. null, with `why`, only when you saw that we never played a man short (a null with a reason takes the proposed kill out); if you couldn't see whether or when we did, write "unsure" with what you saw in `note`, and the kill proposed from the clock stays. The cases for null:
   - coincident minors (one of ours and one of theirs at once): count both teams' skaters on a faceoff frame after the call (the wide tile above). At 5 on 5 (substitutes on, as on LADA Y's Nov 9 game) it is null with "coincident minors, 5 on 5", and `box_in`/`box_out` say when ours sat; at 4 on 4 it is a kill.
   - never served: no panel, an empty box, the player kept playing (LADA R's Sep 21 game had two). A minor at the clock of a power-play goal against may never be served (BW's Oct 11: #54's high-sticking never lit the panel).
   - a penalty shot instead of the minor: the panel posts while the clock is stopped and goes dark before the faceoff, the clock stays frozen about a minute, and all our skaters stand at the bench while their shooter skates in from center. null, and `ps`: [start, end] while all our skaters were at the bench.
   - a misconduct alone: the player sits 10 minutes, but the team doesn't play short (`box_in`/`box_out` still say when he sat).
   A minor late in a period can wait for the next one (Doofers' Sep 19: served from the 3rd's opening faceoff, our box empty to the end of the 2nd).
5. `desc`: one line for the game page; the page puts the period and clock in front of it. What the infraction was and how the penalty went, e.g. "tripping, 3 minutes on the board (the sheet says 2); Fisenko scored shorthanded during it", "holding along the near boards, 2 minutes, 4 on 4 for the first half (their #91 was in the box)", "roughing in a scrum with their #17, coincident minors, both teams played 5 on 5 while he sat the 2 minutes".
Theirs matter too (a 4 on 4, when our power play ended), so pin theirs down the same way, with "kill": null.

Write {out_file}: a JSON list with one object per item above, in this form:
{{"n": 1, "team": "ours", "player": 97, "period": "P2", "clock": "9:21", "minutes": 3, "t": 1676, "spot": [1676, 2210, 655], "whistle": 1678, "box_in": 1690, "box_out": 1898, "kill": [1678, 1898], "why": "", "sat": null, "ps": null, "desc": "tripping, 3 minutes on the board (the sheet says 2)", "sure": "high", "note": ""}}
- `player`: the sheet's number (null for a bench minor); `period` and `clock`: the board's when the penalty was called (normally the sheet's); seconds of video to 0.5 s; null for anything else you couldn't see (but `kill` as in 4); `spot` null for theirs; `sure`: high, medium or low; `note`: anything the session should know, or "".
Your final reply: one line per penalty: n, kill (or why none), spot, and what you saw.
