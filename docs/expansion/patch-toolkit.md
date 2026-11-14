# Expansion study: code-patch infrastructure and the cheapest big wins

Scope: read-only feasibility study (area `patch-toolkit`).  Question set: what mechanisms exist to patch SH-4 code safely in the 98
overlay copies plus `1ST_READ.BIN`; what minimum general mechanism to build now to widen fields and buffers; how it composes with the
proportional font and the money patch; how far window / bubble / font-cell limits (33 and 39 glyphs) can be raised by patching
parameters; a ranked list of candidate patches.

Status words: **PROVEN** = read from code/data or executed here (file, offset or script named), **INFERRED** = follows from proven
facts but not run in the game, **UNKNOWN** = needs an emulator or hardware observation.  Nothing here started Flycast or touched a
window; `extracted/` and the tracks were only read.  New read-only scripts (prefix `ptk_`): `tools/re/ptk_simcov.py`,
`ptk_tailmap.py`, `ptk_sizeclass.py`, `ptk_famscan.py`.  Existing documents relied on: `docs/font-hook-notes.md`,
`docs/font-patch-design.md`, `docs/proportional-font.md`, `docs/font-widths.md`, `docs/window-widths.md`, `docs/memory-map.md`,
`docs/trans-bank.md`, `docs/capacity-design.md`, `docs/number-formats.md`, `docs/layout-issues.md`, `docs/uncovered-text.md`.

## 0. Answers in one table

| Question | Answer | Status |
|---|---|---|
| Is there already a safe way to patch the same SH-4 function in all overlays? | Yes, three hand-written variants of one idea: find the function by exact or masked byte signature, replace a few instructions by a jump or call into a cave in `1ST_READ.BIN`, keep every file size. `fontpatch.py` (exact 16/36/68-byte templates, 105 sites), `moneypatch.py` (prologue + sha1 of masked bytes, 108 sites), `layoutpatch.py` (fixed offsets, 1 file). They share nothing: three site finders, two assemblers, three cave constants, no overlap registry. | PROVEN |
| Is one library function found reliably in every overlay? | Yes for the tsString library: window layout/draw, window constructor, text setter and format expander each match exactly 98 images with a 64-byte masked head (97 FLOW_PRG + `ATFIRST/HELP.BIN`); money function 108 images; string-to-codes function 98 images with a 24-byte head (the 64-byte head contains literal-pool words behind the first `bra`, so it matches only MEETING). | PROVEN (`tools/re/ptk_famscan.py`) |
| Is Unicorn usable as the test emulator? | No: it is not installed (only `capstone` 5.0.7, which has an SH-4 decoder), and upstream Unicorn has no SH-4 target. QEMU is not installed either. The in-repo interpreter `tools/sh4sim.py` is the only executor; it fully implements 37 of 119 mnemonics, 82 more only partly. | PROVEN (installed), INFERRED (Unicorn targets) |
| Minimum general mechanism to build now | One declarative patch engine: site families (masked signature + per-site def-use proof), edit kinds (IMM8, POOLWORD, HOOK12/CALL to a cave, RAW), a cave registry with zero checks and symbols, one assembler with capstone round trip, an overlap registry that applies all specs to the ORIGINAL bytes, differential tests (original vs patched in the interpreter), and an exporter that turns the same edit list into a Lua poke script for live tests. Section 4. | INFERRED (design) |
| Can the 33 / 39 limits be raised by patching window parameters? | The wrap width is one `mov #imm8` per window factory (69 stores of 17, 168 stores of 20, 1 byte each), so the limit itself is trivial to change; but the message window already ends at x=624 of 640 and the frame art is not generated from the window (rows are never read by the library), so W alone buys almost nothing. The real lever is pixels per character: proportional table (47 chars per 468 px line, built), condensed art (53), and the game's own small size class 2 (8x16 half-width glyph, in use by 12 overlays). Section 6. | PROVEN (stores, math), UNKNOWN (frame art, legibility) |
| Biggest cheap wins, ranked | (1) switch the proportional font on after one live test, (2) pixel-aware offline reflow of all strings with the same width table, (3) scale the cave advance by A/24 and use size class 2 windows for long prose, (4) condensed glyph art, (5) escape-token indirection for long names (breaks no struct), (6) the unified patch engine. Section 8. | INFERRED |

