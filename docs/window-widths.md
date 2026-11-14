# Text window widths (per window class line width and rows)

Status words as in docs/font-hook-notes.md: **PROVEN** = read from code / RAM dump / data with an address or a count,
**INFERRED** = follows from proven facts, **UNKNOWN**.  Nothing here ran an emulator; the RAM dumps in `build/emu/` were
only read.

Playtest finding 3: "With this club, any dream can com/e" and "I can't possibly bear such a heav/y" wrapped in the middle of a
word.  Both lines are 34 characters; both strings are drawn in a **17-cell speech bubble that holds 33**.  The validator
assumed 39 for every window.  This note says which width belongs to which string and what the tools now enforce.

## 1. Geometry (PROVEN)

The layout function (docs/font-hook-notes.md s3.3) wraps by *units* (1 per half-width glyph, 2 per full-width glyph).  For a window
with `W = win[0x3c]` cells and the "last cell free" flag `win[0x45] = 1` (every standard window) a glyph is placed while
`units <= 2W-2`:

| W | half-width glyphs per line | full-width (Japanese) per line | note |
|---|---|---|---|
| 17 | **33** | 17 (34 cells) | speech bubble |
| 20 | **39** | 20 (40 cells) | message window |
| 25 | 49 | 25 | slide-in windows seen live at x=656 (off screen), UNKNOWN use |

The wrap is by count, independent of the advance (`win[0x3e]` = 24 / 32 ...), and there is **no word wrap and no clipping**: the
34th character of a W = 17 window is drawn as the first character of the next row; with only `rows` rows of background art
the third row falls out of the box.  `rows = win[0x3d]` is only the box height; the layout function does not stop at it.
In the proportional-font build (docs/proportional-font.md) the same limit is applied in pixels: `(2W-1) * 12 = 396 px` for W = 17,
468 px for W = 20 (`docs/font-widths.md` s5); the cell counts of this note are the monospaced equivalent and stay the conservative rule
(an English line of at most 33 monospaced cells is at most 396 px in the proportional font, because no glyph is wider than 12 px).

## 2. The window classes

Every overlay links the same tsString window library (105 copies) and the same *factories*: constructors that allocate a window and
store its geometry.  Static scan of the 116 FLOW_PRG / ATFIRST images (`tools/re/font/winmap.py`, `cellstores.py`;
table `tools/winwidth_overlays.tsv`; PROVEN as code facts):

| factory | cells / rows / advance / line height | where | meaning |
|---|---|---|---|
| A  | 20 / 3 / 24 / 23, x = 144 (`r3 + 120`) | 99 overlays (`msg_20x3 = yes`) | message window next to the portrait: the secretary pictures in `build/emu/live_msgs.png`; live in `pt1_ram.bin` at (144, 379) with 72 and 89 codes |
| B  | **17 / 2 / 24 / 24**, x from an argument | 70 overlays (`bubble_17x2 = yes`; 46 have none) | the speech bubble; one live copy in `t1_ram.bin` (obj 0x8cb5c500, x = 96, y = 800) |
| C  | 20 / 3 / (set by caller) / 24 | every overlay with a library | bottom window at (20, 240) and the many list-cell copies: live dumps show 20x3 objects at 20 different (x, y) holding 5-20 codes each (Event list columns at x = 120 / 496), so for list cells **W says nothing about the cell width** |
| other | W = 8 (DRAFT), 9 (YOUTH), 10 (GAME, rows 1), 21 (SPF_READ), 2, 5, 0, 1 | 1-2 overlays each | lists / name cells; adv 10 (SCDRF, SEARCH), 16 (BPMATCH, DRS*), 32 (NEWS ticker), 48 (SCDRF, SEARCH): the wrap count does not change with the advance |

No-bubble overlays (46, e.g. HELP, OPTION, G_INCOME, G_RESULT, SPF_READ, TOWN, DRSGRF*, ENDING, FLOW1-11, GMSHOW*, AUTOSAVE,
NEWMONTH) can only show 20-cell text windows.  Overlays without any font slot (OFFICE, TITLE, WEEKLY, BPMWEEK, LOGO, LOADBAR,
FACEMDUL, MOVIE*) draw their text by a path nobody has resolved (UNKNOWN, docs/font-hook-notes.md s4.3); GAME.BIN has its own text
engine with `cmp/ge #37 / #39` glyph limits (UNKNOWN, s6 there).  They fall back to the Japanese rule below.

