<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Open-font glyphs (Roboto Condensed Medium) for the half-width ASCII block

Status: **implemented as an opt-in build flag, `--open-font {off,on}`, default off.  Not seen on screen: no disc was built or booted for this.**
Code: `tools/re/font/render_open_font.py` (generator), `tools/openfont.py` (loader), `tools/fontpatch.py` (`proportional_font(open_font=...)`,
`make_patches(open_font=...)`), `tools/build_patch.py` (flag), `tools/pixelwidth.py` (`set_open_font`, profile `open`).
Data (committed): `translation/fonts/robotocondensed_medium_12x24.bin` (94 x 144 bytes) and `.widths.json` (advance table + provenance).
Tests: `tools/test_open_font.py` (renderer rules, committed data, table consumers), `tools/test_bldflags.py` (flag off / on).
Study outputs (not committed): `build/fontstudy/` (`report_final.txt`, `sheet_medium_final.png`, `strips{1,2,4}x_medium_final.png`, `final_medium_strips.png`).

Why: the original English glyphs are the Japanese font's Latin letters (12 px capitals, hard anti-aliasing, centred narrow letters). Redrawing them
from a modern font gives smoother, more regular text; with the proportional advance table the rhythm is more even.

## 1. Licence

* The user accepted the **SIL Open Font License 1.1** (the current upstream file `google/fonts` `ofl/robotocondensed/RobotoCondensed[wght].ttf`,
  Copyright 2011 The Roboto Project Authors) and chose **Medium (wght 500)**.
* Files: `LICENSES/OFL-1.1.txt` (upstream `OFL.txt`), `REUSE.toml` (annotation `translation/fonts/**`: `OFL-1.1`, copyright 2011 The Roboto Project
  Authors), README "Third-party credit" line and licence table row, `doc/NOTICE-fonts.md`, and a paragraph in the release bundle's `NOTICE.txt`
  (`tools/release.py` `OFL_NOTICE`, written when `LICENSES/OFL-1.1.txt` is part of the bundle).  The generator and the loader are the project's own code
  (GPL-3.0-or-later) and credit the font in their docstrings; the TTF is **not** committed.  There is no `reuse` tool in this repository, the
  annotation was checked by hand (REUSE.toml parses; `translation/fonts/**` is the only new path).
* The bitmaps are a derivative of the font; the OFL allows embedding and redistribution with the notice and licence text, not selling the font alone,
  and a modified font may not use a Reserved Font Name (the metadata lists none).  The bitmaps reach players as bytes of `FONT.BIN` inside the xdelta patches;
  `NOTICE.txt` and `LICENSES/` are in the bundle.
* The `.widths.json` records the SHA-256 of the TTF that was rendered and of the glyph file; `openfont.load()` refuses a glyph file that does not match.

## 2. Method (what the generator does)

Everything is deterministic from (TTF bytes, parameters); the parameters are stored in the `.widths.json`.

1. **Size**: original cap height 18 rows (measured: cap 3.53..21.53, x-height 13.93); Roboto cap ratio 0.711 -> 25.32 px/em.
2. **Rasterise** unhinted at 16x supersampling (Pillow/FreeType, `wght` axis 500), exact area resampling to 12x24 (no ringing).
3. **Vertical grid fitting** (fixes the skeptic's descender flaw): the baseline is a row boundary at **y = 21** (rows 0..20 above, **three rows 21..23 below**;
   the original sits 0.5 row lower with a 1-row descender; baseline 22 left only two rows and squashed `g j p q y` to stubs).
   Flat tops are put on row boundaries: capitals, digits and most punctuation top on row 3 (cap 18), x-height letters **14 rows** (natural 13.4,
   original 13.9), ascenders `b d h k l f` on row 2 (19), `t` 17, `i j` dots 19.  Round overshoots above the landmarks and below the baseline are cut
   flush.  Descenders (`g j p q y`, `, ;`, `( ) [ ] { } |`, `@ Q`) are compressed into the three rows (k 0.53-0.96, `g y` 0.56): a 3 row tail with
   a real hook instead of the earlier 2 row stub with k 0.38; `p q` keep a 3 row stem.  (Alternative tried earlier: baseline 21 as `--baseline 21` in
   the study = this one; baseline 20 would give four rows but moves the text 1.5 px up.)
