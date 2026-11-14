# Glyph draw routine: where the 12 px advance lives, and the minimal hook points (agent `fonthook`)

Status words: **PROVEN** = read from code/data/RAM dump with an address (re-checkable with the scripts below),
**INFERRED** = follows from PROVEN facts but never executed, **UNKNOWN** = not determined. Nothing here was run on an
emulator (Flycast was not touched); the RAM dumps in `build/emu/` were only read. All disassembly is my own SH-4
disassembler `tools/re/font/sh4dis.py` cross-checked against Ghidra 12.2 decompiles (own project copy
`<GHIDRA_PROJECTS>\ghproj_fonthook`: `1ST_READ.BIN` + `MEETING.BIN` at 0x8c2d0000).

Related (written in parallel by other agents, consistent with this note): `docs/text-engine.md` (layout formula),
`docs/font-widths.md` (the width table), `tools/re/font/fontpatch.py` (patch builder).

## 0. Answers in one table

| Question | Answer |
|---|---|
| Is there one glyph drawer? | **No: two layers.** Back end (character code -> glyph pixels -> texture) is ONE shared copy in `1ST_READ.BIN`, reached only through the jump table at 0x8c159000. Front end (pen position, advance, wrap, sprite emission) is a **statically linked copy of the "tsString" window library in every overlay that shows text: 105 copies** (98 code variant A, 6 variant B, 1 variant C) incl. the resident `ATFIRST/HELP.BIN` copy. PROVEN (`hooksites.tsv`, byte-signature scan of all files under `extracted/`). |
| Where is the 12 px? | **Nowhere as a constant.** Half advance = `(int8)win[0x3e] / 2` (rounded toward 0), full advance = `win[0x3e]`, evaluated per character in the layout function. `win[0x3e]` is 24 in the default window (so 12 / 24 px) but **24, 16, 32, 48, 10 (and 1, 5) are stored by overlay code** (section 4.4). The sprite quad of a half-width glyph is a separate 12 px (at advance 24) constant in a per-window template. PROVEN. |
| Half-width glyph pixel data | `FONT.BIN` half block, `index*0x90 + *(0x8c22837c)`, `index = byte-0x20` (byte < 0xA0) or `byte-0x40`; code = `0x8000|byte` (| 0x4000 hang flag, masked off by the blit). One consumer: `FUN_8c15eca4` (texture path) and `FUN_8c15e9c6` (linear-bitmap path). PROVEN (section 2). |
| Minimal hook | **2 sites per layout copy**: H1 = the advance (16 words, F+0x1f6) and H2 = the wrap test (34 words, F+0xa0), both replaced in place by a `jsr` into ONE routine placed in 1ST_READ; plus one 256-byte width table. Both blocks have room (section 7, `hookdesign.py` builds and disassembles the exact patch). **The advance must be scaled by the window's `win[0x3e]/24`**, otherwise the 16/32/48 px windows break. |
| What is NOT covered by H1/H2 | the "linear text" path (string -> 4bpp bitmap, hard coded 6/12 bytes per char, 3 overlays), `DMCLBEDT` name width (len*6), `GAME.BIN`'s own line engine (it draws only the commentary / BCAST subtitle box; since stage 11 `--cell-prop` gives it the table advance, section 6), any caller that centres or right-aligns by counting characters (UNKNOWN how many), and 9 overlays that have no library at all (section 6). |

## 1. Evidence base

* `tools/re/font/sh4dis.py` - full-ish SH-4 disassembler (annotates PC-relative literals); `python -I -X utf8 sh4dis.py MEETING.BIN 8c2de294 8c2de4d4`.
* Ghidra headless (JDK 25) with `Dec.java`/`Dis.java` (`hrun.ps1`, `hovl.ps1`, `himp.ps1`, `hdis.ps1`): raw decompiles `h1.txt` (1ST_READ glyph back end),
  `h2.txt`/`h3.txt` (draw/sprite helpers and compiler runtime), `hm1.txt` (MEETING layout, typewriters, linear renderer).
* Surveys over all 116 overlay files (`build/memmap/overlays.tsv`): `layoutsurvey.py/.tsv`, `hooksites.py/.tsv` (exact patch addresses of all 105 copies),
  `fieldstores.py/.txt` (immediates stored into window fields), `fieldreads.py/.txt`, `lincallers.py/.txt`, `slotscan*.py/.txt`, `stalecheck.py/.txt`, `widthidioms.py/.txt`.
