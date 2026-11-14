<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Third-party notice: fonts

The opt-in build flag `--open-font on` (docs/open-font.md) replaces the 94 ASCII half-width glyphs (0x21-0x7E) of the game's `FONT.BIN` by
bitmaps rendered from **Roboto Condensed Medium** (variable font, wght 500).

* Font: Roboto Condensed, Copyright 2011 The Roboto Project Authors (https://github.com/googlefonts/roboto-classic).
* Source of the font file used for rendering: github.com/google/fonts, `ofl/robotocondensed/RobotoCondensed[wght].ttf` (its SHA-256 is recorded in
  `translation/fonts/robotocondensed_medium_12x24.widths.json`).  The TTF is **not** part of this repository or of a release.
* Licence: SIL Open Font License, Version 1.1 (SPDX `OFL-1.1`), full text in `LICENSES/OFL-1.1.txt`.
* What was changed: the outlines were rasterised at 16x supersampling, scaled so that the capital height is 18 rows, grid fitted (baseline, x-height,
  stem edges on pixel boundaries), glyphs wider than the 12 px tile were squeezed to 12 columns (with a heavier weight to keep the stroke thickness),
  descenders compressed into three rows, and the result was stored as 12x24 4-bit bitmaps (`translation/fonts/robotocondensed_medium_12x24.bin`,
  generator `tools/re/font/render_open_font.py`).  These bitmaps are a derivative of the font and are licensed under the OFL-1.1 as well.
* The bitmaps reach players only as bytes of `FONT.BIN` inside the xdelta patches; the release bundle carries this notice (as part of `NOTICE.txt`)
  and `LICENSES/OFL-1.1.txt`.  The font is not sold on its own and no Reserved Font Name is used (the upstream metadata lists none).
