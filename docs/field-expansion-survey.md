# Field expansion survey: which fixed limits cut English text, and which can be widened by a generic patch

Design study of 2026-11-13 (stage 9e).  Nothing was booted, no disc built, nothing under `tools/` or `translation/` edited; the numbers come
from the extracted overlays, the translation database, the SH-4 listings of `tools/re/aln_dis.py` and a handful of throw-away scripts (kept in
the session scratchpad, named in section 9).  Status words as in `docs/font-hook-notes.md`: **PROVEN** = read from bytes / data with an address or
a count, **INFERRED** = follows from proven facts, **UNKNOWN** = needs a measurement (the cheapest one is named).

Question (user, after the `prop10e` playtest): "if we can figure out how to expand fields and such, that would be great".

**Skeptic review (same day, stage 9e-s): read section 0a first.**  It lists what was re-read from the bytes of `build/trial/prop10e`, the errors found, and which
items are safe to implement next.  Corrections were also made in place and are marked **[skeptic]**.

## 0. Answer in one screen

1. **The text engine does not clip.**  `tsString` (105 library copies) wraps by count / pixel and never cuts (`docs/font-hook-notes.md` 3.3, 5).
   A window width `W` (`+0x3c`) only moves where a line wraps.  So "expanding windows" cures no visible clip by itself; the visible cuts in
   the playtest are **sprite overlap or UV tightness (name tags, plates, HOME/AWAY), per-cell column limits of GAME's bitmap text (OPTIONS rows),
   and padded or counted fields**.  This is why five of the eight visible cuts have different causes (table in section 1).
2. **Widening is possible for three families with a same-size, signature-located patch**, the pattern already shipped for `scout-fix`
   (2 overlays), `tag-fix` (11), `club guard` (20) and `align-fix` (3 + 1): (a) name-tag geometry (icon / strip offsets, window `W = 2`),
   (b) UV and quad widths of text-on-plate sprites (texture has spare columns; measured for the pre-match menu column), (c) GAME's bitmap-text
   cells.  Struct fields (14-byte names, club name, 92 / 288 / 56 / 30 byte records) **cannot** be widened in place; they stay display-side problems
   (`docs/expansion/field-widths.md`).
3. **Cheapest cure of all is text:** the in-match OPTIONS rows are cut exactly at the Japanese byte length of their cell (label 16, value 14,
   INFERRED from 0xc0 = 192 px and the screenshot); `Commentary Text` / `Near/Mid/Far` fit if written with one blank less.
4. **The Roboto Condensed swap barely moves overflow.**  The current proportional table already has narrow `i l` and averages 11.2 px per
   family-name letter; Roboto Condensed at the cap height under test (26 px) averages 11.2 as well, at 24 px 10.7.  It cures at most 4 to 5 % of
   width, none of the eight visible cuts completely (section 6).  The art plates are not affected by the font at all.

Ranked plan (value = visible cuts cured / risk; details in section 7):

| rank | item | cures (of the eight visible cuts) | risk | needs |
|---|---|---|---|---|
| 1 | OPTIONS row strings into the 16 / 14 character cells (data only) | `Commentary Tex`, `Near/Mid/F` | none | text edit, 3 records |
| 2 | **[skeptic] 2a: lineup tags by `TAG_LIMIT` 5 for GAME / TRAINING (SAFE); 2b: tag geometry patch (NOT ready: icon constant unproven, no FPU sim, neighbour collision)** | lineup tags `Kasam t`, `Hisan`, `Kanaw` (10 tags per lineup screen) | 2a low; 2b medium | 2a: one immediate per overlay; 2b: FPU-capable sim or RAM dump, then a bisectable disc |
| 3 | Pre-match menu plates: repaint to <= 91 px (UV widening dropped, 0a C6) | `View Teamwork`, `Opponent Info` | none | art regeneration |
| 4 | **[skeptic] do not do now**: generalise `pw3` (right-anchor) to the `(N - len) * 12` idioms | none (the crowd cut has another cause, 9d) | medium to high | bisectable disc + per-idiom proof |
| 5 | HOME / AWAY plate `efend` = `sakusen` texture repaint | `efend` | none (art) | injector path for the VQ member |
| 6 | GAME second text engine: advance immediates 12 / 24 + 37 / 39 line counter | none of the eight (BCAST subtitle quality) | medium to high | two immediates, one cave routine |
| 7 | Window width tables (`W`) | none (proved: 0 of 5,321 names exceed a 7-cell cell in the proportional font) | low | only for the plain-font build |
| 8 | Widen struct fields (names, club, records) | none | very high | not recommended |

## 0a. Skeptic review (stage 9e-s): what was checked, what was wrong, what is safe

Method: the 115 overlays of `build/trial/prop10e` were read back from the disc (`FLOW_PRG/*.BIN` + `1ST_READ.BIN`, scratch `p10e/`), listings with `tools/re/aln_dis.py`,
the survey's `w2.py` / `w3.py` / `nm1.py` / `pl1.py` re-run, screenshots 100 and 101 re-read.  Nothing was booted, built or edited outside this file.

**Re-verified from bytes (PROVEN, 12 items).**

