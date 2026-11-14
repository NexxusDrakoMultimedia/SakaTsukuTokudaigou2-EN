# Proportional half-width font (patch design, addresses, risks, live test)

Status words: **PROVEN** = decoded, measured or executed (address / script given). **INFERRED** = follows from PROVEN facts but not observed in the game.
**UNKNOWN** = needs the emulator or hardware.

**Nothing in this document has been run in Flycast or on a Dreamcast.** The only execution so far is `tools/sh4sim.py`, an SH-4 integer interpreter
that runs the real layout-function bytes of the overlays (FPU and draw calls stubbed). The feature is off by default
(`--proportional-font off`) until the live test in section 7 has been done.

Investigation records (kept as they are, this file only summarises them): `docs/font-hook-notes.md` (where the pen advances),
`docs/font-widths.md` (glyph measurements, advance rule), `docs/font-patch-design.md` (placement options, per-site appendix, option 1A).

## 1. What it does

| piece | what changes | size effect |
|---|---|---|
| `1ST_READ.BIN` tail | 104 byte routine ("cave") at `0x8c299800`, 256 byte advance table at `0x8c299900` (file offset = address - `0x8c010000`) | none, both areas were zero |
| 98 overlays (97 `FLOW_PRG/*.BIN` + `ATFIRST/HELP.BIN`) | hook H1 (16 bytes, advance) and H2 (36..68 bytes, wrap) inside the statically linked `tsString` layout function | none, in place |
| `/FONT.BIN` and `/ATFIRST/FONT.BIN` | 43 half-width glyphs (`0x21-0x7E` except the digits) shifted left so that the ink starts at column 0 (lossless) | none |
| optional `ABC` variants | same hooks in 6 "B" overlays (COMM, CON_REP, NF_CON, PASS_PL, J1_REP, PL_CON) and 1 "C" overlay (CSAVE3); INFERRED dead code, off by default | none |

Effect (PROVEN by table, `fontpatch.py table`): ASCII advance 5..13 px, mean 10.98 px over the 94 printable codes (12 before); space 6; digits stay 12 so numeric
columns keep their pitch. On the English sample the weighted mean is about 10 px per character (docs/font-widths.md), i.e. roughly 47 characters per 468 px line instead of 39.

## 2. Usage

```
python -I -X utf8 tools/build_patch.py --proportional-font on        # table + shifted glyphs + hooks
python -I -X utf8 tools/build_patch.py --proportional-font control   # hooks + all-12 table, glyphs untouched: must behave exactly like the original game
python -I -X utf8 tools/build_patch.py --proportional-font off       # default: nothing of this feature
   --prop-font-variants A|ABC        # A (default) = the 98 live copies; ABC adds the 7 probably-dead copies
   --prop-font-place tail|gap1       # tail = 0x8c299800 (default); gap1 = 0x8c13bb80 (alternative, same code)
python -I -X utf8 tools/fontpatch.py scan | table | patch [--all] [--dump DIR] | lua
python -I -X utf8 tools/fontcheck.py [--quick]                       # static self-check, 1-3 minutes (needs capstone)
python -I -X utf8 tools/test_pipeline.py                             # contains test group F
```

* Library entry point: `fontpatch.make_patches(read, current=None, variants='A', wrap=True, place='tail', overrides=None, expect=None, glyphs=True)` returns
  `({iso_path: bytes}, report)`; `read(rel)` returns an ORIGINAL extracted file, `current` are bytes from earlier pipeline stages (hooks are found by byte signature in the
  CURRENT bytes, so text patches and repacking compose). `build_patch.apply_prop_font` runs last, after `apply_files`.
* Per-character overrides: `translation/font/advance.json`, e.g. `{"0x41": 12, "i": 4}`, values 1..24 (applied last, indices are the low byte of the code).
* The integration refuses (raises `PipelineError`) when the reserve in `1ST_READ.BIN` is not all zero, when a wrap block does not match its template, or when
  the number of hooked overlays differs from 98 (A) / 6 (B) / 1 (C).
