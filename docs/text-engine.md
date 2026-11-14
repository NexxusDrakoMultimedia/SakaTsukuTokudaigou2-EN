# Text engine of SakaTsuku Tokudaigou 2 (Dreamcast): what English can be displayed

> **Status note (docs, 2026-11-11).** Written before any emulator run. The key claims were confirmed live later (ASCII English renders in the 12 px half-width font, colour codes and the typewriter effect work, messages are compiled when a dialogue opens; docs/playtest-log.md). The limits listed here (39 visible cells, fixed-width spacing) are what the proportional font, window and layout patches work around (docs/pipeline.md section 9).

Author: agent `textengine`. All of this comes from static reverse engineering (Ghidra 12.2
decompiler on `1ST_READ.BIN` and on `FLOW_PRG/MEETING.BIN` imported at 0x8c2d0000) plus data
analysis in Python. **Nothing was run on an emulator or on hardware** (none installed). Status words:

* **PROVEN** = read directly from decompiled code/data and re-checked with a script.
* **INFERRED** = follows from code but a hop (usually a function pointer or a graphics call) was not traced.
* **UNKNOWN** = not determined; a dynamic test is proposed in section 8.

Files: `tools/re/textengine/` (`fontdump.py`, `tsengine.py`, `ts_survey.py`, `survey_overlays.tsv`,
`rd.py`, Ghidra helpers `Dec.java` `Dis.java` `ListF.java` + `*.ps1`, raw decompiler dumps `r*.txt` `m*.txt`
`o*.txt`). Ghidra project copy: `<GHIDRA_PROJECTS>\ghproj_textengine` (programs `1ST_READ.BIN`, `MEETING.BIN`).

## 0. Executive summary

| Question | Answer |
|---|---|
| Which font does the game use? | `FONT.BIN` (NOT `DPFONT/*`, which belong to the bundled DreamPassport web browser `2_DP.BIN`). Loaded by boot function `FUN_8c15ffcc` to RAM 0x8cd5c000. The copy that is loaded is `ATFIRST/FONT.BIN` (INFERRED: same call loads `SHTEX0.ZAR`/`BAR.TBD`/`SECFTEX0.ZAR`, which exist only in `ATFIRST/`); root `/FONT.BIN` decodes to identical glyphs except glyph 3580 - patch both. |
| Glyph cell | Full-width 24x24, 4 bpp (288 bytes, `-bz--` compressed per glyph). Half-width 12x24, 4 bpp (144 bytes, raw). PROVEN. |
| Single-byte chars | ASCII 0x21-0x7f and 0xA0-0xDF are drawn with the **half-width** glyph set (160 glyphs, includes lower case) at a **fixed advance of half the window advance (12 px)**. Not skipped, not full-width, **not proportional**. 0x20 is a blank half cell. PROVEN. |
| Word wrap | The engine wraps **per character, never at word boundaries**. Explicit `0x0a` = line break. Wrap width = window byte `+0x3c` (cells). Rows (`+0x3d`) are not enforced by the library. PROVEN (MEETING copy). |
| Default dialogue window | 20 cells x 3 rows, advance 24 px, line height 24 px => **39 ASCII chars/line** (`2*20-1`), 3 lines. Windows with other widths are set by game code; formula in section 4.4. |
| Control syntax in strings | `0x0a` newline; `@` colour reset, `@R/` `@B/` ... colour (letters `WRBYGMPKO`); `=`, `=W/ =K/ =I/` style; `%s %d %D %m` printf-like; `#sname#` `#YOU#` `#tkNN#` name substitution; raw bytes 0x11-0x19 also colours. **`@ = % #` can never be printed literally** (section 4.2). |
| Overlay loading | Whole file is read from the file system (size = ISO directory length, rounded up to 2048) to a slot base chosen by the caller; image end `_end` is a u32 *inside the image* that sets the heap start. **Appending data is safe only for the 33 overlays with no BSS and only if the `_end` word is raised**; for BSS overlays use existing slack (section 6). |
| Proportional font | Needs code patches in the per-overlay copy of the layout function (byte-identical in 97 of 114 overlays, so patchable by signature). Monospace English works with **zero** code patches. |

## 1. Where text is drawn from

