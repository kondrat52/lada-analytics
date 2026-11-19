Check {n} highlight clips of a rec-hockey game before the team sees them. Each clip is a virtual camera over a wide video of the whole rink: it follows the play, closes in on the net at a goal, and a goal clip ends with a zoomed half-speed REPLAY. Judge only from what the frames show; the clip's own arguments may be wrong (a shot or goal time off by seconds), and catching that is part of the job.

Work folder: W={W}. Python: PY={PY} (run your own scripts with `-I`). Run pipeline commands from {ROOT}. Your scratch folder, the only place you write: {scratch}/. Don't change the clips or anything else.

Us: {team_desc}, in {jersey_desc}. Opponents: {opp_desc}. Referees: black-and-white stripes.
{goalie_line} {nets_line}

Each clip has a contact sheet: one tile per second of the clip, the clip second on each tile; the real-time part first, then the replay (its tiles say REPLAY; each replay second is half a second of play). The tiles nearest the shot, the goal and the pass are framed and labeled SHOT, GOAL and PASS, once in the real-time part and once in the replay; a penalty's call is labeled POSTER. Read each sheet. Where a tile is too small to tell, tile that stretch closer:
`$PY pipeline/run_game.py clipsheet <clip.mp4> {scratch}/<name>_zoom.jpg --from <s> --to <s> --step 0.25`
(the clip seconds as on the sheet). If the game's video is still in W, `$PY pipeline/run_game.py frames $W <out.jpg> --view rink --range <t0> <t1> 0.5` shows the whole rink at those seconds of video, to see what happened outside the clip's frame.

What the team has complained about, and what to ask of every goal clip:
1. Is the shooter in the frame, whole and not at the edge, when the puck leaves his stick: on the SHOT tiles, live and in the replay? (Once he was off the frame because his track carried another number.)
2. Before the shot, does the camera stay with the puck carrier, or does it sit on the net (an empty-looking net, a goalie alone) while the play is still coming up the ice? Three complaints were this, all on rushes: give the first clip second the net is shown without the play.
3. Does the replay start before the shot: does its first tile show the shooter with the puck, or the drive that started a pile at the crease? If the SHOT tile shows a pile and an earlier tile shows the real shot or drive, say so with that clip second.
4. Does the replay run until the puck is in: the goalie beaten, the puck in the net, arms going up? If the play is still going on at the last replay tile, the goal time is early: say so.
5. If a pass is credited, is the passer in the frame at the PASS tiles, live and in the replay?
6. Does the camera follow the credited players and the play, or someone else (often a big player near the camera) while the goal happens small in a corner?
For a penalty: is the penalized player in the frame in the seconds before the call, and is the infraction on screen?
Where a clip lists warnings from the camera-path check, confirm or refute each one from the sheet.

The clips:

{clips}

Write {out_file}: a JSON list with one entry per clip, either
`{{"clip": "{example}", "ok": true}}`
or
`{{"clip": "{example}", "ok": false, "problems": [{{"at": 31.5, "question": 3, "what": "the replay opens on the pile; the drive to the net is at clip 6 s"}}]}}`
where `at` is the clip second (as on the tiles), `question` the number above (0 for anything else) and `what` one line a person can act on. Report only what the tiles show; when you can't tell, say so in `what` rather than guessing.
Your final reply: one line per clip, "ok" or what is wrong and at which clip second.