* Control mode is the safest first disc: if it differs from the original in game, the hooks themselves are wrong and the table is not to blame.

## 3. The drawer (re-verified in this session against the bytes)

PROVEN, `extracted/FLOW_PRG/MEETING.BIN` (load base `0x8c2d0000`, `tools/re/textengine/survey_overlays.tsv`), layout/draw function `0x8c2de294`:

```
8c2de48a  extu.w r12,r12          ; r12 = code; half-width codes are 0x8000 | byte  (a blank 0x2020 is rewritten to 0x8000 at 0x8c2de392)
8c2de48c  tst r9,r12              ; r9 = 0x8000
8c2de48e  bt 0x8c2de4a2           ; bit 15 clear -> full-width path
8c2de490  mov #62,r0              ; --- half-width: replaced by H1
8c2de492  mov.b @(r0,r14),r2      ; r2 = (int8) window[0x3e]  (24 for the normal text windows)
8c2de494  mov #0,r3 ; cmp/gt r2,r3 ; addc r3,r2 ; shar r2     ; r2 = A/2 rounded toward 0  (= 12)
8c2de49c  add r2,r10              ; pen x += 12
8c2de49e  bra 0x8c2de4aa
8c2de4a0  add #1,r11              ; units += 1 (half cell)
8c2de4a2  ...  add r3,r10 ; add #2,r11    ; full-width: pen += A, units += 2
```

* r10 = pen x, r11 = units (half = 1, full = 2), r12 = code, r14 = window, r8 = pen y. The wrap block is `0x8c2de334-0x8c2de376` (H2): wrap when
  `(units+1)>>1 > W-1` (W = `win[0x3c]` cells), or `== W-1` when `win[0x45]==0` and the code has no 0x4000 hang flag; the wrap action loads x0 (`win[0x4a]`) into r10, adds the
  line height (`win[0x3f]`) to r8 and sets units = r13 (0).
* The layout is stateless: recomputed from the window origin on every call, so a change of advance needs no state fix-up elsewhere.
* The back end (jump-table slots in `1ST_READ.BIN`, glyph blit `FUN_8c15e8ea`) draws whole 12x24 / 24x24 tiles and knows no advance (docs/font-hook-notes.md, PROVEN).
* The 12 is `win[0x3e]/2`, not a constant: stores of 24 (142 sites), 16 (42), 10, 32, 48, 5, 1 exist. Hence the cave only uses the table when the window advance is exactly 24 and otherwise keeps `A>>1`.
* The function is copied into 105 overlays by static linking (variants A 98, B 6, C 1; exact byte signatures in `fontpatch.H1_OLD/H2_OLD`). In the RAM dumps the resident copy is `ATFIRST/HELP.BIN`
  (head `0x8cb64bfc`); the MEETING copy is not loaded in the four dumps, so the exact original bytes of the A-variant function were checked in the file only.

## 4. The patch (exact addresses)

### 4.1 Cave and table (placement `tail`)
```
0x8c299800  adv_A   bra adv_c ; mov #62,r0           (entry for variants A and C)
0x8c299804  adv_B   mov #54,r0                       (entry for variant B)
0x8c299806  adv_c   mov.b @(r0,r14),r2 ; mov #24,r3 ; cmp/eq r3,r2 ; bf adv_gen
0x8c29980e          mov.l @(tblp),r1 ; extu.b r4,r0 ; mov.b @(r0,r1),r0 ; tst r0,r0 ; bf ret ; mov #12,r0   ; 0 = no entry -> 12
0x8c29981a  ret     rts ; nop
0x8c29981e  adv_gen mov #0,r3 ; cmp/gt r2,r3 ; addc r3,r2 ; shar r2 ; rts ; mov r2,r0                    ; original A>>1
0x8c29982a  wrap_A  bra wrap_c ; mov #0,r1             (wrap_B at 0x8c29982e: mov #-8,r1)
0x8c299830  wrap_c  W=@(60+r1), A=@(62+r1), L=A*(W-1); flag=@(69+r1); if flag==0 and !(code&0x4000): L-=A;
                    r0 = ((r4 - x0@(74+r1)) > L)  ; rts
0x8c299864  .long 0x8c299900                         (TABLE)
```
Listing (capstone) is in `build/font/font_patch_cave.txt` and was re-disassembled this session. Clobbers r0-r5 and MACL only (`mul.l`).
Table: `0x8c299900-0x8c2999ff`, indexed by the **low byte** of the code (`extu.b`; not `&0x7f`, because katakana slots 0xA0-0xDF would collide with ASCII). Index 0 = space (6 px),
because the string compiler's blank 0x2020 reaches the drawer as 0x8000. A zero entry means "use 12", so the 0x80-0x9f and all katakana entries (still centred 12 px art) stay at 12.

