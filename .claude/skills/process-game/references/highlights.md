# Goals, penalties and clips

What the goal and penalty checkers do and where their rules live, what `highlights` prints and what to do about it,
the penalty-kill cases step 3 meets, `highlights.json`, and the clips.

## The goal and penalty checkers

`run_game.py goals $W --brief` writes one brief per period with goals on the sheet (`W/scratch/goals/prompt_pN.md`,
answer `pN/goals.json`) and one for all the sheet's penalties, ours and theirs (`prompt_pens.md`, answer
`pens/pens.json`), from `pipeline/goal_prompt.md` and `pen_prompt.md`. They need only fetch's output and
`periods.json` with its nets, so they run beside prepare and the review. The templates carry the rules the session
used to paste by hand: our net in that period, which side of the board we are, where to search from the second the
clock showed the sheet's time (and the other period, and a lost digit: LADA R's Sep 21 had a goal in the wrong
period, Beerteam's Sep 27 17:17 for 7:17), the board's late postings, the center faceoff that follows every goal,
the operator running the clock in a stoppage, our goalie pulled, the box trip that decides whose penalty it was, and
the fixed JSON answer. A period without a board clock read gets the earliest second the clock allows and a search on
to the period's end. The briefs name the players the sheet marks playing who aren't in `roster.json` yet, and until
`review --opp` the opponents' look comes from the jersey test's name ("white vs royal blue": royal blue jerseys). A
new rule for the checkers goes into the template.