* RAM dumps (`livewin.py/.txt`): live window objects located by their sprite-template copy; the layout code is resident in every dump.
* `layoutmodel.py`: executable model of the original layout loop and of the proposed pixel-based replacement (randomised equivalence test).
* `hookdesign.py` (+ `hookdesign_meeting.txt`): the concrete in-place patch for variant A, before/after disassembly with displacement checks (not applied to any file).

## 2. Back end in `1ST_READ.BIN` (single shared copy) - PROVEN

Jump table at 0x8c159000 (overlays call `*(0x8c159000+off)`):

| slot | function | role |
|---|---|---|
| 0x3ac | `FUN_8c15e7a0` | SJIS pair -> full-width glyph index (not used for half-width) |
| 0x3b0 | `FUN_8c15e88e` | single byte -> full-width glyph via u16 table 0x8c16a08a (0 users found in the layout path) |
| **0x3b4** | **`FUN_8c15e8ea`** | **glyph blit: `(texlist, desc, code, colour, slot, win)`: fetch glyph into a 32x32 PAL4 texture slot** (internally `FUN_8c15eca4`) |
| 0x3d0 | `FUN_8c15e9c6` | glyph -> linear 4bpp bitmap (stride = `cells*24` px), used by the "linear text" path |
| 0x3d8 | `FUN_8c15e8b6` | glyph -> code reverse lookup |

Ghidra: the only callers of `FUN_8c15e8ea`/`FUN_8c15eca4`/`FUN_8c15e9c6`/`FUN_8c15e7a0` are the table slots themselves; the 1ST_READ code never calls them directly.
The font globals (`0x8c228378` glyph data, `0x8c22837c` half block, `0x8c228380` offset table) are read only in `FUN_8c15e72c` (init), `FUN_8c15e9c6` and `FUN_8c15eca4` (literal scan of 1ST_READ + all overlays). Overlays never touch FONT.BIN memory directly, **except `GAME.BIN`** (`0x8c3202c8`/`0x8c3202e4` load 0x8cd5c004/0x8cd5c000 = FONT header offset table, see section 6).

**Half-width addressing, `FUN_8c15eca4`** (texture path, called from the blit at 0x8c15e914):

```
8c15ecbe  tst r2,r3 ; bt/s -> 8c15ed5c         r2 = 0x8000 (literal 8c15ed48): bit 15 clear -> FULL-width path
8c15ecc6  mov.w @(0x7fff),r0 ; mov.w @(0xa0),r1   mask / split
8c15ecca  and r0,r12                              code & 0x7fff   (strips 0x4000 hang flag too)
8c15ecce  cmp/ge r1,r3 ; ...                      c < 0xa0 ? c-0x20 : c-0x40       (add #-32 / add #-64 at 8c15ecd4 / 8c15ecd6)
8c15ecda  mov.l @(0x8c15ed58)=0x8c22837c,r1       *0x8c22837c = FONT.BIN + hdr[3]  (half block)
8c15ece0..8c15ecee   r4 = idx*0x90 + *r1           (idx*9 via shll2/shll/add, then shll2;shll2 = *16)
8c15ecf6..8c15ed3c   copy 6 bytes per row, 24 rows, into the 24x24 staging buffer 0x8c227a32 with a 12-byte row stride
                      (left 12 px only; the right half keeps stale data -> harmless because the half sprite is only 12 px wide, 3.4)
```
The staging buffer is then twiddled into the 32x32 texture (u16 = 2x2 pixels of 4bpp). `FUN_8c15e9c6` (slot 0x3d0) does the same index math (mask 0x5fff after the 0xbfff pre-mask, 0x90*idx + `*0x8c22837c`) but copies 6 bytes per row into a caller buffer with row skip `(cells*2-1)*6`.
**Nothing in the back end knows an advance**; every glyph is a complete 12x24 (half) or 24x24 (full) tile.

## 3. Front end: the tsString library (duplicated per overlay)

