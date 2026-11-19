Check who of our team was on the ice in a few windows of a rec-hockey video where the automatic shift solver has the wrong number of our skaters. Judge from what you see in the frames, not from the solver's labels.

Work folder: W={W}. Python: PY={PY} (run your own scripts with `-I`). Run pipeline commands from {ROOT}. Your scratch folder, the only place you write: {scratch}/ (create it). Keep each image you Read to about 8 frames.

Us: {team_desc}, in {jersey_desc}. Opponents: {opp_desc}. Referees: black-and-white stripes.
Roster this game (number, nameplate): {roster}.{notes}
{goalie_line} {nets_line}
{card_line}
Rink: {rink_desc} Frame {frame_size}. {bench_desc}{box_desc}
{clock_line}
Tools (enough for the job; don't write your own):
- `$PY pipeline/run_game.py frames $W <out.jpg> --view rink --range <t0> <t1> <step>` renders full-rink frames at those seconds of video (or list times instead of --range). `--view bench` is a close-up of our bench and its door; `--view left-net` / `--view right-net` zoom on a net. A custom crop: `$PY pipeline/run_game.py frames $W <out.jpg> X0 X1 Y0 Y1 TILE_W COLS t1 t2 ...`.
- Add `--tracks` to any `frames` command to draw each tracked box of ours with its track id and the solver's label ("#12"; "?" no number; "x" left out of the solve as seated behind the bench boards).
- `$PY pipeline/run_game.py follow $W <out.jpg> {period} <tid> [<tid> ...] [--range <t0> <t1> <step>]` crops one tracked piece over time, one row per tid (default its whole span, about 10 crops): read a number, see where a piece came from, catch a swap.
- `$PY pipeline/scoreboard.py $W <out.jpg> t1 t2 ...` shows the arena scoreboard (clock, score, penalty panels) at those seconds.
- `$W/{p}/shifts_final.csv`: the solver's shifts (player, t0, t1). `$W/{p}/segs_final.csv`: the tracked pieces behind them (tid, t0, t1, num = the label read or reviewed, -1 = none; plabel = the label after linking; x0,r0 / x1,r1 = position at start and end; bench0/bench1 = the piece starts/ends at our bench). `$W/rev_{p}/manifest.csv` maps a piece (tid) to its review row (row_id). The pieces that overlap each window are listed under it below.

What goes wrong, usually: a piece that ends in mid-ice keeps a player on too long (the solver then drops someone else to keep the count); a lost piece drops a player who was there; a piece that starts at the bench counts from its first frame, so a player still sitting or just climbing on shows as on; two pieces swap identities at a crossing; a timeout (both teams gathered at their benches for 30-60 s, the clock frozen) shows odd counts: the players who come out of it get its seconds and whoever the solver has on instead is off; a line change made during a stoppage legitimately shows 6 for a while (then say so).
{events}
Windows (seconds of video; the solver's lineup at the midpoint):{round_note}
{windows}
{sitters}
For each window: look at full-rink frames every 2-3 s over the window plus ~10 s before and after, count our skaters on the ice (not the goalie), read numbers or nameplates on zooms, and watch the bench door for who stepped on or off and when. For each bench piece, watch the bench close-up over it: seated, or on the ice?

Then write {out_file}: a JSON list with at least one entry per window and per bench piece, each with "item": the window's number or the piece's B number. Every fix you describe must be an entry there: a fix that is only in your reply is lost.
- `{{"item": "1", "period": "{period}", "kind": "on" | "off", "player": N, "start": s, "end": s, "why": "one line"}}`: "on" = that player was on the ice over [start, end] although the solver missed him; "off" = he was not on the ice then although the solver had him on. Make each span cover just the stretch that is wrong (from the real change to the solver's change), to a second. Only list fixes you are fairly sure of.
- `{{"item": "1", "period": "{period}", "ok": "what you saw"}}`: the solver is right (a slow change in a stoppage, a real 4 on 4).
- `{{"item": "1", "period": "{period}", "unsure": "what you saw"}}`: you can't settle it.
- `{{"item": "B1", "period": "{period}", "bench": "fix" | "on" | "unsure", "why": "what you saw"}}` for every bench piece: "fix" = he was seated, and your on/off entries for it carry the same item; "on" = he really was on the ice.
- `{{"item": "1", "period": "{period}", "lead": "the question", "player": N, "start": s, "end": s}}`: something you noticed but couldn't settle (a piece with the wrong label, a player missing elsewhere): the next round's brief makes it a window.
- `{{"item": "1", "period": "{period}", "pk": "start-end", "even": "what you saw"}}`: a listed penalty kill that was played 5 on 5 (one of theirs in their box at the same time: count both teams); write no spans for it.
Your final reply: one line per window and one per bench piece: its item, who was on, and what you wrote for it.
