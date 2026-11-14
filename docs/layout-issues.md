# Layout issues from the first full-English playtest (task D: lists and panels)

Source: playtest session 1 (`docs/playtest-log.md`, trial_plain = full English, plain 12 px font).  Status words: **PROVEN** = executed
or read from code/data with an address, **INFERRED** = follows from proven facts, **UNKNOWN** = needs a measurement that was not
possible without touching the emulator the user is playing in.  Nothing here launched Flycast; the RAM dump
`build/emu/pt1_ram.bin` (Finances screen of an English build) and the older dumps were only read.

| # | Symptom | Cause | Status | Fix |
|---|---|---|---|---|
| 1 | Hometown region list shows `To ho ku`, `Ka ns ai`; `Kanto`, `Hokkaido` fine | the list builder justifies every 4- and 6-byte string as a 2- / 3-character Japanese word | **PROVEN** (code + simulator) | `tools/layoutpatch.py`: two halfwords, wired into `build_patch.py` (section 2) |
| 2 | `Isao Nakagak` clipped in the Event list and the player card | a 13-character name does not fit those panels (12 visible) | symptom **PROVEN**, mechanism **UNKNOWN** (two candidates) | 189 names shortened to <= 12 (ladder), limit recorded (section 3) |
| 3 | `Aogashi Steamship` runs over the logo / heading | sponsor name = town token + suffix, 17 cells against a column laid out for about 16 | cause **PROVEN**, column width **INFERRED** | 4 suffixes shortened (section 4) |
| 4 | `This Season` overlaps / neighbouring cells overrun | label itself equals the Japanese width (12 cells); two value cells were 2 cells wider than the Japanese | partly **PROVEN** | 2 value cells shortened, label left (section 5) |

Files added or changed (nothing committed): `tools/layoutpatch.py` (new), `tools/test_layoutpatch.py` (new),
`tools/build_patch.py` (+`apply_layout_patches`, 22 lines), `tools/re/layout/` (new: `sim_hometown_label.py`, `limits.py`,
`mk_layout_edits.py`, `prop_widths.py`, `wintext.py`), `docs/style-guide.md` (name limit 12), `build/trans/layout_limits.tsv`
(generated), `build/trans/layoutD/*.json` (the merged result files; merge backups `build/trans/backup/0348`, `0349`).

## 1. Units used below

* Plain font: every ASCII character is 12 px = 1 cell; a Japanese character is 2 cells.  A window of `W` cells (`+0x3c`) wraps after
  `2W-1` half-width characters when `+0x45 == 1` (docs/text-engine.md 4.4); there is no clipping and no word wrap.
* Proportional font (opt-in, `docs/proportional-font.md`): table advance per character, space 6, digits 12, weighted mean about 10 px.
  `python -I -X utf8 tools/re/layout/prop_widths.py "text"` prints both widths.
* Panels have **no width of their own**: every text window is 20 (or 25) cells wide and is placed by explicit x/y; what limits a string
  is the gap to the next element.  In the Finances dump `pt1_ram.bin` the labels sit at x=120 and the right-aligned values are padded
  with blanks to end near x=616-628 (`___0_yen` at x=520, `___3_oku_6200_man` at x=424; `tools/re/layout/wintext.py`).  So the
  working budget of a cell is "Japanese width of the same cell" unless a measurement says otherwise.

## 2. Hometown lists: `To ho ku` / `Ka ns ai`  (PROVEN)

**Mechanism.**  `FLOW_PRG/HOMETOWN.BIN` (base 0x8c2d0000) builds one text object per list entry in one init function (0x8c2d2210): 12
regions (index bytes at 0x471a0 into the 8-byte records at 0x47cc4: pointer + first/last prefecture), 50 prefectures (pointer table
0x42200), 10 + 42 kana tabs (0x47308, 0x471b8) and 1,268 towns (126-byte records from 0x15970, name at +2).  All 12 call sites call the
same label builder `FUN_8c2d2a50` (file offset 0x2a50) before the window constructor 0x8c2dcc5c:

```
len = strlen(s)                                    ; 1ST_READ 0x8c014de4
buf[0] = ' '                                       ; always a leading blank
if len == 4: buf = ' ' + s[0:2] + 0x81 0x40 + s[2:4]          ; 2 full-width chars  -> full-width blank (24 px) between them
if len == 6: buf = ' ' + s[0:2] + ' ' + s[2:4] + ' ' + s[4:6]  ; 3 full-width chars  -> half-width blank (12 px) between them
else:        buf = ' ' + s
```
(`cmp/eq #4,r0` at 0x2ab4, `cmp/eq #6,r0` at 0x2ade; the separators are the two literals at 0x467f5 `81 40` and 0x467f8 `20`.)  It is the
Japanese "space out 2- and 3-kanji names so the column lines up" rule.  An English word of 4 or 6 letters is cut into 2-byte pairs:
`Tohoku` -> ` To ho ku`, `Kansai` -> ` Ka ns ai`, `Kyushu` -> ` Ky us hu`, `Nara` -> ` Na<24 px gap>ra`; 3, 5, 7, 8 letters (`Kanto`,
`Hokkaido`, `Okinawa`) are untouched.  That is exactly the reported pattern.

**Evidence.**  `python -I -X utf8 tools/re/layout/sim_hometown_label.py` executes the routine in `tools/sh4sim.py` (strlen / strncpy of
1ST_READ run natively): original -> `' To ho ku'`, `' Ka ns ai'`, `' Ky us hu'`, `' Kanto'`, `' Hokkaido'`; Japanese `北海道` -> `' 北 海 道'`.
`tools/test_layoutpatch.py` (26 checks) asserts all of it.

**Affected (current English).**  Regions `Tohoku`, `Kansai`, `Kyushu`; prefectures `Aomori Miyagi Toyama Nagano Kagawa` (6) and `Gifu Nara
Saga Oita` (4); kana tabs `Shi-`, `Chi-`, `Tsu-`; towns: of the 284 town names of the 126-byte records that the database covers, 92
have 4 or 6 letters (about a third).  (The pointer table `tbl@43858` with 8-byte abbreviations has 421 of 1,248 entries of 4 / 6
letters; no code references it by address, so it is not known to pass through the builder.)

**Fix (implemented, default on).**  English edits cannot fix it (hundreds of 4- and 6-letter place names, fixed spellings).  The patch
`tools/layoutpatch.py` changes the two immediates `04 88` / `06 88` at 0x2ab4 / 0x2ade to `ff 88` (`cmp/eq #-1,r0`; strlen is never -1), so
every string takes the plain ` ` + string path.  Same size, signature-checked (refuses a changed image or a second application), applied by
`build_patch.py` (`apply_layout_patches`, after the text stages, only when HOMETOWN.BIN already carries English).  The simulator result
after the patch is `' Tohoku'`, `' Kansai'`, `' Nara'`.  Cost: still-Japanese entries lose their justification (cosmetic).  Not run in
Flycast (the user is playing); first thing to look at in the next session: Hometown screen, region and prefecture lists.

**Side finding (not changed).**  `中国` is translated `China` in every table (about 100 records).  In the Hometown region table
(`ptr@47cfc`, between `近畿` and `四国`) it is the **Chugoku region**; in the other overlays the same 8-entry region table (東北 ...
九州) appears next to it.  The merge tool writes one English per Japanese text, so a per-context split needs either a per-id edit or a
separate decision; owner: place list (task A).  `Chugoku` (7 letters) fits the 8-byte slots.

## 3. Player names clipped: `Isao Nakagak`  (symptom PROVEN, mechanism UNKNOWN)

**Facts.**  The name is intact in memory: `pt1_ram.bin` holds `Isao Nakagaki\0` (13 characters + NUL) in the 14-byte BPINFO field at
0x8c353724 and in five more copies; the string is complete, so the cut is made when the name is displayed.  Japanese names are at most
11 cells (5 kanji + blank; 1,622 of 5,321 are 9 cells), so the panels were sized for about 11-12 cells, while English names run to 13
(156 px plain).  Window cells are not the limit (all live windows are 20 cells; the label builder above also puts a **leading blank** in
front of every string it builds, which costs one of the 12 visible places).

**Two candidate mechanisms**, both give "12 visible, the 13th lost": (a) a narrow window (`W = 7` cells -> 13 units, one used by a leading
blank; MEETING has such a label window, `+0x3c = 7`, docs/text-engine.md 4.3), (b) a 12-byte copy buffer.  They differ in what the RAM
shows: take a dump with the Event list open and run `python -I -X utf8 tools/re/layout/wintext.py build/emu/<dump>.bin Nakaga`:
`cells=7` and a code array containing all 13 characters -> (a); `n=12` with the letters missing -> (b).  This decides whether the
proportional font helps: under (a) a 7-cell window holds 13 units of 12 px = 156 px minus the blank (about 15 characters of the narrow
font), under (b) it does not help at all.

**What was done.**  Limit for a person name **12 characters** (docs/style-guide.md 7.1 updated, row `person.name` in the limits file).
All 13-character names went one step down the ladder, 189 distinct Japanese names (132 BPINFO players, real coaches and players from
the staff tables, and the family-first Asian names): `Isao Nakagaki` -> `I. Nakagaki` (115 px proportional / 132 px plain),
`Takami Hirano` -> `T. Hirano`; already abbreviated ones keep a unique initial without the blank (`T.Ishiwatari`); family-first names
(`Park Changsok` -> `Park C.`); `Constantino F` -> `Constant. F`.  Same-family collisions exist already in the database (`T. Watanabe`
is five players) and are not new.  The reported name is only the first example (154 by the regular rule, 35 by the explicit table).  `tools/re/layout/mk_layout_edits.py` holds the rules; after the merge it
only emits what is still over the limit.

## 4. Sponsor names overflow: `Aogashi Steamship`  (PROVEN cause, INFERRED width)

A sponsor name is the hometown token `#to#` + a fixed suffix (13 suffix texts: `#to#汽船` ...).  `#to#` expands to the player's hometown
name (3 kanji = 6 cells for 981 of the 1,248 short-table names, up to 12; English 3-17 letters, 7 for the short table).  Japanese total: typically
12 cells, at most 18.  English `Aogashi Steamship` = 7 + 10 = 17 cells = 204 px, `Aogashi Civic Society` = 252 px.  The reported
overflow of the 17-cell name puts the column at about 16 cells (192 px) -> suffix **including its leading blank <= 9 characters** for a
town of up to 7 letters (row `sponsor.suffix`).  Edits: `Steamship` -> `Shipping`, `Civic Society` -> `Society`, `Fisheries` ->
`Fishery`, `Livestock` -> `Farming` (the other nine were already <= 9).  Proportional font: `Aogashi Shipping` = 172 px.
**Open**: the true column width (needs the sponsor list in a dump: `wintext.py` with filter `#to#`-expanded names, or the x of the next
column) and the real length of `#to#` (which of the two town tables the expander uses is UNKNOWN); for towns longer than 7 letters no
suffix of these lengths fits, a `#to#` abbreviation table would be the fix.

## 5. `This Season` / player-card cells (FIRE.BIN, ABROAD.BIN)  (partly PROVEN)

Table `tbl@6c0c` (FIRE) / `tbl@7e78` (ABROAD): five cells of one player-card block, Japanese widths in cells: `本年成績    ` 12,
`%4d試合出場` 12, `%8d得点` 12, `    平均評価` 12, `%7d.%02d点` 12.  English was 12 (`This Season `), 8, **14** (`%8d goals`), 12, **14**
(`%7d.%02d pts`): two value cells ran two cells over the block.  `This Season ` is exactly as wide as the Japanese, so it does not
overflow by itself; its overlap in the screenshot comes from a neighbour (the two value cells above/below it in the same column, or a
baked texture heading) -- UNKNOWN which without the screenshot or a dump of that screen.  Edits (validator keeps `%Nd` tokens, so the
words shrink): `%8d goals` -> `%8d Gls`, `%7d.%02d pts` -> `%7d.%02d` (the row above is the `Avg Rating` label).  Left alone:
`This Season ` (if it still overlaps, `Season` is the next ladder step; the Japanese label has four trailing blanks, they are not needed).

## 6. Limits for the validator: `build/trans/layout_limits.tsv`

Generated by `python -I -X utf8 tools/re/layout/limits.py` (1,730 rows).  Columns: `scope id ja en_now ja_cells en_cells
max_cells_plain max_px_prop max_chars_prop_est basis note`.  `max_px_prop = 12 x max_cells_plain` (the pixel budget is font-independent;
`max_chars_prop_est = px / 10`).  Rows:

* `rule` (5 class rows + per-record rows): `hometown.region` 38, `hometown.prefecture` 11 (slot budget 8 / 12 bytes), `hometown.town` 7
  (short table), `person.name` **12**, `sponsor.suffix` **9** (the 13 sponsor records are listed with their status).
* `design` (1,710 rows, `cell.table` 1,403 / `cell.label` 307): the English of a table cell or one-line label is wider than the Japanese it
  replaced.  This is a **lead list, not a verdict**: a column can be wider than the Japanese, and 40 % of it is the same library strings
  repeated in the save/load overlays (AUTOSAVE 529, PLNUMSET 258, TITLE 267).  Use it to prioritise screenshots.

Integration suggestion for `tools/transcheck.py` (not done, it would change the validator contract): read this file, check
`cells_of_line(en) <= max_cells_plain` for the listed ids and classes, and for the proportional font compare the real table width with
`max_px_prop`.

## 7. Verification

* `python -I -X utf8 tools/test_layoutpatch.py` -> ALL PASSED (26 checks); `tools/test_transwork.py --quick` 294 checks, 0 failed.
* `python -I -X utf8 tools/build_patch.py --dry-run --out build/layoutD_out` -> failed 0, skipped 0; HOMETOWN.BIN reported twice
  (`overlay` text stage, `layout` code stage, +0 bytes); patch digest changes only through the English edits and the two halfwords.
* `tools/test_pipeline.py` passes (351 checks, stage 2 integration): it blanks `en` in a copy of the real database for the no-op test, and
  `build_patches` is wrapped there to default to an empty textures directory (the shipped repainted art in `translation/textures` is
  a real patch; the texture stage has `tools/test_texinject.py`).  The code path added to `build_patch.py` is a no-op unless HOMETOWN.BIN
  already differs from the original (empty-database runs are unchanged).
* Money text (stage 2): `%m` is charged 15 cells (`13 Oku 1500 Man`) by `translib._fmt_cells` / `pixelwidth`.  `winwidth.py violations` on the
  final database: cell mode 0 texts over their window, pixel mode (profile on) 27 texts (32 records), none with `%m`; they are the name-token
  worst cases (`#tkNN#` charged 13 px per cell) of NEWS / TRAINING / MEETING bubbles, see `build/integ/ww/width_violations_px.tsv` when re-run.
  15 ESTABLIS facility-cost texts that the money re-wrap had left at 4 rows in a 3-row window were rewritten to 3 rows (`tools/re/int_estab3.py`,
  `int_estab3b.py`; each line <= 39 cells with `%m` = 15).

## 8. Open measurements (next Flycast session, read-only dumps are enough)