### 4.2 H1 (advance) - 16 bytes at the site, 105 sites, always 4-aligned
Variant A, MEETING, site `0x8c2de490` (PROVEN, disassembled from the patched bytes):
```
8c2de490  mov.l @(0x8c2de49c),r3     ; literal = 0x8c299800
8c2de492  jsr @r3
8c2de494  mov r12,r4                 ; delay slot: code
8c2de496  add r0,r10                 ; pen += table value   (B, C: add r0,r11)
8c2de498  bra 0x8c2de4aa
8c2de49a  add #1,r11                 ; units += 1, kept for the legacy wrap and cursor logic
8c2de49c  .long 0x8c299800           ; (B: 0x8c299804)
```
Old/new hex: A `3ee0ec0200e327333e3221422c3a04a0` -> `02d30b43c3640c3a07a0017b0098298c`; B and C in `docs/font-patch-design.md` s4.1. Per-overlay addresses:
Appendix A there and `build/font/font_patch_sites.tsv`.

### 4.3 H2 (wrap) - replaces the cell test
Variant A site = H1 - `0x15c` (MEETING `0x8c2de334`, 68 bytes -> 28 bytes + NOP fill); B and C site = H1 - `0xde` (36 bytes). New code (MEETING):
```
8c2de334  mov r12,r5 ; mov.l @(0x8c2de350),r3 ; jsr @r3 ; mov r10,r4     ; r4 = pen x, r5 = code
8c2de33c  tst r0,r0 ; bt 0x8c2de378                                        ; no wrap -> continue exactly as the original
8c2de340  (original wrap action: r8 += line height; r10 = x0; r11 = r13)   ; bra 0x8c2de378
```
Rule in the cave: wrap when `pen - x0 > A*(W-1)`, or `> A*(W-2)` when `win[0x45]==0` and no hang flag. For A = 24 and a pen that moves in 12 px steps this is the original
cell rule (derived by hand this session: u units = 12u px, `(u+1)>>1 > W-1  <=>  u >= 2W-1  <=>  12u > 24(W-1)`; hang case `u >= 2W-3  <=>  12u > 24(W-2)`), and the simulator confirmed
bit-exactness (section 5). Consequence: a character is accepted if it STARTS at or before `x0 + 456` (W=20); with a 13 px glyph its right edge can reach 469 px, one pixel more than the 468 px
of the original. The game has no word wrap, so this only matters for lines that run to the limit.

## 5. Verification

Re-done in this session (independently of the three investigators): original bytes of the MEETING function disassembled at `0x8c2de334-0x8c2de376` and `0x8c2de48a-0x8c2de4aa`
(registers and the advance instructions `add r2,r10` at `0x8c2de49c` / `add r3,r10` at `0x8c2de4a8` confirmed), patched H1 and H2 and the whole cave disassembled with capstone and read, the
literal and `mov.l` displacements recomputed by hand, the wrap equivalence derived by hand, the final table compared with `tools/re/font/widths.json`
(identical for all printable ASCII except digits `1` (8 -> 12) and `4` (13 -> 12), forced to 12 by design; katakana left at 0 = 12), `python -I -X utf8 tools/test_pipeline.py` run: 135 checks, 0 failed (group F: 23 checks).