## 1. Inventory of what exists (PROVEN unless marked)

| Piece | File | What it does | Gap |
|---|---|---|---|
| Layout/draw hooks H1 (advance) and H2 (wrap) | `tools/fontpatch.py`, cave 104 B at 0x8c299800, table 256 B at 0x8c299900 | 98 A + 6 B + 1 C copies; templates `H1_OLD/H2_OLD` must match exactly or the build raises; default OFF, in-game UNPROVEN | table used only when window advance `win[0x3e] == 24`; windows with 16/32/48/10 keep fixed steps (risk 6 in `docs/proportional-font.md`) |
| Money formatter | `tools/moneypatch.py`, cave 428 B at 0x8c299a00 (512 reserved) | first 12 bytes of every money function become `mov.l @(1,pc),r0 ; jmp @r0 ; nop ; nop ; .long CAVE`; plus `%D` branch edit; default ON | own `Asm` subclass, own signature hashes |
| Hometown spacer | `tools/layoutpatch.py` | two halfwords (`cmp/eq #4` and `#6` to `#-1`) at fixed offsets 0x2ab4 and 0x2ade of HOMETOWN.BIN | fixed offsets, one file, no family concept |
| Assemblers | `tools/sh4asm.py` (90 lines, 10 forms), `tools/sh4asm2.py` (224 lines, integer subset), `moneypatch.Asm` (extra forms) | words cross-checked against capstone by `fontcheck.py` and `moneycheck.py` | three dialects; no FPU, no `rotl`, `swap`, `xtrct`, `not`, `div1` |
| Executor | `tools/sh4sim.py` (340 lines) | runs the real layout function with FPU as no-op and external calls stubbed; `fontcheck.py` stage 4 runs it on all 105 patched overlays (5760 runs) | opcode coverage below |
| Static checks | `tools/fontcheck.py`, `tools/moneycheck.py` | capstone decode of every patched word, branch/literal/delay-slot checks, xref check that nothing jumps into a replaced interior, nothing outside declared regions changed, size unchanged | written per patch, not reusable |
| Live poke | `tools/emu/fonttest.lua` generated by `fontpatch.lua_source()`; `tools/emu/live.lua` bridge | applies hooks to RAM of a running Flycast without rebuilding the disc | only for the font patch; Flycast dynarec invalidation on write UNKNOWN (`docs/proportional-font-review.md`) |
| Site surveys | `tools/re/font/hooksites.tsv`, `winwidth_overlays.tsv`, `fieldstores.py`, `cellstores.py` | per-overlay addresses of the layout function and of window-field stores | static text files, not wired to a patcher |
| Build integration | `tools/build_patch.py` `apply_prop_font`, `apply_layout_patches`, `apply_money_fmt` | each module exposes `make_patches(read, current)` and composes on the CURRENT bytes (`res.patches`), no file grows | order dependence: a new edit inside the layout function breaks `fontpatch`'s exact template (it fails loudly, which is the right failure) |

### 1.1 Opcode coverage of the interpreter (PROVEN, `tools/re/ptk_simcov.py`)

capstone sees 119 distinct SH-4 mnemonics in the 16-bit opcode space.  `sh4sim.py` fully executes 37; 82 have at least one unsupported encoding
(including `not`, `xor`, `swap.b/w`, `xtrct`, `div1`, `shad`, `shld`, `shlr2/8/16`, `rotl/rotr`, `dt`, `negc`, `subc`, `addv`, `bsr`, `braf`, `sts/lds/stc`
variants, `mac.l`, `dmuls.l`, `muls.w`, `mulu.w`, `pref`, `ocbwb`, and partly `mov.b/w/l` addressing modes).  Of the 385,235 halfwords of
the first 0x12bb00 bytes of `1ST_READ.BIN` that decode, 44.7 percent carry a mnemonic with some unsupported encoding, mostly `mov.l`/`mov.w`/`mov.b` modes
(124,626 + 15,501 + 7,232), `pref` 4,182, `bsr` 2,597, `lds.l`/`sts.l`.  The layout function of MEETING (248 halfwords, 29 mnemonics) is the only
code the existing tests actually run.  Consequence: hooks into the window constructor, the format expander or any 1ST_READ routine cannot be run end to end
until the interpreter is completed (about 80 opcode forms; every one is a few lines; FPU can stay a no-op for equivalence tests).