Reference copy = `FLOW_PRG/MEETING.BIN` (base 0x8c2d0000). Object layout (variant A; PROVEN by the layout code and by RAM dumps, section 4.4):
`+0x20` state, `+0x22` u16 code count, `+0x28` slot limit, `+0x2a` glyph slots used, `+0x2c` typewriter index, `+0x30` code array (u16), `+0x38` draw flags,
**`+0x3c` cells per line (W), `+0x3d` rows, `+0x3e` advance (signed byte), `+0x3f` line height**, `+0x40` codes revealed per update, `+0x41/+0x42` colours,
`+0x43` visible, `+0x45` "last cell free" flag, **`+0x46` size class**, `+0x48` raw, **`+0x4a`/`+0x4c` x/y origin (s16)**, `+0x50` float (passed as `fr4` to the sprite call; value 0xbf803d46 in the default ctor = a depth value, not a scale), `+0x54/+0x58` texture list, `+0x6c` three sprite-descriptor pairs, 0x28 bytes each, selected by `+0x46` (3.4), `+0xe4` colour block.

### 3.1 String -> codes `FUN_8c2ddeea` (MEETING) - PROVEN, no widths
Single bytes 0x21..0x7f / 0xa0..0xdf -> `0x8000|byte` (+0x4000 hang flag for 0xa0-0xa5, 0xa7-0xb0); bytes < 0x21 -> `0x2000|byte`; lead bytes -> `sjis_to_glyph` (slot 0x3ac). It only produces the u16 array.

### 3.2 Typewriter / state machines `FUN_8c2de4d4`, `FUN_8c2de758` - PROVEN, no pen arithmetic
For each newly revealed code (up to `+0x40` per call) they call the blit (slot 0x3b4 via `jsr @r10/@r3`: `0x8c2de620`, `0x8c2de84c`) into texture slot `+0x2a` and bump `+0x2a`/`+0x2c`; at the end they call the layout (`bsr 0x8c2de294` at `0x8c2de674`, `0x8c2de8ec`) when `+0x43 != 0`.
So the typewriter has **no 12 px assumption**: it counts codes, not pixels. Line start is not stored: the layout recomputes every glyph position from `+0x4a/+0x4c` **on every call (per frame)**.

### 3.3 Layout + draw `FUN_8c2de294` (variant A addresses; registers: r14 = window, r10 = pen x, r8 = pen y, r11 = "units", r12 = code, r9 = 0x8000, r13 = 0) - PROVEN

```
8c2de2c0..2c8  r10 = (s16)win[0x4a]  (x origin) ; r8 = (s16)win[0x4c] ; r11 = 0 ; 8c2de2ce r9 = 0x8000 (literal 8c2de32c)
8c2de2da  loop top: r12 = (s16)code[i]
8c2de2e4  non-control (code & 0x2000 == 0) or code == 0x2020  -> 8c2de334 (draw)       [8c2de2e8 bt / 8c2de2f0 bt]
8c2de2f2  code == 0x200a (newline): 8c2de2fe  x = win[0x4a] ; y += win[0x3f] ; units = 0 ; other control codes: skipped, no advance
8c2de334..8c2de376  WRAP TEST (below)
8c2de378..8c2de38c  pen -> floats  (lds r10,fpul ; float -> [r15+32] = x ; r8 -> [r15+36] = y)
8c2de38e  if code == 0x2020 : no draw ; 8c2de392 `bra 8c2de48a ; mov r9,r12`  => a blank is advanced as code 0x8000 (low byte 0!), i.e. as a half cell
8c2de396..8c2de420  colour / shadow state, `jsr 0x8c0376f4` (set vertex colour)
8c2de422  tst r9,r3 : half (bit15) -> 8c2de426 ; full -> 8c2de454 : both store the running glyph-slot counter (@r15) in the sprite descriptor (+0x10)
8c2de47e  jsr 0x8c080454 : sprite(r4 = &{x,y,..,+0x18 texlist,+0x1c descriptor}, r5 = 0, r6 = win[0x38]|{0,2}, fr4 = win[0x50])
8c2de48a  extu.w r12,r12
8c2de48c  tst r9,r12
8c2de48e  bt 8c2de4a2                      ; bit 15 clear = full width
          ---- HALF-WIDTH ADVANCE (12 px at win[0x3e] = 24) ----
8c2de490  mov #62,r0                       ; 0x3e
8c2de492  mov.b @(r0,r14),r2               ; a = (int8) win[0x3e]
8c2de494  mov #0,r3
8c2de496  cmp/gt r2,r3 ; 8c2de498 addc r3,r2 ; 8c2de49a shar r2    ; a/2 rounded toward zero
8c2de49c  add r2,r10                       ; pen x += a/2
8c2de49e  bra 8c2de4aa
8c2de4a0  add #1,r11                       ; units += 1
          ---- FULL-WIDTH ADVANCE (24 px) ----
8c2de4a2  mov #62,r0 ; 8c2de4a4 mov.b @(r0,r14),r3 ; 8c2de4a6 add #2,r11 (units += 2) ; 8c2de4a8 add r3,r10   ; pen x += a
8c2de4aa  i++ ; 8c2de4b0..4b8  loop while i < (s16)win[0x2c] (glyphs revealed so far)
```
**These are the only instructions in the whole drawing path that add the advance** (`add r2,r10` at `0x8c2de49c` = 12 px, `add r3,r10` at `0x8c2de4a8` = 24 px).