Static self-check (`tools/fontcheck.py`, output `build/font/fontcheck_output.txt`, PROVEN by execution, full run 188 s, 0 failures):
1. cave bytes == cave assembled by `tools/sh4asm2.py` from the source (independent encoder), both placements, 100 instructions decoded by capstone;
2. 105 sites at their real load addresses: 2093 patched instructions decoded and matched, literals / branch targets / delay slots / size checked, no xref into a replaced interior;
3. the cave executed in `tools/sh4sim.py` against Python formulas: 4696 cases;
4. the real layout function of every patched overlay executed (5760 runs, 105 overlays): all-12 and all-0 tables are bit-exact the ORIGINAL (pen x and y after every code); the real table gives
   the pen x of the spec. Sample pen advances (MEETING, W=20, A=24):
   * `Hello, World! iiii WWWW`: 11 13 5 5 13 5 6 13 13 9 5 12 6 6 5 5 5 5 6 13 13 13 13, end 220 px instead of 296;
   * `The goalkeeper is injured.`: 13 11 13 6 12 13 13 5 13 13 13 12 13 9 6 5 12 6 5 11 9 13 9 13 12 5, end 285 px instead of 332;
   * `Illegal little pill: 10-0 (1250)`: end 292 px instead of 404; a 101 character line without newline wraps before char #46 (patched) vs #39 (original).

`tools/fontpatch.py` also refuses to patch a file whose hooks do not match, so a damaged image cannot be half patched. `tools/test_pipeline.py` group F additionally checks: flag off = no patches, 101 files patched
(98 overlays + 1ST_READ.BIN + 2 FONT.BIN), sizes unchanged, determinism, overlays differ only in the hook regions (8036 bytes), 1ST_READ differs only in cave + table, font full-width glyphs/header unchanged,
every advance leaves at least 1 blank pixel after the strong ink, composition with text patches, control mode, a built disc with exactly the 102 intended files changed, and that `tools/emu/fonttest.lua` is current.

## 6. Disagreements between the investigators and how they were resolved

| topic | notes | decision |
|---|---|---|
| hook shape | `font-hook-notes`: 32 byte H1 calling `ADVFN(code, window)` with scaling `(tbl*a+12)/24`, routine in the 1ST_READ pre-BSS gap `0x8c13bb80`. `font-patch-design`: 16 byte H1, table used only when A = 24, cave in the tail | the 16 byte hook: smaller, executed bit-exact in 105 overlays. The scaling for A = 16/32 is NOT implemented, such windows keep their fixed advance. `gap1` remains selectable |
| table content | `widths.json` has own values for digits and katakana | digits forced to 12 (numeric columns), katakana left at "12" because their art is centred; everything else equals `widths.json` |
| dead copies | both agree B and C copies call stale 1ST_READ addresses (INFERRED dead) | A only by default, `ABC` as an option |
| table index | `& 0x7f` would be wrong | low byte (`extu.b`), agreed by all three |
| glyph art | width study says redraw; design says "must be left aligned" | `fontpatch.proportional_font` shifts the 43 glyphs losslessly (ink to column 0) in both FONT.BIN copies; nothing is redrawn |

## 7. Live test without rebuilding a disc: `tools/emu/fonttest.lua`

Self-contained: embeds the cave, the table, the shifted glyphs and the hook templates; uses only the bridge helpers `peek` / `poke` / `say` of `tools/emu/live.lua`
(and `flycast.memory.read32`); presses no button, reads and writes no file, results go to `build/emu/live.log`. It is generated by `python -I -X utf8 tools/fontpatch.py lua`
from `tools/emu/fonttest.lua.in` (a test keeps it current). It checks that the target bytes are what it expects before it writes (zero cave area, expected glyphs, known hook bytes) and aborts or skips otherwise.

