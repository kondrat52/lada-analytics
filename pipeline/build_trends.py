"""build_trends.py : trends.html, the team's trends across games, from its games/*/game.json + shifts.csv, and
api/trends.json, the same measures for apps (build_feed.trends_doc). build_site.py runs it. Time in offence and
defence come from game.json's `zones` (zones.py, filled in on publish), shots on goal from its `shots` (shots.py,
read off the arena scoreboard)."""
import os, sys, json, glob
from html import escape
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roster import SKATERS, SUBS, TEAM, SLUG, REPO, GAMES_DIR, SITE_DIR, teams, site_of, opponent_name
from build_feed import trends_doc

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
    periods = game["periods"]
    length = sum(p["end"] - p["start"] for p in periods)
    T = int(max(p["end"] for p in periods)) + 2
    live = np.zeros(T, bool)
    for p in periods:
        live[p["start"]:p["end"]] = True
    for a, b in game.get("stoppages", []):
        live[int(a):int(b)] = False
    goals = [h for h in game.get("highlights", []) if h["type"] == "goal"]
    gf = sum(h["team"] == "for" for h in goals); ga = sum(h["team"] == "against" for h in goals)
    pks = game.get("penalty_kills", [])
    in_pk = lambda t: any(k["start"] <= t < k["end"] for k in pks)
    zones = game.get("zones") or {}
    shots = game.get("shots") or {}          # {"P1": [ours, theirs], ...} from the arena scoreboard
    sp = [shots[p["label"]] for p in periods if p["label"] in shots] or None
    team = dict(
        id=game["id"], date=game["date"], opp=opponent_name(game), opp_code=game["opponent"],
        rink=(game.get("eyebrow") or "").split("·")[-1].strip(), gf=gf, ga=ga,
        result="W" if gf > ga else ("L" if gf < ga else "T"), video_ends_early=bool(game.get("video_ends_early")),
        skaters=int(A.player.nunique()), avg_shift=float(A.dur.mean()), live_pct=float(live.sum() / length),
        penalties=len(penalties(game)), pk_ga=sum(h["team"] == "against" and in_pk(h["t"]) for h in goals),
        pk_min=float(sum(k["end"] - k["start"] for k in pks) / 60),
        offence=zones.get("offence"), defence=zones.get("defence"),
        sp=sp, sf=sum(x[0] for x in sp) if sp else None, sa=sum(x[1] for x in sp) if sp else None)
    players = []
    team_toi = A.dur.sum()
    for num, s in A.groupby("player"):
        on = np.zeros(T, bool)
        for r in s.itertuples():
            on[int(r.t0):int(r.t1)] = True
        by = s.groupby("period").dur.mean()
        players.append(dict(
            game=game["id"], num=int(num), name=SKATERS.get(int(num), ""), sub=int(num) in SUBS,
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


def build(games_dir=GAMES_DIR, site_dir=SITE_DIR):
    rows = [game_rows(gd) for gd in sorted(glob.glob(f"{games_dir}/*/"))]
    team = [t for _, t, _ in rows]
    players = [p for _, _, ps in rows for p in ps]
    if rows:   # the page needs a game; a team without one has only the feed's empty trends.json
        html = open(f"{HERE}/trends_template.html").read()
        html = html.replace("__NAV__", team_nav("trends.html")).replace("__TEAM__", TEAM).replace("__DATA__", json.dumps(dict(team=team, players=players), separators=(",", ":")))
        open(f"{site_dir}/trends.html", "w").write(html)
    os.makedirs(f"{site_dir}/api", exist_ok=True)
    json.dump(trends_doc(rows), open(f"{site_dir}/api/trends.json", "w"), ensure_ascii=False, separators=(",", ":"))
    return len(team)


if __name__ == "__main__":
    print(f"trends over {build()} game(s) -> {SITE_DIR}/trends.html and api/trends.json")
