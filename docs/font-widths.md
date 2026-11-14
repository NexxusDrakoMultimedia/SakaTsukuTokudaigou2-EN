# Half-width glyph metrics and proportional advance table

> **Status note (docs, 2026-11-11).** The proposal measured here is built: the advance table lives in `tools/fontpatch.py` (`--proportional-font on`, docs/proportional-font.md). The proportional font was played in Flycast up to the `trial_prop3` disc (docs/playtest-log.md, project note on tick marks); the stage-3 discs prop6 / prop6r have not been booted yet.

Status legend: **PROVEN** = measured/decoded by code (script named), **INFERRED** = deduced, **UNKNOWN** = not checked.
Everything here is a measurement of the original `extracted/FONT.BIN` half-width block plus a *proposal*; nothing was tested in the game or an emulator.

Code and outputs:

* `tools/re/font/widths.py` (metrics, advance rule, shifted/narrowed renderers), `widths_report.py` (writes the JSON and prints every statistic quoted below),
  `widths_table.py` (the per-character table), `preview.py` (PNG strips).
* `tools/re/font/widths.json` = **code -> advance in px**, flat map, keys `"0x20"`..`"0x7F"`, `"0xA0"`..`"0xDF"` (160 entries, one per half-width glyph slot / single byte).
  `tools/re/font/widths_meta.json` = the same plus the ink columns, left shift and the rule. Full-width glyphs stay 24 px.
* Previews in `build/font/`: `widths_preview_G1.png`, `widths_preview_G2.png`, `widths_preview_H.png`, `widths_preview_all.png`, `widths_preview_narrow.png`
  (each strip pair: top = original fixed 12 px; the others as labelled below; the dotted tick at the right is the 468 px = 39-cell budget).

## 1. What the 160 half-width glyphs are (PROVEN)

`Font.half()` (`tools/font.py`): 160 raw glyphs, 12x24, 4 bpp, 6 B/row, 144 B each, byte -> index `0x20..0x7F -> 0..95`, `0xA0..0xDF -> 96..159` (`font.half_index`).
Contents confirmed here by dumping the nibbles as ASCII art:

* 0x21-0x7E are real ASCII shapes with upper and lower case, digits and punctuation. Exceptions: **0x5C is a yen sign** (V with two crossbars) and **0x7E is an overline** (a 3-row bar at rows 2-4, not a tilde). No backslash, no tilde.
* 0x20 (idx 0), 0x7F (idx 95) and 0xA0 (idx 96) are blank. 0xA1-0xDF are half-width katakana (all non-blank). `0x20` is a control code to the string compiler (drawn as an empty half cell); the glyph is not fetched.
* Pixel values: nibble 0 = full ink, 15 = paper, all 16 levels used (anti-aliased). "Coverage" below = 15 - nibble.
* Vertical metrics (PROVEN, rows 0-23): cap height rows 3-21 (19 rows), digits rows 3-21, lower-case x-height starts at row 7/8 (14-15 rows), ascenders at row 3, descenders to row 22-23, baseline = row 21. These are tall, large-x-height letterforms.
* The letters are **wide for a 12 px cell**: 50 of the 94 ASCII glyphs have ink in column 0, 57 reach column 11 (any ink), 40 have strong ink (coverage >= 4) in column 11 (`#+4<>?@AEKMOPQRSTVWXYZ\_abcekmopsuvwxyz~`). So on the 12 px pitch these letters touch or nearly touch their neighbours (the `build/font/widths_preview_all.png` top rows show it: `signs`, `striker` look gappy only around i/l/r/t).
* Visual note: `g` is a single-story g with a hooked tail; it is distinguishable from `9` but close at a glance (e.g. "young", "manager" in the previews). Keep in mind for name/number-heavy screens.

## 2. Measurement method (PROVEN, `widths.py`)

For each glyph, per column coverage = max over the 24 rows. "any ink" = coverage >= 1, "strong ink" = coverage >= 4 (a column that is visibly black; fringe columns of coverage 1-3 are the anti-aliasing skirt).
Both bounds are listed in the table below; `faint_l`/`faint_r` (strong minus any) is at most 1 px for every ASCII glyph (max measured 1), so the skirt is never more than 1 column.