**Wrap test** `0x8c2de334..0x8c2de376` (PROVEN, transcribed in `layoutmodel.original()`): `r4 = (units+1)>>1 ; r2 = (int8)win[0x3c]-1`;
`r4 > r2` -> wrap (x = win[0x4a], y += win[0x3f], units = 0); else if `r4 == r2 && win[0x45] == 0 && !(code & 0x4000)` -> the same wrap (the `0x8c2de36c..376` copy).
With W = win[0x3c], flag win[0x45] = 1: a glyph is placed while `units <= 2W-2`, i.e. **39 half-width glyphs for W = 20** (model check: `chars per line (default window): [2, 39, 39]`). The wrap uses *units* (1 per half, 2 per full), independent of the advance value.
Note: a space is a drawable code, so a wrap can leave a space at the start of the next line (no trimming). There is **no clipping, no word wrap, no row limit** in this function.

### 3.4 Sprite quad width (the only other 12) - PROVEN (data)
Each window copies a template table (MEETING `0x8c37498c`, 6 entries of 0x14 bytes = 3 size classes x {full, half}) into `win+0x6c` (pair stride 0x28, indexed by `win[0x46]`); entry = u16 `w, h, 0,0,0,0, u1, v1, texslot(+0x10), 0` (`texslot` is written by the layout, `0x8c2de440`/`0x8c2de46e`):

| size class (`win[0x46]`) | full | half | advance seen with it |
|---|---|---|---|
| 0 | 24x24 (u1,v1 = 191) | **12x24** (u1 = 95, v1 = 191) | 24 (RAM: `(adv 24, size 0)`) |
| 1 | 32x32 | 16x32 | 32 (RAM: `(adv 32, size 1)`) |
| 2 | 16x16 | 8x16 | 16 (INFERRED: BPMATCH ctor 0x8c2d3c4a stores `+0x46 = r8`, `+0x3e = 16`, `+0x3f = 19`) |

So the quad of a half glyph is `a/2` px wide and is drawn at the pen x as given; **the glyph tile is always the whole 12-column bitmap**, scaled 2/3 or 4/3 in the 16/32 classes. Consequence: a narrower advance makes tiles overlap (needs transparent paper: UNKNOWN, see section 8), and ink must be left-aligned in the tile (or the sprite x shifted by a left-bearing).

## 4. Duplication, variants, who reaches what

### 4.1 Copies (PROVEN: `hooksites.tsv`, found by 120-byte head signature + exact check of the 34-byte advance code)
| variant | files | code differences | pen x / units regs | fields (cells / advance / lineh / x0) |
|---|---|---|---|---|
| **A** (MEETING) | **98**: 97 `FLOW_PRG/*.BIN` + resident `ATFIRST/HELP.BIN` (the copy at 0x8cb64bfc is present in 5 of the 6 RAM dumps, all but `ram_after_start.bin`) | reference | r10 / r11 | +0x3c / +0x3e / +0x3f / +0x4a |
| **B** (COMM) | 6: COMM CON_REP NF_CON PASS_PL J1_REP PL_CON | same algorithm, object fields 8 lower, F+0x72 wrap, F+0x150 half advance | r11 / r10 | +0x34 / +0x36 / +0x37 / +0x42 (flag +0x3d) |
| **C** (CSAVE3) | 1 | B's registers, A's field offsets | r11 / r10 | +0x3c / +0x3e / +0x3f / +0x4a |