## 3. Which string goes to which window

### 3.1 What could not be done, and why (PROVEN negative result)

The link string -> window is not in the code of the overlays.  Dialogue text is reached through pointer tables (ctx `tbl@OFF[i/n]`)
whose entries are copied into script / state-machine structures (MEETING: `0x8c2d4314` copies the table pointers into a record
array at `+0x578 / +0x8d0`; the displaying code lives elsewhere), and the window is made by a different function than the one that
touches the table.  A call-graph reading ("the function that loads the table, or its callees / callers, calls factory B or A",
`tools/re/font/wresolve.py`, `wresolve_all.py`, result `build/trans/width_refs.json`) resolves 75 of the pointer tables
(`tools/winwidth_tables.tsv`: 45 reach only factory A, 15 only B, 15 both), but it contradicts the data: the tables whose loader
reaches only the 17x2 factory contain **1070 strings with three lines and 42 with a line wider than 34 cells** (DRAFT `tbl@1fe04`:
869 three-line, 40-cell texts), which cannot be shown in a 17x2 window.  So a factory call near a table is a statement about the
*overlay*, not about each string, and is used only in the two ways listed in 3.2 where it can not mislead.

### 3.2 The rule (the Japanese author fitted every string to its window)

A string is drawn in a window that holds the author's Japanese: 2 cells per full-width character, hand-placed `\n`.  The Japanese
therefore gives a lower bound for the window, and its *distribution* (the author fills lines up to the window width) tells the cap.
Evidence from windows resolved above, PROVEN as counts: MEETING `tbl@24d78` (6272 strings) has 5838 two-line strings whose widest
line is **never above 34 except 3 times**, 511 of them exactly 34 and 1380 in 32-34; `tbl@23668` the same (1087 two-line strings, 2 above 34,
173 at 34).  Three-line strings of the same tables reach 40.  Two-line texts written for a 39-cell window would pile up at 36-40.
The 34 is exactly 17 full-width characters, the width of factory B, and 40 is exactly factory A.  In the two tables that
the user's playtest hit (FIRE `tbl@1be20`, CAP_SLCT `tbl@1e18c`, both resolved to factory B above) 197 of 210 and 22 of 30 strings are
two-line / <= 34.

Rules, in order, first match wins (`tools/winwidth.limits`; the `basis` column of `width_classes.tsv`):

| basis | condition | class | max_cells | max_rows |
|---|---|---|---|---|
| `tbl-msg` | the table's loader reaches only factory A (45 tables, 154 records) | MSG20x3 | 39 | 3 |
| `ja-3rows` | Japanese has >= 3 lines (only 20x3 windows have three rows) | MSG20x3 | 39 | max(3, lines) |
| `ja-wide` | a Japanese line is wider than 34 cells (the window is wider than 17 cells) | MSG20x3 | 39 | max(3, lines) |
| `ovl-no-bubble` | the overlay has no 17x2 factory | MSG20x3 | 39 | 3 |
| `tbl-bubble` | the table's loader reaches only factory B | BUBBLE17x2 | **33** | **2** |
| `ja-fit` | everything else that is prose: <= 2 lines, every line <= 34 cells; bubble or message window cannot be told apart | BUBBLE? | **33** (conservative) | 2 |
| `cell` | not prose: label, numunit, name, place, tactic | CELL | 39 default | JA lines |
| `browser` | MESSAGE.INI / 2_DP.BIN HTML text | BROWSER | none | none |

Prose = categories dialogue, meeting, event, training, news, system, dataroom, help of `transwork.classify`.  The strictest limit over all
records of a distinct text (`winwidth.merge_limits`) is the item's limit, because one English string is written to all of them.
The 39 default is used **only** where the 20-cell window is shown by `tbl-msg`, `ovl-no-bubble` or by the Japanese itself (three rows,
a line > 34 cells); everything else that can be a bubble gets 33.  CELL strings keep 39 because their real limit is the column of
the screen layout, not a window (live: 20x3 objects at 20 different origins); they are bounded by `budget_fixed` and by finding 4 of
the playtest (clipped names, column overflows), a separate task.

Counts over the 126,273 records (`python -I -X utf8 tools/winwidth.py classes`, `build/trans/width_classes.tsv`):
CELL 100,610; BUBBLE? `ja-fit` 11,544; MSG `ja-3rows` 11,129; MSG `ja-wide` 925; BUBBLE17x2 `tbl-bubble` 696; MSG `ovl-no-bubble` 209;
MSG `tbl-msg` 154; BROWSER 1,006.  `width_tables.tsv` has the same counts per source table.