With Flycast running `tools/emu/live.lua` (the user starts the game; do not do this while the machine is being used for something else), from the project root in PowerShell:
```
"FONTTEST_MODE = 'prop'" | Set-Content build\emu\cmd.lua -Encoding ascii
Get-Content tools\emu\fonttest.lua | Add-Content build\emu\cmd.lua -Encoding ascii
```
The bridge executes `cmd.lua` within about 20 frames and deletes it. Then read `build/emu/live.log` (lines starting `fonttest:`).

| MODE | effect |
|---|---|
| `prop` | glyphs left aligned + table + H1 + H2 (the real thing) |
| `adv` | like `prop` without H2: advance proportional, wrap still after 39 cells (try this first) |
| `fixed` | control: all advances 12, original glyphs, hooks installed: the screen must look exactly like the unpatched game |
| `restore` | original glyphs and original overlay bytes put back (cave stays, inert) |
| `status` | report only |

Add `FONTTEST_WATCH = true` on the first line of `cmd.lua` to re-scan every ~4 seconds and hook overlays loaded since (the scan reads about 2.7 million words and hitches the frame rate).
The scan covers the overlay arena `0x8c2d0000-0x8cd5c000`, so the resident `HELP` copy and the currently loaded screen are both found. Text that is already on screen keeps its glyph textures: leave the
screen and open it again. Good screens: CLUBEDIT (Name & Mascot), any dialogue with `iiii WWWW` style strings, the HELP screens.

UNPROVEN: that `flycast.memory.write8` invalidates the dynarec's translated blocks (if nothing changes after `prop`, switch Flycast's CPU to the interpreter or leave and re-enter the screen); that the Lua
file loads (no Lua interpreter was available here, so it has not even been syntax checked; it is plain Lua 5.4 generated text with 28 locals).

## 8. Risks and what is unproven

