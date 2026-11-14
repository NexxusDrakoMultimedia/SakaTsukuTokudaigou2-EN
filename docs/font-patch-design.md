# Proportional half-width font patch: where code and table live, exact bytes, build plan

> **Status note (docs, 2026-11-11).** **Superseded as a design document.** The patch described here is implemented in `tools/fontpatch.py` and `tools/patchengine.py` (docs/patch-engine.md) and is built by `--proportional-font on`. Current addresses, status and the live-test procedure are in docs/proportional-font.md; this file is kept for the derivation and the simulator proofs (section 7).

Author: agent `fontpatch` (task C). Status words: **PROVEN** = decoded/measured/executed here (address or script given),
**INFERRED** = follows from PROVEN facts but not run on the game, **UNKNOWN** = needs the emulator test of section 10.
**Nothing in this document was run on an emulator or on hardware** (the desktop was off limits); the only "execution" is the
SH-4 interpreter `tools/re/font/sh4sim.py` running the REAL layout-function bytes of the overlays (section 7).

Code and artefacts (all new, nothing else modified):

| file | purpose |
|---|---|
| `tools/re/font/fontpatch.py` | the patch itself: cave source, hook generators, site scanner, build API (`patch_overlay`, `patch_1st_read`, `embed_table`) |
| `tools/re/font/fontpatch_tests.py` | `selftest` / `liveness` / `manifest` commands (capstone decode check, simulator, xref and delay-slot checks) |
| `tools/re/font/sh4asm2.py` | small SH-4 assembler (own encoder written from the SH-4 manual; checked against capstone and Ghidra) |
| `tools/re/font/sh4sim.py` | SH-4 interpreter for the integer subset (+ FPU stack moves) |
| `tools/re/font/widths.py` | table (256 B) from the half-width glyph block of a FONT.BIN |
| `tools/re/font/test_inline.py` | option 1A check (decode all sites, execute 3) |
| `tools/re/font/shd.py`, `scan_sig.py`, `scan_sig2.py`, `scan_adv_store.py`, `mkpatched.py` | capstone disassembler wrapper, signature scans, patched-copy writer for Ghidra |
| `build/font/font_patch_manifest.json`, `font_patch_sites.tsv`, `font_patch_cave.txt` | machine-readable patches (address, old, new) for every site |
| `build/font/selftest_output.txt`, `liveness_output.txt`, `build/font_sanity.py`, `build/font_sig_scan.txt` | outputs of the checks quoted in section 7 |
| `build/font/ghidra_{MEETING,COMM,CSAVE3,cave}.txt` | Ghidra 12.2 disassembly of the PATCHED bytes (project `<GHIDRA_PROJECTS>\ghproj_fontpatch`) |

## 0. Decisions in one table

| question | decision | why |
|---|---|---|
| Where does new code live? | **104-byte cave in the `1ST_READ.BIN` tail at `0x8c299800`** (file offset `0x289800`; reserve `0x8c299800-0x8c2998ff`), called with `jsr` from a **16-byte in-place hook** in each overlay copy of the layout function | the tail is the bank agents' lowest-risk region (after crt0's BSS end, outside every slot, filler/zero identical in all dumps; docs/trans-bank.md s2.4), starting at the skeptic's `0x8c299800` (docs/capacity-design.md s9); no file grows, no `_end` word, no loader change. Fallback: gap1 `0x8c13bb80` (constants only) |
| Where does the 256-byte advance table live? | **next to the cave: `0x8c299900-0x8c2999ff`** (file offset `0x289900`), same file, same region | one file and one region carry all new bytes (fewest independent failure points, zero disc growth, in-place patch); the default table (all 12) reproduces the original game bit for bit. Option (2) of the task, the FONT.BIN tail at `0x8ce01f00`, works with the same code (only the literal changes) and is kept as an alternative: it costs +16,612 B of disc, a relocated FONT extent and a coupling with the bank's `font` region |
| What gets hooked? | **H1** half-width advance (all 105 overlay copies), **H2** wrap decision (optional but needed for any capacity gain; same 105) | without H2 only the glyph spacing shrinks, lines still wrap after 39 cells |
| Do overlays with their own copy need it? | **Yes, every one**: 105 files (98 variant A, 6 variant B, 1 variant C), list in Appendix A; 9 overlays + SECBND have no copy of the library; 4 of those draw text with their own code (UNKNOWN, section 6.2) | each overlay statically links its own `tsString` window library |
| First emulator test | **Option 1A**: the 16-byte hook reading the table directly (no cave, section 4.3) in ONE overlay (CLUBEDIT: Name & Mascot screen), table = all 12 first, then proportional | smallest possible change that can fail |

## 1. What the drawer does (PROVEN, MEETING.BIN base `0x8c2d0000`, Ghidra + capstone + executed)

`FUN_8c2de294` is the layout+draw function of the tsString window (entry `0x8c2de294`, pushes r8-r14, PR, FR15). Registers inside:
r14 = window object, r12 = current u16 code, r10 = pen x, r8 = pen y, r11 = "units" (half cells used on this line), r13 = 0,
r9 = 0x8000. It walks the code array from index 0 to the cursor (`+0x2c`) **every call** (index initialised at `0x8c2de2d4`), so the layout is
stateless: whatever advance rule is in force is applied from the line start each frame.

Window fields used (variant A offsets): `+0x3c` cells per line W, `+0x3e` advance A (24 for the text windows, see 1.2), `+0x3f` line height,
`+0x45` "last cell free" flag, `+0x4a` x0 (s16), `+0x4c` y0.

| address | instructions (verified by capstone, Ghidra and the interpreter) | meaning |
|---|---|---|
| `0x8c2de2e4-0x8c2de334` | control-code dispatch (`& 0x2000`, `== 0x2020`, `== 0x200a`) | 0x2020 (space) is replaced by r9 = 0x8000 at `0x8c2de394` before the advance; 0x200a = newline |
| `0x8c2de334-0x8c2de377` | wrap block: `r4 = (units+1)>>1; if r4 > W-1 -> wrap; elif r4 == W-1 && flag == 0 && !(code & 0x4000) -> wrap` | cell based; wrap = `pen = x0; y += lh; units = 0` |
| `0x8c2de490-0x8c2de49f` (+ stale delay slot `0x8c2de4a0`) | `mov #62,r0; mov.b @(r0,r14),r2; mov #0,r3; cmp/gt r2,r3; addc r3,r2; shar r2; add r2,r10; bra 0x8c2de4aa; add #1,r11` | half-width advance = `(A + (A<0)) >> 1`, units += 1 |
| `0x8c2de4a2-0x8c2de4a9` | `mov #62,r0; mov.b @(r0,r14),r3; add #2,r11; add r3,r10` | full-width advance = A, units += 2 |
| `0x8c2de4aa` | join: `mov.l @(4,r15),r3 ...` | next code |

1.1 **The advance is not a table or constant: it is `A>>1` computed per character (PROVEN).** The only reads of window `+0x3e` in
MEETING are these two (the other three `mov #62,r0` are constructor stores at `0x8c2dcf26`, `0x8c2dd084`, `0x8c2dea4a`).
Executing the original function in the interpreter with W=20, A=24, flag=1 gives exactly **39 half-width cells per line** (`build/font_sanity.py`;
docs/text-engine.md s4.4 had derived the same number from the decompilation).

