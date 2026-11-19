# LADA, SportNinja and the roster files

## LADA's public API (`https://api.ladaseattle.com/api/v1`)

| Call | Gives |
|---|---|
| `team/<lada_team_id>` | the team's name |
| `team/<id>/game/next/30` | upcoming games: id, date, opponent, `playHome`, `rinkName`, planned `lines` (LADA player ids) |
| `team/<id>/game/last` | only the single most recent game: id, date, score, `boxscoreLink` (no `last/5`) |
| `game/<game id>` | one game: `playHome`, `rinkId`, score, `lines`, `boxscoreLink` |
| `game/<game id>/opponentGames` | the games against that opponent, with ids |
| `team/<id>/Player` | the roster, but only signed in (`lada_ids.py`) |
| `Team/<id>/Schedule/<season>`, `Season/<id>` | a whole season's schedule; needs a season id, not yet found |

Because "last" shows one game, a game published a week late would have no way to find its id. So fetch and publish
keep `teams/<slug>/lada_games.json`, every game the API has shown for the team, and publish takes `lada_game_id`
from it by date. `run_game.py schedule --team <slug>` prints that view: date, home/away, rink, id, whether a
game page exists, and the planned lines translated to jersey numbers, with any LADA id that `roster.json`
doesn't know (a player worth asking about; the lines are a plan, not attendance, and never say whose an id is).
When neither has the game (a game older than the team's last one, before the cache existed), publish probes
`game/<id>` around the ids of the other teams' games near that date: LADA hands ids out in schedule order, so
Beerteam's Sep 13 game (32949) sat four ids past Blue Wings' Sep 13 game (32945). If that fails too, look in
`opponentGames` of any game against that opponent and put the id in `game.json` as `"lada_game_id"`, then
`$PY pipeline/build_site.py`.

`lada_game_id` is what the LADA app uses to link a game to its analytics page; `opponent_name` in `game.json` (or the
team's `opponents.json`) is the name shown. LADA's exact spelling of an opponent is what finds its logo in the
app; a different spelling shows initials. The user's spelling wins for the code and name on the site.

## Player ids: `lada_ids.py`

Only the user can run it: it signs in to LADA as them (password typed hidden, never stored). Give them the exact
line, with a `cd` to the repo:

```sh
cd ~/lada-analytics && ~/.venvs/hockey/Scripts/python.exe pipeline/lada_ids.py --write <slug>
```

On the Windows PC the user's terminal is Windows PowerShell 5.1, which rejects `&&`; give them this form there:

```powershell
cd ~\lada-analytics; ~\.venvs\hockey\Scripts\python.exe pipeline\lada_ids.py --write <slug>
```

Not through the session's `!` prefix: that runs bash with no stdin, so the email prompt dies with EOFError (and the
PowerShell form above loses its backslashes there). Ask for it in the user's own PowerShell window. A sub from
another LADA team comes back "no match" (Akulov #37, Nov 15) and keeps no id; `--write` also adds every LADA roster
player missing from `roster.json`, so mark the new numbers absent in the next game unless they played.

It matches every `roster.json` player to LADA's roster by number and surname and prints same / NEW / DIFFERS /
WRONG / no match. With `--write` it adds the NEW ids and LADA's players whose numbers `roster.json` lacks (surname =
the last word of LADA's name, goalies by position, spares by Sub status), never changing what's there: fix WRONG and
DIFFERS by hand. A sub who isn't on LADA's roster gets no id. A "no match" can be a player LADA lists under
another number: put him under his jersey number with `"lada_numbers": {"<jersey>": <LADA's number>}` (Y's #87
Beregovoy is LADA's #67). A team's first game: if `roster.json` has no players, ask the user to run this first.

A player can wear different numbers on the two jerseys: Beregovoy is BEREGOVOY 87 on Y's light blue and 67 on the
white. `unknown` finds it (138 reads of 67 with his nameplate). He is in `roster.json` under both numbers with the
same LADA id, and the number he didn't wear goes on that game's absent list. `"aliases": {"87": 67}` makes 67 his
primary number: the game pages keep the number he wore, and the season table, trends page and feed totals list him
once, under 67.

Flounders own two jerseys: white with light-blue trim on Oct 4 (rinks.md) and black with light-blue and cream
stripes against Y on Oct 19, where nothing of theirs passed the white test.

## SportNinja game sheets

LADA's game record has `boxscoreLink`; its last path segment is the SportNinja game id, and SportNinja's API is
public: `https://metal-api.sportninja.net/v1/games/<id>` has both teams, the score, the periods with shots per
side, every goal (`goals`: period, clock, the shot's player id, assists), every penalty (`offenses`: player,
type, severity, minutes) and both rosters with `player_number` and `is_playing` (`/rosters` alone gives just
those). `run_game.py sheet $W` turns that into the printed sheet and `W/sheet.json`: `us` (home or visiting),
`score`, `shots` per period as `[ours, theirs]`, `goals` with `scorer` and `assists` as jersey numbers,
`penalties`, `played`, the roster numbers the sheet doesn't mark as playing, and the SportNinja and LADA ids (so
`--lada` or `--sn` is needed once at most). Before fetch the folder's name gives the team. The goals' and penalties'
video seconds come from the board's clock (`goals`, `pk`, the briefs). The user may also hand you the scoresheet PDF
from the SportNinja app; its file name is the SportNinja id ("Game #aioe8TXnLIrFmOVD scoresheet.pdf" → `sheet --sn
aioe8TXnLIrFmOVD`), so the PDF itself needn't be read. `is_playing` is the scorekeeper's and can be wrong (Y's Shakhov
#78 was marked not playing with SHAKHOV 78 on his back all game; Potepalov #15 was marked playing and never
seen; on Sep 21 Mischenko #72 was marked not playing and played from the 2nd period), so the video decides.
Check the sheet's goalie too: on TK's Oct 17 game a sub goalie, Dmitriyev #4, was marked playing and Fisenko #58 not,
while #4 is also skater Sokolov's number on our roster. Mark both #4 (Sokolov didn't play) and #58 absent, leave the
sub goalie out of `roster.json`, and tell the reviewers with `--note` that the #4 in goalie pads is our goalie. An
opponent's number can also pass our jersey test: Roadrunners' #4 ORR wears grey-white with light-blue stripes, and
his crops were most of the 88 reads of "4".
A goalie can come as a skater: on Y's Nov 9 game TK's goalie Fisenko #58 (DF's spare goalie too) played forward for
Y and scored three of our four goals; he went under `subs` with his LADA id from TK's `roster.json`. Bronnikov #74,
the same night, has two LADA ids in our rosters (BW's `subs` 20353, TK's `skaters` 20411); Y took TK's.

A game LADA's schedule view doesn't show (older than the cache, or skipped in mid-season, as Doofers' Sep 27 and
Oct 4 were): publish probes ids itself, but `sheet` doesn't; it stops and asks for `--sn` or `--lada`. The ids have
mostly sat between or right after the team's cached ones (Beerteam's Oct 4 was 32973 between 32972 and 32974; LADA
R's and Y's Oct 5 right after their Sep 28 games), so try `game/<id>` there first, then next to the other teams'
games that day (Doofers' Sep 13, 32947, between Blue Wings' 32945/32946 and Beerteam's 32949).
`game/<any game's id against the same opponent>/opponentGames` lists every game against them with its id, date,
score and `boxscoreLink`. Once you have the id, `sheet $W --lada <id>` adds the game to `lada_games.json` (dated from
the record's `dayTime`) and publish finds it by date.

## `roster.json`

```
team, team_short, team_name      display name, short code, the official name in the LADA app
lada_team_id, site_url           LADA's team id; the site's URL
jersey                           the usual jersey ("light blue")
goalies, skaters, subs           number -> surname as on the back; subs are tagged "sub" on the site and listed
                                 apart in the feed
lada_player_ids                  number -> LADA player id
lada_numbers                     jersey number -> LADA's number, where they differ
aliases                          a player's second number -> his primary one, where he wears two (totals go
                                 under the primary number)
```

A surname two players share (a father and son) counts as a name read for neither; only their numbers tell them
apart; `absent --suggest` leaves out name reads that are pieces of a shared surname (on Doofers' Nov 15 the pieces of
TISLENOK had made Belousenko look present) and, where the reads and the sheet disagree, lists what else was read on
the same crops and tracks. New players go in before prepare (then prepare again); which part they go in changes
only the site. Players who didn't play a game are marked with `run_game.py absent`, never by editing this file.

A sub can wear a roster player's number: on Doofers' Oct 18 game Vasyliev (Turbo Kings) wore #31, Sourov's, with
VASYLIEV on the nameplate and the game sheet naming him. Solve him as that number (mark nobody absent for it; tell
the reviewers with `review --note`), and after publish add `"guests": {"31": "Vasyliev"}` to the game's
`game.json` (publish keeps it) and rebuild with `pipeline/build_site.py`. The game page and game file show #31
Vasyliev, tagged sub; the season table, trends and feed give him his own row, off Sourov's totals. The sheet can
also list a goalie under LADA's number with a digit added (#290 for Wheeler, roster #0 with LADA number 29), which
`absent --suggest` then proposes as absent: keep him.

`opponents.json` maps the opponent code to the full name. `lada_games.json` is the API cache above; commit it
with the game.

## A game between two LADA teams

"2026/09/28 LADA R vs LADA Y" was both teams' game, and the user wanted it on both sites. Neither team's schedule
view had it; probing found R's 32965 and Y's 32967, two ids apart, with one SportNinja sheet between them (`sheet
--lada` for each, which also adds the game to that team's `lada_games.json`). Each team goes into the other's
`opponents.json` (`R` = "LADA R", `Y` = "LADA Y", LADA's names). Detection doesn't depend on the jersey, so one fetch
serves both:

1. Fetch for the light-blue team (the default jersey) and carry it through as usual.
2. Make the other folder by hand: hard links (`ln`) to `video.webm`, `audio.m4a`, `frame600.png`, `video_info.json`,
   `url.txt`, `scoreboard.npy` and `sb.jpg`; copies of `full/dets.csv`, `full/boards_poly.npy`, `full/ov/` and
   `full/log.txt`; and `full/rink.json` with its team, rink, jersey and bench. Without `log.txt` the OCR workers
   crash at once and `jersey` still reports "done" with no reads (check that `full/ocr_*.csv` aren't empty). Then
   `run_game.py jersey $W2 "white vs light blue"` cuts its crops and OCRs them: 22 minutes of decoding for a
   66-minute video, so start it the moment fetch is done.
3. Shared: the periods (each team's own `net`, so swapped), the scoreboard, the shots (pairs reversed, `us`
   flipped), the goals and their clips (cut once, copied into the other site's `games/<id>/clips/`; `for`/`against`
   swapped, `scorer` and `assists` only on the team's own goals). Each team's `pk` and penalty clips are its own.

The jerseys are one LADA design in two colours, and each passes part of the other's test. R's white with blue numbers
passed Y's light-blue crop test (Y's `unknown` listed #84, #66, #36, #10, #64 with R's nameplates; tracking was fine).
Y's light blue with white numbers and trim passed the plain white test on 9% of torsos and made 174 review sheets for
R; `white vs light blue` brought that to 114. Both `--opp` texts said any jersey of the other colour is an opponent
whatever its number: both teams have a #70 and a #12, and #11 Belousenko is on both rosters. R's sheet also had
Shikhanov #70 and Shachak #92 not playing, while their nameplates were read all game.

## A new team

1. `teams/<slug>/roster.json` copied from another team's with empty `skaters`, `subs`, `goalies` and
   `lada_player_ids`, the names, `lada_team_id` and `site_url` changed; `opponents.json` as `{}`.
2. The user runs `lada_ids.py --write <slug>` to fill the players in.
3. `build_site.py` gives it a site and an empty feed; publish rebuilds every team so the root page and the team
   menus list it.
4. Before its first game, check its jersey colour on a frame against `rink.JERSEYS`.
5. The LADA app shows the team's games once its feed URL (`<site_url>api`) is in the app's `shiftSheetFeeds`.