| # | claim | result |
|---|---|---|
| 1 | TRAINING `0x33d66`: `mov #2,r1 ; mov #60,r0 ; mov.b r1,@(r0,r3)` in the task `0x33d54` (obj `+0x30` -> `+0x20` window), then `0x8c388080` -> `0x8c2e8000` | yes, bytes identical in prop10e |
| 2 | CAP_SLCT `mov #7,r10` at `0x79e0`, `mov #7,r8` at `0x7d0a` (spacing `0x32a`); 11 overlays x 2 loads, each followed 0x30 bytes later by the `mov #60` store (`w3.py`: ABROAD `0x94b0` / `0x97da`, ...) | yes (22 halfwords) |
| 3 | EXTRADE `0x2eec` W = 25 (`mov #25,r11` at `0x2ea6`, base `0x8c4d0000`, slot offsets `0x208` / `0x20c`) | yes |
| 4 | GAME line engine: `mov #12,r0 ; mov.b r0,@(1,r2)` at file `0x5049e`, `mov #24,r1 ; mov.b r1,@r2` at `0x504c6`, `cmp/ge #37` at `0x50342`, `cmp/ge #39` at `0x50352`, `mov #82,r4` at `0x50330` | yes |
| 5 | GAME bitmap text `0x641d0`: `cmp/ge r2,r12` with `mov #40,r2` at `0x6424a` / `0x6424c` (the survey also printed `0x8c334248` in 2.2: that is the `bt`, **fixed**) | yes |
| 6 | OPTIONS builder `0x2f29e`: r11 = `0x8c3341d0`, label call x = 0 (`mov r7,r4`), value call x = `0xc0` (`mov.w ... =0xc0,r9 ; mov r9,r4`), y `+= 44`, entry stride 8 (`shll2 ; shll`), value call only when `@(4,entry)` is non-zero | yes |
| 7 | Japanese byte lengths of the OPTIONS records: every label 16 bytes (`  実況テキスト  `), every value 14 (`    近・中・遠`) | yes, from the original `GAME.BIN` |
| 8 | G_INCOME has 6 `* 12` idiom hits with a `+74` store (`0x234 0x276 0x382 0x498 0x4d2 0x1980`), SPONSOR 5, SPONSOR2 5 (`aln_scan12.py`) | yes |
| 9 | TRAINING float pool `c1c00000` (-24.0), `c2400000` (-48.0), `3a83126e` | yes, but see C3 (two copies, the range between is CODE) |
| 10 | `nm1.py`: 0 of 5,321 `player` names have a start-of-last-glyph above 144 px, widest total 153 px | yes, but only the BPINFO `player` names, see C5 |
| 11 | `w2.py`: 495 stores, 148 unresolved, W = 7 x 33 in 11 overlays, W = 25 x 32 in 16, W = 2 x 7 in 5 | reproduces; see C4 for the rows that do not |
| 12 | `pl1.py`: `bfgame.tbd#2` right-column ink ends at x = 195 for rows 3, 4, 6; row 0 reaches 246 | reproduces; see C6 |

**Corrections (errors in the first version).**

* **C1 (wrong, fixed): `short_name` is NOT byte-identical in 11 overlays as 152 bytes.**  Only the first `0x8c` code bytes of the ORIGINAL routine are identical in the 11 sites
  (one md5 for all 11); the literal pool `+0x8c..+0x98` differs per overlay (TRAINING `c4c4348c 804d018c`, GAME `30c0468c 804d018c`).  In prop10e every site differs (the patched
  routine carries its own pool).  The signature for a tag patch must be the 140-byte code or the `LAYOUT` signature of `tag_scan`, never the 152-byte body.
* **C2 (wrong, fixed): the tag-geometry test cannot be run with `sh4sim` as the survey states.**  `tools/sh4sim.py` treats every FPU instruction as a no-op (header lines 5-7; only
  `fmov.s` pushes and pops move r15, `fcmp` raises).  The tag draw code at TRAINING `0x33c40..0x33d52` is all `float fpul,frN` / `fmov @(r0,rX)` / `fadd` / `fsub`.  A "dump the
  sprite list" run needs an FPU-capable simulator (new work, not "one run") or a RAM dump from the emulator (user action).  Measurement 1 in section 6 is therefore NOT cheap.
* **C3 (corrected): the "float pool 0x33c88..0x33d48" is two pools of the same three words** (`0x33c88` and `0x33d40`), and everything between is the instruction stream of the
  draw routine `0x33c40..0x33d52` (decoded as floats, the words between are garbage because they are code).  That routine draws two optional sprites (flags at obj `+16` and `+17`, each in a
  scrolled and an unscrolled variant: `bsr 0x8c3041be` / `bsr 0x8c303fc8`) at `obj(+24,+20) + (-24, -48)`.  Nothing proves they are the pawn icon or the stat bar.  The offsets
  -24 / -48 up-left of the tag are at least as consistent with the **`CF` position label and the captain star** seen above and beside the tags in screenshot 100.  The icon and the bar
  may be drawn by another task entirely.  So "move the icon by +48 px by editing these floats" is **unproven and may move the wrong sprites**.
* **C4 (corrected): the first two rows of the W census are not from `w2.py`.**  `w2.py` resolves a register by the nearest earlier `mov #imm` in the function and it mis-resolves
  the 98 overlays of factory A: ABROAD `0x55fa`: `mov #60,r0 ; mov #20,r3 ; mov.b r3,@(r0,r4)`, the immediate sits BETWEEN the two, the scan finds `mov r0,r3 ... mov #56,r0` earlier and
  reports **W = 56 x 70**; the 185 stores reported as W = 0 are the same kind of leak (value 0 is the `mov #0` of an unrelated register).  A local-window resolver (immediate within 5 words
  of the store, `sk_w4.py`) gives W = 17 x 70 stores in 70 overlays (factory B, matches), **W = 20 x 170 stores in 98 overlays** (factory A; the survey said 99), W = 21 x 2, and 239 of 495
  unresolved.  Rows W = 7 / 25 / 2 / 8 / 10 are confirmed by hand (listings above).  The W = 0 row ("185 stores, default constructor") is **UNRELIABLE**: do not use it.
* **C5 (narrowed): "0 of 5,321 names exceed W = 7" covers only the BPINFO `player` records.**  What the 33 W = 7 windows really draw (list-row names of players, staff, scouts, foreign
  names?) is not proven.  The conclusion "W = 7 is not binding" is true for player names, UNKNOWN for the other contexts.
* **C6 (narrowed): the plate texture "spare 60 columns" is only spare for the text rows 1 to 7.**  Row 0 (the blue plate art) reaches x = 246, the texture uses 246 of 256 columns.
  The cut `View Teamwork` / `Opponent Info` is NOT a UV that is too tight: ink x = 101..195 is 95 px and the quad shows about 91 (9a, `s7x_specs.py` line 63: width 96 -> 91).  Widening the
  UV would put ink past the plate sprite; the plate art would have to be widened too.  The **repaint** is the only sound cure (9a S4); the "UV widener" (design 2.4) is dropped for these plates.