1.2 `units` (r11) is read in exactly one place, the wrap block at `0x8c2de334` (all other mentions are init/reset/increment/push/pop: grep of
the decoded function). Hence once the wrap block is pixel based, r11 is dead.
Window advance values stored by constructors across the overlays (`scan_adv_store.py`, heuristic: `mov #imm` source of the store): 24 in the
large majority, **16 in about 45 stores** (DRSGRF, DRSGRFJ, DRSHRANK, DRSSRANK, BPMATCH, GAME ...), a few 10/20/32/48/1/5/28. So the patch must
not assume A = 24: the cave uses the table only when A == 24 and keeps the original `A>>1` otherwise.

1.3 **Three code variants** of the same function (found by the generalised signature scan `scan_sig2.py`, 105 files, nothing else under `extracted/`):

| variant | files | differences |
|---|---|---|
| **A** | 97 FLOW_PRG overlays + `ATFIRST/HELP.BIN` = 98 | the MEETING code: pen r10, units r11, advance byte `+0x3e`; wrap block contiguous (68 B) |
| **B** | `COMM, CON_REP, NF_CON, PASS_PL` (identical 10,929 B files), `J1_REP, PL_CON` (identical) = 6 | older compile: pen r11, units r10, **all window offsets 8 lower** (adv `+0x36`, W `+0x34`, flag `+0x3d`, x0 `+0x42`, lh `+0x37`); wrap decision split in two fragments around a literal pool |
| **C** | `CSAVE3.BIN` | B's register assignment (pen r11, units r10) with A's window offsets; same split wrap block |

For every site the 16 original bytes of H1 and the 68/36 original bytes of H2 are byte-identical to the variant template
(`fontpatch.wrap_regex`, `ADV_RE`): there are exactly **6 distinct (old,new) byte pairs** in the whole patch (section 4/5), valid for any load base that is a multiple of 4.

## 2. Options compared

### 2.1 Code: where can ~100 bytes of new code live?
| option | what | verdict |
|---|---|---|
| **1a. cave in the `1ST_READ.BIN` tail** (chosen) | `0x8c299800-0x8c299867` (104 B; `0x8c299800-0x8c2998ff` reserved). Region `[0x8c299400,0x8c2b0000)` = 93,184 B after crt0's BSS end (zero fill ends at `0x8c299400`, docs/trans-bank.md s2.2), file bytes zero up to `0x8c2a0000` then the 64-byte filler. Evidence re-checked here: `0x8c299800-0x8c299bff` is zero in ram_2400, live1, live3 and t1; the highest touched byte below it is `0x8c2992bf` (= 11 x 64 B of the Ninja matrix stack `0x8c299000-0x8c2993ff`, live3/t1), 0x540 bytes below the cave; no aligned word in `1ST_READ.BIN`, `FLOW_PRG/*.BIN` or `ATFIRST/*.BIN` points into `0x8c299800-0x8c2999ff` (words that point near it: `0x8c299000` matrix stack (1ST_READ, NEWS, TRAINING), `0x8c299400` crt0 pool, `0x8c29c28c` (INITCON) and the odd value `0x8c29e16f` in 34 overlays = data, not a pointer). | PROVEN statically and in 4 dumps; INFERRED: no store in a game state that was not dumped (the bank's canary test T6 covers it); a matrix-stack overflow would need 16 more 64-byte entries |
| 1b. cave in gap1 `0x8c13bb80` | the 120,096-byte zero hole `0x8c13bb00-0x8c158fff` between `.text` and the jump table: zero in file and dumps (re-checked: 0 non-zero bytes in `0x8c13bb80-0x8c13bc7f` in all 4 dumps), only references are section-table words, below crt0's zero-fill ranges; the bank rates it "low (a GBR-relative access cannot be excluded statically)". `fontpatch.ALT_CAVE_GAP1` | alternative if the tail is needed elsewhere; then the bank's `gap1` must start at `0x8c13bc80` (the first 0x80 bytes `0x8c13bb00` are the bank hook cave) |
| 1c. in-place only, no cave | the hook reads the table itself (section 4.3) | adv = 24 windows only, no fallback; used as the first test |
| 1d. cave appended to each overlay | needs `_end` handling: appending is unsafe for BSS overlays and `GAME.BIN`'s stub zeroes `[start,_end)` (docs/memory-map.md s6) | rejected: 105 different growth cases |
| 1e. cave in the `FONT.BIN` tail | code in a data file rebuilt by the font tooling | rejected |
| 1f. patch the drawer in place with the table lookup inline | the original half branch is 16 bytes: no room for the adv != 24 case | possible only as 1c |

### 2.2 Table: where do 256 bytes live?
| option | verdict |
|---|---|
| **2a. next to the cave: `0x8c299900`** (chosen) | same file and region as the cave (zero-checked reservation `0x8c299900-0x8c2999ff`), no new disc space, written by `fontpatch.patch_1st_read(k, table_bytes)` together with the cave; the default all-12 table is a no-op. The font build recomputes the table from the half-width glyphs (`widths.make_table`) and hands it to the stage that already patches `1ST_READ.BIN`. |
| 2b. last 256 bytes of the FONT.BIN window, `0x8ce01f00` (`fontpatch.ALT_TABLE_FONT`, `embed_table`) | `FONT.BIN` loads to `0x8cd5c000`, window end `0x8ce02000` (next fixed load SHTEX0.ZAR, literal `0x8c16034c`; docs/font.md s6); the loader reads `ceil(size/2048)` sectors, so a file of exactly 679,936 B = 332 sectors fills it. PROVEN: root `/FONT.BIN` is the loaded copy (docs/memory-map.md: 100 % chunk match; ATFIRST copy 96.8 %); `0x8ce01f00-0x8ce01fff` is zero in all four dumps; no aligned word in `1ST_READ.BIN`, `FLOW_PRG/*.BIN`, `ATFIRST/*.BIN` points into `0x8cdfc000-0x8ce01fff` (hits only in `GAME/*` and `TRAINING/*` data files at random-looking values). Advantage: the metrics live in the file whose glyphs define them; the cave treats a zero table byte as 12, so an old FONT.BIN keeps the original behaviour. Costs: +16,612 B on disc (extent relocated by `discbuild`) and the bank's `font` region must end at `0x8ce01f00`; the bank rates the FONT tail "low-medium" (font may grow). |
| 2c. table per overlay | 105 copies, rejected |

Both placements use the same cave code; the table address is one 32-bit literal at the end of the cave. Fail-safe in either case: a table byte of 0 means "use 12". Digits must stay 12 px
and the space should stay 12 px wherever numbers are right-aligned with space padding (see 8).

### 2.3 Do the overlays need the same patch? (list: Appendix A)
Yes. Every overlay links its own copy (`malloc error.tsString.init` in 104 of 114). The layout function is **byte-identical** (H1: all 98 A-sites identical,
H2: all identical) so one signature-based patcher covers them: 105 files, 105 H1 sites, 105 H2 sites. Both copies of HELP (`FLOW_PRG/HELP.BIN`, loaded at `0x8cb60000` in
the dumps, 100 % match; and `ATFIRST/HELP.BIN`, not loaded) are patched. Files that the loader sees are the FLOW_PRG copies (docs/memory-map.md s2).