1. Hometown screen after the patch: `Tohoku`, `Kansai`, `Nara` plain.
2. Event list and player card dump -> `wintext.py ... Nakaga` (section 3): decides window width versus copy buffer.
3. Sponsor list dump -> real column width and the `#to#` expansion (section 4).
4. FIRE / ABROAD player-card block: screenshot after the `Gls` edit; if `This Season` still overlaps, go to `Season`.
5. Club names (section 9): Flycast with a new game / rival club / match screen, a RAM watch on the club-name destination buffers (section 9.7), and
   the candidate popup of the Hometown screen (the preview text must equal the final name).

## 9. Club name guard: a composed club name can no longer overflow (stage 3, owner `ovf`)

Status words as above.  Nothing here was run in Flycast; every claim about the SH-4 code is **PROVEN** by executing the patched bytes of the
real built overlays in `tools/sh4sim.py` (section 9.5) unless it says INFERRED / UNKNOWN.

### 9.1 Where the name is built (re-derived from the code)

`FUN_8c2e072a` (HOMETOWN numbering; file offset `signature + 0x90`, 232 bytes, byte-identical in the 20 overlays of `layoutpatch.CLUB_OVERLAYS`,
`tools/re/ovf_bodycheck.py`) is `compose(town r4, pref r5, word r6, mode r7, out @sp)`:

```
frame 76 bytes: temp = sp+12 (64 bytes)        word = poolword[pool]  (pool outside 1..54 -> debug print, index 0)
mode 0 / 2:  town_short(town, temp) / pref_short(pref, temp)  ->  sprintf(out, "%s%s", temp, word)      (patched: "%s %s")
mode 1 / 3:  the same, sprintf(out, "%s%s", word, temp)
returns strlen(out)
```

* The short name is built in the composer's own 64-byte `temp`, so the **only unbounded write is the final `sprintf` into `out`**, the caller's
  buffer (5th argument).  `town_short` / `pref_short` write at most the table string (<= 12 bytes in the short table).
* The 14-byte `#sname#` field (struct offset 0x103a, next field 0x1048, `docs/expansion/field-widths.md` section 3) is what the design
  assumed.  What the composer callers really pass (`tools/re/ovf_callsites.py`; 17 overlays: 16 with 5 call sites each, EVENT with 1; HOMETOWN, SCHE0
  and SCHE1 carry the library copy but have no caller): obj + 0x1ce (1 site in 16 overlays), obj + 0x58 and obj + 0x48 (3 sites, 16-byte stride), a stack temp
  `sp+16` that the caller copies `min(len, 20)` bytes of into a record field at +14 (1 site), and in EVENT a pointer from the table `0x8c42a4c4`.
  **UNKNOWN**: the exact size of each of those fields (no size is visible at the call; 14 is the documented size of the name fields and the
  16-byte stride fits 14 + 2).  The user's own `sname` is written by N_ENTRY (`0x8c014dd0` copy of the typed name into struct +0x102c / +0x103a,
  `tools/re/ovf_snamesites.py`), not by the composer; the composer feeds rival / match / record names.
* **The Japanese original had no cap either.**  With the Japanese tables (cut of the 2-byte suffix, half-width kana words of 3 to 10 bytes) 2,686 of the
  68,640 municipality + word pairs (3.9 %) are 14 to 20 bytes, and 65 of the 2,695 prefecture + word pairs.  So either those buffers are larger than 14 at
  the sites that produce such names, or the original overflows silently.  The guard assumes the worst case (14 bytes) because a wrong guess costs a corrupted
  neighbour field, while a cut name costs a letter.

### 9.2 What the English builds need (measured on the built overlays)

`python -I -X utf8 tools/build_patch.py --dry-run --dump build/ovf_dump3 --out build/ovf_out --repack on --share dup --append-safe --proportional-font on --refit on`,
then `tools/re/ovf_pairs.py`: 1,248 municipalities (short table at file 0x43854, 1-based) x 55 club words (pool at 0x422c8); town 2 to 12 characters (mean 6.5),
word 4 to 8 (`Dummy` ... `Palentia`; the 8-letter words are `Topolino`, `Braovize`, `Colmillo`, `Elfshrit`, `Avanzare`, `Palentia`), so `town + ' ' + word` is 7 to 21 characters:

| composed length (with the blank) | pairs | share |
|---|---|---|
| <= 13 | 35,283 | 51.4 % |
| 14 | 10,502 | 15.3 % |
| 15 | 8,709 | 12.7 % |
| 16 to 21 | 14,146 | 20.6 % |
| **over 13** | **33,357** | **48.6 %** |

(22,855 without the blank.)  The stage-2 figure of 7,873 (11.5 %) over 13 characters does **not** reproduce here for either variant; it must have been measured
on another set (for example only the 7-letter short names of `layout_limits.tsv`).  The guard does not depend on the number: it bounds every pair.

### 9.3 The rule

`room = 12` (a 14-byte buffer holds 13 characters + NUL; the blank takes one), `lw = len(word)`, `ls = len(short)`:

1. `ls + 1 + lw <= 13`: the name is kept as it is (51.4 % of the pairs).
2. Otherwise the **town** is cut: `cap = max(12 - lw, 4)`, the town becomes `short[:cap-1] + '.'` (`dot=True`, default) or `short[:cap]`.
   `Akabira` + `Tempest` -> `Akab. Tempest`, `Abashiri` + `Sting` -> `Abashi. Sting`, `Kagoshima` + `Mythos` -> `Kagos. Mythos`, `Mythos` + `Kagoshima` -> `Mythos Kagos.`.
3. The word is never cut unless it is longer than `12 - 4 = 8` characters (none is; a hypothetical 12-letter word is cut to 8 and the town keeps 4):
   `word_len = min(lw, 12 - town_len)`.
4. The result is always NUL terminated; the join never writes more than `town_len + 1 + word_len + 1 <= 14` bytes.  The reference model is
   `tools/re/ovf_sim.reference`; the SH-4 code is compared with it byte for byte.

Why a dot, why at least 4: a bare prefix (`Asahi Shadows`) reads like a real place that is not the player's town; the dot marks an abbreviation, as `T. Hirano`
does for people.  `dot=False` gives the bare prefix.  The Japanese original cut the town name silently too (the 市 / 町 suffix).  The minimum of 4 only matters
for 8-letter words (`Gin. Topolino`, `Aom. Avanzare`).  A cut inside a double-byte character is possible only for Japanese data (kanji town + long kana word);
English data is single-byte.

How much is cut, by word length (share of the 1,248 towns): 4 letters 17.9 %, 5: 31.3 %, 6: 46.8 %, 7: 65.7 %, 8: 80.9 % (33,357 cut pairs: 448 / 7,429 / 8,760 /
10,660 / 6,060).  About half of the *possible* names are cut, but a player picks one of a handful of candidates.  A **text-side improvement** (not done: it belongs to
the place list and club-word owners) would be a second short form for the 584 municipalities of more than 6 letters (`Asahikawa` -> `Asahik.`); with towns of
at most 6 letters 5,624 of their 36,520 pairs (15 %) still need a cut.

### 9.4 Implementation (`tools/layoutpatch.py`)

API for the integrator: `layoutpatch.patch_clubnames(data, name, guard=True, dot=True, room=12)` and `layoutpatch.make_patches(read_extracted, current,
guard=True, dot=True, room=12)`.  `build_patch.py` already calls `make_patches(read_extracted, res.patches)`, so **the guard ships by default with no edit**.  A build
flag `--club-guard off` would pass `guard=False` (the old, unbounded join: 5 bytes per overlay, 10 in HOMETOWN with the list spacer) and `--club-dot off` would pass
`dot=False`; `room` is an API-only escape hatch (8..100) for the day a RAM test proves larger buffers.

* **No cave and no new literal.**  The composer (232 bytes) is **replaced in place** by a bounded composer of 224 bytes assembled with `tools/sh4asm2.py`
  (source `layoutpatch._COMP_*`).  It uses the composer's own literal slots (strlen at +0x102, club-word table at +0x11a) and `bsr` to `town_short` / `pref_short`,
  so the font / money caves (0x8c299800..0x8c299c00) and the planned bank are not touched.  The replaced body is checked by SHA-256 in all 20 overlays, the
  literals must lie inside the overlay, a second application is refused (the signature is gone).  Nop padding fills the 8 bytes up to the old literal pool.
* **HOMETOWN is special.**  It carries the same library copy but never calls it (no literal and no `bsr` to `0x8c2e072a`; checked at patch time, the patch refuses otherwise)
  and has an inline copy of the 4-candidate builder: four `sprintf("%s %s", ...)` calls (0x1b7e, 0x1b92, 0x1bd8, 0x1be8) through **one literal each** (word buffer
  `0x8c336a14`, format, sprintf `0x8c014d80`, file 0x1cd0 / 0x1cd4 / 0x1cd8, each loaded exactly 4 times) into stack buffers of at least 56 bytes.  No overflow there, but
  the popup would show `Kagoshima Mythos` while the club becomes `Kagos. Mythos`.  With the guard the dead composer copy is replaced by a 230-byte
  **sprintf-compatible join entry** (`r4` = destination, `@sp` format, `@sp+4` / `@sp+8` the two strings; the one that equals the word buffer is the word; the town is
  first copied into the routine's own frame, so the caller's strings are never modified) and the literal at 0x1cd8 is retargeted to it (4 more bytes differ).  The preview equals the final name.
* `tools/re/hnm/hnm_sim_club.py` now shows the unguarded join (`guard=False`); HOMETOWN's own composer copy no longer exists (dead).

### 9.5 Verification (all executed in the interpreter, nothing launched)

* `python -I -X utf8 tools/re/ovf_sim.py build/ovf_dump3/FLOW_PRG/BPMATCH.BIN --all --robust`: **142,670 composer runs** on the real built overlay (all 68,640 municipality + word pairs in
  modes 0 and 1, all 49 x 55 prefecture + word pairs in modes 2 and 3): **0 problems**.  Checked per run: no store outside the first 14 bytes of `out` and the stack frame
  (write watching), canary bytes 14..47 intact, NUL present, `len <= 13`, return value equals the length, stack balanced, result equal to the reference rule.  Out-of-range arguments
  (town 0 / -1 / 1249 / 5000, prefecture -1 / 49 / 100, word -1 / 55 / 1000, mode 4..7 / -1): 0 problems.  (Output kept in `build/ovf_all_bpmatch.txt`.)
* HOMETOWN's popup join, same exhaustive set in both orders (`build/ovf_all_hometown_popup.txt`): 142,670 runs, 0 problems, the caller's strings untouched.
* `python -I -X utf8 tools/re/ovf_all20.py build/ovf_dump3 3000` (`build/ovf_all20.txt`): 3,000 random runs plus the argument sweep in each of the **20 overlays** (their own load
  bases 0x8c2d0000 / 0x8c4d0000 / 0x8c8d0000 and tables): 0 problems.  CSAVE3.BIN is linked against another 1ST_READ build (`docs/font-hook-notes.md`); its library slots are hooked from its own literals.
* `python -I -X utf8 tools/test_layoutpatch.py`: ALL PASSED (101 checks, about 50 s): patch layout, refusals, the executed composer (original `KagoshiMythos`, unguarded
  `Kagoshima Mythos`, guarded `Kagos. Mythos`), Japanese-pool runs, `dot` / `room`, three other overlays, the popup join, the refusal to replace a referenced composer copy.
* Distribution on the built overlays (68,640 pairs, mode 0): **33,357 (48.6 %) needed a cut**, 35,283 unchanged; result lengths 7: 4, 8: 156, 9: 1,505, 10: 4,654, 11: 7,516,
  12: 10,375, 13: 44,430, never more.  Prefecture + word: 1,292 of 2,695 cut.  Examples: `Akabira Tempest` -> `Akab. Tempest`, `Abashiri Sting` -> `Abashi. Sting`, `Murakami Mistral` -> `Mura. Mistral`,
  `Ginowan Topolino` -> `Gin. Topolino`.
* Not run: `tools/test_pipeline.py` (the integrator runs it once); the guard is part of the default `make_patches`, the patch digest of the standard build changes.

### 9.6 Other places that build or copy club names

* **Composer callers** (9.1): 17 overlays, 81 call sites, all go through the guarded composer; EVENT's single site writes to a table buffer of unknown size.
* **`#sname#` / `#YOU#` expander** (`sprintf(msgbuf, fmt, struct + 0x103a)`, two sites in each of 98 overlays; EVENT 0x1a4a / 0x160b8 and N_ENTRY 0xcf8 / 0x6418 / 0x6424 are the
  extra readers and the writer): reads a NUL-terminated string into big message buffers, no size issue.  N_ENTRY copies the typed names with `0x8c014dd0` (unbounded copy of the typed
  text into +0x102c and +0x103a); the typing window limits them (`docs/expansion/field-widths.md` 2.6).
* **Save slots, schedule, Event list**: no separate composer exists.  They call the library composer (AUTOSAVE, CSAVE*, LOAD, EVENT ... in the list above) or copy a finished name; the
  stack-temp site copies at most 20 bytes into a field at +14, a 13-character name fits.
* **NENREP.BIN** keeps a club pool in **8-byte slots, index-addressed** (`docs/uncovered-text.md`): an 8-letter club word (`Topolino` ...) does not fit a 7 + NUL slot there; check when
  the annual report is touched (not part of this change; the slot cannot move).
* A narrower (9-byte) copy of a **club name** was not found in the code that composes it; the 9-byte fields in `docs/expansion/field-widths.md` are person-name or label fields.  UNKNOWN whether
  any screen copies the 14-byte name into a narrower one (clipping on display is a layout question, section 3).
* The 14-byte **person-name** buffers are a different matter (`docs/style-guide.md` 7.1); this guard only concerns composed club names.

### 9.7 Open items (need Flycast; read-only RAM dumps are enough)

1. Which fields the composer writes into and how big they are: dump RAM with a rival club shown, find the names, compare the distance to the next field (record + 0x1ce, + 0x48 / 0x58).
   If they are larger than 14 (the Japanese data suggests it for some sites), raise `room` and the cut share drops.
2. The Hometown candidate popup: confirm the four previews equal the final names, and whether the popup clips the 13th letter (`Kagos. Mythos` is 13).
3. A new game with a 13-character composed rival name: the neighbour field at struct 0x1048 must stay intact (it was the reason for this work).

### 9.8 Integration result on the real trial discs prop6 / prop6r (integrator, 2026-11-11)

* `tools/build_patch.py` calls the guard through `apply_layout_patches` -> `layoutpatch.make_patches(..., guard, dot)`; new flags `--club-guard on|off` (default on)
  and `--club-dot on|off` (default on) set those two arguments; the layout FileReport of each of the 20 overlays carries the note
  `club-name composer bounded to 13 chars + NUL`.  `room` stays at its default 12.  The guard runs only when HOMETOWN.BIN is part of the patch set (always true for a real build).