* **C7 (superseded by stage 9a / 9d, do not duplicate):** (e) `23 Yen` is the age row `%10d yrs` parsed as money by the library number wrapper (9a M1), cured by the 16 DB
  edits of 9a, which also pad the three blank rows that pushed `Gls` / `Avg Rating` under the window; (d) `efend` is the **`sakusen` texture** (`GAME/GAMEETC.ZAR @110`, id 34716, art-tags.md; 9a M4),
  an art repaint that first needs an injector path for the VQ member (`s7t-proposals.md` 5), not a code search and not "portrait overlap"; (f) the crowd line `1ma827pp` is the
  `strncpy` with 2-byte counts of the crowd-row function at G_INCOME `0x8c4d02d0` (9d patch A / B, sim-proven), NOT a right-anchor problem; lineup tags have a ready same-size cure in 9a M3
  (`TAG_LIMIT` 5 per overlay for GAME and TRAINING, `layoutpatch.patch_tag(limit=)` already takes the limit).
* **C8 (corrected): measurement of the OPTIONS cell.**  The label cut is exactly at the start of the value cell (x = `0xc0` = 192 = 16 x 12), so it is explained by the value call
  alone (a later draw or a cleared bitmap from x = 192) and is **not evidence** of a 16-glyph cell inside `0x8c3341d0`.  The value cut at 14 glyphs is not explained by anything found
  (192 + 168 = 360 is wider than the 240 / 256 px row the function clears), so a hidden limit exists, UNKNOWN.  Both cures are the same text edit and both are within the Japanese byte
  lengths (verified), so the edit is safe whichever cause is true.  On screen the bitmap text is drawn at about 0.7 scale (label glyph pitch 13.2 screen px = 8.6 game px, not 12): the
  12 px values in this document are bitmap pixels.  Also: in prop10e the record TEXT is not at the id offset (repack): the table entries `0x11741c` / `0x117434` point at `0x183201` /
  `0x183252`; the DB ids (`#183214`, `#183274`) are original offsets.
* **C9 (corrected): neighbour collision is not considered by the tag geometry design.**  In screenshot 100 the centre-back tags (`Takem`, `Matsu`) are about 124 screen px (80 game px) apart; a
  7-letter name is up to 96 px.  Moving the icon / bar by +48 px or right-aligning would push one tag into its neighbour.  The 5-letter limit (C7) fits the geometry; the geometry patch does not
  without a spacing change as well.
* **C10 (corrected): "pw3 is at 60 sites in CAP_SLCT, ENDOPT, EVENT"** is `20 shll2 -> nop` per overlay (60 edits) plus 8 strlen literals -> `pw3` per overlay (`layout-issues.md` 10.9); `at_snap` is
  in PLNUMSET only since stage 8h.  The survey did not say that the hang of `prop10c` / `s8e_notag` was **never explained** (`layout-issues.md` 10.8: "the exact instruction was NOT found"); isolation
  removed it.  Any further `pw3` redirect (rank 4) extends exactly the mechanism whose failure is unexplained.
* **C11 (added): the shipped build already "expands" pointer-addressed text** (`--refit on` forces `--hw-relocate`, with the stage 8g table-base guard).  The row "hw pools: yes" in 2.2 is already
  in use; what is left unexpandable is everything addressed by index or stride (names, staff, records).  The guard keeps 417 records in place, so those cannot grow either.
* **C12 (corrected): the Roboto Condensed numbers are for weight 400.**  The user chose MEDIUM (wght 500) and the renderer fixes of 9g (baseline 21, word space 7 to 8, `hscale`) change advances;
  the "0 to 5 %" estimate is an order of magnitude only.
* **C13 (unproven design detail): the GAME line engine hook.**  `@(1,rec)` is the GLYPH COUNT (incremented per glyph at `0x504a8..0x504ac`, compared with 37 / 39 at `0x50342` / `0x50352`) and
  presumably the draw loop bound, so it cannot also hold an accumulated pixel advance; the record is 2 + 2 x 40 bytes with no spare byte, so a new accumulator is needed.  The per-glyph advance is
  stored in the high byte of the u16 slot, so a table advance (<= 255) fits.  A `bsr` cave must lie within +-4 KB of `0x5049e`: GAME has two zero runs there (`0x507c0`, 80 bytes;
  `0x50980`, 152 bytes), NOT proven unused (they may be zero-initialised data).  The "two immediates" estimate is optimistic.

**Challenge from the stage 8 lessons (`hang-investigation.md`, `layout-issues.md` 10.8 to 10.10, `patch-engine.md`).**

* **Shared code patched globally broke the first Event message** (align-fix at_snap wired into EVERY proportional draw, hang at the first EVENT message; cause not found, isolation cured it).
  Every code proposal here touches shared or overlay-wide code: rank 4 (pw3 redirect, money text), rank 6 (GAME line engine, the match overlay), rank 7 (W immediates in 11 overlays).  Each needs
  its own sim proof of isolation (the patched routine runs the same instructions for every input outside the target) AND a bisectable disc, because the simulator has not found the hang cause so far.
* **Relocated bases corrupted tables** (stage 8f).  Nothing in this survey moves a table; but "widen by display-time substitution" (2.2 end) and any stride widening are exactly that class and stay out.
* **Signature-located only:** every proposed edit here is specified by file offset for one overlay.  The shipped rule (stage 8g) is: locate by a signature that is unique in the overlay, prove the
  pattern count (exactly N sites), prove isolation, and fail the build otherwise.  Tag geometry (float pool) and W widening (`mov #7,rX` halfwords: 4 `07ea` and 2 `07e8` matches exist in
  CAP_SLCT alone, only `0x79e0` / `0x7d0a` are the cells) do not yet have such a signature.

