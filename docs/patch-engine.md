# Patch engine core (`tools/patchengine.py`)

Implements parts 1, 3 and 4 of the design in `docs/expansion/patch-toolkit.md` section 4 and re-expresses the two existing code
patches (`tools/fontpatch.py`, `tools/moneypatch.py`) on top of it.  Pure bytes in / bytes out, no emulator, nothing here starts
Flycast.  Status words as in the study: **PROVEN** = executed or compared here.

## 1. What exists now

| Part | Where | What it does |
|---|---|---|
| Cave registry | `patchengine.CaveRegistry`, `patchengine.REGISTRY` | named regions of `1ST_READ.BIN` (address, size, owner, placement tag), non-overlap check, symbol table, zero check, first-fit allocator for new caves |
| Overlap registry | `patchengine.EditSet` / `Edit` | every spec contributes edits `(file, offset, new bytes, owner, expected old bytes or ZERO)`; `apply()` checks all of them against the bytes it is given, refuses overlaps, writes in one pass, never changes a size |
| Site families | `patchengine.Family`, `scan_family`, `mask_bytes` | masked-head function finder: head of at least 24 bytes with pc-relative operands masked, optional per-variant masked hash, alignment, expected copy counts, look-alike refusal |
| Hook builder | `patchengine.hook12` | the 12 byte `mov.l @(1,pc),r0 ; jmp @r0 ; nop ; nop ; .long CAVE` entry replacement |
| Opt-in advance scaling | `fontpatch.cave_bytes(..., scale=True)`, `make_patches(..., prop_scale=True)` | section 4 |
| Interpreter | `tools/sh4sim.py` | integer ISA completed with the opcodes listed in section 5 |
| Tests | `tools/test_patchengine.py` (26 tests), `tools/test_sh4sim.py` (15 tests) | `python -I -X utf8 tools/test_patchengine.py` |

`python -I -X utf8 tools/patchengine.py plan` prints the cave plan.

## 2. The cave plan (collision resolved) - PROVEN collision free by `test_patchengine.Registry`

| Cave | Start | Size (reserve) | Owner | Note |
|---|---|---|---|---|
| `font.lin` | 0x8c299600 | 0xc0 | font | `--lin-center` (default ON with the proportional font, `fontpatch.LIN_SRC`, 192 B): centres narrow glyphs in the linear text writer `FUN_8c15e9c6` (hook 42 B at 0x8c15ea22); reads the advance table 0x8c299900 at run time; sits between `money.lib` (..0x8c299600) and `font.cell`; the cave is exactly 192 bytes = the whole claim |
| `font.cell` | 0x8c2996c0 | 0x40 | font | `--cell-prop` (default ON with the proportional font, `fontpatch.CELL_SRC`, 28 B): `cell_adv`, the proportional advance of the GAME.BIN commentary line engine (called by `layoutpatch.patch_cell_prop` from the half-width block `0x8c32048c`, literal in the zero word `0x8c32053c`); reads the table 0x8c299900 at run time; the spare 64 B behind `font.lin`, proven unused (zero, no pointer into it from 1ST_READ / GAME / any FLOW_PRG overlay) |
| `font.align` | 0x8c299700 | 0x100 | font | `--align-fix` (default ON in the `build_patch.py` command line since stage 8b, together with `--tag-fix`: the short-name routine is replaced inside the 11 overlays, no cave) (`fontpatch.ALIGN_SRC`, 224 B): blank-run grid snap `at_snap` (entered from the table path of the advance routine) and the panel width routine `pw3`; the free zero run below the font cave is `money.lib` 0x8c299400 (0x200, 240 B used), then this (money.libn needs 644 B and moved to the start of the bank, see below) |
| `font.cave` | 0x8c299800 | 0x100 | font | 104 byte advance/wrap routine (144 bytes with `--prop-scale`) |
| `font.table` | 0x8c299900 | 0x100 | font | 256 byte advance table |
| `money.lib` | 0x8c299400 | 0x200 | money | mn6: wrapper of the shared number library (240 B, `moneypatch.LIB_SRC`), registered by `moneypatch` at import |
| `money.cave` | 0x8c299a00 | 0x200 | money | formatter incl. power table: jp style 388 B (default), western 428 B |
| `money.libn` | 0x8c299c00 | 0x400 | money | mn6: numeric-format wrapper (644 B, `moneypatch.LIBN_SRC`); carved from the START of the planned bank by `moneypatch` at import (it shrinks the planned `bank` claim) |
| `bank` (planned) | **0x8c29a000** (was 0x8c299c00 before mn6) | 0x8c2a0000 - 0x8c29a000 = 24,576 | bank | translation bank and every new hook cave; must start here, not at 0x8c299800 (that was the open collision of `docs/capacity-design.md`) |
| `font.gap1.cave` / `font.gap1.table` | 0x8c13bb80 / 0x8c13bc00 | 0x80 / 0x100 | font | alternative placement (`--prop-font-place gap1`), only one placement is ever used |

