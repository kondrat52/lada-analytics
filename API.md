# Shift sheet JSON feed

Read-only JSON, published with the site on GitHub Pages and rebuilt on every push. No login and no keys. Pages sends
`Access-Control-Allow-Origin: *` and caches for up to 10 minutes.

Base URL, one feed per team (each `index.json` says whose it is in `team`, with its `lada_team_id`):

| Team | LADA team id | Base URL |
|---|---|---|
| LADA Turbo Kings | 24 | `https://kondrat52.github.io/lada-analytics/tk/api/` |
| LADA Blue Wings | 10 | `https://kondrat52.github.io/lada-analytics/bw/api/` |
| LADA Beerteam | 5 | `https://kondrat52.github.io/lada-analytics/bt/api/` |
| LADA Doofers | 17 | `https://kondrat52.github.io/lada-analytics/df/api/` |
| LADA Y | 20 | `https://kondrat52.github.io/lada-analytics/y/api/` |
| LADA R | 2 | `https://kondrat52.github.io/lada-analytics/r/api/` |

A team's feed is there from the day it's added, before its first filmed game: `games` and `players` are then empty
and `updated` is `null`.

The feeds used to be at `https://kondrat52.github.io/lada-tk-analytics/api/` (Turbo Kings) and `.../lada-tk-analytics/bw/api/`.
For LADA app versions that still read them, the repo `kondrat52/lada-tk-analytics` mirrors the new feeds there
(copied every hour, links inside pointing to the new URLs) and sends the old pages to the new ones. It goes away
once those versions are gone; don't use the old URLs.

| File | What's in it |
|---|---|
| `index.json` | Team, list of games (newest first) with links to each game's JSON and page |
| `games/<id>.json` | One game: periods, per-player stats, every shift, highlights (clip URLs), stoppages, ice maps |
| `season.json` | Season totals per player |
| `roster.json` | Jersey numbers, surnames and LADA player ids |
| `trends.json` | Per game, newest first: the team's measures and each skater's, as on the trends page |

## Conventions

- **Times are seconds.** Shift and highlight times (`start`, `end`, `t`) are seconds into the game video
  (`video_url`), the same timestamps YouTube uses. `*_in_period` fields count from that period's start.
- **Ice time vs play time.** `toi` is ice time: real elapsed time on the ice from stepping on to stepping off,
  stoppages included (there is no game clock in the video). `play` is live play only, estimated from the video.
  It's an upper bound, since quick whistles can slip through.
- **Players** appear as `{number, name, lada_player_id}`. `name` is the surname as printed on the jersey.
  A substitute (a skater who isn't on the team and subbed in) also has `sub: true`.
  `lada_player_id` is the player's id on the LADA team roster (the feed's `lada_team_id`: LADA gives a player on
  two teams a different id on each), or `null` if not matched yet. Join on
  `lada_player_id` when it's there; jersey numbers can differ between the jersey and the LADA roster.
- **Games** have a date-slug `id` (`2026-09-27-vs-rr`). `lada_game_id` is the LADA API game id (publishing fills
  it in from LADA when it can), or `null`. Match on the date when it's `null`: a team plays at most once a day.
- `schema` changes only when a field is removed or changes meaning. New fields can appear at any time, so ignore
  the ones you don't know.
- Missing numbers are `null` (e.g. `play` for a game without stoppage data, `shortest_shift` when every shift
  was cut off by the recording ending).

## `index.json`

```json
{
  "schema": 1,
  "team": {"name": "LADA Turbo Kings", "short_name": "Lada TK", "lada_team_id": 24},
  "site_url": "https://kondrat52.github.io/lada-analytics/tk/",
  "updated": "2026-09-27",
  "season_url": ".../api/season.json",
  "roster_url": ".../api/roster.json",
  "trends_url": ".../api/trends.json",
  "games": [{
    "id": "2026-09-27-vs-rr", "date": "2026-09-27", "title": "...", "subtitle": "Sun Sep 27, 2026 · 7:50 PM · Renton",
    "opponent": {"code": "RR", "name": null}, "lada_game_id": 32969,
    "goals_on_video": {"for": 1, "against": 2}, "shots": {"for": 40, "against": 16}, "highlights": 4,
    "page_url": ".../games/2026-09-27-vs-rr/", "json_url": ".../api/games/2026-09-27-vs-rr.json"
  }]
}
```

`time` and `rink` (e.g. `"7:50 PM"`, `"Renton"`) are also on each game file. `goals_on_video` counts the goals found in the recording. It isn't the official score: the recording can end
before the final horn (`video_ends_early` in the game file). `shots` is shots on goal as the arena scoreboard counted
them (`for` = us), or `null` for a game whose board wasn't read.

## `games/<id>.json`