**Verdict on the ranked items.**

| rank | item | verdict |
|---|---|---|
| 1 | OPTIONS strings (label <= 16, value <= 14) | **SAFE to implement now** (data only; 9a S1 / S2 already decided `Subtitles`, `  Near/Mid/Far`); validator assertion `len <= 16 / <= 14` optional |
| 2a | lineup tags via `TAG_LIMIT_BY_OVERLAY` {GAME 5, TRAINING 5} (9a M3) | **SAFE**: same routine and same bytes as the booted tag-fix, one immediate changes, `test_tagfix` exists; other 9 overlays stay at 7 |
| 2b | tag geometry (icon / strip offsets, right-align) | **NOT ready**: icon constant unidentified (C3), no FPU simulator (C2), neighbour collision (C9).  Needs an FPU-capable sim or an emulator RAM dump first, then a **bisectable disc** (`s8e`-style, one overlay per disc) |
| 3 | plates `View Teamwork` / `Opponent Info`: repaint to <= 91 px | **SAFE** (art only, 9a S4); the UV widener is dropped (C6) |
| 4 | `pw3` right-anchor for G_INCOME | **Do not do now.**  The visible crowd cut has a different cause and a sim-proven fix (9d); the redirect is money text and extends the mechanism with the unexplained hang.  If ever done: needs a **bisectable disc** and the `test_alignfix`-style proof |
| 5 | HOME / AWAY `efend` | art (sakusen texture repaint); **blocked on an injector path** for the VQ member; no code |
| 6 | GAME line engine hook | **Needs a bisectable disc and a design rework** (C13); no visible cut depends on it; keep for the 9f subtitle study |
| 7 | W widen of name cells | **Skip**: cures nothing, unproven which strings the cells hold (C5), and the sig is not unique |
| 8 | struct fields | never |

Two designs were checked against the simulator as far as it can go: (1) tag geometry: **blocked** (C2, the simulator has no FPU); (2) GAME line-engine hook: the integer parts
are simulatable (the engine is integer) but the count / accumulator conflict (C13) means the design as written would break the draw loop, so no run was made.  The OPTIONS text edit needs no
simulator (data in the string table, bytes verified).  Scratch scripts of this review (`sk_extract.py`, `sk_check1..3.py`, `sk_w4.py`, `sk_zero.py`) are in the session scratchpad.

## 1. The visible cuts and what limits each (status of the cause)

Screenshots 98 to 105 (`prop10e`), scale 640 px = 984 px (x 1.5375).

| # | Visible cut | Mechanism found | Status | Class (section) |
|---|---|---|---|---|
| a | lineup tags `Kasam t`, `Hisan`, `Kanaw`, `Takem`, `Matsu` (100, 102) | text starts at the tag's left edge and the pawn icon plus the stat bar sit about 48 px to the right (the width of the two full-width glyphs the Japanese `short_name` kept, 4 bytes); letters after the 4th or 5th run under the icon; the text is complete, not clipped | **INFERRED** from the screenshot geometry (`Hori` 4 letters clear, `Kasamat` 7 letters shows 5 then icon then `t`) | tag geometry (3) |
| b | left plates `View Teamwork`, `Opponent Info` (100) | the plate text is the texture column `bfgame.tbd#2` (256x256): right column ink ends at x = 195 for rows 3, 4 and 6 (measured, 95 px wide, squashed to the 96 px region); the quad shows the old ink extent | texture facts **PROVEN** (decoded `translation/textures/TRAINING/BFGAME.ZAR/bfgame.tbd#2.pvr`), clipped quad **INFERRED** | plate UV (4) |
| c | OPTIONS `Commentary Tex`, `Near/Mid/F` (101) | GAME's bitmap text: label cell 16 chars, value cell 14 (equal to the Japanese byte lengths `  実況テキスト  `, `    近・中・遠`); the row call passes x = 0 (label) and x = 0xc0 = 192 px = 16 x 12 (value) | call constants **PROVEN**, cell meaning **INFERRED** | GAME bitmap text (6, 7) |
| d | HOME / AWAY `efend` (101) | **[skeptic] the `sakusen` texture** (`GAME/GAMEETC.ZAR @110`, id 34716; `docs/art-tags.md`, 9a M4); the earlier "portrait overlap, draw site not located" is dropped | texture identity PROVEN by docs, exact reason the `D` is missing UNKNOWN; repaint needs an injector path (`s7t-proposals.md` 5) | art |
| e | Transfer panel rows (105): `23 Yen`, `0 Gls` / `Avg Rating` / `3.00` below the panel | **[skeptic] 9a M1: `23 Yen` is the age row `%10d yrs` parsed as money; the blank rows are fixed by 9a's 16 DB edits** (the first version said "salary text" and "UNKNOWN") | other owner | DB text |
| f | crowd line `1ma827pp` (income table) | **[skeptic] 9d: `strncpy` with 2-byte counts in G_INCOME `0x8c4d02d0`; patch A / B (sim-proven), not a right-anchor problem** | other owner | code, 9d |
| g | `Income` tab text past its tab | tab plate is a texture; text wider than the plate art | art | 4 |
| h | Event Ad Budget `okan`, `1 oku` plate | 9a investigation | other owner | - |

## 2. The mechanisms, one by one

### 2.1 Window width fields (`+0x3c` cells, `+0x3e` advance, x0 / y0)  (mechanism 1)

**What the field does (PROVEN, `docs/font-hook-notes.md` 3.3).**  `W` and flag `+0x45` give the wrap: a glyph is placed while its pen start satisfies
`pen - x0 <= 12 * (2W - 2)` px with the proportional hook (`docs/pixel-widths.md`), `2W - 1` half-width glyphs in the plain font.  There is no scissor,
no clip rectangle, no row limit in the layout; `x0` / `y0` (`+0x4a` / `+0x4c`) are just the origin.  No clip symbol or user-clip string exists in
`1ST_READ.BIN` (grep of `clip` hits: 0); the sprite drawer `FUN_8c080454` was not analysed for a scissor (UNKNOWN, but no visible cut needs one).