* Every overlay that shows text embeds its **own copy of the "tsString" window library** (marker string
  `malloc error.tsString.init`, 104 of 114 overlays; `ts_survey.py`). The glyph back end is shared in `1ST_READ.BIN`.
* Overlays reach 1ST_READ services through a function table at 0x8c159000+offset (e.g. `0x8c15939c...`);
  relevant slots: `0x8c1593a8` font init `FUN_8c15e72c`, `0x8c1593ac` SJIS->glyph `FUN_8c15e7a0`,
  `0x8c1593b0` byte->glyph `FUN_8c15e88e`, `0x8c1593b4` glyph blit `FUN_8c15e8ea`, `0x8c1593d0` glyph->linear
  buffer `FUN_8c15e9c6`, `0x8c1593d8` reverse lookup `FUN_8c15e8b6`.
* Overlay-local (MEETING.BIN addresses; other overlays have the same code at other offsets):
  string -> code array `FUN_8c2ddeea`; printf/`#` expander `FUN_8c2df128`/`FUN_8c2de06c`; text window constructor
  `FUN_8c2de988` (default window); text setter `FUN_8c2de1f4`; typewriter/state machine `FUN_8c2de4d4`;
  layout + draw `FUN_8c2de294`.

## 2. FONT.BIN (PROVEN: structure, loader, lookup)

Boot function `FUN_8c15ffcc` (1ST_READ) ends with
```c
(*(code *)PTR_FUN_8c160338)(PTR_s_FONT_BIN_8c160340,0,DAT_8c16033c);   // name, ?, dest  (dest = 0x8cd5c000)
...(PTR_s_SHTEX0_ZAR_8c160348,...)  (PTR_s_BAR_TBD_8c160350,...)  (PTR_s_SECFTEX0_ZAR_8c160358,...)
(*(code *)PTR_FUN_8c160364)(...)   // = FUN_8c15e72c  font init
```
`FUN_8c160338` = `FUN_8c15eeb8` -> `FUN_8c15eede`, the generic file loader: opens by name, gets the file length
`len`, `sectors = (len + 0x7ff) >> 11`, reads `sectors` sectors to the destination.

`FUN_8c15e72c` (font init, 0x8c15e72c): copies the 4 header words into globals and derives pointers:
```c
g[0x8c22835c]=hdr[0] (3648 glyphs)  g[0x8c228360]=hdr[1] (0x10)  g[0x8c228364]=hdr[2] (0x3910)  g[0x8c228368]=hdr[3] (0x9c51c)
*0x8c228378 = hdr[2]+base   // glyph data
*0x8c22837c = hdr[3]+base   // half-width glyph table
*0x8c228380 = hdr[1]+base   // offset table
debug("number of fonts:%d", hdr[0]);
```
FONT.BIN layout (verified by `tools/re/textengine/fontdump.py`, all 3648 glyphs decode to 288 bytes):

| offset | content |
|---|---|
| 0x00 | u32 `3648` glyphs, u32 `0x10` table offset, u32 `0x3910` data offset, u32 `0x9c51c` half-width offset |
| 0x10 | 3648 x u32 offsets, relative to 0x3910; glyph i = bytes [off[i], off[i+1]) = `-bz--` stream (`bzlib.decompress_bz`) -> 288 B = 24x24 px, 4 bpp, 12 bytes/row, low nibble = left pixel; value 15 = background |
| 0x9c51c | 160 raw half-width glyphs of 144 B = 12x24 px 4 bpp (6 B/row). End of file (23040 B). |

Glyph fetch `FUN_8c15eca4(dest, code)` (called from blit `FUN_8c15e8ea`; mask constants read from data):
```c
if ((code & 0x8000) == 0)  bz_decompress(buf, *(u32*)(*0x8c228380 + code*4) + *0x8c228378);       // 0x8c15a9f4
else { c = code & 0x7fff; c -= (c < 0xa0) ? 0x20 : 0x40; src = c*0x90 + *0x8c22837c; ...12 px rows... }
```
So half-width index = `byte-0x20` for 0x20..0x7f (idx 0..0x5f) and `byte-0x40` for 0xa0..0xdf (idx 0x60..0x9f).
Both paths then twiddle the 4-bpp pixels into a 32x32 (`0x20,0x20` passed to the texture-create call in
`FUN_8c15e8ea`; INFERRED that these are w,h) glyph texture; a half-width glyph fills only the left 12 px columns.
Glyph 0x17 (crown/trophy-like icon) is the "missing glyph" returned for unmapped codes.