4. **Horizontal grid fitting** (fixes the soft stems): the left ink edge of every glyph is exactly column 0 (edges are measured at 50 % coverage of the
   16x image, exact to 1/16 px) and the **ink width is snapped to whole columns** (never more than 12), so the first and last stem of a glyph have
   crisp edges: `l` is three columns of level 0, `H` stems are `[1 0 0]` / `[0 0 0]`, every letter has at least two columns of level 0 (test).
   The dot of `i` is wider than its stem, so `i` has one full column with 2/15 fringes on both sides.  Digits are placed on the tabular grid (the font's
   pen box of 12.7 px centred in the 12 px cell, rounded to whole columns), so `1` keeps the font's own optical position (columns 2..9) and all digits
   advance 12.  No gamma: with the snapped edges the stems already reach level 0 (`--gamma` exists, 1.0 is used).
5. **Wide capitals** (W 17.9 px, @ 17.1, m 16.0, M 15.9, w 15.2, A 14.1, % 13.8, V 13.7, X, Y, & ... natural ink at cap height 18): the tile is 12 columns, see
   section 4.  They are squeezed to 12 columns with a **heavier weight** (wght 500 -> up to 660 for W, 610 M/m, 590 w, 650 @) so the strokes keep about
   half of the thickness that the squeeze takes away (`--comp 0.5`).
