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
shift sheet exists, and the planned lines translated to jersey numbers, with any LADA id that `roster.json`
doesn't know (a player worth asking about; the lines are a plan, not attendance, and never say whose an id is).
When neither has the game (a game older than the team's last one, before the cache existed), publish probes
`game/<id>` around the ids of the other teams' games near that date: LADA hands ids out in schedule order, so
Beerteam's Sep 13 game (32949) sat four ids past Blue Wings' Sep 13 game (32945). If that fails too, look in
`opponentGames` of any game against that opponent and put the id in `game.json` as `"lada_game_id"`, then
`$PY pipeline/build_site.py`.

`lada_game_id` is what the LADA app uses to link a game to its shift sheet; `opponent_name` in `game.json` (or the
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

## SportNinja game sheets

LADA's game record has `boxscoreLink`; its last path segment is the SportNinja game id, and SportNinja's API is
public: `https://metal-api.sportninja.net/v1/games/<id>` has both teams, the score, the periods with shots per
side, every goal (`goals`: period, clock, the shot's player id, assists), every penalty (`offenses`: player,
type, severity, minutes) and both rosters with `player_number` and `is_playing` (`/rosters` alone gives just
those). `run_game.py sheet $W` turns that into the printed sheet and `W/sheet.json`: `us` (home or visiting),
`score`, `shots` per period as `[ours, theirs]`, `goals` with `scorer` and `assists` as jersey numbers and a
`video_t` estimate once `periods.json` exists, `penalties`, `played`, and the roster numbers the sheet doesn't
mark as playing. The user may also hand you the scoresheet PDF from the SportNinja app ("Game #...
scoresheet.pdf"), which says the same things. `is_playing` is the scorekeeper's and can be wrong (Y's Shakhov
#78 was marked not playing with SHAKHOV 78 on his back all game; Potepalov #15 was marked playing and never
seen; on Sep 21 Mischenko #72 was marked not playing and played from the 2nd period), so the video decides.
Check the sheet's goalie too: on TK's Oct 17 game a sub goalie, Dmitriyev #4, was marked playing and Fisenko #58 not,
while #4 is also skater Sokolov's number on our roster. Mark both #4 (Sokolov didn't play) and #58 absent, leave the
sub goalie out of `roster.json`, and tell the reviewers with `--note` that the #4 in goalie pads is our goalie. An
opponent's number can also pass our jersey test: Roadrunners' #4 ORR wears grey-white with light-blue stripes, and
his crops were most of the 88 reads of "4".
`sheet` run before `periods.json` exists leaves `video_t` empty, and `goals` then prints every goal at its
period's start: run `sheet` again once the periods are right.

A game LADA's schedule view doesn't show (older than the cache, like Doofers' Sep 19 game): call
`game/<any upcoming game's id against the same opponent>/opponentGames`. It lists every game against them with
its id, date, score and `boxscoreLink` (the SportNinja id, so `sheet --sn` works too). Add the game to
`lada_games.json` (`game/<id>` has the full record) and publish finds it by date. Store `date` as
`YYYY-MM-DDTHH:MM:SS` from the record's `dayTime`: its own `date` is "9/27/2026", which publish's lookup by date
misses; the record has no `rinkName` either. The schedule view can also skip games in mid-season: Doofers' Sep 27
and Oct 4 games never showed up in it, between games that did, and `opponentGames` had both with their sheets (so
did Beerteam's Sep 27 game, 32972, found through their Oct 25 game against the same Cascadiens). Beerteam's Oct 4 game
vs Jackalopes had no later game against them; it was 32973, the id between the team's cached 32972 (Sep 27) and 32974
(Oct 10), so probe the ids between a team's cached games first. LADA R's Oct 5 game vs Best Vibes was missing too
and was 32966, the id right after the team's cached 32965 (Sep 28); `sheet $W --lada 32966 --team r` then worked.
LADA Y's Oct 5 game vs BladeRunners was likewise 32968, right after Y's cached 32967 (Sep 28). With no upcoming game against
that opponent (Doofers' Sep 13 game vs Jurassic Puck, their real first), probe `game/<id>` next to the other
teams' games that day: 32947 sat between Blue Wings' 32945/32946 and Beerteam's 32949.

The scoresheet PDF's file name is the SportNinja id ("Game #aioe8TXnLIrFmOVD scoresheet.pdf" → `sheet --sn
aioe8TXnLIrFmOVD`), so the PDF itself needn't be read. Run before fetch, `sheet` also needs `--team <slug>`: the
work folder doesn't record the team yet, and it defaults to Turbo Kings.

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
apart. New players go in before prepare (then prepare again); which part they go in changes only the site. Players
who didn't play a game are marked with `run_game.py absent`, never by editing this file.

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
--lada` for each). Add it to both `lada_games.json` files and each team to the other's `opponents.json` (`R` = "LADA
R", `Y` = "LADA Y", LADA's names). Detection doesn't depend on the jersey, so one fetch serves both:

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
5. The LADA app shows the team's sheets once its feed URL (`<site_url>api`) is in the app's `shiftSheetFeeds`.