## 2. How the same function copy is found in every overlay (PROVEN)

The tsString window library is statically linked into each overlay, so every copy has the same instruction sequence and differs only in
(a) link-address-dependent displacement fields (pc-relative `mov.w/mov.l @(disp,pc)` = 9nxx/Dnxx, `bra/bsr` = Axxx/Bxxx, `bt/bf(/s)` = 89/8B/8D/8F xx) and
(b) the literal-pool words stored behind the code.  Method used by `tools/re/ptk_famscan.py`: take N bytes of the function in MEETING.BIN
(base 0x8c2d0000), zero those displacement fields, compare every 2-aligned offset of every image.

| function (MEETING address) | head | images matched |
|---|---|---|
| layout/draw `FUN_8c2de294` | 64 B masked | 98 (one copy each) |
| window constructor `FUN_8c2de988` | 64 B | 98 |
| text setter `FUN_8c2de1f4` | 64 B | 98 |
| format expander `FUN_8c2df128` | 64 B | 98 |
| money function (`moneypatch` prologue) | 64 B | 108 (102 A + 6 B per `moneypatch.py scan`) |
| string-to-codes `FUN_8c2ddeea` | 24 B | 98 (the 64 B head matches 1 image: the first `bra` jumps over literal words that differ per link) |
| same, 12 B head | 12 B | 105 images, 106 copies (NEWCON twice): too short, false positive |

Rules learnt: (1) compare only code up to the first branch that skips a literal pool, or hash the whole function with pool words excluded; (2) use at least
24 bytes; (3) a function can start on a 2-aligned address (`FUN_8c2ddeea` ends in `a`), so scan with step 2, not 4; (4) classify copies by the masked hash:
this gives variant A (98), B (6: COMM, CON_REP, NF_CON, PASS_PL, J1_REP, PL_CON), C (1: CSAVE3); B and C are linked against another 1ST_READ build and are INFERRED
dead (`docs/font-hook-notes.md` 4.1); (5) an in-place edit must keep every byte a branch or literal can reach: `fontcheck.py` stage 2 does the xref check.
`tools/re/font/hooksites.tsv` already lists every A site with `F`, `wrap_lo`, `adv_half`, `adv_full` and `check = core_ok` for all.

Why hooks go to ONE cave and not to per-overlay code: 1ST_READ is not relocated and sits at the same RAM address in every dump, so a hook needs only a constant
address in its own 4-byte literal; the cave reads everything it needs from the window object or from the registers (no per-overlay data).  Edits that do need per-overlay
data (a table inside an overlay) use the overlay's own pool word, patched by the same engine.

## 3. Where new code and data can live

| Region | Bytes free | Code safe? | Evidence |
|---|---|---|---|
| 1ST_READ tail 0x8c299c00..0x8c2a0000 (after font + money caves) | 25,600 zero | yes | `ptk_tailmap.py`: single zero run 0x8c299400..0x8c2a0000 = 27,648 B; font claims 0x8c299800..0x8c2999ff, money 0x8c299a00..0x8c299bff (cave 428 B); beyond crt0 BSS end 0x8c299400 (PROVEN, `docs/trans-bank.md` 2.2) |
| 1ST_READ 0x8c2a0000..0x8c2b0000 (64-byte repeating filler) | 65,536 | yes | identical to the file in all 4 dumps, below slot 0 (INFERRED unused; PROVEN identical) |
| `gap1` 0x8c13bb80..0x8c159000 | 119,936 | yes (below crt0 zero fill 0x8c16f800) | `docs/trans-bank.md` 2.4; a GBR-relative access cannot be excluded statically (low risk) |
| `gap2`, `gap3` | 13,402 + 16,637 | yes | same |
| holes at 0x8c16f800..0x8c299400 | 434,176 of the earlier 557,056 B | **NO** | inside crt0 zero-fill (`docs/capacity-design.md` row 41), erased at boot |

