"""regress.py [--work DIR] [--jobs N] [--keep] [--only NAME ...] : re-solve every archived work folder and compare
the result with the shift sheet that was published for it.

`run_game.py archive` keeps each game's detections, tracks, segments, reviews and periods.json (~100 MB), so a
later pipeline can solve the game again. This runs that solve for every such folder in DIR (~/hockey-work) in a
scratch copy (`DIR/_regress/<name>/`: small files copied, dets.csv linked), then compares `shifts_all.csv` with the
published `teams/<slug>/games/<id>/shifts.csv`. With no pipeline change every game must come out identical; after a
change to shifts.py, apply_review.py, solver.py, run2.py, final_stats.py or stoppages.py this shows what moved,
game by game and player by player, before any site is rebuilt.

A player who appears in a re-solve but not in the published sheet is usually roster drift: a number added to
roster.json after the game was published now absorbs reads it didn't then (mark it absent in that folder's
full/rink.json if so).
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable


def game_of(name, team):
    """Work folder name -> (slug, game id): 'bw-2026-09-20-vs-up' -> ('bw', '2026-09-20-vs-up'); Turbo Kings' folders
    have no prefix."""
    m = re.match(r"^(?:([a-z]+)-)?(\d{4}-\d{2}-\d{2}-vs-[a-z]+)$", name)
    if not m:
        return None, None
    return team or m.group(1) or "tk", m.group(2)


def stage(W, T):
    """Copy what a solve reads into T (dets.csv as a link: 70 MB per game)."""
    if os.path.exists(T):
        shutil.rmtree(T)
    os.makedirs(f"{T}/full")
    for f in ("periods.json", "highlights.json", "sheet.json"):
        if os.path.exists(f"{W}/{f}"):
            shutil.copy(f"{W}/{f}", T)
    for f in ("rink.json", "boards_poly.npy"):
        shutil.copy(f"{W}/full/{f}", f"{T}/full/{f}")
    src = os.path.realpath(f"{W}/full/dets.csv")
    try:
        os.symlink(src, f"{T}/full/dets.csv")
    except OSError:
        shutil.copy(src, f"{T}/full/dets.csv")
    for pdir in glob.glob(f"{W}/p[0-9]*"):
        p = os.path.basename(pdir); os.makedirs(f"{T}/{p}")
        for f in ("tracks_v1.csv", "segs_v1.csv"):
            shutil.copy(f"{pdir}/{f}", f"{T}/{p}/{f}")
        # rink.py finds a period folder's rink.json and boards through its dets.csv link (run_period.py makes one)
        try:
            os.symlink(f"{T}/full/dets.csv", f"{T}/{p}/dets.csv")
        except OSError:
            shutil.copy(f"{T}/full/dets.csv", f"{T}/{p}/dets.csv")
    for rdir in glob.glob(f"{W}/rev_p[0-9]*"):
        r = os.path.basename(rdir); os.makedirs(f"{T}/{r}")
        for f in [f"{rdir}/manifest.csv"] + glob.glob(f"{rdir}/review_*.txt"):
            shutil.copy(f, f"{T}/{r}/")


def compare(new, pub):
    """Both shifts tables -> (same, summary string)."""
    key = ["player", "period", "t0", "t1"]
    a = pd.read_csv(new); b = pd.read_csv(pub)
    cols = [c for c in ("player", "period", "t0", "t1", "dur", "play") if c in a.columns and c in b.columns]
    a = a[cols].sort_values(key).reset_index(drop=True); b = b[cols].sort_values(key).reset_index(drop=True)
    if a.equals(b):
        return True, "identical"
    m = a.merge(b, on=key, how="outer", suffixes=("_new", "_pub"), indicator=True)
    added = int((m._merge == "left_only").sum()); gone = int((m._merge == "right_only").sum())
    ta = a.groupby("player").dur.sum(); tb = b.groupby("player").dur.sum()
    d = (ta.reindex(ta.index.union(tb.index), fill_value=0) - tb.reindex(ta.index.union(tb.index), fill_value=0))
    d = d[d != 0].sort_values(key=abs, ascending=False)
    new_players = sorted(set(ta.index) - set(tb.index))
    parts = [f"{added} shift(s) new, {gone} gone"]
    if len(d):
        parts.append("TOI " + ", ".join(f"#{int(p)} {v:+.0f}s" for p, v in d.head(6).items()) + (" ..." if len(d) > 6 else ""))
    if new_players:
        parts.append("players not in the published sheet (roster drift?): " + ", ".join(f"#{int(p)}" for p in new_players))
    if "play" in cols and added == 0 and gone == 0:
        dp = (m.play_new - m.play_pub).abs().sum()
        if dp:
            parts.append(f"play time differs by {int(dp)} s in all")
    return False, "; ".join(parts)


def run_one(W, out_dir, keep):
    name = os.path.basename(W.rstrip("/\\"))
    cfg = json.load(open(f"{W}/full/rink.json")) if os.path.exists(f"{W}/full/rink.json") else {}
    slug, gid = game_of(name, cfg.get("team"))
    if not gid:
        return name, "skip", "not a game folder"
    pub = f"{ROOT}/teams/{slug}/games/{gid}/shifts.csv"
    if not os.path.exists(pub):
        return name, "skip", f"no published {slug}/games/{gid}"
    if not os.path.exists(f"{W}/periods.json") or not glob.glob(f"{W}/p[0-9]*/segs_v1.csv"):
        return name, "skip", "no periods.json or segments to solve"
    T = f"{out_dir}/{name}"
    t0 = time.time()
    try:
        stage(W, T)
        log = f"{out_dir}/{name}.solve.log"
        with open(log, "w", encoding="utf-8") as fh:
            r = subprocess.run([PY, f"{HERE}/run_game.py", "solve", T], stdout=fh, stderr=subprocess.STDOUT, text=True)
        if r.returncode:
            return name, "ERROR", f"solve failed (exit {r.returncode}); see {log}"
        txt = open(log, encoding="utf-8", errors="replace").read()
        m = re.search(r"lineup check: (OK|\d+ to look at)", txt)
        pct = re.findall(r"\((\d+)%\)", txt)
        same, why = compare(f"{T}/shifts_all.csv", pub)
        extra = f"; {'/'.join(pct)}%; lineup {m.group(1) if m else '?'}; {time.time() - t0:.0f} s"
        return name, "same" if same else "DIFFERS", why + extra
    finally:
        if not keep and os.path.exists(T):
            shutil.rmtree(T, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", default=os.path.expanduser("~/hockey-work"), help="where the work folders are")
    ap.add_argument("--jobs", type=int, default=3, help="solves at once (3)")
    ap.add_argument("--keep", action="store_true", help="keep each scratch copy (_regress/<name>/) for a look")
    ap.add_argument("--only", nargs="*", help="folder names to run (default: all)")
    a = ap.parse_args()
    out_dir = f"{a.work}/_regress"; os.makedirs(out_dir, exist_ok=True)
    folders = sorted(d for d in glob.glob(f"{a.work}/*") if os.path.isdir(d) and os.path.exists(f"{d}/full/rink.json")
                     and not os.path.basename(d).startswith("_"))
    if a.only:
        folders = [d for d in folders if os.path.basename(d) in set(a.only)]
    print(f"{len(folders)} folder(s), {a.jobs} at a time; scratch in {out_dir}", flush=True)
    results = []
    with ThreadPoolExecutor(a.jobs) as ex:
        for name, status, why in ex.map(lambda W: run_one(W, out_dir, a.keep), folders):
            print(f"{status:8s} {name:28s} {why}", flush=True)
            results.append(status)
    n = len(results)
    print(f"\n{results.count('same')} same, {results.count('DIFFERS')} differ, {results.count('ERROR')} failed, "
          f"{results.count('skip')} skipped, of {n}")
    sys.exit(1 if results.count("DIFFERS") or results.count("ERROR") else 0)


if __name__ == "__main__":
    main()