**SJIS -> glyph index** `FUN_8c15e7a0` (0x8c15e7a0, transcribed in `tsengine.sjis_to_glyph`):
`hi=code>>8, lo=code&0xff`; code > 0x9890 -> table lookup (51 specific JIS level-2 kanji, 0x8c169f04, indices
0xdca..0xdfc, else 0x17); `hi==0x88`: `0x196+lo`; `hi>0x88`: `(hi-0x89)*188 + 0x293 + (lo<0x7f ? lo-0x40 : lo-0x41)`;
`hi<0x88`: `(hi-0x81)*188 + (lo<0x7f ? lo-0x40 : lo-0x41)`. So the font = rows 0x81-0x83 (symbols, full-width
alnum, kana, 564 slots), JIS level 1 kanji (0x889f..0x9872 starts at index 565) and only 51 level-2 kanji.
Visual checks: glyph 283 = あ, 565 = 亜, 0 = blank. Kanji outside this set will show glyph 0x17.

`FUN_8c15e88e` (single byte -> glyph via u16 table at 0x8c16a08a) maps ASCII to **full-width** glyph indices
(e.g. '0' -> 0xcb, 'A' -> 0xdc); it is NOT used by the tsString path (which uses the half-width set). It is the path
for the other call sites that go through slot 0x8c1593b0 (not traced; no overlay references that slot - only
1ST_READ internals could use it).

## 3. Code units: string -> u16 array (overlay `FUN_8c2ddeea`)  (PROVEN)

Constants read from MEETING.BIN data: 0x2000 control, 0x8000 half-width, 0x4000 hang, lead-byte test with 0x80/0xa0/0xe0.
```c
byte==0 end
'=' (raw==0): "=X/" (X in W,K,I; X is upper-cased by FUN_8c015c14 = toupper) -> 0x2030+{1,2,3}; else 0x2030      // never printed
'@' (raw==0): "@X/" X in "WRBYGMPKO" -> 0x2010+idx (1..9) ; unknown X -> nothing; plain '@' -> 0x2010          // never printed
byte < 0x21          -> 0x2000|byte   (0x0a -> 0x200a newline, 0x20 -> 0x2020 half-width blank)
(b<0x80 || b>=0xa0) && b<0xe0 -> b | 0x8000 | (b in {0xa0..0xa5,0xa7..0xb0} ? 0x4000 : 0)   // single byte, half-width glyph
else lead byte: code = sjis_to_glyph(b<<8|b2); if (code != 0x17 && pair in kinsoku list) code |= 0x4000; consumes 2 bytes
```
Kinsoku list (hanging chars, `0x8c374a04`): `、。」ー…？ぁぅぇぉぃっゃゅょァィゥェォャュョッヵヶ`. ASCII punctuation is **not** in the
half-width list, so `. , ! ?` get no hang privilege. `tsengine.convert()` reproduces this.

Python check: `tsengine.convert(b"Hi @R/there@ A=W/\n")` -> `0x8048 0x8069 0x2020 0x2012 0x8074 ...` (colour 0x2012 = red).

## 4. Preprocessor, controls, layout

### 4.1 `FUN_8c2de1f4(win, fmt, args, raw)` (text setter)
Copies `raw` to window `+0x48`, expands the format with `FUN_8c2df128(buf 0x8c3deadc, fmt, args, raw)`, converts with
`FUN_8c2ddeea` into code buffer 0x8c3deedc, `+0x22 = code count`. The two scratch buffers are 0x400 apart, so the
**expanded text should stay below ~1 KB** (INFERRED, MEETING copy; no bound checks in the expander).

