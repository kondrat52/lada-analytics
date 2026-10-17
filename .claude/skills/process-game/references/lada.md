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

It matches every `roster.json` player to LADA's roster by number and surname and prints same / NEW / DIFFERS /
WRONG / no match. With `--write` it adds the NEW ids and LADA's players whose numbers `roster.json` lacks (surname =
the last word of LADA's name, goalies by position, spares by Sub status), never changing what's there: fix WRONG and
DIFFERS by hand. A sub who isn't on LADA's roster gets no id. A "no match" can be a player LADA lists under
another number: put him under his jersey number with `"lada_numbers": {"<jersey>": <LADA's number>}` (Y's #87
Beregovoy is LADA's #67). A team's first game: if `roster.json` has no players, ask the user to run this first.

A player can wear different numbers on the two jerseys: Beregovoy is BEREGOVOY 87 on Y's light blue and 67 on the
white. `unknown` finds it (138 reads of 67 with his nameplate). He is in `roster.json` under both numbers with the
same LADA id, and the number he didn't wear goes on that game's absent list. The trends page then shows two rows
for him; merging them needs a per-game alias that the pipeline doesn't have yet.

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
`sheet` run before `periods.json` exists leaves `video_t` empty, and `goals` then prints every goal at its
period's start: run `sheet` again once the periods are right.

## `roster.json`

```
team, team_short, team_name      display name, short code, the official name in the LADA app
lada_team_id, site_url           LADA's team id; the site's URL
jersey                           the usual jersey ("light blue")
goalies, skaters, subs           number -> surname as on the back; subs are tagged "sub" on the site and listed
                                 apart in the feed
lada_player_ids                  number -> LADA player id
lada_numbers                     jersey number -> LADA's number, where they differ
```

A surname two players share (a father and son) counts as a name read for neither; only their numbers tell them
apart. New players go in before prepare (then prepare again); which part they go in changes only the site. Players
who didn't play a game are marked with `run_game.py absent`, never by editing this file.

`opponents.json` maps the opponent code to the full name. `lada_games.json` is the API cache above; commit it
with the game.

## A new team

1. `teams/<slug>/roster.json` copied from another team's with empty `skaters`, `subs`, `goalies` and
   `lada_player_ids`, the names, `lada_team_id` and `site_url` changed; `opponents.json` as `{}`.
2. The user runs `lada_ids.py --write <slug>` to fill the players in.
3. `build_site.py` gives it a site and an empty feed; publish rebuilds every team so the root page and the team
   menus list it.
4. Before its first game, check its jersey colour on a frame against `rink.JERSEYS`.
5. The LADA app shows the team's sheets once its feed URL (`<site_url>api`) is in the app's `shiftSheetFeeds`.
