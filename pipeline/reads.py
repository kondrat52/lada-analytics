import pandas as pd, glob, difflib
from collections import Counter

from roster import SKATERS, ALL_SKATERS

# surname (as printed on jerseys) -> number, for fuzzy-matching OCR text; a surname two players share (father and
# son) says nothing about which one it is, so only their numbers tell them apart
_SHARED = Counter(name.upper() for name in SKATERS.values() if name)
NAMES = {name.upper(): num for num, name in SKATERS.items() if name and _SHARED[name.upper()] == 1}
# the surnames of roster players marked absent this game (ROSTER_ABSENT): a plate that fits one of them better than
# any name of a player who plays is nobody's. Dropped from the race, they handed plates to whoever was left: on
# Beerteam's Nov 14 game PIZANO, an opponent's, scored 0.73 against PANOV #76, 0.67 against SHIKHANOV #70 and 0.67
# against EGIAZAROV #27; with #76 and #70 absent the margin rule (0.12 over the next name) passed, and #27 got 70
# name reads. They don't enter the margin: on the 48 archived games that would have dropped 3,111 of 137,586 name
# reads, nearly all a playing player's own (PANOVA, an exact read, against an absent PANOV; Dotsenko's DUTSENKO,
# whose window score ties with an absent BELOUSENKO), where "fits an absent name better" drops 242, PIZANO's 70
# among them. A surname an absent player shares with one who plays stays the player's (marking the other absent is
# how it counts for him).
RIVALS = sorted({name.upper() for num, name in ALL_SKATERS.items() if name and num not in SKATERS} - set(_SHARED))


_NORM = str.maketrans({"D": "O", "Y": "V", "Q": "O", "0": "O"})


def _score(txt, nm):
    """An OCR'd text (normalized) against one surname: the whole name, or its best same-length window for a read
    truncated at the jersey edge (a short one marked down)."""
    nm = nm.translate(_NORM)
    r = difflib.SequenceMatcher(None, txt, nm).ratio()
    for k in range(0, max(1, len(nm) - len(txt) + 1)):
        r = max(r, difflib.SequenceMatcher(None, txt, nm[k:k + len(txt)]).ratio() * (0.85 if len(txt) < 6 else 1))
    return r


def name_to_num(txt):
    """Fuzzy-match an OCR'd surname (often truncated at the jersey edge) to a roster number, or None: below 0.65,
    within 0.12 of the next playing player's name, or closer to an absent player's name (RIVALS) than to any.
    OCR often confuses D/O and Y/V, so both sides are normalized first."""
    best, second, num = 0, 0, None
    txt = txt.translate(_NORM)
    for nm, n in NAMES.items():
        r = _score(txt, nm)
        if r > best:
            best, second, num = r, best, n
        elif r > second:
            second = r
    if best >= 0.65 and best - second >= 0.12 and not any(_score(txt, nm) > best for nm in RIVALS):
        return num
    return None


def load_reads(outdir, min_score=0.9):
    """Returns (reads, names). reads has columns frame,i,num,src ('digit'|'name'); name reads override
    look-alike digit reads from the same crop."""
    o = pd.concat([pd.read_csv(f, header=None, names=["file", "text", "score"], dtype={"text": str})
                   for f in glob.glob(f"{outdir}/ocr_*.csv")])
    o = o.dropna().drop_duplicates(["file", "text"])
    o["frame"] = o.file.str[1:7].astype(int); o["i"] = o.file.str[8:10].astype(int)
    o["text"] = o.text.str.strip()
    dig = o[o.text.str.fullmatch(r"\d{1,2}") & (o.score >= min_score)].copy()
    dig["num"] = dig.text.astype(int); dig["src"] = "digit"
    nm = o[o.text.str.fullmatch(r"[A-Z]{4,}") & (o.score >= 0.7)].copy()
    cache = {x: name_to_num(x) for x in nm.text.unique()}
    nm["num"] = nm.text.map(cache)
    nm = nm.dropna(subset=["num"]).copy(); nm["num"] = nm.num.astype(int); nm["src"] = "name"
    # a name read in a crop replaces that crop's digit reads
    named = set(nm.file)
    dig = dig[~dig.file.isin(named)]
    reads = pd.concat([dig, nm])[["file", "frame", "i", "num", "src", "score"]]
    return reads, nm