**Where the values are written (new census, `w2.py`).**  Every `mov #60,r0 ; mov.b Rm,@(r0,Rn)` of the 113 overlays with a base, `Rm` resolved by a
backward search to the nearest `mov #imm`: 495 stores.

| W (cells) | stores | overlays | what it is |
|---|---|---|---|
| 20, rows 3, adv 24, line 23 (factory A) | **[skeptic] 170** (was 99) | 98 | message window next to the portrait (39 glyphs, 468 px start rule 456); local-window resolver `sk_w4.py` |
| 17, rows 2, adv 24, line 24 (factory B) | 70 | 70 | speech bubble (33 glyphs, 396 px) |
| 0 | ~~185~~ **[skeptic] unreliable** | 105 | the `w2.py` backward search leaks an unrelated `mov #0` (and reports factory A as W = 56 x 70); 239 of 495 stores are unresolved by a local window |
| **7**, rows 1 | **33** | **11** (ABROAD CAP_SLCT DRSOLIST ENDOPT FIRE MEETING NEWCON PLNUMSET RECON SCDRF YOUTH) | list-row name cells: three loops per overlay (rows, scroll up, scroll down), one `mov #7,r10` and one `mov #7,r8` per overlay (CAP_SLCT `0x79e0`, `0x7d0a`; identical code, spacing 0x32a) |
| 25 | 32 | 16 | list cells (EXTRADE `0x2eec`: a loop over slots of 0x218 bytes, two windows each) |
| 2 | 7 | 5 (GAME NEWS OFFICE TRAINING TV_EVENT) | the **name-tag** window (TRAINING `0x33d66`, see 2.3) |
| 8 / 9 / 10 / 21 / 20 | 1 / 1 / 1 / 2 / 3 | DRAFT / YOUTH / GAME / SPF_READ / SS_EDIT | single oddities |

**Can it be widened generically?**  Yes, every store is an immediate or a call-site constant, so a table of `W` per overlay is a handful of
same-size `mov #imm` edits located by signature (the 11 name-cell overlays show the same offsets relative to each other, 0x32a between the two loads; byte identity of the loops was not scanned).
**But it cures nothing visible:**

* The cell width that bites in the plain font is the `2W - 1` count (`Isao Nakagak`, 12 glyphs, 13th wrapped; `docs/layout-issues.md` 3 candidate (a)).
  With the proportional font, measured over all 5,321 English player names: the widest start-of-last-glyph is below 144 px (limit of W = 7) for **every**
  name (`nm1.py`: 0 above 144, widest total 153 px).  So W = 7 is not binding in `prop10e`; the symptom is already gone.
