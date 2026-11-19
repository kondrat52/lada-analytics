You are identifying rec-hockey players in image crops. Accuracy matters more than coverage: answer "?" whenever you are not sure.

Directory: {rev}/
Temporary files go only in {scratch}/ (yours; other reviewers have their own). To look closer at a row, run `{PY} {zoom} {scratch} {rev}/sheet_NNN.jpg R58` and Read the PNG it prints. R58-R59 takes two rows; a last argument (4, or 3-6) keeps only those tiles, counted from 1 at the left; for a roster card give its path and #77. No other script or Python is needed.

1. First Read `roster_card.jpg`. Each row should show one player of ours, in {jersey_desc} (label "#N" = jersey number), in several views; a row or tile in the opponents' colours is an opponent with that number: never match anyone to it. Learn distinguishing features: number/name on the back (also sleeve numbers), sock color/stripes, pants (black shorts over white socks vs. long black), helmet color, glove color, skate color.
Roster: {roster}.{card_notes}{notes} If you clearly see another number on our jersey, report it.
{goalie_line}

2. Then Read ONLY these sheets: {sheets}. Each sheet has up to 8 rows. Each row = one tracked skater over time; every tile is labeled "R<id> <time>s". The tracker can make mistakes: a row may switch from one player to another partway through (a "swap"), and single tiles may show an overlapping player. For every row, decide who it is from numbers/names when visible, otherwise appearance matched against the roster card. Only give a number if reasonably confident (high = number/name visible on that player's part of the row, or a very distinctive look; med = appearance only, with no competing lookalike). If appearance fits several players, answer "?". If the row switches players, report both with the switch time in seconds.
Tiles showing an opponent skater ({opp_desc}) or a referee (black and white stripes) are noise: a row that is all noise (nobody of ours in it) gets "N" as the player; a row of ours with a few noise tiles keeps its player.

3. As soon as you have decided all rows of a sheet, and before reading the next one, Write that sheet's answer to `{rev}/review_sNNN.txt` (sheet_007.jpg -> review_s007.txt) as CSV, header exactly:
`row_id,player,confidence,switch_time,player2,confidence2,note`
player/player2: a jersey number, "?" (one of ours, unsure who), "G" (a goalie, either team's) or "N" (noise: no player of ours); confidence: high/med/low; switch fields empty unless the row switches; note: a few words, no commas. One line per row, every row on that sheet; row_id exactly as on the tile labels, with the R (e.g. R168).
If a Read of an image fails, retry it once. Never answer from other review files: they describe other rows.
