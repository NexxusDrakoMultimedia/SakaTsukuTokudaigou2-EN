"""sk6_docs: correct two stale statements in docs/art-translation.md and append section 12 (skeptic pass).  Idempotent."""
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
p = os.path.join(ROOT, 'docs', 'art-translation.md')
s = open(p, encoding='utf8').read()
old1 = ' FACEMDUL 00056 / 00062 / 00065 (three red face tiles with a single kanji each, in a bind-style file that `texindex` does not list, so they cannot be injected).'
new1 = ' (FACEMDUL 00056 / 00062 / 00065, the three 大 / 特 / 号 face tiles, were listed here as impossible; they are injectable as `ATFIRST/FACEMDUL.DAT @cb7e0/kao_*.pvr` and are installed and applied, see section 12.)'
if old1 in s:
    s = s.replace(old1, new1)
old2 = '* Open: the club-name plates `ALLLOGOS` / `BINDLOGO` / `BINDNAME` written by the club-words workflow did not fit their slots under `exact` (86 textures) at the time of the art6 trial; art6 was built from a snapshot without them.'
new2 = '* The club-name plates `ALLLOGOS` / `BINDLOGO` / `BINDNAME` written by the club-words workflow did not fit under `exact` at the time of the art6 trial (art6 was built from a snapshot without them); they fit now, see section 12.'
if old2 in s:
    s = s.replace(old2, new2)
if '## 12. Skeptic pass' not in s:
    s += '''
## 12. Skeptic pass over section 11 (sk6, 2026-11-12)

* Re-run: `tools/test_texinject.py` 427 checks 0 failed, `tools/test_arttext.py` ALL OK.  Fresh standard trial `build/trial/sk6a` from the LIVE `translation/textures`
  (club-name plates included): 216 texture rows, failed=0; `artcoverage` 206 ids, 0 NOT APPLIED, MISSING only 02213 / 02214 / 03570 / 03571, all four decoded and checked: blank table / plate frames, no text.
  (The only non-zero exit was one string, `BCAST/BCAST.BIN#1c755080`, 75 bytes for a 75-byte budget including the NUL; text side, not art.)
  `tools/re/sk6_fit.py` / `sk6_fit2.py` show ALLLOGOS 66, BINDLOGO 80, BINDNAME 1 textures inject under `exact`, one by one and as a set: the "86 club-name textures do not fit" note in section 11 was stale.
* `artcoverage` does resolve 00056 / 00062 / 00065: FACEMDUL.DAT `@cb7e0/kao_{g_dai,r_toku,y_gou}.pvr`, TITLEM.DAT #11 / #14 / #16 and KSPAPET.ZAR, all applied.
* Defect found and fixed: **LOADBAR.BIN `@1ec#0` (07332) and YOUTH.BIN `@36114#0` (10469)** kept fragments of the old 年 / 月 / 週 top strokes (a dot and dashes at y 31..33 above `Yr` / `Mo` / `Wk`, outside the erase rectangle that started at y 34), and the English sat 3 px below the kanji centre.
  `tools/re/sk6_hdrfix.py` widens the three erase rectangles to y 28..70 and moves the text up 2 px in `tools/re/art1_spec/07332.json` and `10469.json`; `art1_run.py 07332 10469`, then the two `.pvr` copied into `translation/textures` (only the two files; changed pixels x 202..324, y 31..57).  The BAR, YOUTH.ZAR and TRAINING sheets were clean.
* Header overlap: `ar6_hdrsim.py` prints the same 9 px "overlap" for the old kanji, the previous and the new sheet, so its number is not a usable metric; the composed picture `build/ar6/hdrsim.png` (digits right-aligned against the old kanji's left edge, month 12, week 4) is, and shows no digit/unit contact for the installed sheets.  Ink columns in the BAR sheet (`sk6_cells.py`): `Mo` x 268..277, `Wk` x 304..320 (old 月 264..274, 週 300..313); the next sprite starts at x 328.  The code's real digit x is not known, so this is a model, not an emulator check.
* Heuristic overflow scan (`sk6_bbox.py`: new ink outside the old ink's row band, 426 changed textures): the EVENT banner plates grow to the left (whole 256-wide texture), money plates PLATE.ZAR end at x 123 of 128 (+1 px against the pre-ar6 sheet), TV_E1#2 `Decided` x 11..83 inside the old 決定 x 0..86, `Wk n` in SCHE1#3 matches the old footprint.  Needs a screen to settle.
* Not part of art6 and being installed by another run while this pass ran: `TRAINING/BFGAME.ZAR bfgame.tbd#0..#2` (the pre-match tactics menu, ids 37171-37173, fully Japanese in the extracted disc).
'''
open(p, 'w', encoding='utf8').write(s)
print('ok')