* Widening bubbles (17 -> 20) lets text run past the bubble art; the plates are textures.
* Value: only a safety margin for the plain-font build.  Design if wanted: replace the two `mov #7,rX` halfwords per name-cell overlay (22 halfwords:
  `07 ea` -> `08 ea` for r10, the r8 form `07 e8` -> `08 e8`) by signature `3c e0` (mov #60,r0) + `a4 04` / `84 04` (mov.b) with the immediate load inside 400 words and
  exactly 3 stores per register; simulator test: lay out the 5,321 names with the real layout function of CAP_SLCT with W = 7 and 8 and compare rows.
  Risk: very low.  Visible cuts cured: 0.

### 2.2 Copy buffers, strides, sprintf destinations  (mechanism 2)

Census of the database (398,604 records, `fe2.py`): fixed-stride arrays carry the person names, hw pools carry foreign name parts.

| family | stride S / field W | records | files | English at the limit (>= W-1 bytes) | in-place expandable? |
|---|---|---|---|---|---|
| player / staff name arrays | 30 / 14 | 32,450 | 10 | 0 | no (14-byte name field, thousands of index sites) |
| same, reading column | 30 / 16 | 53,200 | 10 | 10 | no |
| | 60 / 14, 60 / 16 | 8,133 + 13,300 | 5 | 0 + 5 | no |
| | 56 / 14 | 6,153 | 10 (18 arrays) | 8 | no (`Damui` 56-byte records, relocator guard) |
| | 112 / 14, 28 / 14, 29 / 13, 29 / 16, 240 / 14 and / 16, 92 / 14 | 2,280 + 1,010 + 3,083 + 4,465 + 2,809 + 44 | 1 to 3 each | 3, 1, 44, 1, 0, 0 | no |
| municipality record | 126 / 35 | 1,014 | 1 | 0 (names are <= 13) | already 35 bytes: full names possible, data only |
| hw pools (`hwptr`) slot 4 / 8 / 12 | - | 16,413 / 84,511 / 11,601 | 74 overlays | 16,182 / 40,744 / 2,112 at the slot | **yes**: pointer strings, `--hw-relocate` with the table-base guard (417 records stay in place, `translation/hw_inplace.tsv`); their real limit is the 14-byte destination |
| `in-place only` records | - | 148,971 | - | 1,230 at max_bytes | n/a |

Code-side buffers found so far (all PROVEN):

| buffer | size | adjacent | state |
|---|---|---|---|
| club name `#sname#` (struct 0x103a) | 14 | next field 0x1048 used 276 times in 57 overlays | guarded (13 chars + NUL), not widenable |
| `#YOU#` (0x102c) | 14 | | not widenable |
| composer temp | 64 | | internal |
| scout row buffer | 12 per row, 89 bytes | rows at b[37..], b[50..], b[63..], b[76..] | `scout-fix` (Age) and the `yrs  ` record |
| PLNUMSET right panel | 52, rows 12 / 13 wide | newline at bytes 12, 25, 38 | exact lengths imposed by text (layout-issues 10.6) |
| tag `short_name` local buffer | 8 | caller buffer | `TAG_LIMIT = 7` is its maximum |
| GAME bitmap text local copy | 40 | | `cmp/ge r2,r12` (r2 = 40) at 0x8c33424c |

**Design for "widen by display time substitution" (not for stride widening):** a name bank keyed by player ID at the display accessor (UNKNOWN whether such an
accessor exists; `docs/expansion/field-widths.md` V5, rank 7).  Risk high, no visible cut in the current list needs it (names fit: 12 characters, widest 153 px).

### 2.3 Name-tag windows  (mechanism 3)

Facts (PROVEN unless marked):

* `short_name(dest, name)`, 152 bytes, **[skeptic] the first 0x8c code bytes are identical in the 11 original overlays (`layoutpatch.TAG_SITES`), the literal pool is not**; `tag-fix` makes it keep the family name up to **7** bytes (the 8-byte local buffer).
* The tag task is TRAINING `PlnameTask` (`0x33d54..0x33db0`): `[obj+0x30]->+0x20` is the text window, the code writes `mov #2,r1 ; mov #60,r0 ; mov.b r1,@(r0,r3)` = **W = 2** (TRAINING
  `0x33d66`), builds the text with `short_name`, then calls `0x8c2e8000` with `0x8c388080` (text setter).  Same constant in GAME, NEWS, OFFICE, TV_EVENT (7 stores, 5 overlays).
  W = 2 is the Japanese design: 4 bytes = 2 full-width glyphs.  With the proportional hook its start limit is `12 * (2*2 - 2) = 24` px, which would wrap `Hori`'s last letter, yet the
  screenshot shows one line: the tag text is therefore drawn by another path or `W` is rewritten later (**UNKNOWN**; cheapest test: run the task in `sh4sim` and read `+0x3c` at the draw).
* Icon and strip positions: **[skeptic] see 0a C3**: two copies of the pool (`c1c00000` = -24.0, `c2400000` = -48.0, `3a83126e`) at TRAINING `0x33c88` and `0x33d40`, used as `fmov (obj+20/24) +/- const` before `bsr 0x8c3041be` / `0x8c303fc8` in the flag-driven draw routine `0x33c40..0x33d52`.
  That these are the pawn icon / strip is **UNPROVEN** (they fit the `CF` label and the captain star as well).
* Capacity the design must provide (all 5,321 family names; `fe3.py`): at `LIMIT 7` the tag is at most 96 px; 90.7 % <= 84 px, 58.9 % <= 72 px; the Japanese space was 48 px
  (15 % of names fit it today).  Roboto Condensed (24 px) would put 99 % under 84 px.

**Design (no code written).**  Do NOT raise `LIMIT` (it is at the buffer maximum and the text is not clipped).  Move the icon and bar: add **+48 px** to the x offset of the
icon / strip sprites relative to the text origin (float literals, 2 to 4 words per overlay), or right-align the text to end at the icon (`x_text = x_icon - width(text)`, needs the
`pw3` routine already in the font cave: `x = anchor - 3 * pw3(text)`).  Signature: the 152-byte `short_name` body is already located; the callers' float pools are located
through the literal that loads `0x8c2e5318` (TRAINING `0x33da4`, GAME `0x1070ec`).  Test: simulate the task with names `Hori`, `Kasamatsu`, `Matsushima`, dump the sprite list, assert icon x >= text end + 4 px for all 5,321 names.
Risk: low to medium (position-only, no struct); 11 overlays share `short_name` but only TRAINING (lineup, placement) and GAME / NEWS (match, news) draw tags, so at most 3 to 4 sites.
Cures: tags (a); nothing else.

### 2.4 Text on art plates  (mechanism 4)

Plates are textures; the text is painted into them (`docs/art-translation.md`).  Two ways to widen: repaint narrower (no code) or enlarge the sprite quad / UV (code).  What the repo knows:

| plate | texture | measured / documented spare width | status |
|---|---|---|---|
| pre-match menu text column | `bfgame.tbd#2` = 37173 / 37286, 256x256 | right column ink x = 101..195, **spare x = 196..255 (60 px)**; left column x = 3..91, `Mid Defence` 91 | **PROVEN**; clipped quad INFERRED, UV location UNKNOWN (searched TRAINING for float `100/256`: not found, the descriptor may be integer) |
| Name Entry tabs | 03541 | quads show only the old ink columns | known clip (`docs/art-translation.md` 10) |
| Office menu rows 3 and 4 | 07405 (+07469, 07539) | must fit 51 px, sprite UV clips there | known clip (`docs/art-sweep-v3.md`) |
| hobby line SS_PR1 | 03836 / 03838 / 03840 | clipped | known clip |
| SUPPORT trait plates | 03869 | `Coaching Talent` clipped | known clip |
| Meeting meter | 03266 | box 62 px wide | art |
| Income / Costs tabs | G_INCOME | tab text wider than the tab | UNKNOWN (measure the texture) |

**Design.**  A generic "sprite descriptor widener": find the u16 / float quad descriptors of a texture through its extents (`tools/re/ar5_find.py` finds sprites by alpha mask;
a UV search like the scratchpad `uvsearch*.py` finds the floats `x / texture_width`), widen `w` and `u1` by the spare columns, signature-checked.  Only valid where the plate art behind
the text is wider than the text, so the plate sprite also has to widen (the blue plate in `bfgame.tbd#2` row 0 is 148 px; the on-screen plate is about 144 px).  Per-plate effort, not generic.
**Cheapest cure:** repaint `View Teamwork` as `Teamwork` and `Opponent Info` as `Opp. Info` (both fit 62 px), no code, no risk.

### 2.5 Right-aligned fields  (mechanism 5)

Where the right edge is set by code (`docs/layout-issues.md` 10.3, 10.4): the player-card panel is already fixed (`pw3`, 60 sites in CAP_SLCT, ENDOPT, EVENT).  The lead list
(`aln_scan12.py`) has about 80 more `* 12` idioms in 22 overlays: G_INCOME 6 (`(8 - len) * 12`), SPONSOR / SPONSOR2 5 each (`(14 - len) * 12`), NENREP 7, NEWS 4, GETREP 4,
CHALMODE 3, DRSGP 5, RECON 3, ENDOPT 3 more, DRSHRANK / DRSISEKI / DRSJAPAN / DRSLIST / DRSSRANK 3 each, OPTION 3, PL_EDIT 3, PWK_EDIT 4, SCHE0 / SCHE1 2 each, SELNAT 3, SUPPORT 1.
Money columns are the money owner's; names are fixed by `pw3`.  Design: reuse the `pw3` redirect (the strlen literal of the idiom -> `pw3`, `shll2` -> `nop`) per site family, one family
(G_INCOME, `(8 - len) * 12`) first because it is the income table of the visible `1ma827pp`; test like `test_alignfix` on the real income row builder.  Risk: medium (money text, 6 sites).
Cures: crowd line (part), none of the others.

### 2.6 The "linear text" path (6 / 12 bytes per glyph)  (mechanism 6)

One shared back end (`1ST_READ.BIN` `FUN_8c15e9c6`, jump-table slot 0x3d0: 6 bytes per half glyph, row stride `cells * 24` px) and three users: DMCLBEDT, ENDING, GAME.  (`docs/font-hook-notes.md` 4.2.)
GAME's user is a **different function from the 0x8c3202b0 engine**: the text-to-bitmap routine `0x8c3341d0`, **3 call sites** (`0x2f2be`, `0x2f4e0` = OPTIONS builders; `0x66b08` = a general draw-string wrapper
with the flags `0x90000 | 0xf0330`).  Its structure (PROVEN from the listing): copy at most 40 bytes of the string (`cmp/ge #40` at `0x8c33424c`), `bytes = 6 * n`, a 240 px row (`0xf0`) or 256 (`0x100`) cleared by
`0x8c33415c`, glyph blit with 2-bit output (4 pixels per byte), x / y arguments in r4 / r5 (x is 0 for labels and 0xc0 for the value call of the same row; y = 44 per row).  Cap 40 characters is far above the 20 a 240 px row holds
(no bound check, per `docs/font-hook-notes.md` 5).
Widening: the pitch (12 px) is hard-coded; a proportional pitch needs a nibble-wise blit (rejected earlier).  Single hook point for the pitch exists (`FUN_8c15e9c6` loop at `0x8c15ea22`, used by the
9b centring proof `lin_center_proof.py`), which fixes `i l` gaps (`OPTI ONS`) but **not capacity**.  Capacity: the cells argument at the 3 call sites (label 16 glyphs = 8 cells, value 14 = 7 cells, INFERRED; the real clip is not yet found, measurement 3).  Risk: medium.  Cures: spacing only.