| # | item | status | how to settle |
|---|---|---|---|
| 1 | The patched game boots and text draws; hook correctness in a real run | UNKNOWN, static + simulator only | `control` disc, then the live test `fixed`, then `adv`, `prop` |
| 2 | Quads of 12 px at a pen step below 12 overlap. If the paper texels (nibble 15) are opaque, each glyph covers the right columns of the previous one | UNKNOWN (the blit converts the nibble into all four ARGB4444 channels; alpha of 15 not traced) | any narrow-glyph run: `iiii`, `ll`, `.,` ; after the shift the overlap is paper-over-paper columns only if transparent |
| 3 | Cave and table in the tail `0x8c299800-0x8c2999ff` are never written by the game in states that were not dumped (match, season, save/load, ending) | INFERRED (zero in 4 dumps; highest touched byte below is `0x8c2992bf`; no pointer into the range in 1ST_READ / FLOW_PRG / ATFIRST) | canary over the range after every mode; the translation bank must start at `0x8c299a00` |
| 4 | BIOS/Flycast accepts the modified same-size `1ST_READ.BIN` | UNKNOWN (no checksum known) | boot the `control` disc |
| 5 | MACL is clobbered by `mul.l` in the wrap routine | PROVEN not live at the hook (randomised-clobber liveness test, 180 runs) | - |
| 6 | Windows with advance 16 / 32 / 48 / 10 keep the fixed advance and the old wrap | PROVEN design limit | scale by `win[0x3e]/24` in the cave if such a window carries English |
| 7 | Not covered by the tsString hooks: linear-text users (`DMCLBEDT` 0x8c2d9758, ENDING, GAME; the writer is centred by `--lin-center`), OFFICE / WEEKLY / BPMWEEK / FACEMDUL (call the font slots directly, no copy of the library), TITLE / LOGO / LOADBAR / MOVIE.  (GAME.BIN's own line engine at `0x8c3202b0`, the commentary subtitle, is a separate case: its pen arithmetic is now located - a constant 12 px per half-width cell - and `--cell-prop` makes it read the table, `docs/layout-issues.md` s19.) | PROVEN by signature scan; the pen arithmetic of the rest UNKNOWN | those screens keep 12 px steps, but they now draw the left-aligned glyphs (item 10) |
| 8 | Callers that centre or right align by counting characters (name entry, menus) assume 12 px per character | **PROVEN** (second playtest): blank-padded columns (PLNUMSET shirt numbers) and `x = anchor - 12 * strlen` cells (player-card panel of CAP_SLCT / ENDOPT / EVENT) are wrong or clip; the rest of the count is a lead list (`docs/layout-issues.md` s10.4) | s10 below: `align_fix` |
| 9 | Placeholder tokens (`#tk00`, `%d`, `$1`) expand at run time to a different width than their source text | UNKNOWN | check names / numbers in dialogue |
| 10 | The shifted glyph art makes screens that are not hooked (item 7) look off by a few pixels | INFERRED | accept, or restrict the shift to hooked windows (not possible: one shared FONT) |
| 11 | Hang-flag mask: the original reads a word from the pool at `0x8c2de446`; the cave hard-codes 0x4000 | PROVEN equal in MEETING (the word is 0x4000, read this session); the other copies are byte-signature identical to the function, so INFERRED equal | the simulator runs of check 4 use each overlay's own bytes and matched the original in all-12 mode |

## 9. Files

* `tools/fontpatch.py` - the patch (cave source bytes, hooks, site scan, `make_patches`, `lua_source`, CLI).
* `tools/fontcheck.py` - static self-check and interpreter runs; `tools/sh4asm2.py`, `tools/sh4sim.py` - assembler and SH-4 interpreter it needs.
* `tools/emu/fonttest.lua`, `tools/emu/fonttest.lua.in` - live test (generated file and its template).
* `tools/build_patch.py` (`apply_prop_font`, flags above), `tools/test_pipeline.py` (group F).
* Investigation scripts and evidence: `tools/re/font/`, `build/font/` (`fontcheck_output.txt`, `font_patch_sites.tsv`, `font_patch_cave.txt`, previews `widths_preview_*.png`).

## 10. Alignment fix (`align_fix`, second playtest; evidence in `docs/layout-issues.md` s10)

The advance table is applied by the cave AFTER the caller has done its own cell arithmetic.  Two consequences were found in the second playtest and are fixed by an optional second cave, `font.align` (`0x8c299700`, 224 of 256 bytes, tail placement, variant A hooks):

| piece | what | where |
|---|---|---|
| `at_snap` | the table path of the advance routine (`rts ; nop` at cave +0x1a) branches here for a blank: the pad blanks of a run of two or more, followed by a glyph, advance to `x0 + 12 * (units + 1)` (never less than 4 px), so columns made by padding (`name + blanks + %2d`) land on the pixel of the original fixed-cell layout; single word spaces and trailing runs are untouched | all 98 hooked overlays (the PLNUMSET shirt-number list is the case that was reported) |
| `pw3` | strlen replacement returning `ceil(pixel width / 3)`, plus the `* 4` of `x = anchor - 12 * len` turned into a `nop`: right-anchored cells end at their anchor instead of up to 5 px past it | the shared player-card panel: CAP_SLCT, ENDOPT, EVENT (20 idioms + 8 strlen literals each) |

* API: `fontpatch.make_patches(..., align_fix=True)` (default False; recommended ON in the build), `fontpatch.patch_1st_read(..., align=True)`, `cave_bytes(ct, scale, align_addr)`, `align_bytes`, `align_symbols`, `panel_scan`, `panel_edits`; `python -I -X utf8 tools/fontpatch.py patch --align-fix`.
  Requires `variants='A'`, the tail placement and the wrap hook; refuses a panel overlay whose bytes are not the known panel.
* With `--proportional-font control` (all-12 table) the fix changes nothing (tested bit-exact against the original layout function, blank runs included).  With `--prop-scale` it only touches the A == 24 path.
* Cost per blank: about 30 instructions, only for blanks of runs; nothing for other characters.
* Tests: `python -I -X utf8 tools/test_alignfix.py` (19 tests, about 1 minute; `ALIGN_FULL=1` runs the snap in all 98 overlays).  Not run in Flycast.