### 4.2 Format expander `FUN_8c2df128` / `#` tokens (only when `raw==0`)  (PROVEN)
* `%s` string pointer (copied verbatim), `%d` -> decimal ASCII digits (`FUN_8c2dd844`, `'0'+n`, optional pad),
  `%D` -> **full-width** digits (2 bytes each, `FUN_8c2dd964`), `%m` -> money text built from Japanese pieces
  (`FUN_8c2dda68`: number + strings from data pointers such as 万/円; **contains Japanese that must be patched**).
  `%x` for any other x emits `x`, so `%%` prints `%`. Arguments are read like a SH-4 va_list.
* `#...#`: up to the next `#`: `#sname#` -> string at `*(0x8c231400)+0x103a`, `#YOU#` -> `*(0x8c231400)+0x102c`
  (club / manager name buffers, INFERRED meaning), `#tkNN#` (NN = 00..31) -> string pointer from a 32-entry table
  (0x8c3df6dc in MEETING). Unknown tokens are re-emitted. The token is copied into a 20-byte stack buffer with no
  bound: **a lone `#` without a closing `#` within 19 bytes overflows it**.
* Therefore in `raw==0` windows English text must not contain `%`, `#`, `@`, `=` literally (use `%%`; there is
  no escape for `# @ =`). Windows created with the raw flag (`+0x48 != 0`, e.g. text entry) treat them literally.
  Which windows are raw is UNKNOWN per call site.

### 4.3 Window structure used by layout (offsets from decompiled accesses, MEETING copy)
`+0x20` state 0..3, `+0x22` u16 code count, `+0x2a` glyph slots used, `+0x2c` typewriter cursor, `+0x30` code array,
`+0x38` draw flags, **`+0x3c` cells per line, `+0x3d` rows (never read by the library), `+0x3e` advance px (24),
`+0x3f` line height px**, `+0x40` chars revealed per update (0 = all at once), `+0x41/+0x42` colour pair,
`+0x44` default colour, **`+0x45` "last cell free" flag**, `+0x48` raw, `+0x4a/+0x4c` x,y, `+0x50` float colour/scale.
Default window constructor `FUN_8c2de988`:
```c
+0x3c=0x14 (20 cells) +0x3d=3 +0x3e=0x18 +0x3f=0x18 +0x38=0x20 +0x45=1 +0x4a=0x14 +0x4c=0xf0 ...
```
Another message window (`FUN_8c2dcf..`, MEETING): `+0x3c=0x14 +0x3d=3 +0x3e=0x18 +0x3f=0x17 +0x40=1 +0x4a=0x90`;
a label window with `+0x3c=7 +0x3d=1`. Other overlays set their own values (not surveyed individually).

### 4.4 Layout `FUN_8c2de294` (MEETING 0x8c2de294; asm at 0x8c2de2da-0x8c2de4b8)  (PROVEN)
```c
iVar4 = (char)win[0x3c] - 1;  iVar5 = (units + 1) >> 1;          // units: 2 per full cell, 1 per half cell
if (iVar4 < iVar5)                                   { x = x0; y += win[0x3f]; units = 0; }   // wrap
else if (iVar5 == iVar4 && win[0x45]==0 && !(code & 0x4000)) { same wrap }
draw glyph (unless code==0x2020);
if (!(code & 0x8000)) { units += 2; x += win[0x3e]; }  else { units += 1; x += win[0x3e] >> 1; }   // 0x2020 counts as half
code == 0x200a : x = x0; y += win[0x3f]; units = 0      // explicit newline
```
Consequences (`tsengine.max_ascii_per_line`): with `W=+0x3c` and `+0x45=1`: full-width chars per line = `W`,
**half-width (ASCII) chars per line = `2W-1`**; with `+0x45=0`: `W-1` and `2W-3`. Default dialogue window
(W=20, flag 1): 39 ASCII chars/line. There is **no word wrap, no row clipping, no automatic paging**: translators must
insert `\n` at word boundaries (`tsengine.word_wrap()` does this) and keep within the window's row budget themselves.
Advance is constant per class (half = `advance>>1`); there is no width table.

## 5. Patch points for good English

1. **Nothing to patch for fixed-width English.** Use ASCII, `\n` at word boundaries, <= `2W-1` chars/line.
   Half-width font already has upper/lower case, digits, punctuation (rendered quality checked as ASCII art).