Rules enforced by the registry: two claims may overlap only when they have the same owner and different placement tags
(alternatives); a patch handed a non-default address (`moneypatch.patch_1st_read(k, addr)`, `fontpatch.patch_1st_read(k, t, (c, t))`)
is refused when the area touches any other claim, including the planned bank.  New caves are carved with
`REGISTRY.alloc(name, owner, size, lo, hi, align)` after the bank owner has replaced the planned `bank` claim by its real pieces.
The historic addresses did not move: the default build is byte-identical (section 6).

## 3. How a spec is written

```python
es = PE.EditSet({PE.IMG_NAME: PE.IMG_BASE})                    # bases only make messages print load addresses
es.add('mypatch.cave', PE.IMG_NAME, addr - PE.IMG_BASE, code, expect=PE.ZERO)       # cave: old bytes must be zero
for s in FAMILY.find(overlay_bytes, name):                       # sites of a family
    es.add('mypatch.hook', name, s.off, PE.hook12(addr), expect=overlay_bytes[s.off:s.off + 12])
new = es.apply({PE.IMG_NAME: k, name: overlay_bytes})            # {file: bytes}; overlapping edits raise EngineError
```

* `apply()` works on whatever bytes it is given (original files, or the current bytes of an earlier pipeline stage), so the result
  does not depend on the order in which specs were added.  A whole-pipeline version of the design ("apply every spec to the ORIGINAL
  bytes") needs the integrator to collect all `EditSet`s first; `fontpatch.overlay_edits()` and `moneypatch.overlay_edits()` already
  expose the edit lists for that.
* Overlap = same file and intersecting byte ranges.  Edits of different owners may only touch (adjacent ranges are fine).  Two edits
  of one owner at the same place are tolerated only when byte-identical.
* `verify_confined(before, after, es, file)` is the L0 test "nothing outside the declared ranges changed, size unchanged".
* `Family(name, head, rule, variants, body_len, align, expect, misaligned)`: `head` must be >= 24 bytes (even) for a masked rule, >= 16
  for the exact rule `'none'`; at least 8 unmasked bytes in a row anchor the search.  Mask rules: `pc` (mov.w/mov.l `@(disp,pc)`),
  `pc+bsr` (default, the money rule, so the existing hashes stay valid), `branch` (also bra, bt/bf/bt.s/bf.s, mova).  A head match whose
  masked body hash is unknown raises (a look-alike must not be patched blindly); a misaligned match raises or, with
  `misaligned='skip'`, is ignored.  `scan_family()` + `family_tsv()` give the review table.

## 4. `--prop-scale` (opt-in, default off) - PROVEN in `sh4sim` against a Python reference

Without it, a window whose advance byte A is not 24 (the 16 / 32 / 48 / 10 px classes: rank lists, size class 2 prose windows, ...)
advances half-width characters by the fixed `A >> 1`, even with the proportional font on.  With it:

    A == 24      w = tbl[c]                       (unchanged; tbl 0 means 12)
    A  > 0       w = (tbl[c] * A + 12) / 24       (tbl 0 means 12; floor division)
    A <= 0       w = (A + (A < 0)) >> 1           (the original rule)

* Identity where the table says 12 (digits, unlisted codes): `(12 * A + 12) / 24 = (A + 1) >> 1`, which equals the original `A >> 1` for
  every even A (all real windows: 10, 16, 32, 48); an odd A would give one pixel more (the formula is the specified rounding).
* Cave: only ONE byte of the default 104 byte cave changes (the displacement of `bf adv_gen` at +0x0c now reaches the appended
  routine at +104); the appended 40 bytes (`CAVE_SCALE_SRC` in `fontpatch.py`, total 144 of the 256 byte reserve) do the scaling with two
  `mul.l`: `(x * 2731) >> 16` is exactly `x / 24` for 0 <= x < 4000 (x <= 24 * 127 + 12 = 3060), checked exhaustively.
  **Every entry offset and every overlay hook byte is identical with and without the option** (`test_overlay_hooks_are_unchanged_by_prop_scale`),
  only `1ST_READ.BIN` 0x8c299800..0x8c299900 differs.  The wrap routine is untouched (random comparison default vs scale cave, both variants).
* Executed tests (`PropScale`): all 256 window advances (-128..127) x 33 character codes x four tables (random, all 12, extreme, the real
  derived table), entry A and entry B (variant B windows keep the byte at +0x36), identity and default-behaviour cases.
* Only the `tail` placement can host it (the `gap1` reserve is 128 bytes: `patch_1st_read(..., scale=True)` raises).
* Not proven in the game: the option is only meaningful together with `--proportional-font on`, and whether size-class-2 windows
  look right needs the same live test as the proportional font itself (`docs/proportional-font.md`).  The wrap test (H2) multiplies the
  window's A by W-1 cells, so a window with A = 16 now wraps by pixels computed with scaled advances: consistent, but unobserved.

## 5. Interpreter additions (`tools/sh4sim.py`, tests `tools/test_sh4sim.py`)

`not`, `swap.b`, `swap.w`, `xtrct`, `xor #imm,r0`, `negc`, `subc`, `subv`, `addv`, `cmp/str`, `div0s`, `div0u`, `div1` (Q/M state added to
the machine), `shad`, `shld`, `shlr2/8/16`, `rotl`, `rotr`, `rotcl`, `rotcr`, `dt`, `mulu.w`, `muls.w`, `dmulu.l`, `dmuls.l` (MACH:MACL),
`sts mach`, `lds Rn,mach/macl/pr`, `clrt`, `sett`, `clrmac`, `bsr`, `bsrf`, `braf`, `pref`, `ocbi/ocbp/ocbwb`, `movca.l`.  Each is executed on edge
and random values against an independent Python reference; the encodings are cross-checked with capstone when it is installed
(mnemonic of every hand-encoded word).  `div1` is validated as the manual's unrolled 32 / 32 unsigned division (div0u; 32 x
`rotcl r1 ; div1 r0,r2`; `rotcl r1`) against Python `//` on 308 cases (divisors below 2**31).  Unknown opcodes still raise `SimError`.
Not added (no hook needs them yet): GBR forms, `ldc/stc`, `mac.l/mac.w`, `tas.b`, cache/TLB instructions other than the above, all FPU
arithmetic.

