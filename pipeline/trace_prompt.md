List every stretch one of our skaters is on the ice in part of a rec-hockey video. The automatic tracker has nothing on him, so nobody knows his shifts: judge only from what you see in the frames.

Work folder: W={W}. Python: PY={PY} (run your own scripts with `-I`). Run pipeline commands from {ROOT}. Your scratch folder, the only place you write: {scratch}/ (create it). Your stretch of video: {t0} to {t1} s, in {period}. Keep each image you Read to about 8 frames.

Us: {team_desc}, in {jersey_desc}. Opponents: {opp_desc}. Referees: black-and-white stripes.
Roster this game (number, nameplate): {roster}.{notes}
{goalie_line} {nets_line}
{card_line}
Rink: {rink_desc} Frame {frame_size}. {bench_desc}{box_desc}
{clock_line}
The player: #{player} {name}. His look: {look}
The tracker follows our jersey colour only and has no track, crop or review row for him, so he has no row on the roster card either. Tell him from a referee (black-and-white stripes, a black helmet, no stick) and from opponents by more than the colour: his helmet, socks, stick and the door he uses. Read his number or nameplate wherever you can.

Tools (enough for the job; don't write your own):
- `$PY pipeline/run_game.py frames $W <out.jpg> --view rink --range <t0> <t1> <step>` renders full-rink frames at those seconds of video (or list times instead of --range). `--tile <px>` and `--cols <n>` set the tile width and tiles per row (1000 px, 2 per row for the rink).
- `--view bench` is a close-up of our bench and its door; `--view left-net` / `--view right-net` zoom on a net. A custom crop: `$PY pipeline/run_game.py frames $W <out.jpg> X0 X1 Y0 Y1 TILE_W COLS t1 t2 ...` (frame pixels).
- Add `--tracks` to any `frames` command to draw our tracked players' boxes with their labels: he never has a box, which helps tell him from them.
- `$PY pipeline/scoreboard.py $W <out.jpg> t1 t2 ...` shows the arena scoreboard (clock, score, penalty panels) at those seconds.

Method:
1. Sweep your stretch with full-rink frames every 4 s (8 frames per image). In each frame decide: is he on the ice (yes / no / can't tell)? Zoom where a figure is far away or half hidden.
2. For every change (off to on, on to off), narrow the second down with frames 1 s apart around it and with the bench close-up: he is ON from the moment he steps through our bench door or over the boards onto the ice, and OFF from the moment he steps off. Standing on the ice in a stoppage (waiting for a faceoff) is ON; sitting in a penalty box is OFF.
3. Between shifts, find him at the bench now and then (a tight crop of our bench every 6 s or so): a seat he keeps, empty while he is on, confirms both edges.
4. If he is on the ice at {t0} or still on at {t1}, start or end that stretch exactly there and say so (`"open_start": true` / `"open_end": true`): another checker has the neighbouring stretch.
5. If he leaves for good (the dressing room, an injury) or sits in a penalty box, say when.

Then write {out_file}:

```json
{{"t0": {t0}, "t1": {t1},
 "shifts": [{{"on": {ex[0]}, "off": {ex[1]}, "sure": "high", "open_start": false, "open_end": false, "note": "through our door at {ex[0]} for #34; off at the door at {ex[1]} in a change on the fly"}},
            {{"on": {ex[2]}, "off": {ex[3]}, "sure": "med", "open_start": false, "open_end": false, "note": "..."}}],
 "notes": "anything odd: a stretch you couldn't see, where you read his number, who he usually changes for, where he sits"}}
```

Seconds of video, to the second, every shift in your stretch however short, and `"shifts": []` if he never came on. `sure`: high (you saw both the step on and the step off), med (an edge within about 3 s), low (an edge is a guess: say which in the note). A shift that is only in your reply is lost: write the file.
Your final reply: one line per shift (on, off, sure).