Limits of the rule (INFERRED, not proven): a two-line / <= 34 string that is really drawn in window A (39) is held to 33 and shows
up as a violation although it would fit; the repair stage then rewrites a string that needed no change.  That is the price of
"conservative"; the flagged cases are the `BUBBLE?` rows of the violations list and can be cleared by one emulator observation of the
table in question (section 6).  Single-line strings of prose categories are treated like the two-line ones.  `max_rows` for BUBBLE is 2:
three English rows leave the box (INFERRED from the 2-row factory; not looked at on screen).

## 4. Tools and files

| item | what |
|---|---|
| `tools/winwidth.py` | the rule (`limits`, `merge_limits`), `classes` (writes `build/trans/width_classes.tsv`, `width_tables.tsv`), `violations` (writes `build/trans/width_violations.tsv`) |
| `tools/winwidth_overlays.tsv`, `tools/winwidth_tables.tsv` | static evidence (committed data), regenerated by `tools/re/font/wresolve_all.py` + `winclasses.py` |
| `tools/re/font/winmap.py`, `wresolve.py`, `wresolve_all.py`, `winclasses.py`, `cellstores.py`, `disov.py`, `findlit.py` | SH-4 scan: window factories, call graph, pool-literal loads; `disov.py OVERLAY lo hi` disassembles a range |
| `tools/transwork.py` | every shard item now has `max_cells`, `max_rows`, `wclass` (item fields appended; keys, shard numbers and order unchanged: `build/trans/results/*` still match their shards, checked for all 259 result files) |
| `tools/transcheck.py` | `LINE_TOO_WIDE` / `PUNCT_AT_EDGE` use `item.max_cells` (39 when absent: old shards keep working); `TOO_MANY_LINES` allows `--extra-lines` only up to `max_rows` |
| `tools/test_transwork.py` | new block `window width` (574 checks pass); the real-database fixture now blanks its two fixture texts in the copy (the real database is translated, the old fixture assumed it was empty) |

Re-run after any new extraction or translation merge: `python -I -X utf8 tools/transwork.py plan` (the plan does not read `en`), then
`python -I -X utf8 tools/winwidth.py violations`.

## 5. The repair list `build/trans/width_violations.tsv`

Every merged English text (27,565 texts have `en`) whose lines exceed its window.  **1,846 texts (2,828 records)** are over:
1,668 in tier A (area meeting 1,161, menus 412, new_game 90, save_load 4, title 1), 161 in tier B, 15 in tier C; by overlay MEETING 1,161,
LOCAL 139, DRAFT 129, EVENT 85, SCDRF 70, NEWCON 53, NEWS 50, RECON 38; 137 of them are in tables proven to be bubbles (`BUBBLE17x2`,
includes the two playtest strings), the other 1,707 are `BUBBLE?` (33 by the conservative rule).  By overshoot: 1 cell 532, 2 cells 475,
3 cells 376, 4 cells 274, 5+ cells 187; 1,634 would wrap into more rows than the window has.  Columns: rank, visibility tier
(A = title, new game, save/load, menus, meeting; B = news, event, training, help, match UI; C = the rest), shard, key, id0, area, category,
class, max_cells, max_rows, basis, records, en_lines, ja_lines, widest, over_by, wrapped_rows, en, ja.  Rank = tier, then the plan order
(what the player meets first); `shard` and `key` are the plan's, so a repair run can go shard by shard
(`transwork.py prompt N` already carries `max_cells`).  No translation was edited.

## 6. Verification that needs the emulator (UNKNOWN, for the user's next run)

* One MEETING two-line string of 34 cells in the Event / meeting room: does it wrap at 33 (bubble) or fit (window A)?  A hit on either
  side moves a whole table (`ja-fit` rows of MEETING `tbl@24d78`, `tbl@23668`: 6,925 two-line strings).
* A three-row English text in a bubble: where does the third row land?
* NEWS ticker (adv 32 windows): the 1-line headlines `tbl@acd18` (402 strings) are held to 33 by `ja-fit`; the ticker may hold 39.
* GAME.BIN's own engine (37 / 39 glyph limits) and the no-font-slot overlays: not covered by this rule.
