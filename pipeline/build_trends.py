"""build_trends.py : trends.html, the team's trends across games, from its games/*/game.json + shifts.csv, and
api/trends.json, the same measures for apps (build_feed.trends_doc). build_site.py runs it. Time in offence and
defence come from game.json's `zones` (zones.py, filled in on publish; "basis" "px" marks a game measured on the
picture's thirds, drawn hollow), shots on goal from its `shots` (shots.py, read off the arena scoreboard), the
season positioning rinks and table from its `positions` (positioning.py), each value the average of a skater's games."""
import os, sys, json, glob
from html import escape
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roster import ALIASES, TEAM, SLUG, REPO, GAMES_DIR, SITE_DIR, teams, site_of, opponent_name, guest_key, number_of, name_of, is_sub
from roster import final_score
from build_feed import trends_doc, season_positions
from positioning import SEASON_GAMES

HERE = os.path.dirname(os.path.abspath(__file__))


def penalties(game):
    """Our penalties: penalty kills, with one carried over an intermission (same player, next period) counted once."""
    out = []
    for k in sorted(game.get("penalty_kills", []), key=lambda k: k["start"]):
        if out and out[-1]["player"] == k.get("player") and k["start"] - out[-1]["end"] < 200:
            out[-1]["end"] = k["end"]
        else:
            out.append(dict(player=k.get("player"), start=k["start"], end=k["end"]))
    return out


def game_rows(gd):
    game = json.load(open(f"{gd}/game.json"))
    A = pd.read_csv(f"{gd}/shifts.csv")
    A["player"] = [ALIASES.get(k, k) for k in (guest_key(p, game) for p in A.player)]   # a player's second number
    # trends with his primary one, a guest (a sub in a roster player's number) apart from that player
    periods = game["periods"]
    length = sum(p["end"] - p["start"] for p in periods)
    T = int(max(p["end"] for p in periods)) + 2
    live = np.zeros(T, bool)
    for p in periods:
        live[p["start"]:p["end"]] = True
    for a, b in game.get("stoppages", []):
        live[int(a):int(b)] = False
    goals = [h for h in game.get("highlights", []) if h["type"] == "goal"]
    vgf = sum(h["team"] == "for" for h in goals); vga = sum(h["team"] == "against" for h in goals)   # on video
    sc = final_score(game)   # the game sheet's final score, else LADA's, else the goals on video
    pks = game.get("penalty_kills", [])
    in_pk = lambda t: any(k["start"] <= t < k["end"] for k in pks)
    zones = game.get("zones") or {}
    shots = game.get("shots") or {}          # {"P1": [ours, theirs], ...} from the arena scoreboard
    sp = [shots[p["label"]] for p in periods if p["label"] in shots] or None
    team = dict(
        id=game["id"], date=game["date"], opp=opponent_name(game), opp_code=game["opponent"],
        rink=(game.get("eyebrow") or "").split("·")[-1].strip(), gf=sc["gf"], ga=sc["ga"], vgf=vgf, vga=vga,
        result=sc["result"], official=sc["official"], score_source=sc["source"], video_ends_early=bool(game.get("video_ends_early")),
        skaters=int(A.player.nunique()), avg_shift=float(A.dur.mean()), live_pct=float(live.sum() / length),
        penalties=len(penalties(game)), pk_ga=sum(h["team"] == "against" and in_pk(h["t"]) for h in goals),
        pk_min=float(sum(k["end"] - k["start"] for k in pks) / 60),
        offence=zones.get("offence"), defence=zones.get("defence"),
        zone_basis=(zones.get("basis") or "px") if zones else None,   # before Nov 24, 2026 only the picture's thirds
        sp=sp, sf=sum(x[0] for x in sp) if sp else None, sa=sum(x[1] for x in sp) if sp else None)
    players = []
    team_toi = A.dur.sum()
    pos = {}   # season key -> his role this game (positioning.py), from the number he wore
    for n, e in ((game.get("positions") or {}).get("players") or {}).items():
        k = guest_key(int(n), game)
        pos[ALIASES.get(k, k)] = e
    for num, s in A.groupby("player"):
        on = np.zeros(T, bool)
        for r in s.itertuples():
            on[int(r.t0):int(r.t1)] = True
        by = s.groupby("period").dur.mean()
        players.append(dict(
            role=(pos.get(int(num)) or {}).get("role"), role_share=(pos.get(int(num)) or {}).get("role_share"),
            game=game["id"], key=int(num), num=number_of(int(num)), name=name_of(int(num)), sub=is_sub(int(num)),
            shifts=int(len(s)), toi=float(s.dur.sum()), avg_shift=float(s.dur.mean()),
            toi_share=float(s.dur.sum() / team_toi), equal_share=1 / A.player.nunique(),
            p1=float(by["P1"]) if "P1" in by else None, p3=float(by["P3"]) if "P3" in by else None,
            plus_minus=sum((1 if h["team"] == "for" else -1) for h in goals if on[min(int(h["t"]), T - 1)])))
    return game, team, players


def team_nav(page):
    """The team selector at the top of a team's index.html or trends.html: every team, each linking to the same page
    of its own site (its index.html while it has no trends.html: no games yet). Empty while there is only one team."""
    sites = [(t, *site_of(t)) for t in teams()]
    sites.sort(key=lambda s: s[0] != "tk")   # Turbo Kings first
    if len(sites) < 2:
        return ""
    has_page = lambda t: page == "index.html" or glob.glob(f"{REPO}/teams/{t}/games/*/game.json")
    links = "".join(
        f'<a href="{escape(os.path.relpath(d, SITE_DIR).replace(os.sep, "/"))}/{page if page != "index.html" and has_page(t) else ""}"'
        f'{" aria-current=" + chr(34) + "page" + chr(34) if t == SLUG else ""}>{escape(name.removeprefix("LADA "))}</a>'
        for t, name, d in sites)
    return f'<nav class="teams" aria-label="Team">{links}</nav>'


def positioning_rows(games):
    """The season positioning rows: every skater with SEASON_GAMES+ games as a defenseman or a forward,
    with his season numbers in that role (season.json's positioning)."""
    out = []
    for k, s in season_positions(games).items():
        if s["D"] or s["F"]:
            out.append(dict(key=k, num=number_of(k), name=name_of(k), sub=is_sub(k), D=s["D"], F=s["F"]))
    return out


def build(games_dir=GAMES_DIR, site_dir=SITE_DIR):
    rows = [game_rows(gd) for gd in sorted(glob.glob(f"{games_dir}/*/"))]
    team = [t for _, t, _ in rows]
    players = [p for _, _, ps in rows for p in ps]
    if rows:   # the page needs a game; a team without one has only the feed's empty trends.json
        html = open(f"{HERE}/trends_template.html").read()
        data = dict(team=team, players=players, positioning=positioning_rows([g for g, _, _ in rows]),
                    season_games=SEASON_GAMES)
        html = html.replace("__NAV__", team_nav("trends.html")).replace("__TEAM__", TEAM).replace("__DATA__", json.dumps(data, separators=(",", ":")))
        open(f"{site_dir}/trends.html", "w").write(html)
    os.makedirs(f"{site_dir}/api", exist_ok=True)
    json.dump(trends_doc(rows), open(f"{site_dir}/api/trends.json", "w"), ensure_ascii=False, separators=(",", ":"))
    return len(team)


if __name__ == "__main__":
    print(f"trends over {build()} game(s) -> {SITE_DIR}/trends.html and api/trends.json")