Results (all from `widths_report.py`):

* **Left bearing**: 44 of 94 ASCII glyphs have blank columns at the left (any ink): shift 1 px for 24 glyphs, 2 for 4, 3 for 7, 4 for 6, 5 for 3. The glyphs that need a >= 2 px left shift to sit at column 0: `! " ' ( ) , . 1 : ; I ` ` f i l r t { | }`. All of these are narrow glyphs that the font designer centred in the cell.
  Shifting is lossless (a shift left by `any_l` never cuts ink; the right side only gains blank columns).
* **Right side**: 57 glyphs have ink in the last column (col 11), so for them **tightening the advance below 12 would cut ink if it were done by clipping**. The proportional scheme below never clips: the advance is always `>= strong ink end + 2`, and the cell/quad stays 12 px wide because each glyph is still drawn as a complete 12x24 tile; only the pen step changes. Where the advance is smaller than 12 the next tile overlaps the right-hand blank part of the previous tile. That is harmless only if paper texels (nibble 15) are transparent: **INFERRED/UNKNOWN**, it depends on the game's blend state (a half-width glyph is already drawn as a 12 px tile inside a 32x32 texture with an empty remainder, `docs/text-engine.md` section 2, which suggests paper is transparent, but this is not proven). Test: draw `Ii` at 5 px pitch in Flycast (not done: emulator off limits).
* Pair safety (PROVEN by exhaustive check over all 94 x 94 ASCII pairs with the proposed advances): minimum blank gap between the strong ink of two neighbours = **1 px**, and **0 of 8836 pairs** have any-ink (fringe) columns of the left glyph overlapping the right glyph's ink columns.

## 3. Proposed advance rule (INFERRED design, numbers PROVEN for the original glyphs)

1. Draw each glyph shifted left by its `shift` column (so that its leftmost non-paper column is column 0). Two ways: redraw the half block data (raw 144 B glyphs, free to edit; `shift` column in the table), or keep the data and subtract a per-code left-bearing table in the patched layout routine. The data route needs no code beyond the advance patch.
2. `advance = (strong ink right column after the shift) + 1 + G`, with **G = 2 for narrow glyphs (strong ink width < 8 px) and G = 1 for wide ones (>= 8 px)** ("hybrid H"). Result range 5..13 px.
3. **Space = 6 px** (0x20, and also the blank 0x7F / 0xA0). Alternatives: 5 px (avg 9.8 vs 10.0) or 7 px; 6 px reads as a clear word gap in the previews.
4. No kerning pairs; no ligatures. Rules: (a) full-width characters keep 24 px; (b) a wide glyph (`+4<>?@AKMOQRSTVWXYZ\acekouvwxy`, 30 glyphs) gets advance 13 > 12 because it is 12 columns wide (e.g. `A`, `M`, `W`); this is the price of using the existing, wide letterforms; (c) hang/kinsoku flag 0x4000 is unaffected.
5. Digits: proportional (`1` = 8, `0` = 12); for right-aligned number columns use the fixed 12 px (or 13) pitch via the table (set digits to one value and centre `1`), because proportional digits misalign columns. Not needed for running prose.

Uniform alternatives measured (`G` = blank px after the strong ink): **G=1** is too tight for stem sequences (`Illegal little` runs together: see `widths_preview_G1.png`), **G=2 uniform** reads well (`widths_preview_G2.png`) but gives away a third of the gain; **hybrid H** reads as well as G=2 (`widths_preview_H.png`, reading by eye, every sample line legible including `Willie Hill's pill.`, `14:30`, `1,250,000,000`) and is the proposal.

## 4. Room gained (PROVEN for the 605-string sample, `widths_report.py`)

Corpus: `tools/re/capacity/ratio/sample.jsonl`, 605 non-skipped strings, field `en_flat` with `|` read as a space and `@X/` / `=x/` escape codes and `@` terminators removed: 38,426 characters (35,996 in the prose/help categories). **16.1 % of all characters are spaces.** Tokens such as `#tk00`, `%d`, `$1` are counted as literal text (they expand at run time; UNKNOWN length).