### 2.7 GAME.BIN's own text engines  (mechanism 7)

Two engines (both PROVEN as code, purpose INFERRED):

1. **Line engine `0x8c3202b0`** (file `0x502b0`, called from the state machine at `0x8c31eee8`, literal `0x4ef50`): per-line records of **82 bytes** (2 header bytes, up to 40 u16 codes), glyph count in byte +1, line break at
   `cmp/ge #37` when the next code is a blank (`0x8c320340..0x8c320354`) and forced at 39; the blit is the standard slot (`0x8c1593b4`), the **advance is stored per glyph as an immediate**:
   `mov #12,r0 ; mov.b r0,@(1,r2)` at `0x8c32049e` (half width) and `mov #24,r1 ; mov.b r1,@r2` at `0x8c3204c6` (full width), added when drawn.  Used for running text (commentary / subtitles, INFERRED).
   **Hook design:** replace the two immediates by a call to a cave routine returning the table advance (the same `ADVFN` of `docs/font-hook-notes.md` 7, table index = the glyph byte) and the 37 / 39 count by
   the accumulated advance against 444 / 468 px (the `WRAPFN` of that note).  Size: 2 halfwords + 2 call stubs (about 40 bytes) in GAME.BIN only, signature: the 82-byte `mul.l` pair at `0x8c320334` / `0x8c32038e`.
   Not covered by the existing proportional hook (which patches the tsString copy of GAME, a different engine).  Value: BCAST subtitle layout (20,914 English clips); risk medium to high (GAME is the match overlay).
2. **Bitmap text `0x8c3341d0`** (2.6): OPTIONS rows, HOME / AWAY plates and other match-UI strings; row bitmap, fixed cells.

The OPTIONS table is `tbl@117414` (7 label / value pairs; labels `  Commentary    `, `  Commentary Text  `, `  Player Names    `, `  Name Format`, `  Camera Type  `, value `    Near/Mid/Far`), builder at
`0x8c2ff29e`: 44-byte row stride, `jsr 0x8c3341d0` once for the label (x 0) and once for the value (x 0xc0).  Observed cut: label to 16 glyphs (`  Commentary Tex`), value to 14 (`    Near/Mid/F`).  Both equal the original
Japanese byte lengths; the English records are `max_bytes` 20 and 16, so the DB never prevented them.  **Fix by text:** label <= 16 characters including the leading blanks (` Commentary Text`, 16; or `  Subtitles`), value <= 14 (`  Near/Mid/Far`, 14).

## 3. Risk and evidence by patch family (shipped and proposed)

| patch | sites | overlays | proof | seen in game |
|---|---|---|---|---|
| `tag-fix` (LIMIT 7) | 11 routine copies | 11 | simulator, byte reference | `Hori` ok, cuts remain (a) |
| `scout-fix` | 4 halfwords | 2 | simulator, 83 checks | ok |
| club guard | 232-byte composer | 20 | 142,670 runs | ok |
| `align-fix` | cave 256 B + 64 B panel edits | 1 + 3 | simulator | no hang (`prop10e`) |
| proposed tag geometry | <= 4 float pools | <= 3 | to build | - |
| proposed GAME advance | 2 immediates + cave | 1 | to build | - |
| proposed name-cell W | 22 halfwords | 11 | to build | - |

## 4. What stays impossible by a generic patch