## 6. Proof that the default build did not change

`tools/re/pe_baseline.py record|compare FILE.json` hashes (sha256) every output of `fontpatch.make_patches` (variants A / ABC x placement
tail / gap1 x wrap on / off x glyphs on / off), `moneypatch.make_patches` (default, variants AB, `decimal_d` off, `tv_card` off), both
composition orders on the current bytes, the font cave of both placements, the money cave and hook at two addresses and the generated
`fonttest.lua`: 49 entries, **identical** before and after the rewrite (recorded from the old modules, compared against the new).  The
public functions and constants of both modules are unchanged (`PLACEMENTS`, `CAVE_SIZE`, `RESERVE`, `ENTRY_*`, `H1_*`, `H2_*`, `NOP`,
`CAVE_ADDR`, `HOOK_LEN`, `FN_LEN`, `SIGS`, `_mask`, `find_sites`, `patch_overlay`, `patch_1st_read`, `make_patches`, `hook_bytes`).  New:
`fontpatch.patch_1st_read(..., scale=False)`, `fontpatch.make_patches(..., prop_scale=False)`, `cave_bytes(..., scale=False)`,
`overlay_edits()`, `FAMILIES`, `moneypatch.FAMILY`, `HEAD`, `overlay_edits()`.  `FontPatchError` and `MoneyPatchError` now derive
from `patchengine.EngineError` (they were plain `Exception`).

