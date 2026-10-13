"""Team roster shared by the pipeline. Each team has a folder teams/<slug>/ (roster.json, opponents.json, games/);
the TEAM environment variable picks one (tk unless set). run_game.py sets it from the work folder's rink.json."""
import json, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def teams():
    """Slugs of every team with a roster.json under teams/."""
    return sorted(t for t in os.listdir(f"{REPO}/teams") if os.path.exists(f"{REPO}/teams/{t}/roster.json"))


def site_of(slug):
    """A team's display name and its site folder under docs/ (roster.json's site_dir, else docs/<slug>)."""
    r = json.load(open(f"{REPO}/teams/{slug}/roster.json"))
    return r["team"], os.path.normpath(f"{REPO}/docs/{r.get('site_dir', slug)}")


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
MEMBERS = {int(k): v for k, v in _r["skaters"].items()}   # number -> surname: the team's own skaters
SUBS = {int(k): v for k, v in _r.get("subs", {}).items()}  # skaters who have subbed for us, not on the team
SKATERS = {**MEMBERS, **SUBS}                               # everyone the pipeline looks for
GOALIES = [int(k) for k in _r.get("goalies", {})]
GOALIE_NAMES = {int(k): v for k, v in _r.get("goalies", {}).items()}
LADA_IDS = {int(k): v for k, v in _r.get("lada_player_ids", {}).items()}  # number -> LADA player id (team roster)

_opp = f"{TEAM_DIR}/opponents.json"
OPPONENTS = json.load(open(_opp)) if os.path.exists(_opp) else {}   # code -> full name


def opponent_name(game):
    """Full opponent name for a game: game.json's opponent_name, else opponents.json, else the code."""
    return game.get("opponent_name") or OPPONENTS.get(game["opponent"]) or game["opponent"]
