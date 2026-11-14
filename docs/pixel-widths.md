# Pixel widths: the line-width rule for the proportional font

> **Status note (docs, 2026-11-11).** The sentence "still unproven in the game" is out of date for the font hooks themselves (a proportional trial disc was played); what is still unproven is everything added since, for example `--prop-scale` (docs/patch-engine.md section 4). The checklist for the next session is docs/playtest-checklist.md.

Status words as in docs/font-hook-notes.md: **PROVEN** = computed by code in this repository, **INFERRED** = follows from proven facts, **UNKNOWN**.
Nothing here ran an emulator; the proportional font hooks (docs/proportional-font.md) are still unproven in the game.

The validator counted glyph cells (33 per speech bubble, 39 per message window, docs/window-widths.md).  With the proportional font patch
(`build_patch.py --proportional-font on`) the real limit is in pixels.  The tools now have a pixel mode driven by the same advance table the build writes.

## 1. The rule (INFERRED from the hook H2, docs/proportional-font.md s4.3)

The cave wraps when `pen - x0 > A*(W-1)` with A = 24 and W = 17 (bubble) or 20 (message window).  A glyph is drawn when its pen **start** is at most
384 px (bubble) / 456 px (message window), i.e. `12*(max_cells-1)`.  A line therefore fits iff

    sum(advance of every glyph except the last) <= 12 * (max_cells - 1)