Re-expression details:

* money: the 12 byte prologue + two word test became the 24 byte masked head `HEAD` (both variants share it once the pc-relative words
  are masked) + the unchanged masked body hash; 102 A + 6 B copies found, offsets identical to the old finder in every overlay.
* font: the three exact 16 byte advance templates are `Family` objects (rule `none`); the wrap block (H2) is still checked as an exact
  template at a fixed distance, as before.  A 16 byte exact template is below the 24 byte masked minimum on purpose: it constrains every byte.
* both: cave writes are `EditSet`s with `expect=ZERO` (same refusal text: "area ... is not zero (already patched, or used by another stage)").
* The TV station card patch (`moneypatch.patch_tv_card`) is still its own function (it rewrites two blocks of one overlay by signature
  and was not touched).  Its ranges do not overlap the money hook (disjoint functions); moving it onto `EditSet` is the next small step.

## 7. Open items / next steps

1. `build_patch.py` (not edited here, other owner): see "integrator edit" below.
2. The translation bank (`docs/trans-bank.md`, `make_regions`) must take its start from `REGISTRY['bank']` (0x8c29a000 since mn6; `moneypatch` carves `money.libn` from the old start).
3. A whole-pipeline "collect all edit sets from the ORIGINAL bytes, apply once" driver (design 4.1 point 4) would use `overlay_edits()` of both
   patches plus the TV card; today the stages compose on current bytes and the zero checks + expected-old-bytes checks catch a bad composition.
4. Assembler merge (`sh4asm2` + `moneypatch.Asm`) and capstone-in-`assemble()` (design 4.1 point 5) are not done.
5. L2 differential tests of the real overlay layout function with `--prop-scale` (as `fontcheck` stage 4 does for the default cave) were
   not added: `fontcheck.py` is outside this task's scope; the routine-level proof (L1) is in `test_patchengine.PropScale`.

### Integrator edit for `tools/build_patch.py` (DONE: `--prop-scale on|off`, default off; docs/pipeline.md 9.2)

```python
# argparse, next to --prop-font-place
ap.add_argument('--prop-scale', choices=['on', 'off'], default='off',
                help='with --proportional-font on: windows whose advance is not 24 (16/32/48/10 px) scale the advance table by A/24 '
                     '(tools/fontpatch.py CAVE_SCALE_SRC, docs/patch-engine.md); default off')
# apply_prop_font(res, font_dir, variants='A', place='tail', glyphs=True, prop_scale=False)  -> pass through:
out, rep = FPT.make_patches(read_extracted, current=res.patches, variants=variants, place=place,
                            overrides=overrides, expect=expect, glyphs=glyphs, prop_scale=prop_scale)
# note text: 'cave @%#x (%d B)' % (rep['cave'], FPT.CAVE_SIZE_SCALE if rep['prop_scale'] else FPT.CAVE_SIZE)
# build_patches(..., prop_scale=False) gets the new keyword last and forwards it in the apply_prop_font call;
# main(): build_patches(..., a.prop_scale == 'on'); reject --prop-scale on without --proportional-font on and with --prop-font-place gap1.
```

## 8. Note: data relocation is not a code patch (stage s8gf, 2026-11-13)

The patch engine above never moves data, but the pointer-string relocation of `--hw-relocate` (forced by `--refit on`) does move data and is
the one stage that can break code that addresses a table by its first element (`base + idx * stride`).  After the prop10c hang it is guarded:
`tools/hwguard.py` reads the overlay's own code (literal loads, index arithmetic) to decide whether a pointer is a text pointer or a table
base, `translation/hw_inplace.tsv` lists the records that never move, relocated strings are 4-byte aligned.  The patch engine's hooks and
caves are untouched.  See `docs/hw-relocation.md` section 6.
