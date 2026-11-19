"""zoom.py OUTDIR IMAGE ROW [TILES]: part of a review sheet or roster card, enlarged, for a reviewer to Read.

ROW is a row id on a review sheet (R58, or R58-R59 for neighbours), a player's row on a roster card (#77), or a row
number counted from 1 at the top; TILES (optional) is 4 or 3-6, counted from 1 at the left. Writes
OUTDIR/<folder>_<image>_<row>[_<tiles>].png and prints its path. Reviewers cropped and enlarged sheets with scripts of
their own (after looking for an interpreter); this is that crop, sized so a Read doesn't shrink it again."""
import sys, os, re, json, csv, cv2

TILE_W, ROW_H = 110, 202     # sheet.py's tiles for review sheets and roster cards: 110 x 180 under a 22 px label
MAX_SIDE, MAX_SCALE = 1500, 4  # a Read shrinks larger images; past 4x a tile gains nothing


def card_rows(folder):
    """The roster card's row order: card_rows.json (roster_card.py), else the roster as prepare saw it, computed
    from the work folder's team and absent list (checked against the card's height by the caller)."""
    p = f"{folder}/card_rows.json"
    if os.path.exists(p):
        return json.load(open(p))
    W = os.path.dirname(folder)
    cfg = json.load(open(f"{W}/full/rink.json")) if os.path.exists(f"{W}/full/rink.json") else {}
    r = json.load(open(f"{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}/teams/{cfg.get('team', 'tk')}/roster.json"))
    return sorted({int(k) for part in ("skaters", "subs") for k in r.get(part, {})} - set(cfg.get("absent", [])))


def rows_of(image, spec, nrows):
    """0-based first and last row for ROW."""
    folder, name = os.path.dirname(os.path.abspath(image)), os.path.basename(image)
    if spec.upper().startswith("R"):
        ids = [r["row_id"] for r in csv.DictReader(open(f"{folder}/manifest.csv")) if r["sheet"] == name]
        want = [("R" + x.strip().lstrip("Rr")) for x in spec.split("-")]
        if not all(w in ids for w in want):
            sys.exit(f"{spec} is not on {name}" + (f" (it has {ids[0]}-{ids[-1]})" if ids else ""))
        return ids.index(want[0]), ids.index(want[-1])
    if spec.startswith("#"):
        order = card_rows(folder)
        if len(order) != nrows:
            sys.exit(f"can't tell which row is {spec} on {name}: give its row number from the top instead")
        if int(spec[1:]) not in order:
            sys.exit(f"{spec} has no row on {name}")
        k = order.index(int(spec[1:]))
        return k, k
    a, _, b = spec.partition("-")
    return int(a) - 1, int(b or a) - 1


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    out, image, spec = sys.argv[1:4]
    im = cv2.imread(image) if os.path.isfile(image) else None
    if im is None:
        sys.exit(f"can't read {image}")
    nrows, ncols = im.shape[0] // ROW_H, im.shape[1] // TILE_W
    try:
        r0, r1 = rows_of(image, spec, nrows)
        t0, _, t1 = (sys.argv[4] if len(sys.argv) > 4 else f"1-{ncols}").partition("-")
        t0, t1 = int(t0) - 1, int(t1 or t0) - 1
    except ValueError:
        sys.exit("ROW is R58, R58-R59, #77 or a row number; TILES is 4 or 3-6")
    if not (0 <= r0 <= r1 < nrows and 0 <= t0 <= t1 < ncols):
        sys.exit(f"{image} has rows 1-{nrows} and tiles 1-{ncols}")
    crop = im[r0 * ROW_H:(r1 + 1) * ROW_H, t0 * TILE_W:(t1 + 1) * TILE_W]
    s = min(MAX_SCALE, MAX_SIDE / max(crop.shape[:2]))
    crop = cv2.resize(crop, (round(crop.shape[1] * s), round(crop.shape[0] * s)), interpolation=cv2.INTER_LANCZOS4)
    os.makedirs(out, exist_ok=True)
    tag = re.sub(r"[^\w-]", "", spec.replace("#", "n")) + (f"_t{sys.argv[4]}" if len(sys.argv) > 4 else "")
    folder = os.path.basename(os.path.dirname(os.path.abspath(image)))
    dst = f"{out}/{folder}_{os.path.splitext(os.path.basename(image))[0]}_{tag}.png"
    cv2.imwrite(dst, crop)
    print(dst.replace("\\", "/"))


if __name__ == "__main__":
    main()