2. **Extra Latin glyphs** (é, ñ, ü, ½, bullets, ...): redraw glyphs in the half-width table of `FONT.BIN`
   (byte 0xA0-0xDF -> idx 0x60..0x9f = offset `0x9c51c + idx*144`) in BOTH `FONT.BIN` and `ATFIRST/FONT.BIN`
   and write those bytes in strings (engine does not care about cp932 meaning). 0xA0-0xB0 carry the hang flag.
3. **Names / numbers**: `%D` prints full-width digits (wide), `%m` builds money text from Japanese pieces copied at fixed
   lengths (2/4/2/3 bytes): both are fixed by code, see docs/number-formats.md (tools/moneypatch.py, `--money-format on`:
   `%D` -> ASCII digits, `%m` -> `Y60M` / `Y1.315bn`).  `%2d`-style widths print literally in a window.  `#sname#`/`#YOU#` content comes from game
   data (outside the text tables).
4. **Window width/capacity**: `+0x3c` (and `+0x3e`) are stores in overlay code (e.g. MEETING `0x8c2dcf..`/`FUN_8c2de988`
   `mov #0x14,r?; mov.b r?,@(0x3c,r?)`); widen windows by changing these immediates where English needs more room
   (the frame graphics are separate textures, UNKNOWN).
5. **Proportional advance** (optional): in each overlay copy of `FUN_8c2de294` change the advance code
   (MEETING VAs: half-width `0x8c2de490-0x8c2de49e` = `mov.b @(0x3e,r14),r2; ...; shar r2; add r2,r10; add #1,r11`,
   full-width `0x8c2de4a2-0x8c2de4a8`) to add `width[code&0x7f]` from a table, and replace the wrap test
   (`0x8c2de33a-0x8c2de36a`, registers r10=x pen, r11=units, r12=code, r14=window) by a pixel-width test.
   Needs a free spot for the table + trampoline. Head 120 B / loop 236 B / window init 104 B of that function are
   byte-identical in **97 of 114 overlays** (`survey_overlays.tsv`, column `layout_sig`), so one signature-based patcher
   covers them; 7 overlays contain the library but with different bytes (COMM, CON_REP, CSAVE3, J1_REP, NF_CON, PASS_PL,
   PL_CON), 9 have no library (BPMWEEK FACEMDUL LOADBAR LOGO MOVIE MOVIE_BG OFFICE TITLE WEEKLY) - their text path is
   UNKNOWN (OFFICE/TITLE/WEEKLY probably draw via other means or contain little text).
   Because the original needs 2 cells of slack to emulate proportional spacing, this is a "nice to have".
6. **Controls to keep when translating**: keep every `@X/`, `=X/`, `%s/%d`, `#..#` token and raw control bytes
   (<0x20 -> `<XX>` tokens in the translation DB); `0x11-0x19` are colours.

## 6. Overlay loading, BSS and "append vs slack"  (mostly PROVEN, details INFERRED)

Overlay stub (offset 0, e.g. MEETING `0xd208d00a...`, literals at 0x24..0x34):
```
r6 = (*(u32*)ENDVAR | 0x80000000) & ~0x1f ; r6 += 0x20 ; r5 = LOAD_BASE ; r4 = DESCRIPTOR
call *(0x8c159144) = FUN_8c163194(r4,r5,r6) ; return DESCRIPTOR
```
`FUN_8c163194(desc, base, end)`: `desc[0] = FUN_8c1631be(base)` (index of `base` in the slot table at 0x8c16bf9c) and
`desc[4] = end` - nothing else (no clearing, PROVEN). Slot table (base,size): `0x8c2b0000/0x20000`, `0x8c2d0000..0x8c9d0000` each
`0x100000`, `0x8cad0000/0x90000`, `0x8cb60000/0x40000`, `0x8cba0000/0x1bc000`.

Loader state machine `FUN_8c162ac0` (0x8c162ac0), opener `FUN_8c162848(…, name, …, load_addr)`:
* the **caller chooses the load address** (it must equal a slot base); after the read, `FUN_8c15fd7e(handle)` gives the load
  address, the stub is called, and `FUN_8c1631be(load)` must equal `desc[0]` or `MODULE ADDRESS MISS ERROR` is printed
  (so the base literal in the stub must match what the flow table asked for);