* Built with `--repack on --share dup --append-safe --proportional-font on --strict` (prop6) and the same plus `--refit on` (prop6r): 0 failed, 0 skipped,
  `verify_disc` OK for both.  Simulator check of the REAL overlays of both builds (`tools/re/int_clubs.py DUMP`, `tools/re/ovf_all20.py DUMP 3000`): 142,670 composer runs
  on BPMATCH and 142,670 popup joins on HOMETOWN, 0 problems each (length <= 13 + NUL, no write outside the buffer, byte equal to the reference rule), all 20 overlays 0 problems.

| | prop6 (no refit) | prop6r (`--refit on`) |
|---|---|---|
| town + word pairs cut (of 68,640) | 32,031 (46.7 %) | 33,357 (48.6 %) |
| unchanged | 36,609 | 35,283 |
| result length 13 | 42,884 | 44,430 |
| result length 12 / 11 / 10 | 10,565 / 7,662 / 5,012 | 10,375 / 7,516 / 4,654 |
| result length 9 or less | 2,517 | 1,665 |
| longest | 13 | 13 |
| prefecture + word pairs cut (of 2,695) | 1,216 | 1,292 |

Cut share by word length (both builds): 3 letters 8.9 % (prop6 only), 4: 17.9 %, 5: 31.3 %, 6: 46.8 %, 7: 65.7 %, 8: 80.9 %.
Examples (prop6r): `Tsurugashima Palentia` -> `Tsu. Palentia`, `Toshima-mura Topolino` -> `Tos. Topolino`, `Nihonmatsu Sting` -> `Nihonm. Sting`, `Tsushima Riccio` -> `Tsush. Riccio`,
`Kisarazu Tigre` -> `Kisara. Tigre`, `Nagoya Corient` -> `Nago. Corient`.

* **Correction of the stage-2 number:** the stage-2 figure "7,873 of 68,640 (11.5 %) over 13" does not reproduce (33,357 / 22,855 over 13 with / without the blank).  The skeptic
  found the nearest value, 7,792, as "over 15 without the blank"; treat 7,873 as obsolete.
* **Known cosmetic issue (FIXED on the text side, see 9.9; originally left open because the composer has only 8 spare bytes of its 232-byte slot):** when the cut lands right after a separator the result looks odd: `N. Hiroshima` + `Topolino` -> `N. . Topolino`
  (720 shapes) and `Minami-Arpe`-style towns -> `Minami-. Arpe` (196 shapes), 916 of the 69,298 cut results of the refit build (1.3 %).  Fix options: (a) text side: a second short form for the 106 town
  shorts that contain a space, hyphen or dot; (b) code side: drop a trailing ' ' / '-' / '.' before writing the dot (about 30 bytes more than the slot has).
* Still UNPROVEN (needs Flycast): the real size of the destination buffers (the guard assumes 14 bytes), whether the popup clips a 13-character name, and that the field at struct 0x1048 stays intact.
  See 9.7 for the checklist.

### 9.9 Odd cuts fixed on the text side (stage 3, owner `pol`)

The cosmetic issue of 9.8 (`N. . Topolino`, `Minami-. Arpe`: the cut lands on a dot, blank or hyphen of the town short form) is gone, with **no code change**.

* **What was wrong.**  107 of the 1,270 slots of the town short table (`tbl@43858`, the pointer table the composer reads; the composer uses slots 1 to 1,248, so 106 of the 107 are reachable, `Kume Is` at slot 1,249 is not) contained a blank, hyphen or dot: directional counties
  (`N Tsugaru`, `W. Kanbara`, `E.Shirakawa`, `Minami-Aizu`, `Mid Koma`, `U. Ina`, `L. Takai`), the `H.` / `M.` city forms (`H. Murayama`, `M. Murayama`), `Ashigara Up` / `Lo`,
  `Shin-Nanyo`, `Toshima-mura` and the islands `Tane Is`, `Yaku Is`, `Kume Is`.  (The stage-3 figure of 106 counted only the 1,248 slots the composer reads.)  The composer keeps `short[:cap-1] + '.'` with
  `cap = max(12 - len(word), 4)`, so any of them cut on the first 3 to 7 characters gave `N. .`, `Minami-.`, `Tane .` or `E.Ib.`.
* **What it is now.**  Every one of the 107 is one letters-only word in the convention the table already used for `Kamiiso`, `Shimokita`, `Nishitama`, `Higashiiwai`:
  direction word fused to the place (N -> `Kita`, S -> `Minami`, E / H. -> `Higashi`, W -> `Nishi`, Mid -> `Naka`, U -> `Kami`, L -> `Shimo`), the place part cut on a vowel when the
  slot (12 bytes = 11 letters; 8 bytes = 7 letters) is too small.  Examples: `N Tsugaru` -> `Kitatsugaru`, `W Tsugaru` -> `Nishitsuga`, `N. Hiroshima` -> `Kitahiro`, `E.Hiroshima` -> `Higashihiro`,
  `W. Kanbara` -> `Nishikanba`, `Minami-Aizu` -> `Minamiaizu`, `M. Murayama` -> `Musashimura`, `Ashigara Up` -> `Kamiashiga`, `Toshima-mura` -> `Toshima`, `Tane Is` -> `Tane`.
  All 107 are `[A-Z][a-z]+`, none exceeds its slot (`len + 1 <= max_bytes`), so the build relocates nothing extra.  Cut result: `Kitatsugaru` + `Topolino` -> `Kit. Topolino`,
  `Higashishi` + `Sting` -> `Higash. Sting`, `Kitahiro` + `Mythos` -> `Kitah. Mythos`; the direction survives the cut, which also separates the sibling counties
  (`Kitamu.` / `Nishim.` / `Higash.` + `Sting`) that the old `N. ` / `W. ` / `E. ` forms made identical.
* **Where.**  The short table is a library copy: the same 107 records exist in **32 translation files** (HOMETOWN.BIN and every club-name overlay, CSAVE3.BIN with a 1,268-slot copy where
  the indices are shifted by two), 3,424 `en` values (32 x 107) carry the new forms (checked by `tools/re/skp_perfile.py`).  Only the `en` text changed, byte-exact line edits, no other field.  The Hometown list fields (the 126-byte `recarr` records and the 19
  `orphan` copies of the same `ja`, shown in the list) were **not** touched, so the list keeps its own text for the same Japanese (as for the 103 groups that already differ, `Ako-gun` / `Ako`); a
  same-`ja` check runs inside each short table (one `en` per `ja`).  Not touched either: NENREP.BIN (an in-place 12-byte stride copy of the same town names, `Kitahiro.`, `W Tsugaru`; no composer in that
  overlay) and the two slot-forced forms that exist only in AUTOSAVE (`Hachin.`, idx 94) and EVENT (`Okushi.`, idx 20); neither gives an odd shape.
* **Cost.**  The fused forms are 1 to 3 letters longer than the old ones, so a few more pairs need a cut: refit build 33,357 -> **33,615** of 68,640 town + word pairs (48.6 % -> 49.0 %), plain build
  32,031 -> **32,343** (46.7 % -> 47.1 %); by word length 4 letters 19.6 %, 5: 32.2 %, 6: 47.0 %, 7: 65.5 %, 8: 80.8 %.  Longest result still 13 characters.
* **Same-form pairs (skeptic check, `tools/re/skp_dups.py`).**  The table already had 115 groups of identical short forms (city + county of the same name, `Katsushika` x3); the change adds 4:
  `Higashimura` (Yamagata county / Tokyo city), `Higashimat` (Saitama / Nagasaki), `Higashiyam` (Tokyo / Yamanashi), `Toshima` (Toshima village and Toshima ward, both Tokyo; `Toshima-mura` was distinct).
  Harmless for the composer (no word is looked up by town); if the Toshima pair matters, `Toshimamura` (11 letters) fits the slot.
* **Verification** (all executed, nothing launched; trial dumps built with `--dry-run --dump`, deleted afterwards): `tools/re/pol_shapes.py DUMP` runs the REAL patched composer of the dump
  in the simulator for all 68,640 town + word pairs in modes 0 / 1 and the prefecture pairs in modes 2 / 3 and counts the shapes `. .`, `-.`, `..`, ` .`, `- `:

| | before (refit build) | after refit build | after plain build |
|---|---|---|---|
| composer runs / problems | 142,670 / 0 | 142,670 / 0 | 142,670 / 0 |
| `. .` / ` .` / `-.` / `..` | 504 / 720 / 196 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

  `tools/re/int_clubs.py` (BPMATCH composer + HOMETOWN popup join, both builds) and `tools/re/ovf_all20.py DUMP 3000` (20 overlays): 0 problems.  `tools/re/pol_tables20.py DUMP` finds no odd shape in the
  town table of any of the 20 club overlays.  `tools/re/pol_baseline.py DUMP JSONL` reproduces the before numbers (33,357 cut pairs, 1,420 odd shape hits counting both orders) from a jsonl copy without a build.
  `python -I -X utf8 tools/refit.py validate` OK, `tools/test_transwork.py` 668 checks 0 failed.
* **Re-running / changing a form.**  `tools/re/pol_apply.py` holds the table (index -> ja, new form) and `pol_old.py` the old forms; it edits by `ja` + old form, so a table that is not the
  town short table is never touched, and a second run changes nothing.

### 9.10 Club words follow the logo art (2026-11-12): figures re-counted

The pool words now read like the logos (`docs/style-guide.md` 12.2, `translation/clubwords_art.tsv`).  Measured on the built overlays of the trial disc `cw1`
(`tools/re/fin_clubs.py build/trial/cw1 cw1`: 142,670 + 137,280 composer runs, 0 problems, 0 odd shapes; `tools/re/cw_cutstats.py` on its `HOMETOWN.BIN`, 1,248 towns x 54 words):

| build | pairs | cut | word itself cut | longest |
|---|---:|---:|---:|---:|
| plain (slot-fit pool: `Avalanc`, `Monolit`, `Topolin`, `Colmill`, `Corrien`, `Herenci`, `Panther`, `Cie`, `Ros`) | 67,392 | 33,711 (50.0 %) | 2,494 (`Blau Wiese`, `Elf Schritt`) | 13 |
| `--refit on` (art spellings: `Avalanche`, `Corriente` ... in full) | 67,392 | 35,764 (53.1 %) | 4,868 (+ `Avalanche`, `Corriente`) | 13 |

Census on the real overlays (55 words incl. `Dummy Team`, 68,640 pairs): 33,635 (49.0 %) cut.  Cut share by word length (plain): 3: 11.3 %, 4: 19.6 %, 5: 32.2 %, 6: 47.0 %, 7: 65.5 %, 8: 80.8 %,
10: 99.8 %, 11: 100 %; with refit also 9: 95.1 %.  Result lengths stay <= 13.

**Consequence.**  The guard keeps the town at 4 characters at least and cuts the WORD to `12 - town` = 8 letters when it is longer than 8, so the logo words of 9 to 11 letters
show shortened in a composed name only (`Tsu. Elf Schr`, `Ton. Blau Wie`, `Kom. Corrient`); standalone (word lists, commentary, messages) they are complete.  A full fix needs a shorter minimum
town (3 would free the 9-letter words, nothing frees 10 and 11) in the assembled composer of `tools/layoutpatch.py` (SHA-checked, sim-verified): not done, open decision for the owner.

## 10. Cell-count alignment with a proportional font: the shirt-number column and the clipped player-card panel  (second playtest, owner `aln`)

Status words as above.  Nothing here was seen in Flycast: the cause is read from the overlays' code (`tools/re/aln_dis.py`, capstone with FPU decoding) and every fix is executed on the REAL overlay bytes in `tools/sh4sim.py`
(`tools/test_alignfix.py`, 19 tests).  The user's disc `build/trial/hsk_full1` was read back (`tools/re/aln_discprobe.py`): the panel code, the strlen literals and the hooks are intact there, so the fix composes on the current pipeline output.

| # | Finding (second playtest) | Root cause | Status | Fix |
|---|---|---|---|---|
| 1 | shirt-number column ragged (`3`, `4` at the right edge, `5` shifted left ...) | each list row is ONE string: name, blanks up to byte 14, the `%2d` number; the proportional name width differs from 12 px per character, so the number lands at a different x per name | **PROVEN** (code + simulator) | cave `at_snap`: the blanks of a run of two or more resynchronise the pen with the fixed-cell grid (10.2) |
| 2 | player-card panel (Captain Select, Event, Ending Options) clipped at the right: `Tokyc`, `Seasor` | each of the 11 cells is placed at `x = anchor - 12 * strlen(text)`; the proportional text is WIDER than 12 px per character (`Tokyo` 65 px, `Season` 75, `Average` 86, `Age 25` 74) so it ends 2 to 5 px past the anchor, where the panel edge cuts it | **PROVEN** that the text overflows its anchor by 2 to 5 px (arithmetic on the real code + table); that the edge cuts exactly there is **INFERRED** from the symptom | `pw3` replaces strlen in the panel code, the `* 4` of the idiom becomes a nop: `x = anchor - 3 * ceil(P / 3)` (10.3) |
| 3b | TV card capital starts on the capsule and runs past the plate | money owner's: numbers in 10.5 | - | not edited here |

### 10.1 The general cause, PROVEN

The text engine never measures text.  `tsString` lays a window out cell by cell (12 px per half-width byte, 24 px per full-width glyph) and the callers that want a column, a right edge or a
gap do the arithmetic themselves **in cells**: pad a field with blanks, or compute `x = anchor - 12 * strlen(s)`.  The proportional font changes the pixels per character, not the callers' arithmetic.
`docs/proportional-font.md` s8 item 8 listed this as UNKNOWN; it is now located (`tools/re/aln_scan12.py` finds the `* 12` idiom: about 140 hits next to a window x store in 25 overlays,
60 of them the shared panel below, the rest are a lead list, 10.4).  The window carries no alignment flag: `+0x38` is passed to the glyph blit as draw flags only, the layout reads x0 (`+0x4a`) and advances.

### 10.2 Columns made by blank padding  (finding 1, PROVEN)

`FLOW_PRG/PLNUMSET.BIN`, row builder at file offset `0x1418` (22 rows, one 20 byte slot per row at `list + 0x36 + 20 * i`): the player's name is copied into the slot, every NUL up to byte 20 becomes a blank
(loop at `0x1510`), then `sprintf(row + 14, "%2d", number)` (`0x155e`, format `0x34b94`) or `sprintf(row + 14, " ")` for a player without a number (`0x1530`).  The number column is therefore byte 14 / 15, x0 + 12 * 14.
Original: names of at most 14 bytes, a number always at the same pixel.  Proportional: the digit lands at `x0 + P(name) + 12 * (14 - len)`, i.e. `12 * 14 + (P - 12 * len)`: with the real table and eight sample names the digit sits at x0 + 171 .. 185 (`Ito` 171, `Li` 172, `Takahashi` 176, `Isao Nakagak` 179, `Okamoto` 182, `Nakagawa` 185), 14 px between names:
the short ones left, the wide-lettered ones at the right edge, exactly "all over the place".  The right-hand panel of the same screen (builder at `0x1302`) is a 4 row x 12 cell buffer (52 blanks, newlines at bytes 12, 25, 38) and has the same property.