## 3. The cave (PROVEN: assembled, decoded by capstone and Ghidra, executed)

104 bytes at `0x8c299800` (file `0x289800`). Hex: `01a03ee036e0ec0218e33032078b15d14c601c000820008b0ce00b00090000e327333e3221420b00236001a000e1f8e13ce01c30ec020270ec03ff7237020770ec001a020820058b40e0184059200820008b38324ae01c30ed000834273429000b0009000099298c`
(the last 4 bytes are the literal `0x8c299900` = TABLE; `fontpatch.assemble_cave()` regenerates it).

```
; H1 advance.  in: r4 = code (low byte = character), r14 = window.  out: r0 = pixels.  clobbers r0-r3.
8c299800  01a0      adv_A:  bra   adv_c            ; variants A, C
8c299802  3ee0              mov   #62,r0           ; delay slot: offset of the advance byte
8c299804  36e0      adv_B:  mov   #54,r0           ; variant B (+0x36)
8c299806  ec02      adv_c:  mov.b @(r0,r14),r2     ; r2 = window advance A
8c299808  18e3              mov   #24,r3
8c29980a  3032              cmp/eq r3,r2
8c29980c  078b              bf    adv_gen          ; A != 24: original behaviour
8c29980e  15d1              mov.l @(0x8c299864),r1 ; r1 = TABLE  (literal 86 bytes ahead, limit 1020)
8c299810  4c60              extu.b r4,r0
8c299812  1c00              mov.b @(r0,r1),r0      ; r0 = table[char]   (values 1..24, signed byte is fine)
8c299814  0820              tst   r0,r0
8c299816  008b              bf    adv_ret
8c299818  0ce0              mov   #12,r0           ; table byte 0 = "no entry"
8c29981a  0b00      adv_ret: rts
8c29981c  0900              nop
8c29981e  00e3      adv_gen: mov  #0,r3            ; original (A + (A<0)) >> 1
8c299820  2733              cmp/gt r2,r3
8c299822  3e32              addc  r3,r2
8c299824  2142              shar  r2
8c299826  0b00              rts
8c299828  2360              mov   r2,r0            ; delay slot
; H2 wrap.  in: r4 = pen x, r5 = code, r14 = window.  out: r0 = 1 -> wrap, 0 -> no.  clobbers r0-r3 and MACL.
8c29982a  01a0      wrap_A: bra   wrap_c
8c29982c  00e1              mov   #0,r1            ; delay slot: offset delta (A, C)
8c29982e  f8e1      wrap_B: mov   #-8,r1           ; variant B: every window offset is 8 lower
8c299830  3ce0      wrap_c: mov   #60,r0
8c299832  1c30              add   r1,r0
8c299834  ec02              mov.b @(r0,r14),r2     ; r2 = W
8c299836  0270              add   #2,r0
8c299838  ec03              mov.b @(r0,r14),r3     ; r3 = A
8c29983a  ff72              add   #-1,r2
8c29983c  3702              mul.l r3,r2            ; MACL = A*(W-1)
8c29983e  0770              add   #7,r0
8c299840  ec00              mov.b @(r0,r14),r0     ; r0 = flag (+0x45)
8c299842  1a02              sts   macl,r2          ; r2 = L
8c299844  0820              tst   r0,r0
8c299846  058b              bf    wrap_l           ; flag != 0: L unchanged
8c299848  40e0              mov   #64,r0
8c29984a  1840              shll8 r0               ; 0x4000
8c29984c  5920              and   r5,r0
8c29984e  0820              tst   r0,r0
8c299850  008b              bf    wrap_l           ; hang character: L unchanged
8c299852  3832              sub   r3,r2            ; else one cell less
8c299854  4ae0      wrap_l: mov   #74,r0
8c299856  1c30              add   r1,r0
8c299858  ed00              mov.w @(r0,r14),r0     ; r0 = x0
8c29985a  0834              sub   r0,r4            ; r4 = pen - x0 = width used on this line
8c29985c  2734              cmp/gt r2,r4
8c29985e  2900              movt  r0               ; r0 = (used > L)
8c299860  0b00              rts
8c299862  0900              nop
8c299864  0099298c  tblp:   .long 0x8c299900
```
Calling convention: `jsr @r3` from the hook (PR is free: the layout function saved it at entry `sts.l pr,@-r15` and already calls other functions); the cave touches only r0-r3,
r4 (an argument the hook just loaded), r5 (argument), MACL; it never touches r6-r15, T is irrelevant at the return points (the next instruction in the function always loads/tests afresh).

Semantics of H2 (new rule, pixel based, start-based like the original): wrap iff `(pen - x0) > L`, `L = A*(W-1)` when the flag byte `+0x45` is non-zero **or** the code has the 0x4000 hang bit,
else `L = A*(W-2)`. For the original fixed advance (every char 12 or 24 px, A = 24) this is **identical** to the original cell rule: original wraps iff `units >= 2W-1` (flag 1), i.e. `pen-x0 >= 12(2W-1) <=> pen-x0 > 24(W-1)`;
for flag 0 and no hang bit `units >= 2W-3 <=> pen-x0 > 24(W-2)` (proven by execution for A = 24, 20, 16, section 7). A hanging full-width char or a char starting at `used <= L` is always drawn,
so the widest char (12 px) ends at most at `x0 + 24W - 12`: the last half cell stays free exactly as in the original.

## 4. Hook H1: half-width advance (all 105 sites)

### 4.1 Exact bytes (A, B, C) - `old` is what is in the file today, `new` replaces it, same length, nothing else changes
Sites are at `site = load base + file offset` listed in Appendix A (always 4-byte aligned, PROVEN for all 105; so the `mov.l` literal sits at `site+12`, displacement 2).

| variant | old (16 B at `site`) | new (16 B at `site`) |
|---|---|---|
| A | `3ee0ec0200e327333e3221422c3a04a0` | `02d30b43c3640c3a07a0017b0098298c` |
| B | `36e0ec0200e327333e3221422c3b04a0` | `02d30b43c3640c3b07a0017a0498298c` |
| C | `3ee0ec0200e327333e3221422c3b04a0` | `02d30b43c3640c3b07a0017a0098298c` |

The 2 bytes after the region (`017b` / `017a`, the old `add #1,rU` delay slot at `site+16`) stay as they are: they are now unreachable. The next original instruction at `site+18` (the full-width branch,
target of the old `bt`) is untouched.