Offsets from the function entry F (`hooksites.tsv` lists every absolute address): A: wrap `F+0xa0 .. F+0xe4`, advance `F+0x1f6 .. F+0x216` (half `+0x1fc`, full `+0x20e`); B and C: wrap `F+0x72 .. F+0xd8`, advance `F+0x150`(half, `0x8c2e0a84`/`0x8c4dd440`) / `F+0x162`(full), next `F+0x16a`.
B and C, with the 1ST_READ addresses they call (`0x8c07e3dc`, `0x8c07e420`, `0x8c028450`, `0x8c028494`), are **linked against a different 1ST_READ build**: in the current `1ST_READ.BIN` those addresses are mid-function (`stalecheck.txt`: 0% of the jsr targets of COMM/CON_REP/NF_CON/PASS_PL/J1_REP/PL_CON and 8% of CSAVE3's look like function entries; median overlay 68%), and 6 of the 7 are at non-slot-aligned bases (`docs/memory-map.md`). **INFERRED: B and C are dead (never loaded) in this build**; patching them is optional.

### 4.2 Linear-text path (`slot 0x3d0`), also duplicated
The 98 A copies contain `FUN_8c2debe0`-style "string -> 4bpp bitmap" code: per glyph `add #12,r12` (full) / `add #6,r12` (half) **bytes** into the bitmap (= 24 / 12 px), row stride `cells*24` px (MEETING `0x8c2dec5e`, `0x8c2dec78`, `0x8c2dec64` = slot 0x3d0). Callers found by `lincallers.py`: only **3 overlays reference it** (DMCLBEDT via `0x8c2d9758`, ENDING `0x8c2dbe48`, GAME `0x8c334268`); the other 95 copies are dead library code (no bsr and no literal pointer to them). PROVEN for the reference count, INFERRED that no indirect call exists.

### 4.3 Which overlay shows text how
* 105 files have a layout copy (above); 104 reference the blit slot 0x3b4 / 0x3ac / 0x3d0 (`slotscan.txt`).
* **No font-slot reference at all**: BPMWEEK, FACEMDUL, LOADBAR, LOGO, OFFICE, TITLE, WEEKLY (`s3ac=s3b4=s3d0=0`); MOVIE/MOVIE_BG only hit 0x3b0-looking halfwords (those are stack offsets, e.g. OFFICE `0x8c6f7a2e`). OFFICE/TITLE/WEEKLY/BPMWEEK still contain 515-1637 Japanese text records (`overlays.tsv`), **how they put that text on screen is UNKNOWN** (no literal pointers into the resident HELP library either).

### 4.4 Live window parameters (RAM dumps, `livewin.txt`) and stored immediates (`fieldstores.txt`)
Windows found by their template copy in `live1/live3/t1_ram.bin` (obj size 252): `(adv, size class, cells)`: `(24,0,25)` x6, `(24,0,20)` x13/38/4, **`(32,1,20)` x40/15**, `(24,0,17)` x1; rows 3, line height 24. Immediates stored into the fields by code (A copies, store sites): advance `{24:142, 16:42, 10:4, 32:2, 48:2, 1:1, 5:1}`, cells `{20:168, 17:69, 25, 10, 9, 8, 5, 2, 1, 0...}`, line height `{24:167, 23:77, 16:25, ...}`. **So the 12 px half pitch is the common case, but 8, 16, 24 and 5 px pitches exist** and a width table has to scale with `win[0x3e]`.

## 5. Where "12 px" / "cells" is assumed (audit)

| place | assumption | status |
|---|---|---|
| layout advance `0x8c2de49c` / `0x8c2de4a8` (x 105 copies) | half = a/2, full = a | PROVEN |
| layout wrap `0x8c2de334..376` | units, `2W-1` half cells per line (39 for W=20) | PROVEN |
| layout line start | `win[0x4a]` re-read at wrap/newline (`0x8c2de34e..352`, `0x8c2de2fe..304`) | PROVEN, no assumption of 12 |
| typewriter (`FUN_8c2de4d4/758`) | none (codes, not pixels) | PROVEN |
| sprite quad (`win+0x6c` templates, `0x8c37498c`) | half quad = a/2 wide, whole 12-col tile drawn | PROVEN |
| back end (blit/fetch) | tile = 12x24 / 24x24 | PROVEN |
| linear path (`0x8c2dec5e/78`, `FUN_8c15e9c6`) | 6 / 12 bytes per glyph, stride `cells*24` px, **no bound check** (an over-long string overruns the bitmap) | PROVEN, 3 users |
| `DMCLBEDT` name edit `0x8c2d9732..974e` | copies <= 40 bytes into a stack buffer, then `len*6` (`mov r12,r1; shll r12; shll2 r1; add r1,r12`) before the call to the linear renderer with cells = 10 | PROVEN (code), meaning INFERRED (byte width of a half-width string) |
| centring / right alignment / cursor positions in menus and name entry | every window is positioned by its creator through `+0x4a/+0x4c`; the library has **no centre flag**. Whether callers compute `len*12` is UNKNOWN: reads of `+0x4a` outside the library at 51 sites, of `+0x3c` at 199, of `+0x3e` at 16 (`fieldreads.txt`, e.g. MEETING `0x8c2d7176`, `0x8c2e04ee` are sprite/cursor placement relative to a window, not string widths); `widthidioms.txt` (x6/x12/mul12 idioms, 630 hits) is a noisy lead list, **not evidence** (I inspected PL_EDIT/CLUBEDIT hits: unrelated rank arithmetic) | UNKNOWN |
| text clipping | none in layout; the sprite drawer `FUN_8c080454` was not analysed for scissoring | INFERRED none |
| string width routines (`strlen*12`) | none in the library; none found by targeted reading | UNKNOWN outside the library |

## 6. Other text engines (not covered by the hooks)

* **`GAME.BIN` second engine = the commentary (BCAST) subtitle line engine, NOT the general in-match "GAME text"** (the match intro `Stadium` / `KICK OFF` and the OPTIONS rows go through the linear writer `FUN_8c15e9c6`, `--lin-center`): function at `0x8c3202b0` reads the FONT header (`0x8cd5c004` offset table, `0x8cd5c000` base), indexes 82-byte per-line records (`mul.l` by 82 at `0x8c320334`/`0x8c32038e`), limits glyph counts with `cmp/ge #37` / `#39`, and calls the **same blit slot** (`0x8c1593b4` at `0x8c320414`, `jsr @r2` at `0x8c320426`). The pen/advance code is now located (stage 11, `docs/layout-issues.md` s19): the half-width advance is the constant `mov #12,r0 ; mov.b r0,@(1,r2)` at `0x8c32049e`, the blank `mov #12,r0` at `0x8c3204f2`, full-width `mov #24,r1` at `0x8c3204c6`, all stored in the 82 byte line record and consumed by the display loop `0x8c31fdc0` (sprite width, UV width, pen step); the advance table is never read.  `--cell-prop` replaces the half-width and blank blocks (call to the 28 byte `font.cell` routine, blank skipped at column 0); it carries its own layout (left aligned from x = 160, wrap at 37 / 39 units).
* GAME/NEWS/TOWN/TRAINING/G_RESULT/SS_EDIT *also* contain the library (A) - the `0x3b0` hits there are false positives (stack offsets).
* `DPFONT` is the browser's font (`2_DP.BIN`), not part of this.

## 7. Minimal hook design (INFERRED design, patch bytes PROVEN to encode/decode; not executed)

**Goal**: per-character advance `adv(c, a)` with `a = win[0x3e]`, applied in every A copy (98 files), optionally B/C.

* **H0 - code + data in ONE place.** Routine and 256-byte table in the `1ST_READ.BIN` zero gap below the jump table (`0x8c13bb80..0x8c159000`, `docs/trans-bank.md` section 2.4; coordinate with the bank cave) or the tail of `/FONT.BIN` (0x8cd5c000-based, already loaded for both the root and ATFIRST copies). Table: byte `b = code & 0xFF` -> width at a = 24 (**index by the low byte, not `& 0x7f`**: the stored code is `0x8000|byte`). Entry for a blank is index 0 (the layout rewrites 0x2020 to 0x8000, section 3.3), so `tbl[0]` is the word space.
* **H1 - advance** (in place, 32 bytes `F+0x1f6..F+0x216`, A variant): `extu.w r12,r12 ; mov r12,r4 ; mov.l @(pool),r3 ; jsr @r3 ; mov r14,r5 (delay) ; add r0,r10 ; bra loop_next ; add #1,r11 ; nops ; .long ADVFN`. `ADVFN(r4 = code, r5 = window) -> r0 = px`:
  `a = (int8)win[0x3e]; if (code & 0x8000) w = (tbl[code & 0xff] * a + 12) / 24 else w = a; return w`. Only r0-r7 are clobbered (callee-saved r8-r14 and the saved PR in the frame are untouched; do not use fr12-fr15, the loop keeps fr15 = 1.0f). Full-width stays `a`.
* **H2 - wrap** (in place, 68 bytes `F+0xa0..F+0xe4`): `extu.w r12,r4 ; mov r14,r5 ; mov.l @(pool),r3 ; jsr @r3 ; mov r10,r6 (delay) ; tst r0,r0 ; bt draw_start ;` then the original wrap action (`mov #63,r0 ; mov.b @(r0,r14),r2 ; mov #74,r0 ; mov.w @(r0,r14),r10 ; add r2,r8 ; bra draw_start ; mov r13,r11`) `; nops ; .long WRAPFN`. `WRAPFN(r4 = code, r5 = window, r6 = pen x) -> r0 = 1 to wrap`:
  `px = r6 - (s16)win[0x4a]; return px >= lim` with `lim = (2W-1)*a/2` (flag win[0x45] = 1; **identical to the original** for uniform widths: `layoutmodel.py` equivalence test, 0 mismatches in 20000 random strings for a in {10,16,24,32,48}, W in {1,2,5,8,10,17,20,25}, both flags) or `lim0 = (2W-3)*a/2` for non-hang chars when flag = 0. For English prefer the *fits* test `px + ADV(code) > (2W-1)*a/2` (the pixel version of "one half cell reserved"; `docs/font-widths.md` section 5 uses 468 px for W = 20, a = 24).
* The `units` counter (`r11`) becomes dead after H2; H1 keeps `add #1,r11` only so that an H1-only build still wraps by count (every glyph then counts as 1 unit, a full-width one too; ship H1 only together with H2).
* **Where to apply**: A: 98 files via `hooksites.tsv` (every address, signature-checked: `core_ok` for all); the same two ADVFN/WRAPFN entry points can serve B/C with their register swap (r11/r10) and field offsets (`+0x36`, `+0x34`, `+0x42`) if they are ever kept.
* Verified here: the exact words, pool displacements (`mov.l @(pc)` target = pool, `bra`/`bt` targets = `loop_next`/`draw_start`), no byte outside the two blocks changes (95 bytes in MEETING) - `hookdesign.py`, output `hookdesign_meeting.txt`.
* **Glyph art assumption**: ink left-aligned in the 12-col tile (the quad is 12 px = a/2 wide, drawn at the pen x; narrower advances overlap the next tile). A left-bearing instead of re-drawing would need a third patch (sprite x = pen - lsb at `0x8c2de378`).
* **Not solved by H1/H2** (stay monospaced or need their own patch): linear-text users (DMCLBEDT, ENDING, GAME: byte advance 6/12 hard-coded in the library copy and in `FUN_8c15e9c6`; proportional would need a nibble-wise blit with 4-bit alignment), `DMCLBEDT` `len*6`, GAME's own engine, any caller-side centring.
* Interaction with other agents' work: `tools/re/font/fontpatch.py` implements the same two sites (its H1/H2) with a cave and a table at the FONT.BIN tail; the sites it finds must equal `hooksites.tsv` (it does for A/B/C: 97+HELP / 6 / 1).

## 8. UNKNOWN / needs a run (nothing could be run)

1. **Paper transparency**: with advance < 12 the next tile overlaps the previous tile's blank right part. Palette alpha of nibble 15 is not read (`FUN_8c15e8ea` passes `colour<<4|colour` and `FUN_8c0283fc` sets the palette bank). Test: draw `Ii` at 5 px pitch.
2. Whether the `win[0x3e] = 16/32/48/10/5/1` windows are text windows that will carry English (list the creating call sites: `fieldstores.txt`). If a=16 windows (rank tables in DRS*, BPMATCH) show English, the glyph is scaled 2/3 (8x16 quad) and the width table must be scaled, not applied raw.
3. Text path of BPMWEEK/OFFICE/TITLE/WEEKLY/LOGO/LOADBAR/FACEMDUL (no font slots).
4. ~~Pen/advance of GAME.BIN's own engine (`0x8c3202b0`)~~ located in stage 11 (section 6); what remains unknown is only the on-screen result of `--cell-prop` (the FPU display loop is not simulated).
5. Callers that centre/right-align by character count (UNKNOWN count; start from `fieldreads.txt`).
6. Whether B/C overlays are ever loaded (INFERRED dead).
7. Dynamic checks: break on `0x8c2de49c`/`0x8c2de4a8` (or the copy resident at `0x8cb64d?`: HELP head 0x8cb64bfc + 0x1fc = 0x8cb64df8) while showing a dialogue; confirm `r10` steps 12 and `r2 == 12`.