All code ever written so far needs under 1 KB.  Estimated need of everything proposed below: 3 to 6 KB.  Space is not a constraint for code; it is a constraint for DATA
banks (names, strings), which compete for the same tail and holes (the bank design in `docs/trans-bank.md` plans to use them).  **Conflict found:** `docs/capacity-design.md`
(open item) wants the bank to start at 0x8c299800 or later, while font and money already own 0x8c299800..0x8c299bff: the cave placement constants are hard-coded in
`fontpatch.PLACEMENTS`, `moneypatch.CAVE_ADDR` and the bank's `make_regions`.  A single registry fixes this (section 4.3).

## 4. The minimum general mechanism (INFERRED design; nothing of it is written)

Goal: widen fields, buffers, window parameters and write new routines without a new hand-made site finder and checker for each.  Target: one module `tools/patchkit.py`
(or `tools/patchkit/`) of about 600 lines plus the interpreter completion, replacing the three ad-hoc finders gradually (the old modules keep working and are
re-expressed as specs later; no flag-day).

### 4.1 Parts

1. **Family** = name + masked byte signature (as in section 2) + optional per-variant masked hash + required alignment + expected copy count (fails if the count differs,
   exactly like `expect={'A': 98}` today).  Output: `[(image, offset, variant)]`, and a TSV for review.  One implementation of the mask rule.
2. **Edit kinds**, each with its own safety proof obligations:
   * `IMM8`: change the immediate of `mov #imm,Rn` (1 byte).  Obligation: the register's def-use chain within the function (`mov #20,r4` in the window constructor feeds BOTH the
     cells store `mov.b r4,@(r0,r14)` with r0 = 0x3c AND the x origin `mov.w r4,@(r0,r14)` with r0 = 0x4a: MEETING 0x8c2dea3e-0x8c2dea5e, PROVEN by disassembly), so each site
     declares which uses it intends to change.  Range -128..127.
   * `POOLWORD`: change a 32-bit literal in the overlay's pool (sizes, strides >= 128, table pointers).  Obligation: every `mov.l @(disp,pc)` that reaches the word is listed
     (xref scan, same technique as `fontcheck` stage 2) and all of them are meant.
   * `HOOK12`/`CALL`: replace >= 12 contiguous bytes by `mov.l @(1,pc),r0 ; jmp @r0 ; nop ; nop ; .long CAVE` (entry replacement, moneypatch style) or by `jsr` + literal with the
     original instructions re-executed inside the cave (font H1/H2 style).  Obligations: site 4-aligned for the literal, delay slot legal, **PR saved** at a `CALL` site (the
     library functions all do `sts.l pr,@-r15` first; a leaf function would be corrupted), cave preserves r8-r14 and does not touch fr12-fr15 (`fontpatch` liveness test).
   * `RAW`: explicit old/new bytes with mask (layoutpatch style).
3. **Cave registry**: named regions (`tail_code`, `tail_data`, `gap1`, `font_tail`) with start, end, current zero check against the file being built, an allocator that hands out
   aligned addresses, a symbol table (`caves.json`) that hooks and caves resolve against, and a refusal when any byte of a reserved range is not zero.  The font and money patches
   register their current addresses first, so nothing moves.
4. **Overlap registry** (the composition rule): every spec is applied to the ORIGINAL bytes of the file and yields an edit list `(file, start, end, owner, new bytes)`; the engine
   refuses overlapping ranges from different owners and then writes all lists in one pass.  This removes the order dependence of `current` composition; text repacking (data) is
   disjoint from code and still runs first.
5. **One assembler**: merge `sh4asm2` and `moneypatch.Asm`, add the missing forms on demand, and make the capstone round trip part of `assemble()` (today it is a separate check).
6. **Verification layers**, run by every spec automatically:
   L0 byte level: capstone decode of each changed word, branch target and literal checks, delay slots, nothing outside the declared ranges changed, size unchanged;
   L1 routine level: cave routines executed in the interpreter against a Python reference over edge and random inputs (as `moneycheck` does for 40,000 amounts);
   L2 differential: the REAL patched overlay function executed against the ORIGINAL one with identity parameters; results must be bit-identical (pen x, y, stores); with real parameters they must follow the
   specified rule (`fontcheck` stage 4); differential tests do not depend on the interpreter being a perfect SH-4, only on it being deterministic;
   L3 live: the same edit list exported as a Lua poke script (as `fonttest.lua` does) and run in the emulator by the user, with a `restore` that skips ranges whose overlay changed.