6. **Levels**: `level = 15 - round(coverage * 15)`, 0 = ink, 15 = paper/transparent, all 16 levels used.
7. **Slots** 0x21..0x7E (94 glyphs); 0x5C stays a yen sign and 0x7E an overline (as in the original block); 0x20, 0x7F and the katakana slots are untouched.
8. **Advance table** (`advance_table`, fixes the width flaws): `advance = ink right edge (columns) + gap`, gap = right bearing of the glyph in the font
   (scaled with the glyph's horizontal factor) + mean left bearing of the lower case letters (1.03 px; the next glyph's left bearing is gone because every
   glyph starts at column 0) - `--tight` 0.5, rounded, at least 1 and at most 3 blank columns; maximum advance 13 (12 columns + 1).  So `t` (8) and `f` (8)
   come out of ink + gap (no fixed 9), `i l` 5, `j` 7, `. , : ;` 5-7, `1` is a digit (12).  **Space = natural space advance 5.81 + mean left bearing 1.03 = 7 px**
   (index 0x20 and index 0, the string compiler's blank cell 0x2020).  Digits 12.  The table is stored in the `.widths.json` (`advance`), not recomputed at build time.

## 3. Results (medium, default parameters; `report_final.txt`)

* Squeezed to the tile: 19 glyphs `% & @ A C G H K M N O Q T V W X Y m w` (the first five are 5-34 % squeezes, the rest 1-8 %).  Mean advance 0x21-0x7E
  **10.65 px** (original build 10.98 with the old 12 px space).  Advances 3..13 px; 13 px for `# % & @ A B C D G H K M N O P Q R S T U V W X Y m o w`.
* Sample strings, total advance px, original build -> open font: `Mythos Stadium` 160 -> 151, `Cloudy` 68 -> 66, `15:00 KICK OFF` 155 -> 147, `OPTIONS` 80 -> 83
  (capitals are wider than before), `Player Names` 138 -> 127, `Commentary Text` 177 -> 163, `Camera Type` 135 -> 121, `Near/Mid/Far` 131 -> 121,
  `Set this month's advertising budget.` 383 -> 350, `Kasamatsu  Hisanaga  Kanawaki  Narusawa` 463 -> 421, the 64 character line 709 -> 640,
  `Mark Keiji Kijima 23 yrs 3200 man` 364 -> 320.  The 12 sample strings gain 3-11 % except capital-only text.
* Database (146,324 fmt-free display lines): lines wider than 468 px (39 cells) **179 -> 104**, total width **91.4 %** of the original.
  The narrow space (7 instead of 12) is most of that gain (docs/pixel-widths.md says the same: the space is the lever).
* `--hscale 0.9` (all glyphs 10 % narrower before the squeeze): only 8 glyphs squeezed (`% @ A M V W m w`), mean 9.90 px, 62 lines over 468 px, total 82.0 %.  It looks
  noticeably more condensed than the Medium default; not chosen, kept as an option (`--hscale 0.9 --tag _h90`, `build/fontstudy/strips*_medium_h90.png`).

Look (contact sheets: `sheet_medium_final.png` glyph grid with the original row above each new row; `strips1x/2x/4x_medium_final.png` strings, original above
new, both on an assumed dark blue message window (22,34,104) and name-tag green (28,104,58) with white ink; the real colours are not in the repository, so
they are assumptions): the new text is crisper and more regular than the original and heavier than it (the original is thin; Medium matches the weight of a
bold-ish UI face).  Descenders of `g j p q y` are readable tails, parentheses and `,` hang below the line, `1` and `i l` look right, wide capitals `W M m w @` are
condensed but legible.  Weak spots seen: `j` and `g` hooks are 3 rows, `@` is compressed, `W M` stems are noticeably denser, `.` after a letter looks a little
detached (advance 7), digits are on the 12 px pitch so numbers look looser than the letters.  Not seen in the game.

## 4. Can an advance be larger than 12 for a wide glyph?  (checked in the docs)

The advance (pen step) can be anything 1..24 (cave table value, `advance.json` accepts 1..24), but the **ink cannot exceed 12 columns**: the back end draws a
whole 12x24 tile per half-width glyph (`docs/proportional-font.md` s3: "draws whole 12x24 / 24x24 tiles and knows no advance"; `docs/font-widths.md` s2: "the cell/quad
stays 12 px wide because each glyph is still drawn as a complete 12x24 tile").  A larger advance only adds blank space after a 12 column glyph.  Hence wide capitals
stay within 12 columns (advance <= 13).  The only ways to a less squeezed W / M are a smaller global scale (`--hscale`) or a two-tile character (not possible with one byte).

## 5. The build flag

* `build_patch.py --proportional-font on --open-font on` (default `--open-font off`; `--open-font on` without `--proportional-font on` stops with
  `--open-font on needs --proportional-font on`; library: `build_patches(..., open_font=True)`).
* Effect: `fontpatch.make_patches(open_font=openfont.load())`: in the root `/FONT.BIN` and in every copy (`FONT.BIN`, `ATFIRST/FONT.BIN`, `fontpatch.font_copies`) the 94
  slots get the committed glyphs (unshifted: they are already column-0 aligned; katakana slots redrawn via `edit_half.png` are still handled as before), and the 256 byte table at
  `0x8c299900` is the committed table (index 0 and 0x20 = 7, digits 12).  `translation/font/advance.json` overrides are applied on top as before; note that the
  space needs **both** `"0x20"` and `"0x00"` (index 0 is the compiled blank cell) if someone wants to override it.
* With the flag off the output is byte-identical to the build without the keyword (`test_bldflags.py`); with it on exactly three files differ: both FONT.BIN copies and
  the 256 table bytes of `1ST_READ.BIN` (58 bytes actually differ).  No code, cave, hook or overlay changes.
* **Table consumers** (all use the same table while the flag is on):
  * the game itself: the cave at `0x8c299800`, the `align_fix` cave (pw3 / blank-run snap) and the wrap hook read the table at run time;
  * `tools/pixelwidth.py` (used by `tools/refit.py` `check_class`, `transcheck`, `transwork`, `winwidth`, `moneycheck`): the `on` profile (default) was derived from the
    ORIGINAL FONT.BIN; `build_patches(open_font=True)` calls `pixelwidth.set_open_font(True)` for the duration of the build (restored in a `finally`), so the refit forms
    and the 468 px / 39-cell lint of the build measure with the new table (`test_bldflags.py` spies `apply_refit` to prove it).  For standalone tools there is the explicit
    profile `--px-profile open`.  The standalone default stays `on` (old table) until the default build flips.
  * `tools/fontcheck.py` (`sample_table`), `tools/test_patchengine.py` and the older study scripts use `proportional_font()` on the original font: static self-checks of the
    original behaviour, unchanged on purpose.
* **Open questions for the playtest / the owner**: (1) the 7 px space also applies to **pad spaces of padded numeric fields** (`%2d`, `%4d`; skeptic D1 had put the space at 12 for
  that reason): a right aligned number then moves 5 px left per pad space.  If it looks wrong in game, override with `advance.json` (`{"0x20": 12, "0x00": 12}` restores 12 for
  all spaces) or give the space 8; the widths of the whole build change accordingly.  (2) The text sits 0.5 row higher than the original (baseline 21 vs 21.5).
  (3) Refit forms: the table is narrower for lower case and wider for some capitals than before, so a few existing refit forms may be longer or shorter in pixels; rerun the
  refit lint with the flag on before switching the default.

## 6. Reproduce

```
python -I -X utf8 tools/re/font/render_open_font.py --weights medium --tag _final --export translation/fonts   # glyphs + table + sheets + report
python -I -X utf8 tools/re/font/render_open_font.py --weights medium --hscale 0.9 --tag _h90                  # variant
python -I -X utf8 tools/test_open_font.py                                                                      # 176 checks
python -I -X utf8 tools/test_bldflags.py                                                                       # flag off / on
```
Requires Pillow (FreeType) and numpy; the TTF is expected at `build/fontstudy/src/robotocondensed/RobotoCondensed[wght].ttf` (download from google/fonts, `ofl/robotocondensed`;
the committed data stays valid without it, the test notes when the TTF differs from the recorded SHA-256).  Parameters (stored in the JSON): baseline 21, cap 18,
xh 14, hscale 1.0, gamma 1.0, comp 0.5, tight 0.5, snap on.
