"""sheet.py OUT.jpg TILE_W TILE_H COLS img1[:label] img2[:label] ...

An item whose path is "none" (or empty) is a blank tile on purpose: roster_card.py pads each player's row to COLS
tiles with "none::", and an empty row stands for a roster number with no crops that period. Those used to go to
cv2.imread, whose "imread_('none'): can't open/read file" warning filled prepare's log (40 lines on Beerteam's
Nov 14 game). A path that should be there and isn't is still a blank tile, and one line at the end says how many."""
import os, sys, cv2, numpy as np
out, tw, th, cols = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
items = sys.argv[5:]
rows = (len(items) + cols - 1) // cols
sheet = np.full((rows * (th + 22), cols * tw, 3), 255, np.uint8)
missing = []
for k, it in enumerate(items):
    path, _, label = it.partition("::")
    if path in ("", "none"):
        continue
    im = cv2.imread(path) if os.path.isfile(path) else None
    if im is None:
        missing.append(path); continue
    s = min(tw / im.shape[1], th / im.shape[0])
    im = cv2.resize(im, (max(1, int(im.shape[1] * s)), max(1, int(im.shape[0] * s))), interpolation=cv2.INTER_CUBIC if s > 1 else cv2.INTER_AREA)
    r, c = divmod(k, cols); y0, x0 = r * (th + 22) + 22, c * tw
    sheet[y0:y0 + im.shape[0], x0:x0 + im.shape[1]] = im
    cv2.putText(sheet, label or str(k), (x0 + 3, y0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 200), 2)
cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
if missing:
    print(f"sheet.py: {len(missing)} of {len(items)} images missing or unreadable, left blank in {out} (first: {missing[0]})",
          file=sys.stderr)