The nominal pen travel `12*max_cells` (396 / 468 px, docs/font-widths.md s5) is the same rule seen from the end; the last glyph may be 13 px wide, so a
fitting line can end 1 px beyond 396 / 468 (inside the engine's 12 px "last cell free" reserve).  When every advance is 12 px the rule is exactly
`cells <= max_cells` (profile `off`, checked by the tests for 1..44 glyphs in both windows).  The game has no word wrap: a line that does not fit breaks
in the middle of a word, the rest starts a new row (`wrap_rows`).  The punctuation-edge rule (PUNCT_AT_EDGE) belongs to the cell model only: in pixel mode
any glyph that starts inside the window is drawn.

## 2. Profiles (`--px-profile`)

| profile | table | use |
|---|---|---|
| `on` (default) | `fontpatch.proportional_font()` on `extracted/FONT.BIN` plus `translation/font/advance.json` overrides: what the build writes with `--proportional-font on`.  ASCII 5..13 px, digits 12, **space 12** (skeptic D1: padded numeric fields keep their pitch), 12 where no rule | the real profile |
| `ideal` | `tools/re/font/widths_meta.json`: the same glyphs, space 6 px (docs/font-widths.md hybrid H) | what a narrow space would buy |
| `off` | 12 px everywhere | identity check: pixel mode == cell mode |

Advances of `on` (`python -I -X utf8 tools/pixelwidth.py table`): 5 px `' , . : ; I ` i l`; 6 `! |`; 8 `[ ]`; 9 `" ( ) J f j r t { }`; 10 `-`; 11 `/ B D F H L N ^ h n`; 12 space, digits
and `# $ % & * = C E G P U _ b d g m p q s z ~`; 13 `+ < > ? @ A K M O Q R S T V W X Y Z a c e k o u v w x y`.  Note the 13 px group: lower case `a c e k o u v w x y`
and capitals are wider than the old 12 px cell, so text heavy in those letters can be wider in pixels than in cells.

## 3. Dynamic tokens: worst case, never the average (`tools/pixelwidth.py`)

| token | cells (translib.WIDTH_SUBST / `_fmt_cells`) | charged |
|---|---|---|
| `#sname#`, `#tkNN#` (names) | 10 | 10 x 13 px = 130 |
| other `#xxx#` | 8 | 8 x 13 px = 104 |
| `%s` or explicit `%Ns` | 8 / N | 13 px per cell |
| `$N` | 6 | 13 px per cell |
| `%d` 3, `%D` 6, `%m` 15 (jp money style), `%f` 6, `%x` 4, explicit `%5d` | | 12 px per cell (digits are fixed 12 px; sign, comma and space are <= 12) |
| `%%` | 1 | the `%` glyph |
| `@Y/ @ =K/ =`, raw `<XX>` | 0 | 0 |

13 px is the widest advance in the table, so a name of 10 wide letters cannot exceed the charge.  The consequence: a line with a name token is charged **10 px
more** than the cell rule charged it (130 vs 120), so pixel mode is not strictly more lenient.  With tokens at 12 px per cell 16 more of the historic 1,846 texts would pass (1,179 instead of 1,163);
the worst case was kept on purpose.  Fixed-column strings (`wclass` CELL: labels, names, numunits) must pass the cell rule as well: their window is not known to use the hook (section 6).

## 4. Tools

| tool | what |
|---|---|
| `tools/pixelwidth.py` (new) | table (`get_table`), `advances`, `check_line`, `fits`, `wrap_rows`, `wrap_text` (greedy word wrap in cells or pixels), CLI `table | width TEXT | wrap TEXT CELLS` |
| `tools/transcheck.py` | `--width-mode cells|pixels` (default cells), `--px-profile`; `check_text(item, en, extra_lines=0, width_mode='cells', px_profile='on')`, `check_result(..., width_mode, px_profile)`; same error code `LINE_TOO_WIDE` with `width` / `start` / `max_px` / `over_px`; PUNCT_AT_EDGE only in cells mode; item `max_cells` is converted (`max_px = 12*max_cells`), shards need no new field |
| `tools/transwork.py` | `prompt N --width-mode pixels [--px-profile]`: rule 4 speaks pixels (advance table, token charges, `wrap` helper) and each item carries `max_px`; `show N --width-mode pixels` prints max_px.  Default output of both is unchanged (rule 4 is `RULE4_CELLS`, a verbatim copy); `plan` and the shard files are untouched |
| `tools/winwidth.py` | `violations --width-mode cells|pixels|both` (cells default writes `width_violations.tsv` as before, pixels writes `width_violations_px.tsv`, always prints the cells-vs-pixels comparison); `recheck LIST.tsv` re-measures any cell-format list in pixels without a database; `wrap TEXT CELLS [--width-mode]` proposes line breaks; library `check_en_px` |
| `tools/test_transwork.py` | new block `pixel width` (table, identity, 30 / 36 / 77-glyph boundaries, tokens, transcheck, wrap, recheck, prompt) |

There was no word-wrap code in the repository before; `pixelwidth.wrap_text` is the first (greedy at spaces, existing newlines kept, a word wider than the window gets its own line).

## 5. Results

### The 1,846-text violation list of docs/window-widths.md s5 (measured with its own English, kept as `build/trans/width_violations_1846_cells.tsv`)

| pixel profile | disappear | remain |
|---|---|---|
| `on` (the build, space 12) | **1,163 of 1,846 texts (1,873 of 2,828 records)** | 683 texts (955 records): tier A 582, B 95, C 6; 44 are in proven bubble tables, 639 `BUBBLE?` |
| `ideal` (space 6) | 1,800 | 46 |
| `off` | 0 | 1,846 (identity) |

The remainder is `build/trans/width_violations_1846_px.tsv` (columns as `width_violations_px.tsv` below; `in_cell_list` = yes).  Overshoot of the remainder in px: 1-5 px 168 texts, 6-10 px 119, over 20 px 209 (the rest
in between).  **The space is the lever**: the build keeps the space at 12 px (skeptic D1), so almost all of the room that narrow letters give is eaten by spaces.  Other space widths over the same list:
10 px 1,486, 9 px 1,607, 8 px 1,691, 7 px 1,763, 6 px 1,800 disappear.

### The current translation database (34,137 merged texts)

The database was edited after the 1,846 list was made (the repair stage fitted the texts to the cell rule): **`build/trans/width_violations.tsv` is now empty (0 texts over the cell rule)**.
`build/trans/width_violations_px.tsv` has **27 texts (32 records)** that are over only in pixel mode (`in_cell_list = new`): tier A 4, tier B 23; 26 of the 27 carry `#tk` / `#sname#` / `%f` tokens (the worst case charge,
over by 1-15 px, e.g. `@Y/#tk20#@ has decent kick accuracy but ...`), one has `%f %f`, and one plain line is over by 2 px ("My head and body are out of sync,\nsomehow..." 391 px, 33 cells).  Rewriting them is the
later stage's job (nothing was rewritten here).  Columns of `width_violations_px.tsv`: rank, visibility, shard, key, id0, area, category, class, max_cells, max_rows, basis, records, en_lines, ja_lines,
widest_px, max_px (nominal 12*max_cells), over_px (px by which the last glyph starts beyond 12*(max_cells-1)), wrapped_rows (engine break), widest_cells, in_cell_list, en, ja.

Regenerate: `python -I -X utf8 tools/winwidth.py violations --width-mode both` (about 9 s).

## 6. What is not proven (UNKNOWN, for the next emulator session)

* The H1/H2 hooks have not run in the game (docs/proportional-font.md s7): the whole pixel rule is the model of the cave, verified only by the simulator, not on screen.  Until the font patch is switched on the cell mode remains
  the rule for the shipped build (default of every tool).
* Windows with advance 16 / 32 / 48 / 10 (lists, the news ticker) keep fixed 12 px steps: a text drawn there does not get the proportional benefit.  `BUBBLE?` / news strings are measured as if proportional.
* Centred and right-aligned columns (name entry, menus) assume 12 px per character (docs/proportional-font.md risk 8).
* A line that ends exactly at the limit has its last glyph up to 1 px beyond 396 / 468 px.

## 7. Proposals

1. Decide the space width with one in-game look at a padded numeric field (`%2d`, `%4d`, skeptic D1): a 6-8 px space would clear 1,691-1,800 of the 1,846 historic violations and is the single biggest gain; keep the 12 px
   pad only where the pad is a literal run of spaces in front of digits (e.g. override per field, or leave digits to a 12 px `0x20` variant).  `translation/font/advance.json` {"0x20": 8} is read by the build and by every tool here.
2. The later text stage should reflow with `winwidth.py wrap` / `pixelwidth.wrap_text` (profile `on`) instead of rewriting words: most of the 683 remaining texts are lines 1-20 px over that a different break fixes.
3. After the font patch is proven in the game, switch the default of `--width-mode` to `pixels` in `transcheck` and the translator prompt, and drop the 33 / 39 cell wording from the style guide.