**Wiring superseded in stage 8h (section 10.9): the paragraph below describes the stage 8b wiring, in which the table path of the font cave ended in `bra at_snap` and EVERY proportional draw of every overlay went through the snap.  Now `at_snap` is entered only by the overlays in `fontpatch.ALIGN_SNAP_FILES` (PLNUMSET), through their hook literal; the font cave is not changed at all.  The rule itself (what the snap computes) is unchanged.**

**Fix (cave `font.align`, label `at_snap`).**  The table path of the advance routine ends in `rts ; nop` (cave +0x1a); with `align` that pair becomes `bra at_snap ; nop` (the only changed cave word, entries and the 98 hooks are byte-identical).
For a BLANK (code `0x8000`, low byte 0) that belongs to a run of at least two blanks (the previous OR the next code is a blank) and is followed, after the rest of the run and any colour controls, by a glyph (not by a newline or the end),
the advance becomes `max(4, x0 + 12 * (units + 1) - pen)`: the pixel the fixed-cell layout reaches after this blank.  Narrow text gets the slack added to its first pad blank, wide text (13 px letters) makes the pad blanks shrink (down to 4 px each) so
the column still lands on the grid.  A single blank between words keeps the table advance; runs at the end of a row do nothing.  Registers: r0 to r5 and the T bit only (the same as the hook), reads `@(4,r15)` (the loop index, a slot of the layout's frame: the same
in all 98 copies, executed in all 98), window `+0x30 / +0x22 / +0x4a`, pen r10 and units r11 of variant A (B and C hooks are not supported: `align_fix` needs `variants='A'`).
Only for windows with advance 24 (the table path); other windows keep `A >> 1` and are already on their grid.

**Verified on the real function.**  `tools/test_alignfix.py` lays out the shirt-number rows (`Ito`, `Kenji`, `Takahashi`, `Nakagawa`, `Isao Nakagak`, `Wanyama Wang`, `Li`, `Okamoto`) with the real patched layout function of PLNUMSET.BIN, real table, real cave:
the digit is at x0 + 180 for every name (one and two digit numbers; without the fix six different x, 171 to 185), word spaces and ordinary text are identical with and without the fix
(`The goalkeeper is injured.`, `Hello, World! iiii WWWW` ...), the control build (all-12 table) is bit-identical to the ORIGINAL layout with the fix on (blank runs and all), leading runs (`   7`), runs before a colour code, runs at a row end and
after a newline, 13 px overshoot, full-width glyphs.  The wrap test (H2) sees the same pen positions as the original cell rule at the grid, so the number cannot wrap earlier than in the Japanese game.

**Limit.**  Right-aligned TEXT in a padded field (`strncpy(b + 37 + (12 - len), money, len)` of the scout panel) starts on the grid but may end a few pixels beyond the field end when the text is wider than 12 px per character
(the compact money form of s9 / docs/number-formats.md 4.7 is the answer there).  English names are at most 12 letters (style guide), so at least two pad blanks always precede the shirt number.

### 10.3 Right-anchored cells  (finding 2, PROVEN arithmetic, INFERRED clip edge)

The player card (name, age, hometown, years, salary, position, `Season`, apps, goals, `Average`, points: 11 `tsString` windows of 20 cells created by the default constructor `0x4f6c` and filled by the setters at
CAP_SLCT `0x9300..0x95a8`) is placed by one function per state (CAP_SLCT `0x9d48..0xa340`, 20 idioms).  Every cell uses the same compiler idiom
`mov r2,r1 ; shll r2 ; add r1,r2 ; mov r12,r1 ; shll2 r2 ; sub r2,r1 ; mov.w r1,@(0x4a,rW)`: `x = anchor(r12) - 12 * len`, where `len` is the `strlen` the setter returns and stores at `obj + 64 / 72 / ... / 144`.
The Japanese text of a cell is `len` bytes = `len / 2` glyphs of 24 px = `12 * len` px; the English text is `P` px.  With the table, `Tokyo` is 65 px for 60 assumed, `Season` 75 / 72, `Average` 86 / 84, `Age 25` 74 / 72,
`1/2 yrs` 81 / 84 (fits), `3100 man` 97 / 96: the text starts 12 * len px left of the anchor and ends P - 12 * len px right of it.

The same code is in **three** overlays, byte for byte (offsets relative to the first idiom are identical): `CAP_SLCT.BIN` (idioms from `0x9f9a`), `ENDOPT.BIN` (`0xfad2`), `EVENT.BIN` (`0x289aa`); the Event info panel of the playtest is EVENT's.

**Fix (`fontpatch.panel_scan` / `panel_edits`, signature located, same size, refuses anything else).**  Per overlay 8 literal pools that hold the libc `strlen` (`0x8c014de4`; 18 loads, all inside the panel block, every load checked) are
redirected to `pw3` (cave `font.align`, `0x8c29977c`), a drop-in strlen (r4 = text, r0 = result, r1 and r2 preserved) that returns `ceil(P / 3)` for the pixel width `P` of the byte string with the table (two byte glyphs 24 px, half-width
katakana by table, blank = table index 0, controls 0); and 18 of the 20 `shll2 rL` of the idioms (`* 4`) become `nop` (the 2 salary idioms keep theirs, 10.3a).  So `x = anchor - 3 * ceil(P / 3)`: the text ends at the anchor or at most 2 px before it.  A two byte Japanese glyph still gives
exactly 8 units = 24 px (tested: `pw3 * 3 == 12 * bytes`), and with the all-12 table `pw3` is `4 * strlen`, i.e. the original placement (tested).
Verified: the idiom arithmetic EXECUTED from the patched bytes for all 60 sites (x = anchor - 3 * len, originals: anchor - 12 * len), `pw3` against a Python model over 140 strings, and the REAL laid-out end of `Tokyo`, `Season`, `Average`, `Age 25`, `1/2 yrs`, `3100 man`, `DF`, `0 apps`, `0 goals`, `0.00 pts`,
`Isao Nakagawa`, `Hokkaido`, `Kanagawa`, `12 oku 3400 man` ... lies within 2 px of the anchor (0 to -2), whereas the unpatched placement overflowed for 8 of these 17 (`Tokyo` +5, `Kanagawa` +5, `Season` +3, `12 oku 3400 man` +3, `Average` +2, `Age 25` +2, `0 apps` +1, `GK` +1; `tools/re/aln_report.py`).

### 10.3a The salary cell keeps its `shll2`  (playtest prop10g: ghost glyph past the panel border on the Captain Select screen; trace `w1yjmbr03`, fixed 2026-11-13)