7. **Emulator**: complete `sh4sim.py` for the integer ISA (section 1.1) rather than adopt another emulator.  Unicorn and QEMU are not available; Ghidra's SLEIGH emulation could
   serve as an independent oracle for a handful of routines but needs JDK 25 and is slow; Flycast remains the only full-system oracle and is reserved for the user.

### 4.2 How it composes with the proportional font and the money patch

* Font H1/H2 own: layout function offsets F+0xa0..F+0xe4 (wrap, 68 B in variant A) and F+0x1f6..F+0x216 (advance, 16 B); money owns the first 12 bytes of each money function and the `%D` branch in the expander.  A new spec may touch any other byte of those functions (for example the window constructor, which is a separate function) and the overlap registry makes the ownership explicit.
* The cave is shared: the advance routine can be extended without moving hooks (hooks reference only the entry addresses 0x8c299800 / 0x8c299804 / 0x8c29982a / 0x8c29982e).  The extension that matters (section 6.2) is scaling the table value by A/24 so that windows with advance 16 / 32 / 48 use the same table: `w = (tbl[c] * A + 12) / 24`, which is already the design in `docs/font-hook-notes.md` section 7 (H0/H1); today the cave falls back to `A>>1` when A != 24 (PROVEN from the cave listing, `docs/font-patch-design.md` section 3).
* Any new hook family (window constructor stores, string compiler escape) is independent of the layout function and needs no change to font or money.
* Money patch and font patch are independent today because their functions are disjoint; the registry only formalises that.

### 4.3 Hazards the engine must encode (all PROVEN as facts, each cost something already)

* Shared registers across fields (the `mov #20,r4` example above).
* Delay slots: `mov.l @(disp,pc)` and branches are illegal in delay slots (`sh4sim.illegal_slot`).
* pc-relative literal reach: `mov.l` 0..1020 bytes ahead, 4-aligned base (`(pc & ~3)`); `fontpatch.H2_ALIGN` exists because variants B/C are 2-mod-4.
* Variant differences: window object offsets are 8 lower in variant B, register assignment differs in B/C (`docs/font-patch-design.md` 1.3).
* crt0 zero fill erases anything placed in 0x8c16f800..0x8c299400 (section 3).
* Overlay code is loaded by DMA into RAM at runtime; static patches in the file need no instruction-cache handling, but LIVE pokes might (UNKNOWN: whether `flycast.memory.write8` invalidates the dynarec).

## 5. Test harness decision

Build, in this order: (a) complete the interpreter for integer opcodes used by the library and 1ST_READ helpers (about 80 forms; target: run the window constructor, the format
expander and the string compiler of MEETING end to end with stubs for the jump-table calls); (b) a `verify_spec` driver implementing L0 to L2; (c) a Lua exporter for L3.
Effort is moderate and entirely local.  Risk is low for the shipped patch (the checks only gate the build) and the main residual risk is an interpreter bug in an opcode shared by test and
patch: mitigated by L2 (same interpreter on both sides) and by decoding every word with capstone.

## 6. Window, bubble and font-cell limits

### 6.1 What the limits are made of (PROVEN)

* Wrap rule: a glyph is placed while `units <= 2W-2` with W = `win[0x3c]` and the free-cell flag `win[0x45] = 1`: 33 half-width glyphs for W = 17 (bubble factory B), 39 for W = 20 (message window, factory A); `docs/window-widths.md` section 1.  With the H2 hook the same limit becomes `(2W-1)*A/2` pixels (396 and 468).
* W is stored by one immediate per factory: `mov #60,r0 ; mov #17,r3 ; mov.b r3,@(r0,r4)` (ABROAD 0x8c2d5758-0x8c2d575c, bubble factory); `ptk_sizeclass.py` over the 98 A overlays finds 69 overlays storing 17 and 97 storing 20 (plus `?` stores from register arguments, 224 sites).  Editing one is one byte (`e311` to `e315` for 21).
* `win[0x3d]` rows is never read by the library; the box height is art drawn by the caller (`docs/window-widths.md`; the frame graphics are separate textures, `docs/text-engine.md` 5).
* The default window object is x = 20, y = 240, W = 20 (`mov #20,r4` feeding both fields); the secretary message window is x = 144 (factory A, live at (144, 379)), so its right edge is 144 + 480 = 624 of 640 px (INFERRED from the x origin and 24 px per cell): there is no room to grow W for it.
* Bubble factory B has x as an argument and W = 17 (408 px); room depends on the speaker position (UNKNOWN per call site).
* There is no word wrap, no clipping, no row limit in the layout function; the typewriter counts codes, not pixels (`docs/font-hook-notes.md` 3.2, 5).

