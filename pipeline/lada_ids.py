"""lada_ids.py : check roster.json's players and lada_player_ids against the team's LADA roster, or fill them in.

Signs in to LADA as you once (password typed hidden, never stored or printed), reads
GET team/<lada_team_id>/Player for each team named and matches every roster.json player by jersey number +
surname. Prints, per player: same, NEW (an id to add), DIFFERS, no match (a sub off the
roster has none), and WRONG for an id LADA gives to someone else.

Without --write it changes nothing. With --write it adds to roster.json what LADA has and roster.json doesn't:
the NEW ids, and every LADA player whose number isn't in roster.json yet (surname = the last word of LADA's name;
goalies by LADA's position, spares by its Sub status). It never changes or removes what's already there, so
check the DIFFERS / WRONG lines by hand, and any number two LADA players share against SportNinja's game sheets
(who wore it).

    $PY pipeline/lada_ids.py [--write] [<slug> ...]   (teams/<slug>/roster.json; $TEAM, else tk, when none named)
    $PY pipeline/lada_ids.py --write bt df y r        (fill in new teams' rosters with one sign-in)
"""
import argparse, getpass, json, os, sys, unicodedata, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roster import REPO, teams

API = "https://api.ladaseattle.com/api/v1"


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def call(method, path, token=None, body=None):
    req = urllib.request.Request(f"{API}/{path}", method=method, headers={"Accept": "application/json"})
    if token:
        req.add_header("Authorization", token)  # raw, as the LADA app sends it
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, data, timeout=20) as r:
        return r.read().decode()


def check(slug, token, write):
    path = f"{REPO}/teams/{slug}/roster.json"
    r = json.load(open(path))
    team_id = r["lada_team_id"]
    try:
        players = json.loads(call("GET", f"team/{team_id}/Player", token=token))
    except urllib.error.HTTPError as e:
        print(f"\n{slug}: LADA won't show you team {team_id}'s roster (HTTP {e.code}); skipped")
        return
    by_id = {p["id"]: p for p in players}
    ids = {int(k): v for k, v in r.get("lada_player_ids", {}).items()}
    names = {int(k): v for part in ("skaters", "subs", "goalies") for k, v in r.get(part, {}).items()}
    print(f"\n{slug}: LADA team {team_id} ({r['team']}), {len(players)} players on the roster\n")
    new_ids = {}
    for num, name in sorted(names.items()):
        hits = [p for p in players if p.get("number") == num and fold(name) in fold(p.get("name"))]
        mine = ids.get(num)
        owner = by_id.get(mine)
        if mine and owner and (owner.get("number") != num or fold(name) not in fold(owner.get("name"))):
            state = f"WRONG: LADA gives {mine} to #{owner.get('number')} {owner.get('name')}"
        elif len(hits) == 1:
            pid = hits[0]["id"]
            state = "same" if mine == pid else "NEW" if mine is None else f"DIFFERS (roster.json {mine})"
            if mine is None:
                new_ids[num] = pid
        else:
            state = "ambiguous" if hits else "no match"
        lada = ", ".join(f"{p.get('name')} {p['id']}" for p in hits) or "-"
        print(f"#{num:<3} {name:<14} {lada:<30} {state}")
    if not write:
        return
    # LADA's players whose number roster.json doesn't have yet; the league's shared account stays out. Two with
    # the same number: the regular before the sub, and the one left out is printed (check SportNinja's game sheets)
    added = []
    for p in sorted(players, key=lambda p: (p.get("number") or 0, p.get("status") == "Sub")):
        num, full = p.get("number"), (p.get("name") or "").strip()
        if not num or not full or num in names or "dannikh" in fold(full):
            if not num and full:
                print(f"     {full:<14} no number on LADA; left out (LADA id {p['id']})")
            elif num in names and fold(names[num]) not in fold(full):
                print(f"#{num:<3} {full:<14} the number is {names[num]}'s in roster.json; left out (LADA id {p['id']})")
            continue
        part = "goalies" if p.get("position") == "Goalie" else "subs" if p.get("status") == "Sub" else "skaters"
        names[num] = full.split()[-1]
        r.setdefault(part, {})[str(num)] = names[num]
        new_ids[num] = p["id"]
        added.append(f"#{num} {names[num]}" + ("" if part == "skaters" else f" ({part[:-1]})"))
    if not new_ids:
        print(f"\n{slug}: nothing to add")
        return
    ids.update(new_ids)
    for part in ("goalies", "skaters", "subs"):
        r[part] = {str(k): v for k, v in sorted((int(k), v) for k, v in r.get(part, {}).items())}
    r["lada_player_ids"] = {str(k): v for k, v in sorted(ids.items())}
    open(path, "w").write(json.dumps(r, indent=2, ensure_ascii=False) + "\n")
    print(f"\n{slug}: wrote {os.path.relpath(path)}: {len(added)} player(s) added"
          + (f" ({', '.join(added)})" if added else "") + f", {len(new_ids)} LADA id(s)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("teams", nargs="*", help="team slugs (folders in teams/)")
    ap.add_argument("--write", action="store_true", help="add what LADA has and roster.json doesn't")
    a = ap.parse_args()
    slugs = a.teams or [os.environ.get("TEAM") or "tk"]
    unknown = [t for t in slugs if t not in teams()]
    if unknown:
        raise SystemExit(f"unknown team {', '.join(unknown)}; known: {', '.join(teams())}")
    email = input("LADA email: ").strip()
    password = getpass.getpass("LADA password (hidden): ")
    token = call("POST", "user/login", body={"email": email, "password": password, "rememberMe": False})
    for slug in slugs:
        check(slug, token.strip().strip('"'), a.write)


if __name__ == "__main__":
    main()