* **size = file system length**: `FUN_8c15fb72`/`FUN_8c15fc3c` store `len` (gdfs stat) at handle+0x28 and
  `(len+0x7ff)>>11` at +0x2c; the read covers whole sectors, and the sector span marks the 1 MB slots covered. No size table.
* heap/arena: `slot+0x40 = desc[4]` (`_end` rounded) and `slot+0x14 = (sum of slot sizes + base) - desc[4]`;
  `FUN_8c163224` then writes the first free-block header **at `_end`** and the module's `malloc` serves `[_end, base+N MB)`.
* BSS clearing: not done by the generic stub or by the loader (PROVEN for `FUN_8c163194`/`FUN_8c162ac0`). `GAME.BIN` has an extra loop in
  its stub (hand-disassembled from the raw words, INFERRED) that zeroes `[*(0x8c4bc88c)=0x8c4b58dc, *(0x8c4bc890)=0x8c517608)`, i.e. the last
  0x61d2c bytes up to its file end; `TRAINING.BIN`'s stub has a different variant (not decoded).

`ENDVAR` (a u32 inside the image) classification by `ts_survey.py` (heuristic on stub literals; see tsv):
**33 overlays have `_end == file end` (no BSS)**, 76 have BSS (`_end` - file end = 245 B .. 678 KB, e.g. MEETING 250262 B,
FLOW1..11 3309 B), 2 `end<file` (MOVIE, MOVIE_BG), 2 not found (GETREP, NENREP), SECBND is another format.

**Conclusion (INFERRED from the code above, needs the dynamic test in 8.1):**
* Appending X bytes to an overlay and changing nothing else is **unsafe**: the appended bytes land on `_end` where the
  allocator header is written (no-BSS case) or on the BSS variables (BSS case).
* For the 33 no-BSS overlays it is safe to append **if** the u32 at `ENDVAR` is increased by X (stub then passes the new end,
  heap starts after the new data). Heap shrinks by X only.
* For BSS overlays do not append; place new strings in existing slack/padding or reuse the original string slots
  (translation must fit `max_bytes`), or relocate strings into unused tails of other regions. (Growing `_end` does not help there: BSS addresses are
  absolute in the code, so BSS cannot move.)
* The loader also reads whole sectors, so the file-system rebuild must update the ISO directory lengths; reading is by path.

## 7. Verification actually run

* `fontdump.py`: all 3648 + 160 glyphs of `FONT.BIN` and `ATFIRST/FONT.BIN` decoded; glyph sizes all 288 B; glyph diff between the
  two files = glyph 3580 only; half-width tables identical.
* `tsengine.py`: model of conversion/layout; `max_ascii_per_line(20,1)=39`, `(20,0)=37`, `(7,1)=13`; `sjis_to_glyph(0x82a0)=283` (あ,
  confirmed visually), `0x889f=565`, `0x8140=0`.
* `ts_survey.py`: 114 overlays parsed, 104 with the library, 97 with identical layout code, end-var classification (tsv).
* NOT run: any emulation, any graphics call, any real patch.

## 8. Dynamic tests to settle the UNKNOWNs (no emulator available here)

1. **Overlay append safety**: patch a no-BSS overlay (e.g. `CE_VS.BIN`, `NEWUNIF.BIN`) by appending 0x1000 bytes and raising the
   `ENDVAR` word by 0x1000, boot in an emulator (Flycast/Redream) to the screen using it, then repeat without raising the word.
   Also dump RAM at `_end` to confirm the arena header is written there.
2. **Wrap formula**: run the game, show a 3-line message with 45 `W` characters and count characters per line (expect 39 for the
   default window) and check that the 40th char wraps; test `.`/`,` at the last cell.
3. **Glyph quad size / half-width spacing**: screenshot a line of `iiiiiiiiii` vs `WWWWWWWWWW` (expect identical 12 px pitch) and check
   the right half of the 32x32 glyph texture is not drawn (no overlap).
4. **Raw-flag windows** (name entry): enter `#`, `@`, `=`, `%` and observe whether they print.
5. **Which FONT.BIN** is read at boot: patch one glyph in `ATFIRST/FONT.BIN` only, then in root `FONT.BIN` only.
6. **Row clipping**: show 5 lines in a 3-row window; confirm no clipping.