### 6.2 Levers, with their numbers

Characters per line for the prose population (`docs/font-widths.md` section 4: average advance 12.00 / 9.96 / 8.84 px; line limits 468 px message window, 396 px bubble):

| Option | px per character | message window (468 px) | bubble (396 px) | needs |
|---|---|---|---|---|
| original fixed 12 px | 12.0 | 39 | 33 | nothing |
| proportional table (built, default OFF) | 9.96 | 47 | 39 | live test; table only for A = 24 |
| proportional + narrowed glyph art (option B) | 8.84 | 53 | 44 | redraw 94 glyphs (data only) |
| size class 2 (8x16 half glyph, A = 16, line height 16), fixed 8 px pitch, W raised to 30 / 26 | 8.0 | 59 (W = 30: 480 px, 59 glyphs) | 51 (W = 26: 408 px) | constructor edits, frame fit |
| size class 2 + table scaled by A/24 | 6.6 | 70 | 59 | cave scaling + above |

Rows: a 3-row message window at line height 24 becomes 4 rows at 16 px in the same 72 px, a 2-row bubble becomes 3 rows (INFERRED, frame art decides).  Capacity per window
with class 2 and the scaled table: message 70 x 4 = 280 glyphs against 39 x 3 = 117 today (2.4 times); bubble 59 x 3 = 177 against 33 x 2 = 66 (2.7 times).

Evidence that class 2 is an existing, working mode of the engine (PROVEN as code facts): the template table has 3 size classes {full, half} = 24x24/12x24, 32x32/16x32, 16x16/8x16 (`docs/font-hook-notes.md` 3.4); the glyph tile is always the whole 12-column bitmap scaled by quad size.  `ptk_sizeclass.py` finds `+0x46` stores of class 2 in 46 sites of 12 overlays (DRSGRF, DRSGRFJ, DRSHRANK, DRSSRANK, ESTABLIS, EVENT, GAME, INVEST, NEWS, OPTION, SELNAT, TRAINING), and BPMATCH shows the exact recipe after construction (0x8c2d3c4a-0x8c2d3c68): `+0x46 = r8`, `+0x3e = 16`, `+0x3f = 19`, `+0x50 = fr15`; the quad is chosen at draw time by `win[0x46]`, so a post-constructor store works.  What is not known: how legible the 12-to-8 px horizontal squeeze looks (UNKNOWN), whether sampling is bilinear (UNKNOWN), how the frame art lines up (UNKNOWN), and the texture-slot budget per window (UNKNOWN: `+0x28` slot limit / texture list size; a window with 4 rows of 70 glyphs may exceed the glyph textures allocated by the constructor; the Japanese design needs at most 60 full-width glyphs per window, English at 39 x 3 has already shown 2 lines live).

The factories A and B do not store `+0x46` (the default constructor stores r13 = 0 there, MEETING 0x8c2dea7c).  Setting class 2 in them needs 4 more bytes than the
factory has; two options: a hook (`CALL`) at the `+0x3e` store site, which has 10 contiguous replaceable bytes (`mov #62,r0 ; mov #24,r5 ; mov.b r5,@(r0,r4) ; mov #63,r0 ; mov.b r5,@(r0,r4)` in ABROAD 0x8c2d5764-0x8c2d576c, then `mov #64,r0`), or one more hook where the layout selects the template by `win[0x46]` so that the class follows A (A = 16 selects class 2).  Both are INFERRED feasible and fall under `HOOK12`.

### 6.3 Verdict on the 33 and 39 limits

