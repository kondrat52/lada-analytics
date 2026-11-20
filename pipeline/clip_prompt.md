Check {n} highlight clips of a rec-hockey game before the team sees them. Each clip is a virtual camera over a wide video of the whole rink: it follows the play, closes in on the net at a goal, and a goal clip ends with a zoomed half-speed REPLAY. Judge only from what the frames show; the clip's own arguments may be wrong (a shot or goal time off by seconds, the camera on the wrong player), and catching that is part of the job.

Work folder: W={W}. Python: PY={PY} (run your own scripts with `-I`). Run pipeline commands from {ROOT}. Your scratch folder, the only place you write: {scratch}/. Don't change the clips or anything else.

Us: {team_desc}, in {jersey_desc}. Opponents: {opp_desc}. Referees: black-and-white stripes.
{goalie_line} {nets_line}

Each clip has a contact sheet: one tile per second of the clip, the clip second on each tile; the real-time part first, then the replay (its tiles say REPLAY; each replay second is half a second of play). The tiles nearest the start of the scoring play, the scorer's last touch, the goal and the pass are framed and labeled START, SHOT, GOAL and PASS, once in the real-time part and once in the replay; a penalty's call is labeled POSTER. Read each sheet. Where a tile is too small to tell, tile that stretch closer:
`$PY pipeline/run_game.py clipsheet <clip.mp4> {scratch}/<name>_zoom.jpg --from <s> --to <s> --step 0.25`
(the clip seconds as on the sheet). The game's video is in W: `$PY pipeline/run_game.py frames $W <out.jpg> --view rink --range <t0> <t1> 0.5` shows the whole rink at those seconds of video, to find a player outside the clip's frame; a custom crop, `frames $W <out.jpg> X0 X1 Y0 Y1 TILE_W COLS t1 t2 ...`, maps a tile linearly onto those frame pixels, and the detections nearest a spot (skates in frame pixels) are `{dets} <t> <x> <y>`. Each clip below says how its clip seconds map to seconds of video.

The rule the team holds every goal clip to: the replay shows the player who put the puck in, taking his shot. That is the credited scorer the clip names (ours or theirs) unless you positively see him somewhere he cannot have scored from. The team complained about a clip in 7 of the 14 games to mid-November, and twice since because the replay was on someone else (both times the scorer had shot from the point or the boards while the frame was on the crease).

What to ask of every goal clip:
1. Is the credited scorer in the frame, whole and not at the edge, at his last touch (his shot, deflection or jam): on the SHOT tiles, live and in the replay? If the player shooting on the SHOT tile is someone else, look for the credited scorer first, by his number or nameplate: is he in the frame at all, then or in the seconds before? A shot from the point or the boards is easy to miss when the frame is on the crease. If he isn't in the frame, the clip is on the wrong player.
2. Before the shot, does the camera stay with the puck carrier, or does it sit on the net (an empty-looking net, a goalie alone) while the play is still coming up the ice? Give the first clip second the net is shown without the play.
3. Does the replay start before the scoring play: its first tiles show the START (the rush, the drive or the pass that began it) or, without one, the scorer with the puck before his last touch? Is the SHOT tile his last touch? If the play started earlier than the replay, or the last touch is at another clip second, give that clip second.
4. Does the replay run until the puck is in: the goalie beaten, the puck in the net, arms going up? If the play is still going on at the last replay tile, the goal time is early: say so.
5. If a pass is credited, is the passer in the frame at the PASS tiles, live and in the replay?
6. Does the camera follow the credited players and the play, or someone else (often a big player near the camera) while the goal happens small in a corner?
For a penalty: is the penalized player in the frame in the seconds before the call, and is the infraction on screen?
Where a clip lists warnings from the camera-path check, confirm or refute each one from the sheet.

The clips:

{clips}

Each problem you report gets a `kind`, which decides what happens next:
- `camera`: the live part or the replay doesn't show the play, or doesn't show the player who scores at his last touch: the credited scorer not in the frame, the camera on someone else, an empty net while the play is elsewhere, the scorer cut off at the edge; for a penalty, the camera not on the penalized player. The clip is cut again. Give `spot`: [t, x, y] of the credited scorer at his last touch (for a penalty, the player at the infraction), t in seconds of video and x, y his skates in frame pixels, found on full-rink frames and the detections command; null if you can't find him.
- `time`: a time is off: the goal, the last touch, the start or the pass happens at another moment than its tile. `which`: "goal", "shot", "start" or "pass"; `estimate`: the clip second where it really is (as on the tiles; or `estimate_t` in seconds of video); for "shot", "start" and "pass" also `spot`: [t, x, y] as above, when you can. The clip is cut again.
- `credit`: the clip shows the play and the scorer's last touch, and the credited scorer is in the frame and clearly did not shoot: someone else did. `seen`: the number of who did; `credited_at`: [t, x, y] where you see the credited scorer at that moment, t in seconds of video and x, y his skates in frame pixels, as for `spot` (the goal checker's own sighting, where a clip gives one, will do). Only then: if the credited scorer isn't in the frame, it is `camera`, unless the clip below says the goal checker saw someone else score. Nothing is cut again; it goes to the team.
- `cant_tell`: something you can't make out from the frames (a number you can't read, the puck hidden in a pile). Nothing is cut again; it goes to the team.

Write {out_file}: a JSON list with one entry per clip, either
`{{"clip": "{example}", "ok": true}}`
or
`{{"clip": "{example}", "ok": false, "problems": [{{"kind": "camera", "at": 26.25, "question": 1, "what": "the replay's SHOT tile shows white #76 shooting from the point; the credited #36 is not in the frame from 22 to 33 s; on full-rink frames he is at the far point and shoots at 1256.4", "spot": [1256.4, 2811, 577]}}, {{"kind": "time", "at": 31.5, "question": 3, "what": "the drive that starts the pile is at clip 6 s, before the replay opens", "which": "start", "estimate": 6.0, "spot": null}}]}}`
where `at` is the clip second (as on the tiles), `question` the number above (0 for anything else) and `what` one line a person can act on. `ok` is false only when there is a `camera` or a `time` problem; list `credit` and `cant_tell` problems with `"ok": true`. Report only what the tiles and frames show; when you can't tell, say so (`cant_tell`) rather than guessing.
Your final reply: one line per clip, "ok" or what is wrong (its kind) and at which clip second.