Decoded (MEETING, variant A; identical to Ghidra's listing `build/font/ghidra_MEETING.txt`):
```
8c2de490  02d3        mov.l @(0x8c2de49c),r3   ; literal at +12, disp 2, EA = (0x8c2de490 & ~3) + 4 + 2*4  (4-aligned)
8c2de492  0b43        jsr   @r3                ; -> adv_A
8c2de494  c364        mov   r12,r4             ; delay slot (does not write r3)
8c2de496  0c3a        add   r0,r10             ; pen += result      (B/C: add r0,r11)
8c2de498  07a0        bra   0x8c2de4aa         ; join
8c2de49a  017b        add   #1,r11             ; delay slot, keeps the legacy units count   (B/C: add #1,r10)
8c2de49c  0098298c    .long 0x8c299800         ; (B: 0x8c299804 = adv_B)
```
### 4.2 Why it is safe at this point (PROVEN)
* **Registers**: free at the hook: r0-r7 (caller-saved; everything after the join reloads r2/r3 from the stack/window), T. Live: r8-r15. Verified structurally (the draw `jsr` is
  *before* the hook; after the join the first uses of r0-r4 are definitions) and **dynamically**: `fontpatch.py liveness` runs patched code with r0-r5 and T randomised at every hook exit and
  compares positions and all external call arguments (r4-r7, r8, r10 of every `jsr`) with the original: 180 runs, 0 differences (negative control: randomising r0-r12 does change the result).
* **Delay slots**: every delayed branch of the cave and of all 210 hooks (425 branches) is followed by a legal slot (no branch, no PC-relative load, jump register not written): `static_slot_check`.
* **PC-relative literals**: `mov.l @(disp,PC)` requires 4-aligned literal within 1020 bytes forward: H1 literal at +12 (disp 2), H2 literal at +0x1c (A, disp 6) / +0x1a (B, C, disp 3 from the `mov.l` at +2), cave literal 86 B ahead; the assembler raises on any violation and the xref scan found **no branch or pc-relative reference into the interior of any replaced region** (`xref_check`, 105 sites).
* No `_end`/BSS/size change: all hooks are in place, so none of the append problems of docs/memory-map.md s6 applies (including GAME.BIN and ESTABLIS).

### 4.3 Option 1A: minimal first test (no cave)
16 B at the same site, reading the table directly (no adv != 24 handling, no fallback):

| variant | new bytes (16 B at `site`; old bytes as in 4.1) |
|---|---|
| A | `02d3cc603c022c3a07a0017b0099298c` |
| B, C | `02d3cc603c022c3b07a0017a0099298c` (add r2,r11 / add #1,r10) |

```
mov.l @(lit),r3 ; extu.b r12,r0 ; mov.b @(r0,r3),r2 ; add r2,r10 ; bra join ; add #1,r11 ; .long 0x8c299900
```
Executed (`tools/re/font/test_inline.py`) on MEETING, COMM and CSAVE3 against the model with a proportional table (A = 24 windows) and with an all-12 table (== original behaviour, bit-exact): both pass; all 105 sites decode with capstone. `fontpatch.hook_adv_inline()` generates it, `patch_overlay(..., hooks=('adv_inline',))` applies it.

## 5. Hook H2: wrap decision (optional, all 105 sites)

H2 replaces the cell-based wrap block by a call to `wrap_A`/`wrap_B`. Variant A: the whole contiguous 68-byte block `0x8c2de334-0x8c2de377` (the code after it, `0x8c2de378`, is the draw code).
Variants B/C: only the first 36-byte fragment (`0x8c2e09a6-0x8c2e09c9` in COMM, `0x8c4dd362-0x8c4dd385` in CSAVE3); the second fragment (flag-0 logic, reached only by the `bf` inside the first) becomes unreachable and stays as it is.

| variant | old | new |
|---|---|---|
| A (68 B at `site-0x15c`) | `b3643ce000e3ec0201744733ff723e3421442734068b3fe0ec024ae0ed0a2c3810a0d36b20340d8b45e0ec022822098b6f92cd632823058b3fe0d36bec000c384ae0ed0a` | `c36506d30b43a36408201b893fe0ec022c384ae0ed0a15a0d36b09002a98298c` + 18 x `0900` (nop) |
| B (36 B at `site-0xde`) | `a36434e000e3ec0201744733ff723e3421442734178b37e0ec0242e0ed0b2c3821a0d36a` | `c36505d30b43b36408202c8937e0ec022c3842e0ed0b26a0d36a2e98298c090009000900` |
| C (36 B at `site-0xde`) | `a3643ce000e3ec0201744733ff723e3421442734178b3fe0ec024ae0ed0b2c3821a0d36a` | `c36505d30b43b36408202c893fe0ec022c384ae0ed0b26a0d36a2a98298c090009000900` |

Decoded, MEETING (Ghidra `ghidra_MEETING.txt`), variant A:
```
8c2de334  c365   mov r12,r5            ; code
8c2de336  06d3   mov.l @(0x8c2de350),r3
8c2de338  0b43   jsr @r3               ; -> wrap_A
8c2de33a  a364   mov r10,r4            ; delay slot: pen x         (B/C: mov r11,r4)
8c2de33c  0820   tst r0,r0
8c2de33e  1b89   bt 0x8c2de378         ; no wrap -> draw code      (B/C: 0x8c2e0a0c / 0x8c4dd3c8 = old join)
8c2de340  3fe0   mov #63,r0            ; wrap: y += line height
8c2de342  ec02   mov.b @(r0,r14),r2
8c2de344  2c38   add r2,r8
8c2de346  4ae0   mov #74,r0            ; pen = x0
8c2de348  ed0a   mov.w @(r0,r14),r10   ; (B/C: ,r11 and offsets 55/66 for B)
8c2de34a  15a0   bra 0x8c2de378
8c2de34c  d36b   mov r13,r11           ; units = 0 (dead afterwards, kept for fidelity)
8c2de34e  0900   nop
8c2de350  2a98298c .long 0x8c29982a    ; wrap_A   (B: 0x8c29982e = wrap_B; C: wrap_A)
8c2de354  ...    nop x 18 up to 0x8c2de377
```
Register/delay/literal checks as in 4.2 (r1-r5 and MACL clobbered; r1-r4 are redefined before use at the old join in every path, r5 is redefined by `mov #0,r5` before the draw call: dynamic test above).
B/C offsets (W 52, adv 54, flag 61, x0 66, lh 55 for B) are inside `wrap_B`; the hook itself carries only lh and x0.

## 6. Inventory

### 6.1 Overlays that need it (all 105 files; full table Appendix A, machine-readable `build/font/font_patch_sites.tsv`)
* Variant A (98): ABROAD AUTOSAVE BACKUP BPMATCH CAP_SLCT CE_VS CHALDANI CHALMODE CLUBEDIT CSAVE CSAVE4 DATAROOM DMCLBEDT DRAFT DRSBEST DRSDENDO DRSGP DRSGRF DRSGRFJ DRSHRANK DRSISEKI DRSJAPAN DRSKIYA DRSLIST DRSOLIST DRSRANK DRSSRANK ENDING ENDOPT ESTABLIS EVENT EXFLAG EXTRADE FIRE FLOW1..FLOW11 FREELOAD GAME GAMEOVER GETREP GMSHOW00-02 G_INCOME G_RESULT HELP (both copies) HEREWEGO HOMETOWN INITCON INVEST JSCEVENT LOAD LOCAL MEETING MON_INST NENREP NEWCON NEWMONTH NEWS NEWS_ED NEWS_OP NEWUNIF NEW_YEAR N_ENTRY OPTION PLNUMSET PL_EDIT PWK_EDIT RECON SCDRF SCHE0 SCHE1 SEARCH SELNAT SONGSAVE SPF_READ SPONSOR SPONSOR2 SPT_CLUB SS_EDIT SUPPORT S_SELECT TOWN TOWNDATA TRAINING TV_EVENT VTRLOAD YOUTH (`FLOW_PRG/*.BIN`, plus `ATFIRST/HELP.BIN`).
* Variant B (6): COMM CON_REP NF_CON PASS_PL (site `0x8c2e0a84`, wrap `0x8c2e09a6`), J1_REP PL_CON. Variant C (1): CSAVE3 (`0x8c4dd440` / `0x8c4dd362`). B/C are tiny network/password stubs; if they carry no English text they can be skipped (no harm either way).

### 6.2 Not covered (no signature) - UNKNOWN text path
`BPMWEEK, FACEMDUL, LOADBAR, LOGO, MOVIE, MOVIE_BG, OFFICE, TITLE, WEEKLY` (+ `SECBND`, not an overlay) contain neither the tsString library nor the advance code.
Counting the jump-table offset halfwords `0x3ac/0x3b0/0x3b4/0x3d0` (font slots of `1ST_READ`, docs/font.md s2): **OFFICE, WEEKLY, BPMWEEK and FACEMDUL call the font functions directly**
(OFFICE 12/8/5/3, WEEKLY 8/0/1/1, BPMWEEK 5/0/1/0, FACEMDUL 2/2/6/2), i.e. have their own text drawer whose advance logic is not analysed here. LOGO/MOVIE/MOVIE_BG/LOADBAR/TITLE: 0-4 font references each (TITLE 3 + 4 of the `0x3b4`/`0x3d8` slots).
If their text is translated and must be proportional, each needs its own hook; with the fixed 12 px font nothing is needed. `1ST_READ.BIN` itself has no copy (0 hits).
Other readers of a `+0x3e` byte exist in DRSHRANK (`0xadc8`), EVENT (`0x2e4e8`), TV_EVENT (`0x36c`, address `0x8c2d036c`) and WEEKLY (`0x2ba48`, not inspected). The three inspected ones only test it (`mov.b @(r0,r14),r3; tst r3,r3; bf`, EVENT and DRSHRANK) or copy it (`+0x3e -> +0x20` of the same object, TV_EVENT); none uses it as a pen advance, and since the patch never changes the field they are unaffected whatever object they belong to.

## 7. Verification performed (all reproducible: `python -I -X utf8 tools/re/font/fontpatch.py selftest|liveness|manifest`)

| check | result |
|---|---|
| assembler vs capstone 5.0.7 (SH-4): every emitted word of the cave and of all 105 x 2 hooks decodes to the instruction text the assembler meant | 0 mismatches |
| Ghidra 12.2 (`SuperH4:LE:32`, independent decoder) disassembly of the patched MEETING, COMM, CSAVE3 and 1ST_READ images (`build/font/ghidra_*.txt`, project `ghproj_fontpatch`) | all 50 cave instructions and all hook instructions identical to the assembler's meaning (only difference: Ghidra prints immediates in hex), delay slots (`_`) where intended, branch targets and literal addresses as in sections 3-5 |
| signature of H1/H2 old bytes at all sites; no overlap; patched image differs from the original only inside the declared regions; file size unchanged | 105/105 |
| base-agnostic build API (`patch_overlay`, base 0) == per-site manifest bytes | 105/105 (so the build needs no base table) |
| **execution** of the real function bytes in `sh4sim.py` (stubs for external calls, FPU as no-op): original vs Python model of the cell rule; patched with all-12 and all-0 tables vs the ORIGINAL (bit-exact pen/y after every code); patched with a proportional table vs the new rule; W/A/flag in {20/24/1, 20/24/0, 7/24/1, 13/24/0, 20/16/1, 10/20/0}; 4 test strings incl. full-width, hang flags, spaces, colours, newlines | full matrix on MEETING (A), COMM (B), CSAVE3 (C), reduced matrix on the other 102 sites: **0 failures** |
| negative controls | a corrupted cave instruction fails the model; clobbering r0-r12 at the exits fails (r0-r5 does not) |
| the proportional rule gains capacity | with a sample table (3..12 px) one W=20 line holds 58 chars instead of 39 (sample only; real gain depends on the glyph art) |
| liveness | 180 randomised-register runs: identical positions and external call arguments |
| xrefs | no branch / pc-relative reference into a replaced interior (`xref_check`) |

Not verified: the FPU part of the function (position -> float, draw call arguments) is modelled as a no-op, the draw back end was not executed; no emulator run.

## 8. Table content and font-side requirements (PROVEN data, INFERRED consequences)

* `table[b]` is indexed by the **low byte of the u16 code**, i.e. the character byte `b` (0x21-0x7f, 0xA0-0xDF) because the string compiler produces `0x8000 | 0x4000? | b`.
  The space cell (`0x2020`) reaches the cave as `0x8000`, so **`table[0]` must be the SPACE width**, `table[0x20]` is only a spare copy. All other indices (0x01-0x1f, 0x80-0x9f) are unused.
* `widths.py` computes `advance = right-most ink column + 1 + gap`; measured on the ORIGINAL half-width glyphs (gap 1): 74 of the 94 ASCII glyphs are 12 px, mean 11.38 px (docs/font.md s3: capitals fill the cell) - **the original art gains almost nothing**;
  the font must be redrawn with 1 px of side bearing and **left-aligned ink** (the advance is added after drawing at the pen position).
* UNKNOWN: whether the 12-px glyph quad is drawn with transparent background. If the quad has opaque paper, a narrower advance makes the next quad cover the right columns of the previous glyph.
  (The glyph texel conversion `FUN_8c15eca4` puts the nibble into all four ARGB4444 channels; whether 15 is transparent was not traced.) Test T-3 settles it; draw glyphs so that their paper columns beyond the advance are the same colour as the background anyway.
* Keep digits 0x30-0x39 and the space at 12 px if numbers are right-aligned with space padding (`%3d`-style fields assume 12 px per cell); proportional digits would misalign columns.
* `+0x3e == 16` windows keep the original 8-px half advance and the original 2W-1 wrap (cave fallback): their English text stays fixed-pitch. A scaled variant `w*A/24` is possible later (one multiply, cave has 150 B left) but is not needed for the first test.

## 9. Build integration plan (`tools/build_patch.py`, `tools/discbuild.py`)

Facts (PROVEN, read from the code): `build_patch.build_patches` collects `res.patches {iso path: bytes}` of CHANGED files only; `_put` raises if a file is produced by two stages;
`apply_font` rebuilds BOTH `FONT.BIN` copies from `translation/font/edit_*.png` and checks `len(new) <= FONT_LIMIT (679936)`; `discbuild.plan_patches` writes a patched file in place when it fits its extent
(strategy `gap`), so same-size files need no relocation. `1ST_READ.BIN` is the last file on the disc and a plain file (no container); `FONT.BIN` is a bare container (`tools/font.py`).

New code (all of it exists in `tools/re/font/fontpatch.py` with a pure-bytes API; move it to `tools/` when integrating):
1. **Flag** `--prop-font` (default off: the build stays byte-identical to today). It requires the glyph sheets (`translation/font/`): a proportional table needs redrawn glyphs (section 8).
2. **FONT.BIN stays as `apply_font` builds it** (primary placement 2a: no padding, no growth). `apply_font` additionally returns the final root-font half-width block; the stage below turns it into the table with
   `widths.make_table(F.Font(new_root_font), gap=1, space=6)` (digits and space forced to 12 by default; optional per-character overrides from `translation/font/advance.json` {byte: px}, each value 1..24).
   *Alternative 2b*: `new = fontpatch.embed_table(new, table)` pads the root font to exactly 679,936 B with the table in its last 256 B and the build passes `table=fontpatch.ALT_TABLE_FONT` to `assemble_cave`; the ATFIRST copy is left alone.
3. **New stage `apply_font_code(res, table)`** after `apply_font` and before `apply_members` / `apply_files` (a whole-file replacement of one of these files in `translation/files` then wins only if applied before: document the order):
   * `1ST_READ.BIN`: `cur = res.patches.get('/1ST_READ.BIN') or read_extracted('1ST_READ.BIN')`; `new = fontpatch.patch_1st_read(cur, table_bytes=table)`: it refuses unless `0x8c299800-0x8c2998ff` is all zero, writes the cave at file offset `0x289800` and the table at `0x289900`
     (same length, in place). It composes with the ptrblob text stage (strings only) and with the bank hook patch (`0x8c13bb00` cave + literal `0x8c160360`); the bank's tail region must start at `0x8c299a00` instead of `0x8c299800` (the skeptic's start plus this 512-byte reservation).
     Register the result with a helper `_replace(res, iso, new, old)` (the existing `_put` raises when the text stage already produced the file).
   * every `FLOW_PRG/*.BIN` and `ATFIRST/HELP.BIN`: `cur = res.patches.get(iso) or read_extracted(...)`; `new, sites = fontpatch.patch_overlay(cur, iso)`; no signature = unchanged (not an error). The scan is by signature on the CURRENT bytes,
     so it does not depend on what the text repacker did (it never moves code) nor on `--append-safe` growth; it is base-agnostic (all load bases are multiples of 4).
   * summary line `font code: 105 overlays patched (A=98 B=6 C=1), cave @0x8c299800, table @0x8c299900`; a hard error when the count differs from 105 (guards against a damaged image).
4. **Disc cost**: no file grows. `1ST_READ.BIN` and the 105 overlays (34.6 MB = 16,887 sectors) are rewritten in place: ECC/EDC work only, no extent change. (Alternative 2b: FONT.BIN +16,612 B = 8 sectors, relocated by `plan_patches`.) Use `--only` while testing.
5. **Bank coordination** (docs/trans-bank.md, `tools/re/capacity/bank/bankbuild.py`): the `tail` region starts at **`0x8c299a00`** (cave+table reserve `0x8c299800-0x8c2999ff`; that also satisfies the skeptic's "start at 0x8c299800 or later" and its "keep the last 0x40 B before 0x8c2b0000 unused"); `gap1`, `gap2`, `gap3` and the `font` region are untouched.
   If the bank needs the whole tail, switch to the alternative: `CAVE = ALT_CAVE_GAP1` (`0x8c13bb80`, bank `gap1` starts at `0x8c13bc80`) and, if wanted, `TABLE = ALT_TABLE_FONT`.
6. **Tests**: `fontpatch.py selftest` (3 min) as a slow test; `tools/test_pipeline.py` gets one fast case: patch the extracted overlays, assert 105 sites, only the declared bytes differ, `patch_1st_read` composes with the bank hook patch.
7. **Staged rollout** (so that a failure is attributable): (a) `hook_adv_inline` (option 1A, 16 B) in CLUBEDIT only + table in the tail (all 12: must look identical; then proportional); (b) cave + H1 in all overlays; (c) + H2.

## 10. Risks, UNKNOWNs and the emulator tests that settle them (do NOT run while the user is using the machine)

| # | item | status | test / pass criterion |
|---|---|---|---|
| T-1 | the cave and table in the 1ST_READ tail (`0x8c299800-0x8c2999ff`) are never written by the game in states not dumped (match, season, training, save/load, browser, ending) | INFERRED (static + 4 dumps) | the bank's canary test T6 (`canary.py`) over `0x8c299800-0x8c2999ff` after every game mode; pass = 0 changed bytes |
| T-2 | boot: the BIOS accepts `1ST_READ.BIN` with the cave and table (same size, no checksum known) | INFERRED | boot to the title; dump RAM: `0x8c299800` = `01a03ee036e0...`, `0x8c299900` = table |
| T-3 | glyph quad background (overlap when advance < 12) | UNKNOWN | CLUBEDIT name screen / any dialogue with `iiiiWWWW`: no clipping of the right side of a glyph |
| T-4 | wrap: 20x3 dialogue window prints more than 39 narrow characters per line and wraps at `used > 24(W-1)`; with an all-12 table exactly 39 | INFERRED (executed in the interpreter) | MEETING/HELP dialogue |
| T-5 | the three non-text readers of `+0x3e` (DRSHRANK, EVENT, TV_EVENT) are unaffected (we do not change the field) | PROVEN by construction | none |
| T-6 | A = 16 windows: unchanged behaviour | PROVEN by construction (fallback path, bit-exact in the simulator) | BPMATCH/ranking screens look as before |
| T-7 | instruction cache: patched bytes are in files loaded by the BIOS/overlay loader before execution | INFERRED (same as every other text patch) | none expected |
| R-1 | OFFICE/WEEKLY/BPMWEEK/FACEMDUL own drawers | UNKNOWN | separate analysis if their text is proportional |
| R-2 | `mul.l` clobbers MACL; no other MACL use in the function (no `mul/mac` instruction in the decoded function) | PROVEN for MEETING, INFERRED for others (identical code) | none |

## Appendix A. Sites (H1 = half-width advance hook address, H2 = wrap hook address; base = load base from `tools/re/textengine/survey_overlays.tsv`)

| overlay file | var | load base | H1 address | H2 address |
|---|---|---|---|---|
| FLOW_PRG/ABROAD.BIN | A | 0x8c2d0000 | 0x8c2d5f84 | 0x8c2d5e28 |
| FLOW_PRG/AUTOSAVE.BIN | A | 0x8c8d0000 | 0x8c8dbe64 | 0x8c8dbd08 |
| FLOW_PRG/BACKUP.BIN | A | 0x8c4d0000 | 0x8c4d23cc | 0x8c4d2270 |
| FLOW_PRG/BPMATCH.BIN | A | 0x8c2d0000 | 0x8c2dc08c | 0x8c2dbf30 |
| FLOW_PRG/CAP_SLCT.BIN | A | 0x8c2d0000 | 0x8c2d4a74 | 0x8c2d4918 |
| FLOW_PRG/CE_VS.BIN | A | 0x8c2d0000 | 0x8c2d234c | 0x8c2d21f0 |
| FLOW_PRG/CHALDANI.BIN | A | 0x8c4d0000 | 0x8c4d21b0 | 0x8c4d2054 |
| FLOW_PRG/CHALMODE.BIN | A | 0x8c4d0000 | 0x8c4d3674 | 0x8c4d3518 |
| FLOW_PRG/CLUBEDIT.BIN | A | 0x8c2d0000 | 0x8c2d6124 | 0x8c2d5fc8 |
| FLOW_PRG/COMM.BIN | B | 0x8c2e0000 | 0x8c2e0a84 | 0x8c2e09a6 |
| FLOW_PRG/CON_REP.BIN | B | 0x8c2e0000 | 0x8c2e0a84 | 0x8c2e09a6 |
| FLOW_PRG/CSAVE.BIN | A | 0x8c4d0000 | 0x8c4dbe54 | 0x8c4dbcf8 |
| FLOW_PRG/CSAVE3.BIN | C | 0x8c4d0000 | 0x8c4dd440 | 0x8c4dd362 |
| FLOW_PRG/CSAVE4.BIN | A | 0x8c4d0000 | 0x8c4dd8c8 | 0x8c4dd76c |
| FLOW_PRG/DATAROOM.BIN | A | 0x8c2d0000 | 0x8c2da7c8 | 0x8c2da66c |
| FLOW_PRG/DMCLBEDT.BIN | A | 0x8c2d0000 | 0x8c2ddea8 | 0x8c2ddd4c |
| FLOW_PRG/DRAFT.BIN | A | 0x8c2d0000 | 0x8c2d9108 | 0x8c2d8fac |
| FLOW_PRG/DRSBEST.BIN | A | 0x8c4d0000 | 0x8c4d3e88 | 0x8c4d3d2c |
| FLOW_PRG/DRSDENDO.BIN | A | 0x8c4d0000 | 0x8c4d6cf4 | 0x8c4d6b98 |
| FLOW_PRG/DRSGP.BIN | A | 0x8c4d0000 | 0x8c4d5808 | 0x8c4d56ac |
| FLOW_PRG/DRSGRF.BIN | A | 0x8c4d0000 | 0x8c4d40cc | 0x8c4d3f70 |
| FLOW_PRG/DRSGRFJ.BIN | A | 0x8c4d0000 | 0x8c4d5de0 | 0x8c4d5c84 |
| FLOW_PRG/DRSHRANK.BIN | A | 0x8c4d0000 | 0x8c4d5d44 | 0x8c4d5be8 |
| FLOW_PRG/DRSISEKI.BIN | A | 0x8c4d0000 | 0x8c4d30e0 | 0x8c4d2f84 |
| FLOW_PRG/DRSJAPAN.BIN | A | 0x8c4d0000 | 0x8c4d2570 | 0x8c4d2414 |
| FLOW_PRG/DRSKIYA.BIN | A | 0x8c4d0000 | 0x8c4d27a0 | 0x8c4d2644 |
| FLOW_PRG/DRSLIST.BIN | A | 0x8c4d0000 | 0x8c4d8db8 | 0x8c4d8c5c |
| FLOW_PRG/DRSOLIST.BIN | A | 0x8c4d0000 | 0x8c4d7044 | 0x8c4d6ee8 |
| FLOW_PRG/DRSRANK.BIN | A | 0x8c4d0000 | 0x8c4d64d8 | 0x8c4d637c |
| FLOW_PRG/DRSSRANK.BIN | A | 0x8c4d0000 | 0x8c4d6e64 | 0x8c4d6d08 |
| FLOW_PRG/ENDING.BIN | A | 0x8c2d0000 | 0x8c2e8fcc | 0x8c2e8e70 |
| FLOW_PRG/ENDOPT.BIN | A | 0x8c8d0000 | 0x8c8d5b78 | 0x8c8d5a1c |
| FLOW_PRG/ESTABLIS.BIN | A | 0x8c2d0000 | 0x8c2dfdd8 | 0x8c2dfc7c |
| FLOW_PRG/EVENT.BIN | A | 0x8c2d0000 | 0x8c2ea4f0 | 0x8c2ea394 |
| FLOW_PRG/EXFLAG.BIN | A | 0x8c4d0000 | 0x8c4dc4b8 | 0x8c4dc35c |
| FLOW_PRG/EXTRADE.BIN | A | 0x8c4d0000 | 0x8c4e387c | 0x8c4e3720 |
| FLOW_PRG/FIRE.BIN | A | 0x8c2d0000 | 0x8c2d4d18 | 0x8c2d4bbc |
| FLOW_PRG/FLOW1.BIN | A | 0x8c2d0000 | 0x8c2d0b78 | 0x8c2d0a1c |
| FLOW_PRG/FLOW10.BIN | A | 0x8cb60000 | 0x8cb60b78 | 0x8cb60a1c |
| FLOW_PRG/FLOW11.BIN | A | 0x8cba0000 | 0x8cba0b78 | 0x8cba0a1c |
| FLOW_PRG/FLOW2.BIN | A | 0x8c3d0000 | 0x8c3d0b78 | 0x8c3d0a1c |
| FLOW_PRG/FLOW3.BIN | A | 0x8c4d0000 | 0x8c4d0b78 | 0x8c4d0a1c |
| FLOW_PRG/FLOW4.BIN | A | 0x8c5d0000 | 0x8c5d0b78 | 0x8c5d0a1c |
| FLOW_PRG/FLOW5.BIN | A | 0x8c6d0000 | 0x8c6d0b78 | 0x8c6d0a1c |
| FLOW_PRG/FLOW6.BIN | A | 0x8c7d0000 | 0x8c7d0b78 | 0x8c7d0a1c |
| FLOW_PRG/FLOW7.BIN | A | 0x8c8d0000 | 0x8c8d0b78 | 0x8c8d0a1c |
| FLOW_PRG/FLOW8.BIN | A | 0x8c9d0000 | 0x8c9d0b78 | 0x8c9d0a1c |
| FLOW_PRG/FLOW9.BIN | A | 0x8cad0000 | 0x8cad0b78 | 0x8cad0a1c |
| FLOW_PRG/FREELOAD.BIN | A | 0x8c8d0000 | 0x8c8dc378 | 0x8c8dc21c |
| FLOW_PRG/GAME.BIN | A | 0x8c2d0000 | 0x8c2ed088 | 0x8c2ecf2c |
| FLOW_PRG/GAMEOVER.BIN | A | 0x8c4d0000 | 0x8c4d282c | 0x8c4d26d0 |
| FLOW_PRG/GETREP.BIN | A | 0x8c2f0000 | 0x8c300ad0 | 0x8c300974 |
| FLOW_PRG/GMSHOW00.BIN | A | 0x8c2d0000 | 0x8c2d0ed0 | 0x8c2d0d74 |
| FLOW_PRG/GMSHOW01.BIN | A | 0x8c2d0000 | 0x8c2d1048 | 0x8c2d0eec |
| FLOW_PRG/GMSHOW02.BIN | A | 0x8c2d0000 | 0x8c2d0ed0 | 0x8c2d0d74 |
| FLOW_PRG/G_INCOME.BIN | A | 0x8c4d0000 | 0x8c4d3d7c | 0x8c4d3c20 |
| FLOW_PRG/G_RESULT.BIN | A | 0x8c6d0000 | 0x8c6d609c | 0x8c6d5f40 |
| FLOW_PRG/HELP.BIN | A | 0x8cb60000 | 0x8cb64df8 | 0x8cb64c9c |
| FLOW_PRG/HEREWEGO.BIN | A | 0x8c2d0000 | 0x8c2d8e40 | 0x8c2d8ce4 |
| FLOW_PRG/HOMETOWN.BIN | A | 0x8c2d0000 | 0x8c2dc5fc | 0x8c2dc4a0 |
| FLOW_PRG/INITCON.BIN | A | 0x8c6d0000 | 0x8c6d21a4 | 0x8c6d2048 |
| FLOW_PRG/INVEST.BIN | A | 0x8c4d0000 | 0x8c4d6f4c | 0x8c4d6df0 |
| FLOW_PRG/J1_REP.BIN | B | 0x8c4e0000 | 0x8c4e0a84 | 0x8c4e09a6 |
| FLOW_PRG/JSCEVENT.BIN | A | 0x8c2d0000 | 0x8c2d36b0 | 0x8c2d3554 |
| FLOW_PRG/LOAD.BIN | A | 0x8c4d0000 | 0x8c4e0a0c | 0x8c4e08b0 |
| FLOW_PRG/LOCAL.BIN | A | 0x8c2d0000 | 0x8c2d41a8 | 0x8c2d404c |
| FLOW_PRG/MEETING.BIN | A | 0x8c2d0000 | 0x8c2de490 | 0x8c2de334 |
| FLOW_PRG/MON_INST.BIN | A | 0x8c4d0000 | 0x8c4d3cb8 | 0x8c4d3b5c |
| FLOW_PRG/NENREP.BIN | A | 0x8c2e0000 | 0x8c2ea96c | 0x8c2ea810 |
| FLOW_PRG/NEWCON.BIN | A | 0x8c6d0000 | 0x8c6d8cd0 | 0x8c6d8b74 |
| FLOW_PRG/NEWMONTH.BIN | A | 0x8c2d0000 | 0x8c2d8a48 | 0x8c2d88ec |
| FLOW_PRG/NEWS.BIN | A | 0x8c2d0000 | 0x8c2f4350 | 0x8c2f41f4 |
| FLOW_PRG/NEWS_ED.BIN | A | 0x8c8d0000 | 0x8c8d5c44 | 0x8c8d5ae8 |
| FLOW_PRG/NEWS_OP.BIN | A | 0x8c8d0000 | 0x8c8d2c40 | 0x8c8d2ae4 |
| FLOW_PRG/NEWUNIF.BIN | A | 0x8c2d0000 | 0x8c2d3e28 | 0x8c2d3ccc |
| FLOW_PRG/NEW_YEAR.BIN | A | 0x8c4d0000 | 0x8c4d1b24 | 0x8c4d19c8 |
| FLOW_PRG/NF_CON.BIN | B | 0x8c2e0000 | 0x8c2e0a84 | 0x8c2e09a6 |
| FLOW_PRG/N_ENTRY.BIN | A | 0x8c8d0000 | 0x8c8d67f8 | 0x8c8d669c |
| FLOW_PRG/OPTION.BIN | A | 0x8c8d0000 | 0x8c8d37f8 | 0x8c8d369c |
| FLOW_PRG/PASS_PL.BIN | B | 0x8c2e0000 | 0x8c2e0a84 | 0x8c2e09a6 |
| FLOW_PRG/PLNUMSET.BIN | A | 0x8c2d0000 | 0x8c2d79ac | 0x8c2d7850 |
| FLOW_PRG/PL_CON.BIN | B | 0x8c4e0000 | 0x8c4e0a84 | 0x8c4e09a6 |
| FLOW_PRG/PL_EDIT.BIN | A | 0x8c4d0000 | 0x8c4dddc4 | 0x8c4ddc68 |
| FLOW_PRG/PWK_EDIT.BIN | A | 0x8c2d0000 | 0x8c2d487c | 0x8c2d4720 |
| FLOW_PRG/RECON.BIN | A | 0x8c4d0000 | 0x8c4d9880 | 0x8c4d9724 |
| FLOW_PRG/SCDRF.BIN | A | 0x8c2d0000 | 0x8c2d575c | 0x8c2d5600 |
| FLOW_PRG/SCHE0.BIN | A | 0x8c4d0000 | 0x8c4d9d78 | 0x8c4d9c1c |
| FLOW_PRG/SCHE1.BIN | A | 0x8c4d0000 | 0x8c4d9d70 | 0x8c4d9c14 |
| FLOW_PRG/SEARCH.BIN | A | 0x8c4d0000 | 0x8c4d6a0c | 0x8c4d68b0 |
| FLOW_PRG/SELNAT.BIN | A | 0x8c2d0000 | 0x8c2d94c8 | 0x8c2d936c |
| FLOW_PRG/SONGSAVE.BIN | A | 0x8c8d0000 | 0x8c8dc620 | 0x8c8dc4c4 |
| FLOW_PRG/SPF_READ.BIN | A | 0x8c2d0000 | 0x8c2d1744 | 0x8c2d15e8 |
| FLOW_PRG/SPONSOR.BIN | A | 0x8c6d0000 | 0x8c6db324 | 0x8c6db1c8 |
| FLOW_PRG/SPONSOR2.BIN | A | 0x8c4d0000 | 0x8c4de970 | 0x8c4de814 |
| FLOW_PRG/SPT_CLUB.BIN | A | 0x8c2d0000 | 0x8c2d3808 | 0x8c2d36ac |
| FLOW_PRG/SS_EDIT.BIN | A | 0x8c4d0000 | 0x8c4d9220 | 0x8c4d90c4 |
| FLOW_PRG/SUPPORT.BIN | A | 0x8c2d0000 | 0x8c2d74f4 | 0x8c2d7398 |
| FLOW_PRG/S_SELECT.BIN | A | 0x8c2d0000 | 0x8c2d5614 | 0x8c2d54b8 |
| FLOW_PRG/TOWN.BIN | A | 0x8c4d0000 | 0x8c4d6d48 | 0x8c4d6bec |
| FLOW_PRG/TOWNDATA.BIN | A | 0x8c4d0000 | 0x8c4d7afc | 0x8c4d79a0 |
| FLOW_PRG/TRAINING.BIN | A | 0x8c2d0000 | 0x8c2e77dc | 0x8c2e7680 |
| FLOW_PRG/TV_EVENT.BIN | A | 0x8c2d0000 | 0x8c2d42d0 | 0x8c2d4174 |
| FLOW_PRG/VTRLOAD.BIN | A | 0x8c2d0000 | 0x8c2dc71c | 0x8c2dc5c0 |
| FLOW_PRG/YOUTH.BIN | A | 0x8c2d0000 | 0x8c2dc65c | 0x8c2dc500 |
| ATFIRST/HELP.BIN | A | 0x8cb60000 | 0x8cb64df8 | 0x8cb64c9c |


## Appendix B. Reproduce

```
python -I -X utf8 tools/re/font/fontpatch.py scan        # 105 sites, variants, alignment
python -I -X utf8 tools/re/font/fontpatch.py selftest    # decode + region + simulator matrix (~3 min)
python -I -X utf8 tools/re/font/fontpatch.py liveness    # register-clobber test
python -I -X utf8 tools/re/font/fontpatch.py manifest    # build/font/font_patch_manifest.json, _sites.tsv, _cave.txt
python -I -X utf8 tools/re/font/mkpatched.py             # build/font/patched/{MEETING,COMM,CSAVE3,1ST_READ}.BIN for Ghidra
python -I -X utf8 tools/re/font/widths.py                # advance table from the original half-width glyphs
```