* **Struct fields** (14-byte person and club names, 92-byte BPINFO, 288-byte runtime player, 56 / 112 / 28 staff arrays): thousands of index sites, saves store them (`docs/expansion/save-format.md`).  English must fit 12 / 13 characters.
* **Texture size** (VQ slots, VRAM, UV compiled in overlays): widening a plate beyond its texture is a format change (`docs/texture-injection.md` 7).
* **Full-width cells of the Japanese design** (2 cells of 24 px): equal 48 px, ~4 letters.

## 5. Font swap (Roboto Condensed, stage 9c): effect on overflow

Advance estimate (`fe1.py`, `fe3.py`: Pillow natural advance of `RobotoCondensed[wght]` at weight 400, size 24 / 26, clamped 4..13, space 6 or 12), over the translation database:

| measure | current table | RC 24 px | RC 26 px |
|---|---|---|---|
| average px per letter, 5,321 family names | 11.23 | 10.73 (-4.5 %) | 11.17 (-0.5 %) |
| labels (96,420 texts), width ratio, space 6 / space 12 | 1.00 | 0.926 / 0.962 | 0.964 / 0.999 |
| prose (22,516 texts), same | 1.00 | 0.863 / 0.947 | 0.907 / 0.991 |
| name / slot texts (247,336), same | 1.00 | 0.944 / 0.961 | 0.985 / 1.002 |
| labels wider than the Japanese width (lead list, not a verdict) | 46,356 | 37,521 / 40,621 | 42,961 / 46,195 |
| prose wider than the Japanese width | 5,214 | 1,005 / 2,962 | 1,777 / 4,776 |

| string | current px | RC 24 | RC 26 | field |
|---|---|---|---|---|
| `Kasamatsu` | 110 | 103 | 106 | tag 48 px (design), icon gap |
| `Commentary Text` + 2 blanks | 177 | 156 | 166 | 16-glyph cell, 12 px monospace in GAME (font only changes the glyph art) |
| `View Teamwork` / `Opponent Info` | 155 / 144 | 140 / 135 | 146 / 141 | art plates: font swap irrelevant |
| `Isao Nakagaki` | 148 | 136 | 141 | W = 7 name cell: fits either way |

Conclusions: (i) the swap changes the overflow picture by under 5 % for names and labels unless the advance table is tightened below natural advance (the upper bound of the gain is about 10 %);
(ii) GAME's OPTIONS / plates use a 12 px pitch and fixed cells, so the swap only changes glyph shapes there; (iii) the fields that still overflow after the swap are exactly those of sections 2.3 to 2.7, so the plan
above is font-independent; (iv) a narrow font makes the tag geometry patch more valuable, not less (99 % of tags under 84 px at 24 px).

## 6. Measurements needed (none needs Flycast; cheapest first)

1. `sh4sim` run of the TRAINING `PlnameTask` (`0x33d54`) with names of 4, 7 and 9 letters, reading `+0x3c` at the draw and the sprite list (decides 2.3: whether `W = 2` is live, which float is the icon offset).
2. Decode and dump the sprite descriptors of the pre-match menu (BFGAME) from the overlay data around the first reference to texture 37173 (floats or u16, 2.4).
3. Run `0x8c3341d0` in `sh4sim` against the real GAME.BIN with the FONT header (`0x8cd5c004`) and a 19-glyph label: confirms the 16 / 14 cells and where the cells argument comes from.
4. One RAM dump of the HOME / AWAY screen with `wintext.py` (decides the `efend` cause).

## 7. Plan with order, design and tests

1. **OPTIONS strings** (data): `FLOW_PRG/GAME.BIN#183214` -> label <= 16 characters, `#183274` value <= 14 characters, keep `#1831f0 ... #183260` at <= 16.  Test: assert `len <= 16` / `<= 14` in the validator for the records of `tbl@117414`.  (`Commentary Tex`, `Near/Mid/F`.)
2. **Tag geometry** (measurement 1 first): same-size float edits or a right-align redirect to `pw3`, in TRAINING (lineup) first; simulator test over all 5,321 names; optional second step GAME / NEWS.
3. **Plates**: repaint `View Teamwork` / `Opponent Info` narrower now; the UV widener only after measurement 2 and only if more plates need it (list in 2.4).
4. **Right-anchor family** for G_INCOME (6 sites) with the income row builder test; then SPONSOR / NENREP if the playtest shows cuts.
5. **GAME line engine hook** (2.7 item 1): only with a BCAST playtest request; two immediates and a cave routine.
6. **W widen of name cells**: optional safety net for the plain-font build, 22 halfwords.
7. Never: struct widening (section 4).

## 8. Open points for the user

* Tag design: widen by moving the icon (+48 px) or by right-aligning the text to the icon (names then grow to the left, like the Japanese right-aligned columns).
* `View Teamwork` / `Opponent Info`: shorter words (`Teamwork`, `Opp. Info`) or UV work.
* HOME / AWAY `Defend`: attract-demo text is a texture (`GAME/GAMEETC.ZAR` `sakusen.pvr`, `injectable false`) per `docs/s7t-proposals.md` 5; confirm in game whether the plate text is the texture or the bitmap text.

## 9. Evidence scripts (session scratchpad, not part of the repo)

`w1.py` / `w2.py` / `w3.py` (window `W` census and the 22 `mov #7` sites), `fe1.py` / `fe1b.py` / `fe3.py` (width census, font estimate), `fe2.py` (stride and slot census),
`nm1.py` (names against W = 7), `t1.py` (literal and `bsr` callers of an entry), `uv1.py` (float UV search), `pl1.py` (plate ink extents of `bfgame.tbd#2`), `pn1.py` (panel strings against W).
Listings: `python -I -X utf8 tools/re/aln_dis.py GAME 641d0 64420`, `... GAME 502b0 504c0`, `... TRAINING 33c40 33dc0`, `... CAP_SLCT 7960 7ab0`, `... EXTRADE 2ea0 2f80 8c4d0000`.