| Field | Meaning |
|---|---|
| `periods[]` | `{label: "P1", start, end, length}` in video seconds |
| `penalty_kills[]` | `{period, start, end, player}`: our skater in the box; 4 skaters on the ice for the window |
| `shots` | Shots on goal from the arena scoreboard: `{for, against, periods[]}`, `periods[]` with `{label, for, against}`; `null` when not read. Read at the end of each period, so a shot counted late by the scorekeeper lands in the next one |
| `players[]` | Sorted by ice time: `shifts, toi, play, avg_shift, median_shift, longest_shift, shortest_shift`, `plus_minus` (goals for minus goals against while on the ice, from the goals on video, as in `trends.json`), and `periods[]` with `{label, shifts, toi, avg_shift}` |
| `shifts[]` | Every shift: `{number, period, start, end, duration, play, start_in_period}` |
| `highlights[]` | `{type: "goal" \| "penalty" \| "moment", team: "for" \| "against" (goals), title (moments), player (penalties), t, period, t_in_period, clip_url, poster_url, note, on_ice[]}`. Clips are 1280×720 H.264 MP4 without audio, about 5 MB. `on_ice` lists our skaters on the ice for a goal or a moment (a play worth a clip that isn't a goal or a penalty) |
| `stoppages[]` | `[start, end]` pairs: estimated stoppages (whistle to puck drop) |
| `ice` | Where our skaters were on the ice during their shifts: the team's map and each player's (below), or `null` for a game without maps |
| `video_url`, `page_url` | The full game on YouTube; the shift sheet page |

`shortest_shift` leaves out shifts cut off by the recording ending mid-play.

### Ice maps (`ice`)

The rink seen from above with our net at the bottom, so the team attacks up: a grid of `cols` x `rows` cells of
`cell_ft` feet (42 x 100 cells of 2 ft: 84 ft across, 200 ft from our end boards to theirs). Only games at a rink
whose camera has been calibrated have maps (Snoqualmie A and B so far); the others have `ice: null`.

```json
"ice": {
  "cell_ft": 2, "cols": 42, "rows": 100, "alphabet": "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
  "team": {"tracked": 12767.5, "zones": {"offence": 0.364, "neutral": 0.331, "defence": 0.305}, "grid": "000...0"},
  "players": [{"number": 13, "name": "Belousenko", "lada_player_id": 20412, "tracked": 1731.6,
               "zones": {"offence": 0.328, "neutral": 0.329, "defence": 0.343}, "grid": "..."}]
}
```

| Field | Meaning |
|---|---|
| `tracked` | Seconds of the player's shifts the map is made of (for the team, summed over the skaters): the time his tracked position carried his number. Most but not all of `toi` |
| `zones` | Share of `tracked` (0–1) in the offensive zone (past their blue line), the neutral zone and the defensive zone |
| `grid` | One character per cell, `rows` x `cols` of them: row 0 is at our end boards, each row runs from the left boards to the right (left as the team attacks up). A cell's value is `alphabet.indexOf(char) / (alphabet.length - 1)`: time there, smoothed over a few feet, as a share of the map's busiest cell (0 = none, 1 = the busiest). Each map has its own scale, so compare shapes, not shades, between players |

`players[]` is sorted by `tracked` and leaves out a skater with under 30 s tracked.

## `season.json`

`players[]` sorted by ice time per game: `{number, name, lada_player_id, games_played, shifts, toi, toi_per_game,
play, avg_shift, longest_shift, shortest_shift, plus_minus, games[]}`, `plus_minus` summing the game files' (goals on
video). `games[]` lists that player's games, newest first: `{id, date, opponent: {code, name}, toi, shifts, avg_shift,
play, plus_minus}`. A player who wears a second number (another jersey's)
has one entry, under his primary number, with the games he wore either; the game files keep the number he wore.
A sub who wore a roster player's number in one game (a "guest") has an entry of his own, with that number, `sub:
true` and his own name, so two entries can share a `number`.

## `roster.json`

`skaters[]` and `goalies[]`, each `{number, name, lada_player_id}`, and `subs[]`: skaters who have subbed for the
team without being on it. A player who also wears a second number is listed once, under his primary number, with
`other_numbers` (e.g. `[87]`). Edit the repo's `teams/<slug>/roster.json` to change them.

## `trends.json`

The numbers behind the trends page, one entry per game in `games[]`, newest first. Averages and "latest game vs
earlier" comparisons are left to the reader.

| Field | Meaning |
|---|---|
| `id`, `date`, `rink`, `opponent`, `lada_game_id`, `video_ends_early` | As in `index.json` and the game file |
| `goals_on_video`, `result` | Goals found in the recording, and `"W"`, `"L"` or `"T"` from them |
| `shots` | As in the game file: `{for, against, periods[]}`, or `null` when the board wasn't read |
| `zones` | `{offence, defence}`: share of live play (0–1) spent near their net and near ours; the rest is the middle of the ice. `null` when not measured |
| `skaters` | Skaters who dressed for us |
| `avg_shift` | The team's average shift (seconds) |
| `play_share` | Share of the periods' time that was live play (0–1), estimated like `play` |
| `penalties` | `{count, short_handed, goals_against}`: our penalties (one carried over an intermission counts once), seconds spent killing them, and goals against during the kills |
| `players[]` | Sorted by ice time: the player fields, `shifts, toi, avg_shift`, `toi_share` (share of the team's skater ice time; an equal split is `1 / skaters`), `avg_shift_p1` and `avg_shift_p3` (average shift in the first and third periods, `null` without a shift there) and `plus_minus` (goals for minus goals against while on the ice, from the goals on video). A second number a player wore is under his primary one, as in `season.json` |