The limits are not the binding constraint once pixels per character fall.  Raise capacity in this order: proportional table, offline reflow, then size class 2 for the few windows that
carry the long prose (message window A in 99 overlays, bubble B in 70).  Widening W is useful only together with class 2 (W must grow by 1.5 to keep the same pixel width) and costs 1 byte per site.  A wider
frame is an art/texture task (see the art notes), not a code task, and is limited by the 640 px screen.

### 6.4 "Larger font cell budget"

The half-width glyph tile is 12x24 inside a 32x32 texture (`docs/text-engine.md` 2); 160 half glyphs of 144 B; the root `FONT.BIN` has 16,612 B of slack before the next load address
(0x8ce02000, SHTEX0.ZAR; PROVEN, `docs/memory-map.md` section 7 row 3; limit 679,936).  Slack buys about 115 raw half glyphs; it is not a constraint for English (ASCII is already complete).  A wider
half tile (for example 16 px for bold or large text) is already class 1 (16x32).  No further tile geometry is available without changing the texture size passed to the glyph blit (`FUN_8c15e8ea`, UNKNOWN).

## 7. Widening fields and buffers: the three mechanisms

1. **Immediate/literal edits (cheap, local).** Strides, copy lengths (`strncpy` sizes), `cmp/ge #37/#39` limits in GAME.BIN's own engine (INFERRED sites at 0x8c320334, 0x8c32038e) and window geometry are
   `mov #imm8` or pool words.  Per site this needs the def-use proof of section 4.1.  Limit: imm8 range, and a record stride change moves every later field and every other consumer (other overlays, save routines).
2. **Re-layout of a record (expensive, breaks saves).** Stride tables (person records 30/60 B with name[14], staff 56/112/28 B, BACKUP 240 B, CSAVE3 29 B, municipalities 126 B with a 35-byte name; `docs/uncovered-text.md` 4.3) are walked by
   compiled code in 3 to 10 overlays each; the save routines (CSAVE*, BACKUP, AUTOSAVE) copy whole records.  Widening them breaks save compatibility with the Japanese game exactly in these records and in
   `ETC_DATA/BPINFO.BIN` (name[14], 13 characters).  It is only worth doing where no indirection works.
3. **Escape-token indirection (cheap, breaks no struct).** Names overflow because the 14-byte field is fixed (16,021 of the 18,673 unfittable strings are person-name table entries,
   `docs/capacity-design.md` item 1).  Instead of widening the field, store a 3-byte token in it (reserved lead byte + u16 index, NUL) and expand it to the long English name in the string compiler `FUN_8c2ddeea` (98 copies,
   found with a 24-byte masked head, section 2) from a table in a bank.  Every `%s` and field copy keeps working because the token is an ordinary short string; no stride, struct or save layout changes (saves
   then contain tokens, which only the English build understands: that is the only compatibility break, limited to saves written by the English build).  Risks (INFERRED): callers that compute a name's width from `strlen`
   (`DMCLBEDT` `len*6`, centring), the linear-text path (DMCLBEDT, ENDING, GAME) and GAME.BIN's own engine bypass the compiler; the reserved lead byte must be unused by the existing text (needs a byte histogram; lead bytes 0xEB..0xFC are
   rejected by the extractor, so they are candidates); the `=x/` and control-byte handling inside the compiler must be read before the hook is placed (it compares the byte with 0x3d).  This is a form of table lookup, not text compression.

## 8. Ranked candidates (benefit per effort, then risk)