One rule times every goal: **`t` is the second the puck crosses the line, in a scramble the last jam; `shot` is
where the scoring sequence starts, in a scramble the shot or drive that began it.** Taking the first jam as the goal
left two replays ending before the puck went in (LADA R's Nov 9 goals 4 and 5), and taking the pile as the shot left
a replay that opened after the drive (LADA R's Oct 26 opener, 5 s after Shachak's drive) or on the wrong player
(Beerteam's Oct 18 3rd, the last poke instead of Kleiman's jam).

`goals $W` alone prints the sheet's goals at the seconds the clock implies and, once prepare has made tracks, the
center-ice faceoffs and long stoppages that aren't period starts.

## What `highlights` prints, and what to do

`highlights $W` builds the entries from the answers and the sheet and prints a `!` line for whatever doesn't add up;
`--write` writes `highlights.json`, replaces `pk`'s kills with the penalty checker's, and logs an `off` span for a
player boxed without a kill. It keeps hand edits to an existing file: `scratch/goals/generated.json` records what it
wrote, matched by the sheet's goal or penalty number, so a goal whose time moves stays one entry, and an entry deleted
by hand stays deleted (take its record out of `generated.json` to have it back).

- **Our scorer and assists are always the sheet's.** A checker who saw someone else put it in (`scorer_seen`) goes to
  the user: ask them to check with the team, and change the credit only on their word. The sheet has been wrong
  (Doofers' Sep 27 credited Babkin, who wasn't on the ice; Y's Oct 19 Yafunyaev, who sat on the bench while Lisitsyn
  scored), and so has a frame check (Beerteam's Sep 27 read Kleiman for Shikhanov, both on the ice). The lineup check
  then keeps listing the credited player as off the ice, which is expected; the clip still follows the shooter, since
  the track at `shot` is followed whatever its label.
- **An assist the team names that the sheet lacks** (TK's Oct 25: Prozhogin #61 on Belousenko's goal) goes into that
  goal's `assists` in `highlights.json` by hand, which `--write` keeps, with a note that the sheet lacks it; then
  `clips --only` that goal, since a clip frames only the credited players.
- **Theirs** carry no `scorer` or `assists` (those keys hold our numbers); the note names the sheet's scorer.
- **A goal the board counts and the sheet doesn't** isn't entered: the sheet's score stands, the notes describe it,
  and the user is asked (Blue Wings' Nov 7: the board 6-5, the sheet 5-5, corrected days later and brought in by
  `scores`). Adding it then means one hand-written `highlights.json` entry, one clip and a republish.
- **A goal not on video** (the video starts after it, as LADA R's Nov 9 did with the board at 17:23 and 1-0; or the
  recording skips, as LADA R's Sep 14 lost two minutes of the 3rd) stays out; the notes say so, and the page's score
  is the sheet's.
- **An empty-net goal** and the checker's note on our goalie leaving: an `extra` span (`span $W extra ...`).
- The goal checker's `on_ice` goes into the lineup check: a skater it read on the ice whom the solver has off becomes
  a gap window (TK's Oct 25 showed #33 in #89's place on the page before this check existed).

## Penalties

`pk` proposes our kills from the sheet and the clock (SKILL step 3); in a period without a board clock read the
proposal is ROUGH (its start only the earliest it can be) and `pk --write` leaves it out unless `--rough`. The penalty
checker's `kill` decides at `highlights --write`: [start, end] replaces the proposal; null with a reason in `why`
means no kill and takes the proposal out; "unsure", or no `kill`, keeps the proposal, and `highlights` says so.
`pk --write` skips a penalty the checker has answered. The cases where the two part, and what the answer then holds:

- **A bench minor** (too many players) is served by a skater: `sat` names him, and he is the kill's player.
- **Two penalties of ours at once** are two overlapping kills: the solver expects 3 skaters then.
- **The sheet names the wrong player**: the box decides (Doofers' Sep 19: the sheet #31, the panel and the box #37).
- **A minor late in a period can wait for the next one** (Doofers' Sep 19: Sourov sat the first 2:00 of the 3rd, our
  box empty to the end of the 2nd), so the kill is in the 3rd only.
- **Never served**: no panel, an empty box, the player kept playing (LADA R's Sep 21, two of them). A minor at the clock
  of a power-play goal against may never be served (BW's Oct 11: #54's high-sticking never lit the panel); `pk`
  gives such a minor no kill and the brief asks.
- **Coincident minors** (one of ours, one of theirs at once): `pk` gives none. At 4 on 4 it is a kill. At 5 on 5 with
  substitutes (LADA Y's Nov 9: `skaters` missed a player and a kill cost the solver a skater for 4 minutes) the
  checker answers no kill, and `highlights --write` puts our boxed player `off` from box_in to box_out. Count both
  teams on a faceoff frame, never `skaters` alone; a gap checker who finds a listed kill played 5 on 5 reports it,
  and `gaps --apply` prints it with `!!` and the two steps: the kill out of `periods.json` by hand, and the `span ...
  off` line it gives for our boxed player.
- **A major or misconduct with a minor** can have a teammate serve the minor (LADA R's Sep 21: #10 sat #81's, and #81
  never came back, an `off` to the end; Doofers' Oct 18: Panova sat #61's while the panel said 61). A misconduct alone
  sits the player without a kill.
- **A penalty shot against us** replaces the minor, and SportNinja still lists the minor (BW's Oct 18). The panel posts
  while the clock is stopped and goes dark before the faceoff, the clock stays frozen about a minute, and all our
  skaters stand at the bench while their shooter skates in. No kill: a `ps` span (`span $W ps ...`), the infraction
  clipped as the penalty and the shot as a `"moment"` titled "Penalty shot" with the net's x as its focus. A penalty
  shot for us leaves our shooter on the ice, which `ps` doesn't model yet.

## `highlights.json`

```json
[{"type": "goal", "team": "for", "t": 3828, "scorer": 54, "assists": [36], "clip": "clips/goal-3.mp4",
  "poster": "clips/goal-3.jpg", "note": "3rd period, clock 9:06: in alone on the goalie, 4-2",
  "shot": [3826.5, 2900, 640], "pass": null, "on_ice": [54, 36, 12]},
 {"type": "penalty", "player": 4, "t": 3580, "clip": "clips/penalty-4.mp4", "poster": "clips/penalty-4.jpg",
  "note": "1st period, clock 3:40: 3 minutes, ended by their power-play goal at 0:38"},
 {"type": "moment", "title": "3 on 0, no goal", "t": 1234, "clip": "clips/moment-1.mp4", "poster": "clips/moment-1.jpg",
  "note": "..."}]
```

`t` is seconds of video at the goal or the infraction. `shot`, `pass` ([t, x, y], skates in source pixels) and
`on_ice` are working keys for the clips and the lineup check; publish leaves them out of `game.json`. A `"moment"` (a
play worth a clip that is neither goal nor penalty, as the user asked for TK's 3-on-0 on Oct 17) is written by hand:
the page lists who was on the ice for it, and it doesn't count toward goals. A user's "around 3:00 in the 1st" is
usually the clock (3:11 left, video 898), not 3:00 into the video: try both.

## Clips

`clips $W <game-id>` cuts every entry of `highlights.json` with the arguments the sessions used to type: each clip
from 12 s before `t` (for a goal, 8 s before its pass or shot if that is earlier) to 10 s after, the poster at `t`. A
goal closes in on the net it went into and ends with a zoomed half-speed replay, framing our credited scorer and
assists and following the checker's `shot` and `pass`; a penalty follows the player who took it; a moment follows the
main group. The replay starts 1.5 s before
`shot` (4 s before `t` without one), or 2 s before `pass`. Every cut and `--dry-run` first checks the camera's path
and saves the warnings in `$W/clips_check.json`: a shot after the goal or far before it, the replay window, the
scorer's track missing or someone else's at the shot, the shooter, net or passer out of the frame, and the camera on
an all-but-empty net while the play is elsewhere (the three complaints about rushes). The cut writes a contact sheet
per clip (`W/scratch/clips/<name>.jpg`) and the checker's brief; `clipsheet <mp4> <out.jpg> --from <s> --to <s>
--step 0.25` tiles any stretch closer. Clips land in the team site's `games/<id>/clips/`, about 5 MB each, with the
recording's sound where it has any.

A clip's own arguments go in `$W/clip_args.json`, keyed by clip name, and win over the generated ones: `t0`, `t1`,
`focus` (an x, `#N`, or `"-"` for none), `shot` and `pass` (null leaves one out), `replay_from` (seconds before `t`),
`tracks`. For example `{"goal-3": {"shot": null}, "moment-1": {"focus": "3260"}}`.

| Situation | What to give |
|---|---|
| A scramble | `t` the last jam, `shot` the shot or drive that began it (the rule above); `replay_from` if the replay must start earlier still (TK's Oct 25: a scramble 7 s after the shot) |
| The scorer's track carries another number | nothing: the track at `shot` is followed whatever its label (TK's Nov 1: Belousenko's track labeled 89) |
| No track near the shot (an untracked scorer at the post; the dry run warns `scorer-track`) | `"shot": null`: the replay then zooms on the net (Beerteam's Oct 18: the nearest track 400 px away sent the camera to the other end) |
| An assist, or a goal against off a rush | the checker's `pass`: without it the tight crop keeps a passer only within ~1150 px and the replay frames only the scorer (LADA Y's Nov 2) |
| A long rush to an empty net | the checker's `shot`: before it the net joins the scorer only within 1300 px (`LEAD_W`), which TK's Oct 25 and LADA R's Nov 2 empty-netters needed |
| The camera follows the wrong body (a track that is another player's in the window; a big player near the camera) | `"tracks": "TID;TID"` (scorer's first, then each assist's, from `frames --tracks` or `follow`); a track carrying another number for longer in the window is already left out |
| A solo rush the length of the ice | a subagent traces his skates every 0.5 s by eye into a t, x, y CSV outside `scratch/` (archive keeps it there), then `"tracks": "<csv>"` (Beerteam's Nov 7: Lee from his own zone) |
| A goal after the period's tracks end (a period cut short) | track the stretch into a folder of its own, `run_period.py $W/full $W/p3tail <t0> <t1> <our net x>`, then `"tracks": "<W>/p3tail/tracks_v1.csv:<tid>"` with the folder's full path, since `clip_args.json` expands no `$W` (LADA R's Nov 2) |
| A penalty | the default `#player`; a focus x can lock onto someone right by the camera (at Kirkland a referee in the near corner) |
| A moment or a penalty shot | `"focus"`: the net's x (`rink.py` nets) or a corner (about 500 left, 3300 right); a focus x only weights where the players are, so it can't bring an empty net into the frame |