The first version of the fix nopped all 20 idioms.  The salary cell (card + 104, `Salary 1400 man`) is the exception: its setter (CAP_SLCT `0x9510`, called from the card constructor `0x96be` and from three smaller card builders
`0x9a90 / 0x9b46 / 0x9bea`) never calls `strlen`.  It formats the text with the money function (`jsr` to the overlay's money function, hooked to the money cave by `moneypatch`), stores the NUL at `buf[r0]`, hands the buffer to the window text setter
and returns **`r13` = the money function's return value = the number of bytes written = the number of CHARACTERS** (`1400 man` = 8; the hooked function writes ASCII, one byte and 12 px per character, exactly the old `12 * len`).
It is not a `pw3`, so with the `* 4` removed the cell was placed at `anchor - 3 * 8 = anchor - 24` instead of `anchor - 96`: the text ended 72 px right of the anchor and the tail of the number and the unit spilled over the panel border.

Checked for this fix (CAP_SLCT disassembled, ENDOPT and EVENT compared word by word):

| item | result |
|---|---|
| the other setters `0x9300 0x9364 0x93ca 0x9452 0x9478 0x94be 0x9544 0x9576 0x95a8` | each ends `mov.l lit,r2 ; jsr @r2 ; mov r14,r4 ; (epilogue) ; rts` with `lit` one of the 8 patched strlen pools (`0x9354`, `0x9608`) and returns that `r0`: pw3 after the patch.  The name cell (card + 64) is `jsr strlen` at `0x9652` (pool `0x9790`).  Lengths +112 / +136 and the placeholder lengths are stored by the card constructor `0x9234 / 0x926e`, which load pool `0x9354`: pw3 |
| ENDOPT / EVENT salary setter | the instruction words of `0x9300 .. 0x9d48 .. 0xa340` equal CAP_SLCT's (offset by `0x5b38` / `0x1ea10`); only the literal pools differ.  Their money literal is the overlay's money function (ENDOPT `0x52b0`, EVENT `0x194b0`), found and hooked by `moneypatch.find_sites` like CAP_SLCT's `0xb11c`, so the return value is a character count there too |
| readers of card + 104 | the two idioms (state 1 `0xa02c`, state 2 `0xa2f0`); the third `mov #104,r0` near `0xa4a0` is a STACK slot (`@(r0,r15)`) of a call-argument push (what the callee is, was not traced), not a read of the card |
| the 18 other idioms | every one reads a field written by a pw3 setter (list above), so `* 1` is right for them |

**Fix.**  `fontpatch.salary_sites` finds the idiom by the signature `68e0 ed02 4ae0 2361 0042 1c32 c361 0842` (`mov #104,r0 ; mov.w @(r0,r14),r2 ; mov #74,r0 ; mov r2,r1 ; shll r2 ; add r1,r2 ; mov r12,r1 ; shll2 r2`: exactly 2 per
overlay, state 1 and 2), `panel_edits` nops the other 18 `shll2` and leaves the two salary words as `08 42`.  Unchanged: the 8 strlen -> `pw3` literals per overlay.  Bytes that differ from the original per panel overlay: 18 x 2 + 8 x 4 = 68 (was 72).
File offsets of the kept `shll2`: CAP_SLCT `0xa03a`, `0xa2fe`; ENDOPT `0xfb72`, `0xfe36`; EVENT `0x28a4a`, `0x28d0e`.

**Proof** (`tools/test_alignfix.py` class `Salary`): the REAL setter of each patched overlay runs in the simulator with the REAL money cave hooked into the overlay's money function; it returns 8 for `1400 man` / `3100 man` (and `len(text)` for 1, 800, 7800, 9999), then the patched idiom bytes give
`x = anchor - 12 * count` and the text (pixel width from the table) ends at the anchor (0 px for `1400 man` and `3100 man`, within 3 px for the others).  Control with the salary `shll2` nopped: `x = anchor - 24`, the text ends 72 px past the anchor
(the screenshot).  `tools/test_align_isolation.py`: 18 nops per overlay, the salary words unchanged.  **Not proven**: the look on the screen (not booted); the anchor value (`r12`, panel x + 168) was not read from the code.

### 10.4 Not covered (lead list for the next round)

`tools/re/aln_scan12.py` also reports the idiom (or its float variants) next to a window x store in CHALMODE (3), DRSGP (5), DRSGRFJ (2), DRSHRANK, DRSISEKI, DRSJAPAN, DRSLIST, DRSSRANK (3 each), ENDOPT (3 besides the panel), GETREP (4), G_INCOME (6, `(8 - len) * 12`),
NENREP (7), NEWS (4), OPTION (3), PLNUMSET (3, row y), PL_EDIT (3), PWK_EDIT (4), RECON (3), SCHE0 / SCHE1 (2 each), SELNAT (3), SPONSOR / SPONSOR2 (5 each, `(14 - len) * 12`), SUPPORT (1).  Not reviewed one by one: many compute a row y or a table
index, and money text (G_INCOME, SPONSOR) is the money owner's.  Blank-padded fields everywhere are handled by 10.2 without any site list.  `tools/re/aln_panelmap.py`, `aln_sites.py`, `aln_lenreads.py` map the panel idiom in all three copies.

### 10.5 Finding 3b: the TV card capital (for the money owner, `moneypatch.TV_CARD`, not edited here)

Geometry: the `Capital` capsule ends near x = 448, the plate near x = 616 (640-space), so the text may use x = 452 .. 612 = **160 px**.  Widths with the table (space 12, lower-case `oku` / `man`): `32 oku 5000 man` 183 px, `99 oku 9999 man` 183, `999 oku 9999 man` 195,
`5 oku 3000 man` 171 (none fits 160); `32 oku 5000M` 148, `32 oku 5000m` 147, `32oku 5000man` 159, `32oku5000man` 147 (fit).  The code in the tree draws the compact form at x = 456 (456 .. 603): fine.  If it is drawn LEFT aligned at a fixed x the end varies with the digits:
for the right edge to be exactly 612 use `x = 612 - 3 * pw3(text)` (`pw3` = `fontpatch.align_symbols(...)['pw3']`, available with `align_fix` in any cave of the font owner; or measure in Python at patch time, widths in `tools/re/layout/prop_widths.py`).  The original code drew at x = 440 with width 184, which is
what overlapped the capsule (448) and ran past the plate (616).

### 10.6 A text finding for the string owners (suspected, not verified in game)

`FLOW_PRG/PLNUMSET.BIN#34b74` ` Shirt No. %2d ` is 14 characters; the Japanese ` 背番号  %2d ` is 12 bytes and the row of the right-hand panel is 12 cells (`sprintf(b + 13, ...)` into a 52 byte buffer whose next row starts at byte 26).  The 14th character and the NUL
land on bytes 26 / 27, so the NUL ends the string there and the two rows below (position + age, ...) would not be shown for a player WITH a number.  The unnumbered label ` Squad No.  ` (`#34b64`) is exactly 12.  Suggest <= 12 characters, same wording for both (for example ` Shirt No.%2d` and ` Shirt No.  `; or ` Squad No.%2d`).
`max_bytes` 16 is the slot size, not the row width.

**Skeptic review (2026-11-12): confirmed, wider than first thought, FIXED.**  The builder (`PLNUMSET.BIN` 0x1302) blank-fills a 52 byte buffer, runs `sprintf(b + 13, label)` and `sprintf(b + 31, "%s %2d歳")`, THEN writes a newline at bytes 12, 25 and 38 and a NUL at 51 (`tools/re/aln_dis.py PLNUMSET 1302 1418`).  So the label of row 1 must be EXACTLY 12 characters after expansion (its NUL lands on byte 25, which the newline then replaces): longer, the newline eats the last digit and the NUL ends the text (position / age row lost); SHORTER, the NUL stays inside the row and ends the text just the same.  The position + age text starts at byte 31 (column 5 of row 2, right aligned to the row end in Japanese: `DF 25歳` = 7 bytes) and may have 7 characters at most (the newline at byte 38 would replace the first age digit of a longer text, the NUL would land in row 3).  Old English: ` Shirt No. %2d ` = 14 and `%s Age %2d` = 9 expanded, i.e. the shirt number was not shown (1 digit: replaced by the newline) and the age row was broken.  New (`tools/re/skp_fix_plnumset.py`, `en` of the two records only): `#34b74` ` Shirt No.%2d` (12) and `#34b84` `%s %2dyo` (7, `DF 25yo`).  Rule for any future edit: `#34b64` / `#34b74` exactly 12 characters, `#34b84` at most 7 expanded (position is 2 characters). Not verified in Flycast.

### 10.7 API and integration (for `tools/build_patch.py`, not edited here)

```python
out, rep = FPT.make_patches(read_extracted, current=res.patches, variants='A', place='tail', overrides=overrides, expect=expect,
                            glyphs=glyphs, prop_scale=prop_scale, align_fix=align_fix)        # align_fix default False (library default unchanged)
# rep['align'] = 0x8c299700 (cave), rep['pw3'] = 0x8c29977c, rep['panel'] = [(rel, 20, 8)] * 3; 3 overlays + 1ST_READ.BIN get more bytes, no file grows
# flag: --align-fix on|off (recommended default ON): reject it without --proportional-font on / glyphs, with --prop-font-variants ABC and with --prop-font-place gap1
```
`align_fix=True` raises `FontPatchError` for `variants != 'A'`, the gap1 placement, `wrap=False`, a non-zero `font.align` reserve, and for a panel overlay whose bytes are not the known panel (already patched, changed).  Registry: `font.align` `0x8c299700`, 256 bytes (224 used), below `font.cave`
(`docs/patch-engine.md` s2).  `--proportional-font control` + `align_fix` stays bit-exact (tested).  Files: `tools/fontpatch.py` (`ALIGN_SRC`, `panel_scan`, `panel_edits`, `align_bytes`), `tools/sh4asm2.py` (+ `mov.x @rm+,rn`, `mov.x rm,@-rn`, `mov.l @(d,rm),rn`, `mov.b/.w @(d,rm),r0`,
`cmp/eq #imm,r0`, `tst #imm,r0`), `tools/test_alignfix.py`, helper scripts `tools/re/aln_*.py` (docs/helper-scripts.md).

**Integrated (stage 8b).**  `tools/build_patch.py --align-fix on|off` (default ON) passes `align_fix=True` to `fontpatch.make_patches`; it is refused with a clear error without `--proportional-font on`, with `--prop-font-variants` other than `A` and with `--prop-font-place gap1`.
Read back from `build/trial/prop10a`: the align cave equals `align_bytes`, CAP_SLCT / ENDOPT / EVENT hold 20 `nop` (since 10.3a: 18; the 2 salary idioms keep `shll2`) + 8 `pw3` literals each, no file changed size, and PLNUMSET's real layout from the disc bytes puts the digit at x0 + 180 (1 digit) / x0 + 168 or 180 (2 digits) for 12 names.

### 10.8 Skeptic review of the alignment fix (2026-11-12)

Re-run / re-derived, nothing started in an emulator.  `tools/test_alignfix.py` 19 tests OK, `test_sh4sim` 15, `test_patchengine` 26, `test_layoutpatch` ALL PASSED, `fontcheck --quick` OK, `test_textdb` 0 failures.

* **Root cause re-derived** from the disassembly (`aln_dis.py PLNUMSET 1418 1580`: name copied, NULs up to byte 20 become blanks, `sprintf(row + 14, "%2d")`; `CAP_SLCT 9300..a400`: every panel cell is `strlen` result stored at obj + 64 + 8 i and read back ONLY as a halfword inside the `x = anchor - 12 * len` idiom: `aln_lenreads.py` plus the add-form scan `skp_lenreads_add.py`, whose two hits in ENDOPT are other objects).  The advance of a blank in the table is 12 px, so the snap changes nothing unless proportional letters precede the run.
* **Registers**: the layout function is byte identical in all 98 overlays except its literal pool words; after the hook r1, r4 and r5 are redefined before use on every path (loop top, wrap block, draw call `mov #0,r5`), so the cave may use r0 to r5.
* **Disc read back** (a fresh trial disc built with `align_fix=True` forced on, `tools/re/skp_build_align.py`, deleted afterwards): the align cave equals `align_bytes`, the cave word at +0x1a is `bra`, CAP_SLCT / ENDOPT / EVENT hold 20 nops + 8 `pw3` literals at the offsets of the extracted originals (`skp_panel_disc.py` logic), no file changed size; `tools/re/skp_discsim.py` runs PLNUMSET's REAL layout from the disc bytes: the digit lands at x0 + 180 (1 digit) or x0 + 168 / 180 (2 digits) for 12 names including `WWWWWWWWWWWW`, `iiiiiiiiiiii`.
* **Differential test on real strings** (`tools/re/skp_difftest.py MEETING 250 26`, the real layout with and without the cave): 250 sampled strings of the translation without a blank run: 0 differences (names, titles, bubbles, money forms, wide letters).  137 strings with a run of two or more blanks differ, all of them column labels (`Yr %s Population    %s`, GETREP / DRSHRANK rows, `    No.  %2d`, `%-12s  %2dy`, the debug lists), the pen is moved to the grid by 3 to 30 px.
* **Known limit, by design**: a DOUBLE blank inside running prose is also treated as a column (the pen jumps to the grid, up to the accumulated difference, e.g. `Hello,  World` +20 px).  No visible English string has one (`skp_dblspace.py`: the 216 hits are debug text, format lists and Dream Passport HTML), so write single spaces after a full stop in any new text.
* **Not covered by the owner** (still open after the second playtest): finding 5 (header digit sprites overlapping the `Mo` / `Wk` unit sprites, placed by code), finding 6 (SCHE1: `Wk 1` under the `Today` arrow, `Pre-season Match` overflow), the `(8 - len) * 12` / `(14 - len) * 12` idioms of G_INCOME / SPONSOR (lead list 10.4: `len` is now the length of an English money text), and right-aligned text in padded fields is a few pixels wider than the field when its letters are wider than 12 px (`13 oku 1500m` = 147 px in 144).
* **Inferred, not seen**: that the panel edge cuts exactly at the anchor.  If the clip sits elsewhere the `Tokyc` symptom stays; the arithmetic (2 to 5 px of overflow) is proven.
* **Found and fixed here**: the right-hand panel strings of the shirt number screen, section 10.6.


## 11. Scout info panel: the blank Age number and the vanishing rows 3 and 4  (stage 8h, owner `s8hb`)

Where: the scout (Search / Scout Draft) info panel, overlays SCDRF and SEARCH.  Each overlay has two builders (SCDRF 0x7598 = current player with the
`%4d/%d yrs` row, 0x76d8 = candidate with the `Wants %2d yrs` row; SEARCH holds the same code 0x12b0 higher, base 0x8c4d0000).  They fill a 12 wide
row buffer b (all **PROVEN** by running the real builders of the real overlay bytes in `tools/sh4sim.py`, `tools/test_scoutfix.py`):

    b[37..48] money   b[49] '\n'   b[50..61] row 2 (Wants / yrs)   b[62] '\n'   b[63..74] age row   b[75] '\n'   b[76..87] club or country   b[88] NUL

1. **Age number blank.**  The age row is `sprintf(b + 71, 'Age %2d', age)`.  The Japanese `%2d歳` is 2 digits + one 2 byte kanji = a 4 byte field
   (b[71..74] + NUL on the newline at b[75]).  `Age 25` is 6 characters + NUL = b[71..77]: the later `\n` store at b[75] and the club sprintf at
   b[76] overwrite the digits (`Age ` stays).  Fix: the delay slot of the two sprintf calls `add #71,r4` (0x7447) becomes `add #69,r4` (0x7445),
   so the row is b[69..74] and its NUL is the b[75] newline store.  Two halfwords per overlay, same size: SCDRF 0x7684 and 0x779a, SEARCH 0x8934 and
   0x8a4a.  Signature: `mov.l r3,@-r15 ; mov.l r2,@-r15 ; jsr @rX ; add #71,r4`; exactly 2 sites or the patch is refused (already patched, foreign
   image, moved code).  `tools/layoutpatch.py` `patch_scout` / `scout_patches`, build flag `--scout-fix on|off` (default on, `apply_scout_fix`).
2. **Rows 3 and 4 vanish on the current player panel.**  The English `%4d/%d yrs` is 10 characters; the Japanese `%4d/%d年契約` is 12 bytes and the
   row buffer is 12 wide, so the sprintf NUL has to land on b[62] (overwritten by the newline).  With 10 characters the NUL stays at b[60], the
   panel string ends there and the age and club rows are never shown.  Fix (translation DB, no code): `en` `%4d/%d yrs  ` (12 characters, 2 trailing
   blanks) for FLOW_PRG/SCDRF.BIN#32c9c and FLOW_PRG/SEARCH.BIN#32a04 (max_bytes 16; the repacker relocates when needed).
3. Proof: on the original extracted bytes with the English formats put in the table (`tools/test_scoutfix.py`, 83 checks): unpatched = `Age ` with no
   number on both overlays and both builders; patched = `Age 25` right aligned in 12, club row present, newlines at b[49] b[62] b[75], NUL at b[88]; the patched
   and unpatched runs write the same bytes and differ only inside b[63..77]; the 10 character yrs format still loses rows 3 and 4 with the patched code
   (so the text change is needed as well); on the Japanese original the 4 byte field ends at b[74].

Same idiom elsewhere (listed, NOT changed here, not analysed): **CAP_SLCT, ENDOPT, EVENT** (the player-card panel code: `sprintf(b + 74, 'Age %2d')` for the
`%2d才` record, `ptr@8e30 / e968 / 27840`, and a second one for `%2d歳` through `jsr` without an offset add, `ptr@935c / ee94 / 27d6c`; these are also
the overlays of the alignment hooks), **NEWCON** (`Age %2d\nFrom:...` multi-line formats, `ptr@aa24 / aa3c`), ENDOPT `%s Age%2d %s` (ptr@1411c).  Other
`%4d/%d yrs` (10 characters, 12 byte Japanese original) rows: ABROAD ptr@7e5c, FIRE ptr@6bf0, PLNUMSET ptr@9884, SELNAT ptr@de0c (and `%d/%d yrs` in
CAP_SLCT, ENDOPT, EVENT); whether they sit in a 12 wide NUL-overwritten buffer is **UNKNOWN**.

### 10.9 The alignment fix and the hang at the manager's first message (stage 8h, owner `s8ha`, 2026-11-13)

**Symptom (user playtests).**  `build/trial/s8e_notag` (align on, tag off) and `prop10c` (both on) hang at the first message after the manager is picked (header `1 Yr 1 Mo 1 Wk1st`, secretary,
EMPTY message window); `build/trial/s8e_nofix` (both off) shows that message.  The two discs differ in exactly four files (`tools/re/s8ha_discdiff.py`): `1ST_READ.BIN` (the align cave at `0x8c299700..0x8c2997e0` and the
word at file offset `0x28981a`, `rts` -> `bra at_snap`), and `CAP_SLCT.BIN`, `ENDOPT.BIN`, `EVENT.BIN` (20 `shll2` -> `nop` and 8 strlen literals -> `pw3` each).  Both discs still carry the refit relocation bug of stage 8f.

**What was tried and what it proved (all on the REAL bytes of the discs, nothing was started; scripts `tools/re/s8ha_*.py`).**

| # | check | result |
|---|---|---|
| 1 | which overlay shows that screen | `docs/scdrf-hang-ramdump.md`: in the earlier hang of the same screen the dump shows `SCDRF.BIN` + `INITCON.BIN` resident, EVENT gone; the first rows of `SCDRF.BIN.jsonl` are the manager greetings (`I can certainly build you a winning club.`).  So the first message is most probably SCDRF's, and SCDRF is byte-identical in `s8e_notag` and `s8e_nofix` (INFERRED, not seen in an emulator).  EVENT's panel edits cannot be involved in that screen; the only differences SCDRF can see are the font cave hook and the align cave |
| 2 | `at_snap` on a string without a blank run | the layout is identical to the cave without it: ALL 1,821 English strings of `SCDRF.BIN` (window of 33 cells, `tools/re/s8ha_strdiff.py`, real SCDRF image + real `1ST_READ.BIN` of `s8e_notag`): 0 differences, 0 simulator errors; no SCDRF string contains a blank run; every typewriter frame of the manager greetings (`tools/test_align_isolation.py`) identical |
| 3 | real window objects | the RAM dump `build/emu/hang_v1_ram.bin` (SCDRF scene) holds 952 `tsString` windows: laid out with the real layout function with and without the cave (`tools/re/s8ha_ramwin.py`, a lazy 16 MB memory over the dump, hook at `0x8c2d5768`): 0 step-limit hits, 0 simulator errors, ONE window differs (the scout panel `    3100..` / `Wants  3 yrs` / `        Age ` / `       Osaka`, a blank-run text, as intended) |
| 4 | random frames | `tools/re/s8ha_fuzz.py`: 600 random code arrays (blanks, runs, newlines, colour controls, full-width codes; in 300 of them with a window code count (+0x22) of 0, 1, 7, 200, 0x7fff, 0xffff or 0x8000 that differs from the revealed count), advance 24 / 16 / 32: no hang, no exception, same number of glyph positions |
| 5 | EVENT strings | 150 EVENT strings with blank runs / without, real EVENT layout, W = 40: no hang, no change for a string without a run (`skp_difftest.py EVENT 150 40`) |
| 6 | register and flag effects of the hook | after the hook the layout redefines r1 .. r5 before use on every path; the cave never touches r6 .. r15, the stack or the frame (tested directly) |
| 7 | the panel edits (`pw3`, `nop`) | all 18 loads of the 8 patched pools are the panel's own (`tools/re/s8ha_poolloads.py`); `pw3` clobbers what the libc strlen clobbers (r0, r3, r4 advanced past the NUL, r5; the original leaves r5 = r0 and r3 = 0; no caller of the 18 sites reads them: `s8ha_sites.py`); the card constructor `0x8c2f7b70` is created by an Event VM opcode at `0x8c2d2d18` |
| 8 | does the game overwrite the cave area at run time | the matrix stack `njInitMatrix(0x8c299000, 16)` ends at `0x8c299400` (NEWS and TRAINING pass 32 and end at `0x8c299800`, the font cave); in the RAM dump of the hung scene nothing between `0x8c2992c0` and `0x8c299800` differs from the file.  Not excluded for deeper scenes |

**Result: the exact instruction at which the align-on path goes wrong was NOT found.**  By execution, `at_snap` is the identity for every string without a run of two or more blanks and cannot loop (the look-ahead was bounded by the code
count; now also by 63 codes); the layout of the message window is the same with and without it.  Candidate causes that remain, most likely first (none verified):
(a) the hang is not the alignment fix at all but the refit relocation bug (both discs carry it; the first message may read a table that was moved, for example the manager's greeting index from a relocated array, and the memory it then reads differs between the builds only
by the align cave bytes);
(b) a run time write into `0x8c299700..0x8c2997e0` by a scene that reaches deeper than the dumps (the font cave one block above is not hit, the money library at `0x8c299400` is);
(c) the panel edits in a screen that does run EVENT (not the manager's greeting).  (a) and (b) are decided by ONE boot, `build/trial/s8e_noalign` (align off, tag on, relocation bug present; built, never booted): hang = the alignment fix is innocent; no hang = it is not.

**Fix: the alignment fix can no longer touch any draw it was not proven for** (`tools/fontpatch.py`, `tools/test_align_isolation.py`):

* `fontpatch.cave_bytes` no longer takes `align`: the font cave (`0x8c299800`, 104 bytes) is byte-identical with and without `--align-fix`; the `rts ; nop` at `+0x1a` stays (stage 8b changed it to `bra at_snap`, the word `71af` at `1ST_READ.BIN 0x28981a`).
* `at_snap` is now the HOOK ENTRY of the overlays in `fontpatch.ALIGN_SNAP_FILES = ('FLOW_PRG/PLNUMSET.BIN',)` only: their 16 byte advance hook keeps its 12 code bytes and the literal that follows (`0x8c299800`, the cave entry) becomes `0x8c299700` (`at_snap`), ONE byte (`0x98` -> `0x97`) per overlay.
  All other overlays (97 hooked ones) have exactly the bytes of the align-off build and never enter the align cave; the three panel overlays differ from align off only in the panel edits (64 bytes each).
  `1ST_READ.BIN` differs from align off only inside `0x8c299700 .. 0x8c2997ff`.  Proven over the whole tree by `ByteIsolation` (`make_patches` over all overlays, 1 s).
* Inside `at_snap` (256 of the 256 reserved bytes after the stage 8hk lower bound check, see 10.10, `tools/re/s8ha_asm.py`): a glyph other than the blank, or any window whose advance A is not 24, is a tail jump to the unchanged font cave (`bf CAVE`, r4 and the frame untouched: the same registers and the same return as without the fix);
  for a blank the frame assumption is VALIDATED before it is used (`@(4,r15)` < code count and `codes[@(4,r15)]` is a blank), otherwise the plain table advance (again the font cave); the look-ahead is capped at 63 codes (a longer run is not a column).
  Only a validated blank run followed by a glyph returns from the align cave, with the same value as in section 10.2.  `pw3` moved from `0x8c29977c` to `0x8c299798` (stage 8h) and to `0x8c29979c` (stage 8hk).
* `make_patches(..., align_fix=True)` selects the mode `fontpatch.align_mode()`: environment variable `SAKA_ALIGN_MODE`, default `default` (snap in PLNUMSET + panel edits).  Bisect modes: `snap-only` (no panel edits), `panel-only` (no snap anywhere), `snap-all` (the stage 8b wiring: the snap in every hooked overlay).
  `build_patch.py` is not touched: `--align-fix on` means the default mode; set the variable around the build to bisect (`SAKA_ALIGN_MODE=panel-only python -I -X utf8 tools/build_patch.py ...`); `--align-fix off` is the control.

**Proof of equivalence** (`tools/test_align_isolation.py`, 18 tests, 36 s; `tools/test_alignfix.py`, 20 tests, 78 s, the shirt-number column etc. unchanged):

* shirt-number column: PLNUMSET's real layout function with the real table puts the digit at `x0 + 180` for `Ito`, `Kenji`, `Takahashi`, `Nakagawa`, `Isao Nakagak`, `Wanyama Wang`, `Li`, `Okamoto` (and `x0 + 168 / 180` for two digit numbers), as before;
* battery with the snap in EVERY overlay (the worst case, mode `snap-all`) against align off, real overlays SCDRF, EVENT, SEARCH, GAME, DRAFT, HOMETOWN, MEETING, N_ENTRY, OPTION, real English strings (message window of 33 cells, a 20 cell label, a typewriter frame with half of the codes revealed):
  every string WITHOUT a run of blanks lays out identically (pen x / y after every code); the SCDRF manager greetings, every 5th typewriter frame, identical;
* `at_snap` called directly the way the hook calls it: every glyph other than a blank, and blanks in windows with A = 16 / 32 / 10 / 12 / 48, give the same r0 / r4 / r6 .. r15 as the font cave; single blanks, trailing runs and runs before a newline give the table advance;
  a wrong frame (index beyond the text, garbage index, a non-blank under the index, a code count of 0 / 1 / 3 / 0x7fff / 0xffff / 0x8000) never gives anything but the table advance or the snap of the real run; a run of 70 blanks is not snapped.

**Unverified** (needs the emulator, nothing was booted): that `s8e_noalign` shows the first message (decides (a) / (b)); that the default mode removes the hang; that the shirt-number column is still aligned in game (simulated only); the panel edits in game
(10.8).  If the hang survives the default mode, boot `SAKA_ALIGN_MODE=panel-only` and `snap-only` discs: `panel-only` leaves every font hook byte-identical to align off and keeps only the EVENT / CAP_SLCT / ENDOPT edits.

## 12. Hardware strings that are table bases (stage s8gf, 2026-11-13)

Seen in the prop10c playtests (Event screen empty message window, scout screen with `35 oku 8500m`, no Age, garbage picture box, freeze
mid message) and caused by `--hw-relocate` (forced by `--refit on`) moving strings that are the FIRST ELEMENT of a table: the code reads
`table[idx * stride + base]` through the literal that named the "string" (SCDRF.BIN 0x37df0 `Damui`, 56 byte player records, 11 literal
sites; EVENT.BIN literals 0x1b54 / 0x2fec / 0x16238 and `$N` case 45; SEARCH, WEEKLY, ENDING, SPF_READ; the `Nuchitos` byte table in about
38 overlays; `O. Kawamoto`, `Credit Svc`, `Dream Mach.` ... arrays).  Rule now: a hardware string whose pointer is a table base, or whose use
cannot be shown to be text, is written in place and never moved nor lent to other strings (417 records, `translation/hw_inplace.tsv`);
a layout or translation decision for such a record has the in-place slot as its limit.  Relocated (text) strings are 4-byte aligned.
Details: `docs/hw-relocation.md` section 6.

### 10.10 Skeptic re-proof of the stage 8h alignment design and the scout fix (owner `s8hk`, 2026-11-13)

Everything below ran in `tools/sh4sim.py` on real bytes (extracted overlays, the 1ST_READ.BIN and overlay images read back from the DISCS `s8e_nofix` / `s8e_notag`); nothing was booted, no disc was built.

* **The old `at_snap` of `s8e_notag` was disassembled from the disc** (`0x8c299700`): non-blank glyphs `bf` straight to `rts`; every blank went through `mov r0,r4 ... mov r4,r0`, i.e. it **clobbered r4** (the glyph code) on every blank
  of every proportional draw, and it read `@(4,r15)`, `r14+0x30`, `r14+0x22` without any validation.  The real layout function of SCDRF / INITCON / EVENT / SEARCH, run with the `s8e_notag` and the `s8e_nofix` 1ST_READ over the SAME overlay, writes
  byte-identical memory and identical pens for 24 runs each; only r4 differs at the join.  So no simulation reproduces the hang with the old cave either: the cause of the hang is STILL NOT FOUND (see the next point for what the new design leaves).
* **What the default mode leaves different from `s8e_nofix`**: the 256 byte align cave at `0x8c299700` (executed by PLNUMSET only) and the panel edits in CAP_SLCT / ENDOPT / EVENT.  The first message after the manager is picked is run by SCDRF + INITCON
  (`docs/scdrf-hang-ramdump.md`), which are byte-identical to `s8e_nofix` in the default mode and never enter the align cave.  If that disc still hangs, the cause is neither the hook nor the panel: boot `s8e_noalign` / a `--align-fix off` disc.
* **The panel edits are consistent** (checked on CAP_SLCT, the same code in ENDOPT / EVENT): the 18 patched strlen loads sit in 12 small helpers (`0x9300 .. 0x95a8`, `0x9634`, the card constructor `0x97a8`, `0x9160`) that call `sprintf` and then `strlen` and STORE the length in
  the card object (`+64 .. +136`); the only consumers are the 20 `shll2` sites of the draw code (`0x9fa2 ..`; 18 of them became `nop`, the 2 salary sites must not: 10.3a, the salary helper `0x9510` returns a character count and is the 19th, strlen-free setter this skeptic pass missed).  No length is used as a byte count or a copy size.
* **A real (if contrived) defect was fixed in `at_snap`**: the frame check only tested `&codes[i] < &codes[n]`; a garbage index slot such as `0x7fffffff`, `0xffffffff` or `0xfffffffe` makes `2 * i` wrap round, so `&codes[i]` pointed to the word
  BEFORE the array and, when a blank run stood there, the snap was accepted.  `at_snap` now also requires `&codes[i] >= codes` (`cmp/hs r3,r2 ; bf CAVE`, 4 bytes, the cave is exactly 256 bytes).  Random-frame fuzz (6,000 frames, wrong index, wrong
  count, wrong array pointer, advance 0 / 16 / 24 / 255, codes of 0 / 0x8000 / 0x8100 / 0xffffff00): 0 simulator errors, 0 unaligned accesses, the only differences from the font cave are validated blank runs and frames whose code count (+0x22) is inconsistent with
  the array, which cannot be detected from inside the cave.  New test `test_index_that_wraps_below_the_array_gets_the_plain_advance` (fails without the two instructions).
* **PLNUMSET** (the only overlay that enters the snap): real layout function, 48 strings x 2 typewriter frames, snap on vs off: identical memory writes and pens for every string without a blank run, 7 of the 8 blank-run column strings differ as intended; r5 / r1 .. r3
  are dead after the hook (the loop reloads them) so the extra clobber of r5 on the blank path is harmless.
* **Scout fix, re-run on the DISC images** (`s8e_nofix` SCDRF and SEARCH with the real English tables, the real money cave of that disc's 1ST_READ): `patch_scout` accepts the disc bytes (2 bytes each, the same offsets), both builders, domestic (table T0, `rec[14] < 50`, or 50 and `rec[15]`)
  and overseas (T1, `rec[14] >= 50`, `rec[15]` up to 200) variants, 40 + 18 real candidate indices x 3 ages / contracts: `Age 25` right aligned in 12, the club / country row identical to the unpatched run, newlines at b[49] b[62] b[75], NUL at b[88], the same set of bytes written,
  nothing past b[91]; the longest English table entry of T1 is `Turkmenistan` (12), so the 12 wide row is never overrun.

## 13. Event income table: the crowd line `1ma827pp`  (stage 10, owner `c1`, 2026-11-13)

**Symptom** (prop10e screenshot, AWAY MATCH table): the crowd line read `1ma827pp`.  **Cause, PROVEN** (study 9d, the real bytes run in `tools/sh4sim.py`): the crowd-row function at `FLOW_PRG/G_INCOME.BIN` 0x2d0
(callers: HOME MATCH at 0x19aa, AWAY MATCH at 0x1a0e) builds `<hi>万<lo>人` in a 32 byte stack buffer: itoa digits, then the unit records copied by the libc `strncpy` (0x8c013294) with hard-coded counts `mov #2,r6`
(0x326, 0x354) and `add #2,r14` (0x32e, 0x35c).  Two bytes are right for 万 and 人 and wrong for `man` (cut to `ma`) and `ppl` (cut to `pp`); no space is ever written.  A lone `0` people reads `0`.
Not a field width problem (the buffer holds `99man 9999ppl` easily) and not the money library.

**Fix** (`layoutpatch.patch_crowd`, flag `--crowd-fix`, default on; zero size change):

| Where | Old | New |
|---|---|---|
| 0x264a0 (zero padding) | 00 00 00 00 00 | `man ` NUL |
| pool word 0x3d8 | 0x8c4f6490 | 0x8c4f64a0 |
| 0x326 / 0x32e | `e602` / `7e02` | `e604` / `7e04` (copy 4, step 4) |
| 0x354 / 0x35c | `e602` / `7e02` | `e603` / `7e03` (`ppl`: copy 3, step 3) |
| 0x264a8 (zero padding) | 5 zero bytes | `0ppl` NUL |
| pool word 0x3e4 | 0x8c4f6498 | 0x8c4f64a8 |
| 0x360 / 0x366 | `e603` / `7e03` | `e604` / `7e04` (`0ppl`) |

The units stay English database records (`#26490` `man` becomes unused, `#26494` `ppl` is still read in place, `#26498` `0`).  Located by the 232 code bytes 0x2d0..0x3b8 (identical in the original, hsk_full1
and prop10e), the old halfwords, an all-zero 0x264a0..0x264bc and the English `ppl` / `0` records; foreign or already patched images raise `LayoutPatchError`, Japanese units `CrowdUntranslated` (the build skips
the fix with a note: the Japanese 2 byte counts are right).

**Proof** (`tools/test_crowdfix.py`, 52 checks, the real function in the simulator with the English units and digit table written in place): unpatched 10827 -> `1ma827pp`, 7 -> `7pp`, 0 -> `0`; patched
10827 -> `1man 827ppl`, 15000 -> `1man 5000ppl`, 10000 -> `1man ppl`, 827 -> `827ppl`, 7 -> `7ppl`, 0 -> `0ppl`, 99999 -> `9man 9999ppl`; every value ends at x = 593 (x = 504 + (8 - len) * 12 plus the
proportional width), the longest starts at x = 456, clear of the Crowd label column.  Exactly 16 bytes change.  **Not proven**: that the game never writes into the padding at 0x264a0..0x264bb (no code reference
was found) and the on-screen look (never booted); the right edge is 7 px short of the money rows (600), an optional float tweak 504.0 -> 511.0 at 0x3ec is not applied.

**In-memory standard build** (`build_patches` with the standard flags, only the overlays EVENT, SCDRF, SEARCH, TRAINING, GAME, G_INCOME, `--crowd-fix on` against `off`): the patch applies to the real English bytes and
exactly 16 bytes of `G_INCOME.BIN` differ; EVENT, SCDRF, SEARCH and TRAINING are byte-identical with and without it (the Event first-message path and the scout panel bytes are not touched).

The Income / Costs tabs of the same screen are a text change (`G_INCOME#2003c` `@B/Earn@`, `#20045` `@Y/Cost@`, 45 / 46 px against a 58-62 px plate), no code.

## 14. Commentary subtitles still typing when the clip ends  (stage 10, owner `c1`, 2026-11-13)

**Symptom** (user): the English commentary subtitle is still revealing, or is cut, when the cutscene ends or fades.  **Cause, PROVEN** (study 9f): the box update function of `FLOW_PRG/GAME.BIN` (0x8c31eee8, file 0x4eee8,
once per game tick from 0x8c31dd04, state byte at box + 1) reveals one character per two states: state 2 (0x8c31f242) reads it only when `int(timeline)` is odd (`sts fpul,r3 ; tst r8,r3 ; bf` at 0x8c31f248; the timeline float grows
by 1.1 per tick), state 3 draws it and the main loop returns to state 2 on the next tick: 2.233 ticks per character (2.017 at step 1.0).  `BCAST.BIN` has no timing field and nothing waits for the typewriter.  English
text is about 1.9x longer than the Japanese; 77% of the 17,603 commentary lines take longer than their clip (the Japanese fills about half of it).

**Fix** (`layoutpatch.patch_bcast_speed`, flag `--bcast-speed off|1.7|1.9|2.2`, default 1.9; GAME.BIN only, same size, no cave): site 1 = signature `a6f33df35a038823018ba0a00900` (file 0x4f244, once in all of `extracted/`) at +4:
`5a 03 88 23` -> `5a 00 07 c8` (`sts fpul,r0 ; tst #7,r0`: the existing `bf` reveals on 7 of 8 timeline values; `03 c8` = `tst #3` = 1.7); site 2 = signature
`04e005e067a0e18003e064a0e180` (file 0x4f2bc, once) at +10 (file 0x4f2c6): `64 a0` -> **`18 ae`** = `bra 0x8c31eefa` (was: `bra 0x8c31f392`, the return to the main loop after a character was read).  0x8c31eefa is the first instruction behind
the prologue's frame set-up (`add #-12,r15`): the registers r8..r14 are reloaded and the dispatch runs again with the state byte just stored (3), so the character is drawn in the same tick by the NORMAL state 3 code (flag test included).
2.2 keeps the gate and replaces its `bra` (file 0x4f24e, `a0 a0`) by a nop, one character per tick.  Speed-ups: 1.7 = 1.67x, 1.9 = 1.94x (2.233 -> 1.150 ticks per character), 2.2 = 2.23x; commentary lines still longer than
their clip: 13.9% / 5.2% / 1.7% (name callouts 60 / 9 / 5).  Bytes that differ from the original GAME.BIN at 1.9: 5 (0x4f249..0x4f24b and 0x4f2c6..0x4f2c7).

**The first version of this patch crashed the emulator (prop10g, `prop10g_nolin`; `prop10g_nobcast` and prop10e play): root cause PROVEN in the simulator.**  Site 2 was `64 a0` -> `11 a0`, a `bra` to 0x8c31f2ec, the draw call of state 3
(`mov #0,r5 ; jsr @r13 ; mov r11,r4`).  In the original the draw is reached on the NEXT tick, after the prologue (0x8c31ef0c, `mov.l 0x8c31ef50,r13`) has put r13 = 0x8c3202b0 (the draw routine) back.  But the slot pick, state 1
(0x8c31ef6e..0x8c31f23e), loads **r13 = 0x8c159000** at 0x8c31ef7a (`mov.l 0x8c31f05c,r13`: the base of a table of 4-byte FUNCTION POINTERS of the debug / sound library, read as `@(0x28c,r13)` / `@(0x42c,r13)` by its error paths; the first
words are 0x8c163224, 0x8c16325a, ...) and then FALLS THROUGH into state 2 (0x8c31f23e `mov #2,r0`, 0x8c31f242) in the same tick.  Whenever the first character of a message is read in the tick that picked the slot, the first version
branched to the draw with r13 still = 0x8c159000: `jsr @r13` executes the pointer table as SH-4 code (`24 32 16 8c` = `0x3224`, `0x168c`, ...), writes through garbage registers and the process dies.  That is the first message of every box,
about 7 of 8 timeline phases (gate `tst #7`), including the pre-match tactics explainer popup; the original never draws in the tick that read the character (it returns and draws on the next tick), so it never meets the stale r13.  The old test
started in state 2 (r13 fresh from the prologue) and therefore passed.  Patch 1 is harmless (checked: after the gate passes r3 is reloaded at 0x8c31f252 and r0 at 0x8c31f256; on the failing path r0 is the return value
that the manager 0x8c31dd04 ignores) and the debug flag 0x8c3e3428 (the state 3 draw is skipped when it is non-zero) is only ever read: 53 literal loads, no store, no other file holds its address, so it is not the cause.
`tools/test_bcastspeed.py` keeps the first version as a NEGATIVE CONTROL (`11 a0`): started in state 1 at timeline phases 1.0 .. 7.7 its call targets contain 0x8c159000; started in state 2 they do not.  The shipped `18 ae` calls only 0x8c3202b0
from state 0 and state 1, for 10 timeline phases, three texts (plain, `%n` / `%p`, Shift-JIS pairs) and a three message queue, and draws exactly the text in order.

**Isolation**: the Event and scout message typewriter is the separate tsString library (a copy of it also sits in GAME.BIN, 0x2e000 bytes away from the sites, untouched).  The box routine has ONE literal reference in all of `extracted/`
(the manager 0x8c31dd04 of GAME.BIN, which also runs the tactics explainer: it is a commentary slot), the only caller of the draw function 0x8c3202b0 is the box routine; both signatures are unique over all extracted files; no direct branch
and no 32-bit pointer of GAME.BIN targets a patched instruction (the patched bytes are reachable only through state 2); from states 3, 4, 5, 6, 7, 8, 0x55 (debug flag 0, 1 and a pointer), an empty queue and a slot that is not due, the
patched routine writes the same memory and makes the same calls as the original (72 runs); with the debug flag set the patched routine never calls the draw routine, like the original.  `tools/test_bcastspeed.py` (78 checks): 'off' is a no-op;
a second application, a foreign image, one site, moved sites and the first (crashing) version are refused.  **Not proven (needs a boot)**: that the game is happy with the draw one tick earlier (the simulator runs the box routine only, not the
channel updaters 0x8c31dd98 / 0x8c31e524, the timeline update or the renderer; the draw routine itself reads no timeline), the real tick rate (26.9 characters/s at 60 ticks/s, 13.4 at 30), the in-game feel (if it reads too fast use 1.7) and that no other script
path assumes the slow reveal.  If a disc with `--bcast-speed 1.9` still crashes, build the same disc with `--bcast-speed off` (prop10e behaviour) and report which screen; `1.7` / `2.2` differ only by the gate.
Optional follow-up not built: shorten the 928 longest segments (`bcast_trim_c1265.tsv`, median cut 4 characters).

## 15. Lineup name tags: 5 letters in GAME and TRAINING  (stage 10, owner `c1`, 2026-11-13)

The short-name tag routine (`--tag-fix`, `docs/pipeline.md` 9.11) shows the last word of the name up to `TAG_LIMIT` = 7 letters.  In the match lineup (GAME) and Practice > Player Placement (TRAINING) the tag is drawn
beside other sprites and the third to seventh letters were clipped (`Kasam t`, `Hisan`, `Kanaw`, study 9a M3).  `layoutpatch.TAG_LIMIT_BY_OVERLAY = {'GAME': 5, 'TRAINING': 5}` (via `tag_limit_for(name)`, an explicit limit can only
lower it) gives those two overlays 5 letters (`Kasam`, `Hisan`, `Kanaw`, `Yamad`); the other nine overlays (CAP_SLCT, ENDOPT, EVENT, G_RESULT, NEWCON, NEWS, OFFICE, TOWN, YOUTH) keep 7.  Same routine, same 152 bytes; only the
`add #LIMIT,r7` immediate differs.  `tools/test_tagfix.py` runs the real routine of every overlay at its limit.  The 5 letter width is the geometry estimate of the study, not measured on screen.

## 16. Linear text: narrow glyphs left aligned in their 12 px tile  (stage 10, owner `c2`, 2026-11-13)

**Symptom** (user, study 9b): in the match intro (`Stadium`, `Cloudy`, `KICK OFF`) and the in-match OPTIONS rows `i`, `l`, `I`, `!` ... sit at the left edge of a 12 px cell with a 7 px gap behind them (`OPTI ONS`, `Stad ium`).
**Cause, PROVEN**: those strings are drawn by the linear text path (GAME.BIN 0x8c2ed7d8 -> `FUN_8c15e9c6` of `1ST_READ.BIN`), not by the tsString window library, so the proportional hook never sees them: the writer copies one 6 byte
row of a 12 x 24 glyph per loop pass into a fixed 12 px cell, and the proportional font moved every glyph's ink to the left of its tile.  `hsk_full1` had the same gap (its glyphs were left aligned too).

**Fix** (`fontpatch.LIN_SRC`, flag `--lin-center {on,off}`, default on with `--proportional-font on` on the tail placement; `tools/test_lincenter.py`): the 42 bytes of the loop body (file 0x14ea22, `mov r4,r2 ; add #8,r2 ; pref @r2`
and six `mov.b @r4+,r2 ; mov.b r2,@r14 ; add #1,r14`) become `mov.l lit,r1 ; jsr @r1 ; nop ; bra 0x8c15ea4c ; nop ; .long 0x8c299600 ; 7 nops`; the unchanged `add r6,r14 ; tst r5,r5 ; bf/s` of the loop follows.  The cave
`font.lin` (registry claim 0x8c299600, 256 bytes, 192 used; money.lib ends at 0x8c299600, `font.align` starts at 0x8c299700) maps the glyph index back to the character code (`+32` below 96, `+64` above), reads the advance of the font
table at 0x8c299900 **at run time** (so it follows whichever table is built: the default proportional one or the Roboto Condensed Medium one) and shifts the 6 byte row right by `k` pixels (`4k` bits, nibble 15 = paper comes in on the left):
`k = (14 - adv) >> 1` for `adv <= 9`, `k = (13 - adv) >> 1` for `adv >= 10`; advance 0 (unlisted code) and every `k = 0` row are copied unchanged by the original six byte moves.  The writer saved `PR` itself, so the `jsr` is free; r4-r6,
r13, r14, r15 are kept, r0-r3 and r7 (dead in the loop and in the epilogue) are clobbered.  The hook is found by its exact 42 bytes plus the neighbouring `add r3,r6` and `add r6,r14 ; tst r5,r5 ; bf/s ; add #-1,r5`; exactly one hit at
0x8c15ea22 or the build stops (already patched, foreign, truncated and moved images are refused; a non-zero cave range is refused by the engine; `--lin-center on` without `--proportional-font on` or with the gap1 placement is refused).

**The rule against the Roboto table** (`--open-font on`; its glyphs are rendered with the left ink at column 0 or 1 and the advance is ink width + 1 or 2): the same arithmetic holds.  Over all 158 half-width codes (0x20..0x7E,
0xA1..0xDF), in BOTH tables, the k rightmost columns of every shifted glyph are paper, so no ink pixel leaves the tile (`lost_ink` check in the test); with the Roboto table the centring error (left margin - right margin) is at most 2 px
(one pixel of centre error): the ink of `i`, `l`, `I`, `!`, `'` moves 4-5 px, `r t f j ( ) [ ]` 3 px, `/ ^ ~` 2 px, `E F L b c e k v x y z _ < = > ?` 1 px; capitals, `m w`, digits (advance 12) and everything with advance >= 12 stay.  The rule was not
changed for Roboto (`.`, `]`, `j`, `|`, `f`, `t`, `<`, `=`, `?`, `z` are one pixel off the exact centre because the advance does not say whether the gap was one or two pixels).

**Proof** (`tools/test_lincenter.py`, 21 tests): the REAL writer of the patched `1ST_READ.BIN` in `tools/sh4sim.py` with the REAL `FONT.BIN` glyph array of each build: all 158 half-width codes equal a Python shift reference, the control (lin off)
copies every glyph, wide / zero-advance / `k = 0` glyphs are byte-identical, the registers the writer keeps (r4-r6, r8-r15, `PR`) and every memory byte outside the 12 x 24 destination are those of the control; a two cell call (row pitch 24)
works; the strings `Stadium`, `Cloudy`, `KICK OFF`, `OPTIONS`, `Subtitles`, `Near/Mid/Far` ... cell by cell.  Isolation: the patched image differs from the lin-off image only in the 42 hook bytes and the 192 cave bytes of `1ST_READ.BIN` (both
fonts); every other file of the build is byte-identical, so the Event first-message path (EVENT.BIN, the font cave) and the scout panel (SCDRF / SEARCH) are untouched.  **Not proven**: the look on screen (the writer is also used by ENDING /
DMCLBEDT (NOT by OPTION.BIN, see section 17); narrow glyphs there are centred too), and the exact centre of `.` `]` `j` `|` (one pixel).  Reference: `lin_center_proof.py` of study 9b.

## 17. 16 px windows: gapped narrow letters on the OPTION lists and the Practice player panel  (stage 10 follow-up, owner `il`, 2026-11-13)

**Symptom** (user screenshots of `prop10g`): `Trai ni ng`, `Advance Schedul e`, `B G M`, `S E`, `AUDIO` on the OPTION screen (option / sound-test lists, OPTION.BIN) and `H i roshi  Hase`, `26 yr s`, `Ai chi`, `0 App 0 G`
in the Practice player-info panel (TRAINING.BIN).  These are NOT drawn by the linear writer that `--lin-center` fixes: `tools/re/font/lincallers.txt` has `bsr_calls=0 literal_refs=0` for both overlays, so they never call
`FUN_8c15e9c6` (the statement of section 16 that OPTION uses the linear writer is wrong; only ENDING, DMCLBEDT and GAME do).  They are ordinary tsString window text, so the proportional hook sees them, and it answers 8 px.

**Cause, PROVEN by code reading and execution** (the hook, not the glyphs):
1. OPTION.BIN: the list builder `0x8c8d16a0` walks a 12 byte entry table at `0x8c8d7cdc` (word 0 = label pointer: `Hide`, `Comm On`, `BGM` @`0x7ec8`, `SE`, `Advance Schedule` @`0x7eec`, `Training` @`0x809c` ...), builds a window
   with the generic constructor `0x8c8d3e58` and then stores `+0x46 = 2` (size class 2: half quad 8 x 16, the 12 col tile scaled 2/3, docs/font-hook-notes.md s3.4) and **`+0x3e = 16`** (`mov #16,r2 ; mov #62,r0` at `0x8c8d1706` and `0x8c8d176e`).
   TRAINING.BIN: the panel function that prints `%D yrs` (`0x8c35be54`, record `#8be54`), `%D App %D G` (`#8be68`) and the position tags `GK/ DF/ MF/ FW/` through the window printf `0x8c2e8000` into an array of 7 windows
   at obj `+0x24 .. +0x54`, created at `0x8c2f2468 ..`; every one gets `+0x46 = 2`, `+0x3e = 16`, `+0x3f = 16` (stores at `0x8c2f24ba 2538 25b0 261a 2692 26fc 2772`).  The name and birthplace windows are the first ones of the same array (INFERRED).
2. The font cave (`font.cave`, H1) is `A == 24 -> table[char]`, **any other A -> the original `(A + (A<0)) >> 1`**.  For A = 16 that is 8 px for every half-width character, fixed.  The proportional glyph art keeps the ink at the left of
   its tile (`i` ink 2 px of a 12 col tile, 2/3 scaled to ~1.3 px), so `i l r t f j` are followed by ~5 px of paper: the same mechanism as the 7 px gap of section 16, here at 2/3 scale.  `hsk_full1` and the pre-open-font builds showed it too,
   less visibly; the Roboto Condensed Medium glyphs make it obvious.  `--lin-center` cannot reach it (different code path), `--align-fix` is unrelated (A != 24 there).
3. Windows with A = 16 are all over the game (stores found by `tools/re/font/fieldstores.py`-style scan: BPMATCH 2, DRSGRF 2, DRSGRFJ 5, DRSHRANK 3, DRSSRANK 3, GAME 7, NEWS 11 (+2 with A = 32), OPTION 2, TRAINING 7; A = 10 / 48: SCDRF, SEARCH;
   A = 1: EVENT, WEEKLY; A = 5: GAME).  EVENT's A = 1 window is the reason `--prop-scale` (which rescales EVERY A != 24: `(t * A + 12) / 24` gives 1 px per glyph instead of 0 at A = 1) is NOT the fix to use: it would change the Event
   message path that hung before.

**Fix** (`fontpatch.SMALL_SRC`, flag `--small-prop {on,off}`, **default OFF**, `tools/test_smallprop.py`): a second advance entry `sm_adv` in the unused tail of the 256 byte font cave reserve (`0x8c299800 + 0xA0 .. 0xE0`; the default cave, its entry
offsets, the table and every other cave stay byte-identical).  `FontPatchError` unless `--proportional-font on` with glyphs, variant A and the tail placement.  Only the advance hook literal (4 bytes) of the overlays in `SMALL_FILES` = OPTION.BIN
and TRAINING.BIN points at `sm_adv`; every other overlay (EVENT, SCDRF, SEARCH, GAME, NEWS, G_INCOME ...) is byte-identical to a build without the flag.  `sm_adv` reads A: `A != 16` is a tail jump (`bf`, PR / r4 / r14 untouched) into the unchanged
font cave entry, so the A = 24 windows of TRAINING (and of OPTION) behave exactly as before; `A == 16` returns `w = (2 t + 1) / 3` from a 25 byte table, t = `table[char]` (0 = unlisted = 12), which equals `(t * 16 + 12) / 24` (the `--prop-scale`
formula, here for A = 16 only) and the 2/3 sprite scale: `i` 3 px, digits / blanks / unlisted codes 8 px as before (so padded fields and the blank-padded OPTION labels keep their width).  No multiply, no MACL (the `--prop-scale` routine clobbers MACL).
The wrap routine (H2) is not touched: it is pixel based already, a line of narrow letters simply holds more of them.

**Proof** (`tools/test_smallprop.py`, 15 tests, nothing booted): the table against the formula; the routine against capstone (no `mul` / `macl`); `sm_adv` executed in `tools/sh4sim.py` for every code 0..255 and every window advance -128..127 with BOTH
tables (default proportional, Roboto Condensed Medium): A = 16 gives the formula, every other A gives the unchanged cave's value; PR, r4-r15 and memory untouched; the REAL hooked tsString layout function of the REAL patched TRAINING and OPTION overlays at A = 16:
pen positions of `Hiroshi Hase`, `Training`, `Advance Schedule`, `BGM`, `26 yrs`, `0 App 0 G`, `Aichi` are the scaled advances, the same strings at A = 24 / 32 / 10 and blanks / digits at A = 16 are identical to the flag-off build; isolation (above) and
the refusals.  **Not proven (needs one boot)**: that the quad really is 2/3 scale at A = 16 on screen (docs/font-hook-notes.md s3.4 is PROVEN from data but the look was never seen), that no screen of OPTION / TRAINING right-aligns a number with `(N - len) * 8`
(same family as the unexplained align hang, section 10.9), and the name / birthplace windows of the panel.  Other A = 16 overlays (BPMATCH, DRS*, GAME, NEWS) are candidates for `small_files=` after the first boot; they are NOT in the default list.


## 18. In-match OPTIONS: the selected-option highlight lit the wrong characters  (stage 10 follow-up, owner `opt`, 2026-11-13)

**Symptom** (user screenshot of `prop10h`): in the in-match OPTIONS panel (Commentary / Subtitles / Player Names `ON/OFF`, Name Format `A/B`, Camera Type `Near/Mid/Far`) the dim value row shows a bright patch in the wrong place:
`ON/O` bright and `FF` dim when ON is selected, nothing bright when OFF is selected, `A/` bright for A and nothing for B, and in the camera row only `ar` of `Near/Mid/Far` bright.

**How the panel is drawn (PROVEN by code reading; the sprite engine itself is not simulated)** (`FLOW_PRG/GAME.BIN`, load base `0x8c2d0000`):
1. The row builder `0x8c2ff29e` walks the table at `0x8c3e7404` (file `0x117404`, 8 byte entries `(label, value)`; row 0 `OPTIONS`, row 1 the resume entry, rows 2..6 the five option rows = the 10 pointers of the DB context `tbl@117414`) and calls the bitmap text writer
   `0x8c3341d0` twice per row (`x = 0` label, `x = 0xc0 = 192` value, `y = 44 * row`).  The writer renders into ONE texture at **half scale**: one character = one fixed **12 px cell = 6 texture pixels** (the linear writer `0x8c2ed7d8` -> `FUN_8c15e9c6`, 6 bytes
   per cell; no proportional advance, section 16 only centres a narrow glyph inside its cell).  The value text starts at texture u 96 and is 14 cells (168 px) wide; the whole value is drawn **dim**.
2. The update function `0x8c3010e4` (cursor `@(38)`, settings bytes `@(40)`: `[1]..[3]` toggles, `[4]` A/B, `[5]` camera 0..2) then plays one **highlight sprite** per option row through `0x8c080454(obj + 44, id, 32, 1.0)`: `0x82 / 0x83` (`settings[1]` ON / OFF),
   `0x84 / 0x85`, `0x86 / 0x87`, `0x88 + settings[4]` (A / B), `0x8a + settings[5]` (Near / Mid / Far); `0x7a..0x81` are the label strips.  The sprite records are the 20 byte table at `0x8c3e743c` (file `0x11743c`, record `id` at `+20 * id`, `<10h`:
   `w, h, x, y, u0, v0, u1, v1, type, 0`).  A highlight sprite re-draws a **window of the same texture** brighter: `w = 2 (u1 - u0)`, `x = 182 - 2 u0` (the sprite engine mirrors x), `u = 96 + 6 * cell`.
3. The windows are fixed cell ranges fitted to the Japanese full-width values (a full-width glyph = 2 cells): `  ＯＮ・ＯＦＦ` -> ON = cells 2..5, OFF = 8..13; `        Ａ・Ｂ` -> A 8..9, B 12..13; `    近・中・遠` -> Near 4..5, Mid 8..9, Far 12..13.
   **Check of the model:** the windows computed from the Japanese strings with exactly this rule reproduce all 11 original records (220 bytes) of both overlays bit for bit (`tools/test_optionsfix.py` part 1).

**Why the English text breaks it (numbers):** the English values keep the same fixed windows, so the lit text is whatever sits in those cells.  `  ON/OFF` (O 2, N 3, `/` 4, O 5, F 6, F 7): ON window 2..5 = `ON/O`, OFF window 8..13 = nothing (the string ends at cell 7).
`        A/B` (A 8, `/` 9, B 10): A window 8..9 = `A/`, B window 12..13 = nothing.  `  Near/Mid/Far` (N 2 ... r 5, `/` 6, M 7 ... d 9, `/` 10, F 11, a 12, r 13): Near window 4..5 = `ar`, Mid window 8..9 = `id`, Far window 12..13 = `ar`:
the camera row of the screenshot (Far selected) lights exactly `ar`.  The 2-cell windows (24 px) cannot hold `Near` (4 cells), `Mid` or `Far` (3 cells) at all, so a pure text/padding change cannot make all three rows right (preference (a) fails for the camera row): the window
data has to move.  ENDING.BIN has an identical copy of the panel (builder at file `0x50d2`, string table `0x2bf80`, sprite records `0x68f20`, byte-identical 220 byte block) and the same fault.

**Fix, data only (no code), `--options-fix {on,off}` default on** (`tools/layoutpatch.py` `patch_options` / `options_patches`, `build_patch.apply_options_fix`): the 11 sprite records are recomputed from the cells of the option words in the **current** value strings (read through the pointer table, so repacked / edited
strings are followed): `u0 = 96 + 6 first`, `u1 = 96 + 6 end`, `w = 12 (end - first)`, `x = 182 - 2 u0`; `h, y, v0, v1, type` stay.  With the DB strings (`  ON/OFF`, `        A/B`, `  Near/Mid/Far`) the windows are ON 2..3, OFF 5..7, A 8, B 10, Near 2..5, Mid 7..9, Far 11..13,
i.e. exactly the selected word and nothing else.  Located by the 220 byte original block (unique, file `0x117e64` / `0x68f20`); a Japanese value image is left alone; foreign or already patched records, a word that ends past cell 14 and a value without its `/` stop the build.  Same size, 33 changed bytes per overlay.
Text: the ENDING copies of `Commentary Text` and `    Near/Mid/Far` were still the old strings (cut to `Commentary Tex` / `Near/Mid/F`, 4 + 12 > 14 cells); now `  Subtitles` and `  Near/Mid/Far`, equal to GAME.

**Proof / not proven.**  `tools/test_optionsfix.py` (about 70 checks, nothing booted, no disc built): the model against the original bytes, the broken windows over the English strings (`ON/O`, `A/`, `ar` / `id` / `ar`), the fixed windows of every record for both overlays, the lit text of each state, disjoint ordered windows inside 14 cells, byte isolation, a moved or
re-indented string, the refusals and the build wiring.  **Only simulated / computed:** the cell geometry (all from the data and the Japanese ground truth), **not** the sprite engine (FPU code, `tools/sh4sim.py` has no FPU) and not the screen.  Needs one boot: (a) the three ON/OFF rows, the A/B row and the camera row each brighten exactly their word in both states, (b) the
sprite engine accepts the new widths (24 / 36 / 48 px instead of 48 / 72 / 24; it reads `w` and the UV from the record, nothing else was found), (c) the glyph centring of `--lin-center` keeps every letter inside its cell (the tile is 12 px, so it should).  Fallback: `--options-fix off`.

## 19. Commentary subtitle: gapped narrow letters and the blank at the start of a wrapped line  (stage 11, `--cell-prop`, 2026-11-13)

**Symptom (playtest prop10h, match commentary box).**  `Fi r st hal f`, `easi l y`, `wi l l`: every `i l r f t` is followed by a gap, although `--lin-center` is on; and the second line of a wrapped sentence starts with a blank (`By my watch, First half Suzuki Cut out` / ` easily here.`).

**Cause (PROVEN by disassembly, `FLOW_PRG/GAME.BIN`, load base `0x8c2d0000`, file offset = address - base; the diagnosis was a read-only workflow, the numbers below were re-checked against the bytes here).**  The commentary (BCAST) subtitle is drawn by the line engine `0x8c3202b0` (called from state 3 of the box state machine `0x8c31eee8`),
**not** by the tsString library (`font.cave`, `--align-fix`) and **not** by the linear writer `FUN_8c15e9c6` (`--lin-center`); that is why neither flag reaches it.  Per character it compiles the code (`0x8c3200f2`: ASCII -> `0x8000 | byte`), then writes one cell into an 82 byte line record: byte 0 glyph count, byte 1 *unit* count (half-width +1, full-width +2; the wrap test uses it), then 40 pairs `(present flag, advance byte)`.
The advance is a **constant**: half-width `mov #12,r0 ; mov.b r0,@(1,r2)` at `0x8c32049e` / `0x8c3204a0`, full-width `mov #24,r1` at `0x8c3204c6`, blank `mov #12,r0` at `0x8c3204f2` (flag 0).  The display loop `0x8c31fdc0` reads that byte for every cell and uses it three ways: sprite width, UV width (`adv * 8`) and the pen step (`x += adv`, FPU, starts at x = 160, left aligned).
The advance table at `0x8c299900` is never read.  A half-width glyph of the proportional font is drawn left aligned in its tile, so every narrow glyph is followed by (12 - advance) px of paper.  The wrap rule (`0x8c320340..0x8c320354`): at 37 units and a blank next, or hard at 39, `bsr 0x8c3201fe` starts a new record (zero filled, column 0) and the breaking blank is then processed **as the first cell of the new line** by the blank block `0x8c3204e0`: 12 px of nothing, which is the stray leading space.

**Fix, `--cell-prop {on,off}` (default on with `--proportional-font on` on the tail placement; refused otherwise).**  Same size, signature located, three places:
* `font.cell` (new registry claim, `0x8c2996c0`, 64 bytes = the spare tail of the old 256 byte `font.lin` reserve; the lin cave is exactly 192 bytes, so `font.lin` is now a 0xC0 claim) holds `cell_adv(r4 = compiled glyph) -> r0`: `table[r4 & 0xff]` clamped to 12, 0 (unlisted) -> 12; 28 bytes (`fontpatch.CELL_SRC`).
* the **half-width block** `0x8c32048c..0x8c3204a1` (22 bytes, file `0x5048c`) now computes the same record pointer and calls `cell_adv` through `jsr` instead of `mov #12,r0` (an overlay calling the resident 1ST_READ tail, like the tsString hook).  Its literal is the free zero word `0x8c32053c` (file `0x5053c`, between the `0x8000` mask word and the jump table; no pc-relative load of the image reads it, `tools/test_cellprop.py`),
  read by `mov.l @(40,pc),r3`.  r2 (record pointer) survives the call; r0 / r1 / r3 / r4 are dead after the store; PR is saved by the engine's own prologue (`sts.l pr,@-r15` at `0x8c3202be`).
* the **blank block** `0x8c3204e0..0x8c3204fd` (30 bytes, file `0x504e0`) writes the table's blank advance S (derived from the BUILT table, entry 0: **12** in both the default and the Roboto table after the D1 fix, i.e. a blank looks as before; the code takes any 1..12) and **skips a blank at column 0**: it jumps to the common tail `0x8c3204fe` (column + 1, glyph count + 1) without writing the cell or counting a unit.  The cell keeps flag 0 and advance 0 (records are zero filled by `0x8c3201fe`), so the display loop adds 0 px and draws nothing; the wrap test is unchanged (units are not counted).
Not touched: full-width glyphs, the wrap logic (a pixel based wrap could only gain 1..2 characters before the 40 slot record is full: not worth the risk), the display loop (FPU), the pen origin.  Lines stay left aligned.  The Roboto table has advances of 13 px (`m w W` ...): they are clamped to 12 because the sprite cell is 12 px wide (the same clamp the linear writer uses by not shifting).

**Proof (`tools/test_cellprop.py`, 23 tests; nothing booted, no disc built).**  The REAL patched blocks and the REAL cave run in `tools/sh4sim.py` for all 94 ASCII codes (+ the kana slots, an unlisted code and a 24 px entry) at column 0, 3 and 20 with BOTH tables (default proportional, Roboto Condensed Medium): the advance byte is `table[code]` clamped to 12 (0 -> 12; control: 12), one unit is counted, and every other memory byte and
the registers r5..r15 equal the unpatched engine's; the blank is skipped at column 0 (no cell, no unit, column and glyph count still advance) and written with S at every other column (S = 12, 7, 1 and the built value).  The image differs from the original only inside the two blocks and the 4 byte literal; the `--bcast-speed` sites (`0x4f248`, `0x4f2c6`) and the OPTIONS records are byte-identical whichever patch runs first; `1ST_READ.BIN` differs from the cell-prop-off image only in the 28 cave bytes.
The reserve `0x8c2996c0..0x8c2996ff` is zero in the original image, inside no other claim (`test_patchengine`), and **no 4 byte word in `1ST_READ.BIN`, `GAME.BIN` or any `FLOW_PRG` overlay points into it**.  Refused: second application, foreign / damaged / truncated image, non-zero literal or cave, a bad cave address, a blank advance outside 1..12, gap1 placement, no glyphs.
**Not proven / needs one boot:** the display loop (FPU) and the sprite engine are not simulated: it is *inferred* that a smaller advance byte clips the sprite to its leftmost `adv` px (width and UV scale 1:1 with the byte) and that nothing else reads the byte.  Boot check: a commentary line with `i l t f` reads `First half` without gaps, no glyph is clipped on its right edge (the table advance is the grid-fitted extent, the same data the tsString path trusts), `W m w` (13 px, clamped to 12) are not cut, and a wrapped second line no longer starts with a blank.
Fallback: `--cell-prop off` (the engine is then byte-identical to before).
