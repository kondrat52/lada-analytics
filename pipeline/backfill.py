"""backfill.py [--team SLUG ...] [--only ID ...] [--work DIR] [--dry-run] [--no-build] : bring every published game
up to what publish now writes, without republishing it, then rebuild the sites.

Per game (teams/<slug>/games/<id>/), one at a time (a game's dets.csv is about 80 MB):
- the stoppages: a goal inside one moves its start to just after the goal (stoppages.after_goals), always from the
  motion estimate before that correction: the work folder's stoppages.json, else game.json's `stoppages_raw` (which
  it writes, as publish does), so a goal's time changed since can move a start back. Each shift's `play` in
  shifts.csv follows. That is exact without a work folder: `play` is the live seconds of [int(t0), int(t1)) inside
  the periods and outside the stoppages, all of which game.json and shifts.csv hold (on Nov 24, 2026 the published
  `play` of all 55 games came out identical from them). The six games without a work folder (Turbo Kings' Sep 13 to
  Oct 10, Blue Wings' Sep 13) got their `stoppages_raw` from their game.json before the correction (commit 773b927).
  A game with neither moves its published stoppages again, which can only move a start later. Run again, it
  changes nothing.
- with the game's archived work folder (~/hockey-work/<id> for Turbo Kings, <slug>-<id> for the others, with its
  dets.csv): time in offence and defence from the play's position in feet (zones.py; the picture's thirds at a rink
  without a calibration) and each skater's role and positioning parts (positioning.py), as publish makes them.
- without one: its zones stay as they were published, from the picture's thirds, and say so ("basis": "px").
A game that fails (a work folder missing a file: segs_final.csv, tracks_v1.csv, boards_poly.npy) is left as it was;
the others go on, the sites are still rebuilt, and the failed games are listed at the end with why (exit status 1).
Prints per game what moved; --dry-run writes nothing."""
import argparse, glob, json, os, subprocess, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stoppages

REPO = os.path.dirname(HERE)


def work_folder(work, slug, gid):
    """The game's archived work folder with its detections, or None."""
    W = os.path.join(work, gid if slug == "tk" else f"{slug}-{gid}")
    if not os.path.exists(f"{W}/full/dets.csv") or not os.path.exists(f"{W}/periods.json"):
        return None
    team = json.load(open(f"{W}/full/rink.json")).get("team", "tk") if os.path.exists(f"{W}/full/rink.json") else "tk"
    return W if team == slug else None


def raw_stoppages(game, W):
    """The motion estimate of the stoppages before the goal correction and where it came from: W's stoppages.json,
    else game.json's stoppages_raw; (None, None) with neither."""
    if W and os.path.exists(f"{W}/stoppages.json"):
        return json.load(open(f"{W}/stoppages.json")), "the work folder's stoppages.json"
    if "stoppages_raw" in game:
        return game["stoppages_raw"], "stoppages_raw"
    return None, None


def with_raw(game, raw):
    """game with its stoppages_raw set, placed right after its stoppages."""
    if "stoppages_raw" in game or "stoppages" not in game:
        return dict(game, stoppages_raw=raw)
    out = {}
    for k, v in game.items():
        out[k] = v
        if k == "stoppages":
            out["stoppages_raw"] = raw
    return out


def backfill(gd, W, dry=False):
    """One published game: returns a line saying what moved. Writes nothing until it has all of it."""
    gj = f"{gd}/game.json"
    game = json.load(open(gj, encoding="utf-8"))
    A = pd.read_csv(f"{gd}/shifts.csv")
    old = game.get("stoppages", [])
    goals = stoppages.goal_times(game.get("highlights"))
    raw, src = raw_stoppages(game, W)
    base = raw if raw is not None else old
    new = stoppages.after_goals(base, goals)
    live = lambda s: int(stoppages.live_mask(game["periods"], s).sum())
    moved = sum(1 for a, b in base if any(a <= t < b for t in goals))
    play0 = int(A.play.sum()) if "play" in A else None
    line = [f"live {live(old)} -> {live(new)} s ({moved} stoppage(s) moved, from "
            f"{src or 'the published stoppages: no stoppages_raw'})"]
    if raw is not None:
        game = with_raw(game, raw)
    game["stoppages"] = new
    if "play" in A:
        A["play"] = stoppages.play_column(A, game["periods"], new)
        line.append(f"shifts' play {play0} -> {int(A.play.sum())} s")
    z0 = game.get("zones")
    if W:
        from zones import detections, play_position, zone_shares
        from ice import positions
        from positioning import game_positions
        dets = detections(f"{W}/full")
        play = play_position(f"{W}/full", game, dets)
        game["zones"] = zone_shares(f"{W}/full", game, play, dets) or z0
        del dets
        if play is None:
            line.append("no positions (no calibration for the rink)")
        else:
            D = positions(W)
            pos = game_positions(W, game, play, D) if D is not None and len(D) else None
            if pos:
                game["positions"] = pos
                roles = [e["role"] for e in pos["players"].values()]
                line.append(f"roles {roles.count('D')} D, {roles.count('F')} F, {roles.count(None)} unclear")
            else:
                line.append("no positions (no labeled positions" +
                            (")" if D is None or not len(D) else " in live play)"))
    elif z0 and "basis" not in z0:
        game["zones"] = dict(z0, basis="px")   # zones.py's picture thirds, all it had then
    z1 = game.get("zones")
    if z1:
        f = lambda z: f"{z['offence']:.3f}/{z['defence']:.3f}" if z else "-"
        line.append(f"zones {f(z0)} -> {f(z1)} ({z1.get('basis')})")
    if not dry:
        json.dump(game, open(gj, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        A.to_csv(f"{gd}/shifts.csv", index=False)
    return "; ".join(line)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--team", nargs="*", help="team slugs (default: every team)")
    ap.add_argument("--only", nargs="*", help="game ids (default: every published game)")
    ap.add_argument("--work", default=os.path.expanduser("~/hockey-work"), help="where the work folders are")
    ap.add_argument("--dry-run", action="store_true", help="print what would move, write nothing")
    ap.add_argument("--no-build", action="store_true", help="don't rebuild the sites afterwards")
    a = ap.parse_args()
    n, failed = 0, []
    for gd in sorted(glob.glob(f"{REPO}/teams/*/games/*/")):
        gd = os.path.normpath(gd); gid = os.path.basename(gd); slug = os.path.basename(os.path.dirname(os.path.dirname(gd)))
        if (a.team and slug not in a.team) or (a.only and gid not in a.only):
            continue
        n += 1
        W = work_folder(a.work, slug, gid)
        head = f"{slug:3s} {gid:20s} {'work folder' if W else 'no work folder'}"
        try:
            print(f"{head}: {backfill(gd, W, a.dry_run)}", flush=True)
        except Exception as e:   # a work folder missing a file: report it, leave the game as it was, go on
            why = f"{type(e).__name__}: {e}"
            failed.append((slug, gid, why))
            print(f"{head}: FAILED, left as it was ({why})", flush=True)
    print(f"{n} game(s){' (dry run: nothing written)' if a.dry_run else ''}"
          f"{f', {len(failed)} failed' if failed else ''}")
    if n and not a.dry_run and not a.no_build:
        subprocess.run([sys.executable, f"{HERE}/build_site.py"], check=True,
                       env={k: v for k, v in os.environ.items() if k not in ("TEAM", "ROSTER_ABSENT")})
    if failed:
        print(f"\n{len(failed)} game(s) failed and were left as they were:")
        for slug, gid, why in failed:
            print(f"  {slug} {gid}: {why}")
        sys.exit(1)


if __name__ == "__main__":
    main()
