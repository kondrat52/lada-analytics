"""Team roster shared by the pipeline. Each team has a folder teams/<slug>/ (roster.json, opponents.json, games/);
the TEAM environment variable picks one (tk unless set). run_game.py sets it from the work folder's rink.json.

ROSTER_ABSENT (comma-separated jersey numbers) drops players from SKATERS for one game: a roster number that
didn't play soaks up partial reads of other numbers (a "3" read off 43, 53 and 35 gave #3 ice time she never
had), so the solve must not know it. run_game.py sets it from the work folder's rink.json ("absent", see
`run_game.py absent`); the site builders never see it, since the published roster is the whole team."""
import json, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def teams():
    """Slugs of every team with a roster.json under teams/."""
    return sorted(t for t in os.listdir(f"{REPO}/teams") if os.path.exists(f"{REPO}/teams/{t}/roster.json"))


def site_of(slug):
    """A team's display name and its site folder, docs/<slug>/."""
    return json.load(open(f"{REPO}/teams/{slug}/roster.json"))["team"], f"{REPO}/docs/{slug}"


SLUG = os.environ.get("TEAM") or "tk"
if SLUG not in teams():
    raise SystemExit(f"unknown team {SLUG!r}; known: {', '.join(teams())}")
TEAM_DIR = f"{REPO}/teams/{SLUG}"
GAMES_DIR = f"{TEAM_DIR}/games"
_r = json.load(open(f"{TEAM_DIR}/roster.json"))
TEAM = _r["team"]                                           # short display name on the site
TEAM_NAME = _r.get("team_name", TEAM)                       # official name in the LADA app
TEAM_SHORT = _r.get("team_short", TEAM)
LADA_TEAM_ID = _r.get("lada_team_id")
SITE_URL = _r.get("site_url", "")
SITE_DIR = site_of(SLUG)[1]                                  # the team's pages and api/ under docs/
ABSENT = {int(x) for x in os.environ.get("ROSTER_ABSENT", "").replace(" ", "").split(",") if x}  # out this game
MEMBERS = {int(k): v for k, v in _r["skaters"].items() if int(k) not in ABSENT}   # number -> surname: the team's own skaters
SUBS = {int(k): v for k, v in _r.get("subs", {}).items() if int(k) not in ABSENT}  # skaters who have subbed for us, not on the team
SKATERS = {**MEMBERS, **SUBS}                               # everyone the pipeline looks for this game
ALL_SKATERS = {int(k): v for part in ("skaters", "subs") for k, v in _r.get(part, {}).items()}  # the whole roster
GOALIES = [int(k) for k in _r.get("goalies", {}) if int(k) not in ABSENT]   # the first one is in goal this game
GOALIE_NAMES = {int(k): v for k, v in _r.get("goalies", {}).items()}
LADA_IDS = {int(k): v for k, v in _r.get("lada_player_ids", {}).items()}  # number -> LADA player id (team roster)
ALIASES = {int(k): v for k, v in _r.get("aliases", {}).items()}  # a player's second number -> his primary one: the
# game pages keep the number he wore, totals across games (season, trends) go under the primary number

_GUESTS = {}   # guest key -> (number worn, surname)


def guest_key(num, game):
    """A skater's key in `game`: his number, or for a guest a key of his own, 1000·k + the number. A guest is a sub
    wearing a roster player's number that game (game.json "guests": {"31": "Vasyliev"}); his own key keeps his time
    off the roster player's totals. Game pages and game files keep the number worn."""
    name = (game.get("guests") or {}).get(str(int(num)))
    if not name:
        return int(num)
    for k, v in _GUESTS.items():
        if v == (int(num), name):
            return k
    k = 1000 * (len(_GUESTS) + 1) + int(num)
    _GUESTS[k] = (int(num), name)
    return k


number_of = lambda key: _GUESTS[key][0] if key in _GUESTS else key                # the jersey number to show
name_of = lambda key: _GUESTS[key][1] if key in _GUESTS else SKATERS.get(key, "")
is_sub = lambda key: key in _GUESTS or key in SUBS

_opp = f"{TEAM_DIR}/opponents.json"
OPPONENTS = json.load(open(_opp)) if os.path.exists(_opp) else {}   # code -> full name


def opponent_name(game):
    """Full opponent name for a game: game.json's opponent_name, else opponents.json, else the code."""
    return game.get("opponent_name") or OPPONENTS.get(game["opponent"]) or game["opponent"]


def final_score(game, slug=None):
    """A game's score, from the first source that has it: the SportNinja game sheet (game.json's sheet_score, set by
    publish and refreshed by `run_game.py scores`, since scorekeepers correct sheets after the game), LADA's result
    (teamGoals/opponentGoals in teams/<slug>/lada_games.json, by the game's lada_game_id), else the goals on video.
    Returns dict(gf, ga, result "W"/"L"/"T", source "sheet"/"lada"/"video", official: not from the video)."""
    p = f"{REPO}/teams/{slug or SLUG}/lada_games.json"
    if p not in _LADA_GAMES:
        _LADA_GAMES[p] = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    lada = _LADA_GAMES[p].get(str(game.get("lada_game_id")), {})
    sheet = game.get("sheet_score") or {}
    if sheet.get("for") is not None and sheet.get("against") is not None:
        gf, ga, source = int(sheet["for"]), int(sheet["against"]), "sheet"
    elif lada.get("teamGoals") is not None and lada.get("opponentGoals") is not None:
        gf, ga, source = int(lada["teamGoals"]), int(lada["opponentGoals"]), "lada"
    else:
        goals = [h for h in game.get("highlights", []) if h["type"] == "goal"]
        gf, ga, source = sum(h["team"] == "for" for h in goals), sum(h["team"] == "against" for h in goals), "video"
    return dict(gf=gf, ga=ga, result="W" if gf > ga else "L" if gf < ga else "T", source=source,
                official=source != "video")


_LADA_GAMES = {}   # lada_games.json path -> its contents