| # | Candidate | Benefit | Effort | Risk | Notes |
|---|---|---|---|---|---|
| 1 | Switch on the proportional font (built) after one live test of `fonttest.lua` in CLUBEDIT (T-3 transparency, hook correctness) | +20 percent glyphs per line (39 to 47), 17 percent less width | tiny (a test) | low-medium: unproven in game; centring and right-aligned columns assume 12 px (UNKNOWN count) | `docs/proportional-font.md` section 7; keep digits fixed at 12 |
| 2 | Pixel-aware offline reflow and validator: use `advance.json` widths in `transcheck`, `word_wrap`, and the width-violation list (1,846 texts over limit under the cell rule) | removes most mid-word wraps and most violations without any code risk; works with every option below | small | none (build time only); dynamic strings (names, tokens) still need margin | do together with #1 so the limit becomes 468 / 396 px |
| 3 | Cave: scale table by A/24 (`w = (tbl[c]*A+12)/24`, fall back as today) and wrap in pixels for all A | makes #4 and the 16 px rank/list windows proportional too | small (cave about 30 bytes more; L1 test) | low | no new hook sites |
| 4 | Size class 2 for long-prose windows: factory A and B edits (A = 16, line height 16, class 2, W x 1.5), per window class, chosen by the table `winwidth_tables.tsv` | up to 1.5 times glyphs per line and 1.5 times rows: 2.4 to 2.7 times capacity per window | medium (HOOK12 per factory family, per-site def-use, frame-fit check) | medium: legibility of 8x16, frame art, texture-slot budget UNKNOWN | prototype on ONE overlay with the live bridge before building a family |
| 5 | Condensed half-width glyph art (option B) + table | +13 percent over #1 (53 per 468 px) | medium (art; tools `font.py` exist) | low (data), taste | pays only with #1 |
| 6 | Unified patch engine (section 4) | no direct player benefit; makes every later patch cheap and safe; removes the cave address conflict | medium-large | low (gates the build) | build the registry and overlap check first, assembler and interpreter completion as needed |
| 7 | Escape-token names via the string compiler | removes the largest class of unfittable fixed strings (16,021 of 18,673) without touching structs or save layout | medium-large (hook, bank builder, translation DB side) | medium (strlen-width callers, linear path) | needs a byte-histogram and the bank design from the memory study |
| 8 | Raise W alone (bubble 17 to 20-21, 1 byte per factory) | +18 percent in bubbles if the frame art allows | tiny | medium-high: frame art UNKNOWN, screen edge | only after a frame look in the emulator |
| 9 | Replace the layout function by a cave routine with real word wrap and automatic reflow | removes the need for hand `\n` | large | medium-high | not needed if #2 is done; defer |
| 10 | Re-layout of 14-byte name records | names without abbreviation | very large | high: breaks saves (BACKUP, CSAVE3, BPINFO), many overlays | avoid; use #7 |

## 9. UNKNOWNs and the experiments that settle them (for a later emulator session; none was run here)

1. Proportional font in game: advance and wrap correct, paper texels transparent at pitch < 12 (T-3), no boot failure of the modified `1ST_READ.BIN`.
2. Size class 2 on one window: poke `+0x46 = 2`, `+0x3e = 16`, `+0x3f = 16` after construction (BPMATCH recipe) and look at 8x16 English; check the texture-slot budget with a 4-row, 70-glyph text.
3. Bubble/message frame: poke W = 21 or 25 in one factory and see whether the frame art is fixed (expected) and where the text ends relative to it.
4. Whether `flycast.memory.write8` invalidates the dynarec for live code pokes (needed for L3).
5. The unused-lead-byte census for the escape token (static, can be done now).
6. Whether callers centre or right-align by character count (list from `tools/re/font/fieldreads.txt`).

## 10. Files written

* `docs/expansion/patch-toolkit.md` (this file).
* `tools/re/ptk_simcov.py` (opcode coverage of `sh4sim.py` against capstone), `tools/re/ptk_tailmap.py` (1ST_READ tail map and existing cave claims), `tools/re/ptk_sizeclass.py` (window size-class and geometry stores over the 98 A overlays), `tools/re/ptk_famscan.py` (masked function-family matching).  All read-only, `python -I -X utf8 <file>`.

## Status after stage 3 (docs, 2026-11-11)

See `docs/expansion/status.md` for the table of what was built from this study, its flag or file, how far it is proven, and what is still open.  The summary for this study:

* Done: the patch engine core (`tools/patchengine.py`, `docs/patch-engine.md`: cave registry, overlap registry, site families, hook builder), the proportional font as the standard build flag (played in Flycast up to `trial_prop3`), the pixel-aware validator (candidate 2) and the opt-in advance scaling (`--prop-scale`, candidate 3, unproven in game).  Money (`tools/moneypatch.py`) and layout / club-name guard (`tools/layoutpatch.py`) were built on the same approach.
* Not done: candidates 4 (size class 2), 5 (condensed art), 7 (escape-token names), 8 (raise W), 9 (replace the layout function); the experiments of section 9 (items 2 and 3 in particular) are the next emulator session's work.