| advance model | avg px / char (all) | avg px / char (prose+help) | chars per 468 px line (prose) |
|---|---|---|---|
| fixed 12 (game today) | 12.00 | 12.00 | 39.0 |
| G=1 uniform | 9.84 | 9.77 | 47.9 |
| **hybrid H, space 6 (proposal)** | **10.02** | **9.96** | **47.0** |
| G=2 uniform | 10.68 | 10.61 | 44.1 |
| proposal with narrowed letters (option B, section 6) | 8.84 | 8.81 | 53.2 |

So proportional spacing gives **~17 % less width per character (9.96 vs 12 px, +20.5 % chars per line: 39 -> ~47)**. Decomposition of the 1.98 px/char saving: the space character (6 vs 12 px, 16 % of all chars) gives 49 % of it, glyphs advancing < 12 px (i l I . , ' : ; ! 1 f j r t [ ] | and the 9-11 px letters) give 68 %, and the 13 px wide letters cost back 16 %.
Greedy word-wrap simulation over the prose/help sample (paragraphs split at `|`): fixed 39 chars = 1210 lines, hybrid H at 468 px = **1040 lines (0.86x)**, G=1 1027 (0.85x), G=2 1109 (0.92x), narrowed 955 (0.79x).
For comparison: the existing hand-wrapped English `en` lines (<= 39 chars) average 29.2 chars = 293 px in H and the longest is 422 px, so **every existing line already fits 468 px** with margin; proportional widths only help if the line breaks are re-flowed (they are not worse anywhere). The longest "word" in the sample (a placeholder blob) is 312 px, no single word exceeds the line.

## 5. What 39 cells means in pixels (PROVEN from the engine formula, line limit INFERRED as px)

`docs/text-engine.md` 4.4 (`FUN_8c2de294`): half-width character = 12 px = 1 unit, full-width = 24 px = 2 units; wrap before a character when `(units+1)>>1 > W-1` (and for flag `+0x45 = 0` also at equality). For the default dialogue window W = 20, flag 1: a character is drawn only while `units <= 38`, i.e. at most **39 half cells = 468 px of pen travel (the last glyph's pen at <= 456, its ink end <= 467)**; 20 full-width cells = 480 px is the nominal window width. The 12 px between 468 and 480 is the engine's reserve of one half cell ("last cell free" = `2W-1` rather than `2W`). Window pixel origin x0 = `+0x4a` (0x14 = 20 or 0x90 for MEETING); the visible frame edge was not measured (UNKNOWN), so 468 px is the conservative budget to use, and **a proportional layout must replace the units test by `pen_x - x0 + advance <= 468`** (INFERRED mapping) to keep the same right margin. Other windows: pixel budget = `12*(2W-1)` (flag 1) or `12*(2W-3)` (flag 0), e.g. W = 7 -> 156 px.

## 6. Options and recommendation

* **A. Keep fixed 12 px (zero code).** Cap/lower-case glyphs already have ~0-2 blank columns; legible; 39 chars/line.
* **B. Narrowed redraw (glyph data; pays off only together with C).** Horizontally resample wide glyphs by 0.83 (preview `widths_preview_narrow.png`, bottom row of each pair; boxed filter, preview only): reads legibly but thinner/condensed; at the fixed 12 px pitch it would still be 39 chars/line, so B only pays off together with the advance patch (53 chars per 468 px) or with a 10 px pitch. **UNKNOWN**: a global smaller pitch is not a data change either, because the pitch is `win[0x3e]>>1` = 12 in code, so B needs the same patch as C to pay off.
* **C. Proportional advance patch (recommended).** Needs a 256-entry byte table (index = `code & 0xFF`, **not** `code & 0x7F`: the stored code is `0x8000 | byte` and bytes 0xA0-0xDF would collide with ASCII 0x20-0x5F) and a pixel test instead of the unit test in each overlay's layout routine (`docs/text-engine.md` section 5: MEETING VAs `0x8c2de490-0x8c2de49e` advance and `0x8c2de33a-0x8c2de36a` wrap; identical in 97 of 114 overlays). Gains ~17 % width. The same table also lets the builder compute line widths exactly (lint with `widths.json`).
* The shift-left table can be baked into the glyph data (step 1 of section 3) so only advance + the pixel test are patched.
* Needs an in-game test before relying on it: overlapping 12 px quads at < 12 px pitch (paper-transparency, see section 2), and that half-width glyph drawing uses `x` of the pen directly.

## 7. Per-character table (PROVEN)

Columns: ink columns inside the 12 px cell (0-11) for any ink and for strong ink (coverage >= 4); `shift left` = leading blank columns to remove; `blank right (strong)` = blank columns to the right of strong ink before shift (11 - last strong column); `advance` = proposal H in px. Space (0x20), 0x7F and 0xA0 = 6; katakana 0xA1-0xDF are in the JSON with advances 6-13 computed from their current ink (they are the free slots for accents/symbols; recompute with `widths_report.py` after redrawing).

| code | char | ink cols (any) | ink cols (strong) | shift left | blank right (strong) | advance |
|---|---|---|---|---|---|---|
| 0x21 | `!` | 4-7 | 4-7 | 4 | 4 | 6 |
| 0x22 | `"` | 3-11 | 4-10 | 3 | 1 | 9 |
| 0x23 | `#` | 1-11 | 1-11 | 1 | 0 | 12 |
| 0x24 | `$` | 0-10 | 1-10 | 0 | 1 | 12 |
| 0x25 | `%` | 0-10 | 0-10 | 0 | 1 | 12 |
| 0x26 | `&` | 0-11 | 0-10 | 0 | 1 | 12 |
| 0x27 | `'` | 5-7 | 5-7 | 5 | 4 | 5 |
| 0x28 | `(` | 4-11 | 4-10 | 4 | 1 | 9 |
| 0x29 | `)` | 3-9 | 3-9 | 3 | 2 | 9 |
| 0x2A | `*` | 0-10 | 0-10 | 0 | 1 | 12 |
| 0x2B | `+` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x2C | `,` | 3-6 | 3-5 | 3 | 6 | 5 |
| 0x2D | `-` | 1-9 | 1-9 | 1 | 2 | 10 |
| 0x2E | `.` | 2-5 | 2-4 | 2 | 7 | 5 |
| 0x2F | `/` | 1-10 | 1-10 | 1 | 1 | 11 |
| 0x30 | `0` | 0-11 | 0-10 | 0 | 1 | 12 |
| 0x31 | `1` | 2-7 | 2-7 | 2 | 4 | 8 |
| 0x32 | `2` | 0-11 | 1-10 | 0 | 1 | 12 |
| 0x33 | `3` | 0-10 | 1-10 | 0 | 1 | 12 |
| 0x34 | `4` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x35 | `5` | 0-11 | 1-10 | 0 | 1 | 12 |
| 0x36 | `6` | 0-11 | 0-10 | 0 | 1 | 12 |
| 0x37 | `7` | 0-11 | 1-10 | 0 | 1 | 12 |
| 0x38 | `8` | 0-11 | 0-10 | 0 | 1 | 12 |
| 0x39 | `9` | 0-11 | 0-10 | 0 | 1 | 12 |
| 0x3A | `:` | 4-7 | 5-6 | 4 | 5 | 5 |
| 0x3B | `;` | 4-7 | 5-6 | 4 | 5 | 5 |
| 0x3C | `<` | 0-11 | 1-11 | 0 | 0 | 13 |
| 0x3D | `=` | 0-10 | 1-10 | 0 | 1 | 12 |
| 0x3E | `>` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x3F | `?` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x40 | `@` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x41 | `A` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x42 | `B` | 1-11 | 1-10 | 1 | 1 | 11 |
| 0x43 | `C` | 0-11 | 0-10 | 0 | 1 | 12 |
| 0x44 | `D` | 1-11 | 1-10 | 1 | 1 | 11 |
| 0x45 | `E` | 1-11 | 1-11 | 1 | 0 | 12 |
| 0x46 | `F` | 1-10 | 1-10 | 1 | 1 | 11 |
| 0x47 | `G` | 0-10 | 1-10 | 0 | 1 | 12 |
| 0x48 | `H` | 1-10 | 1-10 | 1 | 1 | 11 |
| 0x49 | `I` | 4-6 | 4-6 | 4 | 5 | 5 |
| 0x4A | `J` | 1-7 | 1-7 | 1 | 4 | 9 |
| 0x4B | `K` | 0-11 | 1-11 | 0 | 0 | 13 |
| 0x4C | `L` | 1-10 | 1-10 | 1 | 1 | 11 |
| 0x4D | `M` | 0-11 | 1-11 | 0 | 0 | 13 |
| 0x4E | `N` | 1-10 | 1-10 | 1 | 1 | 11 |
| 0x4F | `O` | 0-11 | 1-11 | 0 | 0 | 13 |
| 0x50 | `P` | 1-11 | 1-11 | 1 | 0 | 12 |
| 0x51 | `Q` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x52 | `R` | 0-11 | 1-11 | 0 | 0 | 13 |
| 0x53 | `S` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x54 | `T` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x55 | `U` | 0-10 | 1-10 | 0 | 1 | 12 |
| 0x56 | `V` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x57 | `W` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x58 | `X` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x59 | `Y` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x5A | `Z` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x5B | `[` | 1-7 | 2-6 | 1 | 5 | 8 |
| 0x5C | \ (yen glyph) | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x5D | `]` | 0-5 | 0-5 | 0 | 6 | 8 |
| 0x5E | `^` | 1-11 | 1-10 | 1 | 1 | 11 |
| 0x5F | `_` | 1-11 | 1-11 | 1 | 0 | 12 |
| 0x60 | ` (grave) | 3-6 | 3-5 | 3 | 6 | 5 |
| 0x61 | `a` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x62 | `b` | 1-11 | 1-11 | 1 | 0 | 12 |
| 0x63 | `c` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x64 | `d` | 0-10 | 0-10 | 0 | 1 | 12 |
| 0x65 | `e` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x66 | `f` | 3-10 | 3-9 | 3 | 2 | 9 |
| 0x67 | `g` | 0-11 | 1-10 | 0 | 1 | 12 |
| 0x68 | `h` | 1-11 | 1-10 | 1 | 1 | 11 |
| 0x69 | `i` | 5-8 | 5-7 | 5 | 4 | 5 |
| 0x6A | `j` | 1-7 | 1-7 | 1 | 4 | 9 |
| 0x6B | `k` | 0-11 | 1-11 | 0 | 0 | 13 |
| 0x6C | `l` | 5-8 | 5-7 | 5 | 4 | 5 |
| 0x6D | `m` | 1-11 | 1-11 | 1 | 0 | 12 |
| 0x6E | `n` | 1-11 | 1-10 | 1 | 1 | 11 |
| 0x6F | `o` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x70 | `p` | 1-11 | 1-11 | 1 | 0 | 12 |
| 0x71 | `q` | 0-10 | 0-10 | 0 | 1 | 12 |
| 0x72 | `r` | 3-10 | 3-9 | 3 | 2 | 9 |
| 0x73 | `s` | 1-11 | 1-11 | 1 | 0 | 12 |
| 0x74 | `t` | 2-9 | 2-9 | 2 | 2 | 9 |
| 0x75 | `u` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x76 | `v` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x77 | `w` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x78 | `x` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x79 | `y` | 0-11 | 0-11 | 0 | 0 | 13 |
| 0x7A | `z` | 1-11 | 1-11 | 1 | 0 | 12 |
| 0x7B | `{` | 3-10 | 4-9 | 3 | 2 | 9 |
| 0x7C | \| | 4-7 | 5-7 | 4 | 4 | 6 |
| 0x7D | `}` | 2-8 | 2-8 | 2 | 3 | 9 |
| 0x7E | ~ (overline glyph) | 1-11 | 1-11 | 1 | 0 | 12 |

