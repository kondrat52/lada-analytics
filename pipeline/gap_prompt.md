Check who of our team was on the ice in a few windows of a rec-hockey video where the automatic shift solver has the wrong number of our skaters. Judge from what you see in the frames, not from the solver's labels.

Work folder: W={W}. Python: PY={PY} (run your own scripts with `-I`). Run pipeline commands from {ROOT}. Your scratch folder, the only place you write: {scratch}/ (create it). Keep each image you Read to about 8 frames.

Us: {team_desc}, in {jersey_desc}. Opponents: {opp_desc}. Referees: black-and-white stripes.
Roster this game (number, nameplate): {roster}.{notes}
{goalie_line} {nets_line}
Read {card} once for everyone's look (sock stripes, pants, helmet and glove colours tell players apart when the number is hidden).

Rink: {rink_desc} Frame {frame_size}. {bench_desc}{box_desc}

Tools:
- `$PY pipeline/run_game.py frames $W <out.jpg> --view rink --range <t0> <t1> <step>` renders full-rink frames at those seconds of video (or list times instead of --range). `--view bench` is a close-up of our bench and its door; `--view left-net` / `--view right-net` zoom on a net. A custom crop: `$PY pipeline/run_game.py frames $W <out.jpg> X0 X1 Y0 Y1 TILE_W COLS t1 t2 ...`.
- `$PY pipeline/scoreboard.py $W <out.jpg> t1 t2 ...` shows the arena scoreboard (clock, score, penalty panels) at those seconds.
- `$W/pN/shifts_final.csv`: the solver's shifts (player, t0, t1). `$W/pN/segs_final.csv`: the tracked pieces behind them (tid, t0, t1, num = the label read or reviewed, -1 = none; plabel = the label after linking; x0,r0 / x1,r1 = position at start and end; bench0/bench1 = the piece starts/ends at our bench). `$W/rev_pN/manifest.csv` maps a piece (tid) to its review row (row_id). The pieces that overlap each window are listed under it below.

What goes wrong, usually: a piece that ends in mid-ice keeps a player on too long (the solver then drops someone else to keep the count); a lost piece drops a player who was there; a piece that starts at the bench counts from its first frame, so a player still sitting or just climbing on shows as on; two pieces swap identities at a crossing; a line change made during a stoppage legitimately shows 6 for a while (then say so).
{events}
Windows (seconds of video; the solver's lineup at the midpoint):
{windows}
{sitters}
For each window: look at full-rink frames every 2-3 s over the window plus ~10 s before and after, count our skaters on the ice (not the goalie), read numbers or nameplates on zooms, and watch the bench door for who stepped on or off and when. Then write {out_file}: a JSON list of
`{{"period": "P1", "kind": "on" | "off", "player": N, "start": s, "end": s, "why": "one line"}}`
where "on" means that player was on the ice over [start, end] although the solver missed him, and "off" means he was not on the ice then although the solver had him on. Make each span cover just the stretch that is wrong (from the real change to the solver's change), to a second. Only list fixes you are fairly sure of. For a window where the solver turns out right (a slow change in a stoppage, a real 4-on-4) add `{{"period": "P1", "window": "t0-t1", "ok": "what you saw"}}`; for one you can't settle, `{{"period": "P1", "window": "t0-t1", "unsure": "what you saw"}}`.
Your final reply: one line per window, who was on and the fix.
