# SCDRF texture hang: what the RAM dump shows (owner `hrd`, 2026-11-12)

Input: `build/emu/hang_v1_ram.bin` (main RAM 0x8c000000..0x8cffffff, dumped by the user from Flycast while `bis_v1` was hung; no registers), the discs
`bis_v1` / `bis_e`, the original files.  Nothing was launched.  Companion document: `docs/scdrf-texture-hang.md` (owner `hsd`, static analysis, wrote the fix).
This document is the independent confirmation from the dump and the proof on a rebuilt disc.  Status words: **PROVEN** = read from the dump / disc bytes /
disassembly, **INFERRED** = follows but not traced to the end.

## 0. Result

**Root cause (PROVEN): the repainted texture is not "a table in the overlay", it is the content of a STORED ZSARC member (`scda.tbd`, header at file 0x2ff38,
data 0x2ff64..0x32998) embedded in `FLOW_PRG/SCDRF.BIN`.  `texinject` rewrote the record inside the member and left the member header's data CRC16 as it was.
The game verifies that CRC before it uses the member, gets NULL, and builds the screen with a garbage texture-list handle.**

The dump shows every link of that chain except the final wait loop:

| link | evidence in the dump | status |
|---|---|---|
| the overlay running at the hang is SCDRF, not EVENT | slot 1 struct: descriptor 0x8c2ebec4, base 0x8c2d0000 = SCDRF; slot 5: descriptor 0x8c6d5604 = INITCON.BIN; EVENT.BIN is not loaded | PROVEN |
| the load is complete and correct | RAM 0x8c2d0000.. equals the `bis_v1` file in 6,397 of 6,409 64-byte chunks; the 335 differing bytes are 7 small runs of run-time variables (0x1bec8..0x1d5d4, 0x32c84); the texture bytes are all there | PROVEN |
| the member in RAM fails the game's check | header at 0x8c2fff38 says CRC16 0xbb66 (the original data's), the data in RAM has another CRC; header CRC still valid; the re-implemented walker stops with a CRC mismatch on the RAM image and on the `bis_v1` file, and passes on the original, `bis_e` and `fix_v1` | PROVEN |
| the game's error path is silent | the error printf (0x8c159f78 -> 0x8c011084) returns at once when byte 0x8c230bd6 is 0; it is 0 in the dump | PROVEN |
| the texture list was never built | SCDRF's list handle 0x8c33b780 holds 0x3f800000 (a float 1.0 left on the stack), not a heap pointer | PROVEN |
| the screen uses the garbage handle | the window object at 0x8c4cede0 (pointer at 0x8c33b76c) has 0x3f800000 in its texture-list field +0xf8 | PROVEN |
| the window then never finishes (empty message window, vblank still running) | not traced: no registers, the wait loop was not located | INFERRED |

The disc itself is sound: `SCDRF.BIN` has the same size (410,142) and LBA (430,424) in `bis_v1`, `bis_e` and `fix_v1`, `verify_disc` is clean, and the
two discs differ in this one file only.  Hypotheses (a) loader checksum / compressed overlay, (c) PVR header / format and (d) overlap with the text repack
are excluded; (b) "the region is not only a texture" is the right family, with the twist that the surrounding structure is a checksummed archive member.

## 1. Which overlay, and is the image intact (`tools/re/hrd_ram.py slots`, `tools/re/hrd_scdrf.py`)

Slot structs at 0x8c228384 (12 x 0x60): slot 1 = SCDRF (count 2, heap start 0x8c33f620 = `overlays.tsv` `end_rounded`), slot 5 = INITCON (0x8c6d0000),
slot 10 HELP, slot 11 FACEMDUL, the rest free.  So the "second Event screen" before the scout choice is already run by **SCDRF + INITCON**; EVENT.BIN is gone.
That answers how a texture of the scout overlay can stop the flow "before the scout screen": the scout overlay is what draws that screen.

`hrd_scdrf.py bis_v1 bis_e build/emu/hang_v1_ram.bin`:
* `bis_v1` vs `bis_e`: 2 ranges, 10,743 bytes, 0x2ff93..0x30c81 and 0x30c8a..0x32993.  Both inside the record's slot 0x2ff78..0x32998.  No text, pointer or
  font-patch byte differs, so the repack does not overlap the texture.
* table at 0x2ff64 (all three files): 1 record, flags 0x80000100 (ARGB1555, twiddled, `-bz--`), 128x128, offset 0x14, stamp 0x540af03e; the stream decodes to
  32,768 bytes in every file.  The original stream is 10,781 bytes (slot 10,784), the new one 10,556 bytes plus zero fill.  The declared size is the true size.
* bytes in front of the table: `... 77 c9 2a 37 66 bb 00 00 00 0c 00 01 "scda.tbd" 00 06 00 00 28 a9 00 00 00`: a ZSARC member header (hdrlen 0x2c, `-nc--`,
  packed = orig = 10,804, CRC16 0xbb66 at +0x13, name extension, header-CRC extension).  Bytes behind the member (0x32998): `00 00 00 00` = archive
  terminator, then u16 sprite coordinates.
* RAM vs `bis_v1`: 7 ranges / 335 bytes (variables); RAM vs `bis_e`: the same plus 0x2ff93..0x32993.  No truncated or partial load.

## 2. The check that fails (`tools/re/hrd_members.py`, `tools/re/hrd_walk.py`)

SCDRF's init function 0x8c2d10fc (disassembly of the original; the literal 0x8c2fff38 at file 0x120c is the only reference to the member):

```
8c2d110a  mov #0,r6 ; r14 = 0x8c159000 (1ST_READ jump table) ; r5 = 0x8c2fff38
8c2d1110  jsr @(0x3d4,r14)   r4 = 0        -> 0x8c15a87c: FUN_8c15a45a(0, member, 0, 2)   "data pointer of member 0"
8c2d1116  mov.l r0,@(4,r15)                 result saved, NOT tested
8c2d1120  jsr @(4,r14)      r4 = 0x80e8     scratch buffer
8c2d112e  jsr @(0x38c,r14)  r4 = result, r5 = scratch, r6 = r15   -> 0x8c15a942 "texture list from the TBD at r4", handle to @r6
8c2d1134  mov.l @r15,r3 ; mov.l r3,@0x8c33b780                     handle stored, return value NOT tested
```

`FUN_8c15a45a` with mode 2 and a stored member (`tools/re/ghidra/d2.txt`): `if (packed != orig) error; if (crc16(data, orig) == header.crc16) return data;
"CRC mismatch %d"; return 0`.  `hrd_members.py` / `hrd_walk.py` on the member at 0x2ff38:

| image | header CRC | data CRC16 == header | walker |
|---|---|---|---|
| original, `bis_e` | valid | yes | OK, list of 1 record |
| `bis_v1` (disc) | valid | **no** | fails -> NULL |
| RAM dump at 0x8c2d0000 | valid | **no** | fails -> NULL |
| `fix_v1` (disc) | valid | yes | OK, 1 record, payload sha1 5bde22a28b = the repainted PVR |

With NULL, `0x8c15a942` allocates 8 bytes, reads the record count from address 0 (`mov.l @r3,r2` with r3 = 0: the boot ROM, not a table), asks for
`count*12` and `count*44` bytes, and on allocation failure returns -1 **without writing the handle** (`bra` to the exit at 0x8c15a99e).  SCDRF then copies
whatever was on its stack into 0x8c33b780.  In the dump that word is 0x3f800000, and the same value sits in the window object's field +0xf8
(0x8c4ceed8), written by `mov.l @0x8c33b780 -> @(0xf8, window)` at 0x8c2d0928..0x8c2d0932.  A list handle is a heap pointer in a good run (the neighbours
0x8c33b770..0x8c33b778 and 0x8c33b784 are 0x8c4c.... / 0x8c8c.... pointers).  The messages ("CRC mismatch", "can't malloc size") go through 0x8c011084,
whose first test is `if (*(u8*)0x8c230bd6 == 0) return`; the byte is 0, so nothing is shown and nothing halts.  From there the window works with a list at
0x3f800000 and never completes: that last step is INFERRED (the header, calendar and secretary come from other, valid texture lists, which fits the picture).

## 3. Fix and proof (`build/trial/fix_v1`)

The fix was written by `hsd` while this analysis ran (it is in the tree, not repeated here): `texinject.inject` refreshes the data CRC16 and the header CRC
of the stored member around an embedded table (`refresh_stored_member`), `build_patch.apply_textures` fails the build if a member that was valid becomes
stale (`stale_stored_members`), `tools/test_texinject.py` section G covers SCDRF, SEARCH x2, NEWCON, RECON.  Re-run here:
`python -I -X utf8 tools/test_texinject.py --quick --no-plan` -> `310 checks passed, 0 failed`.

`build/trial/fix_v1` = the `bis_v1` command line with the current tools (`--repack on --share dup --append-safe --proportional-font on --strict
--money-format off --club-guard off --textures-dir build/int/tsub/v1`; log `build/trial/fix_v1.log`: failed 0, skipped 0, `verify_disc` OK 0 errors 0 warnings,
digest 0083182872).  Read back from the disc tracks:

* `skh_discdiff.py fix_v1 bis_v1`: one changed file, `SCDRF.BIN`, same size and LBA, **4 bytes**: 0x2ff4b..0x2ff4c (data CRC16, member +0x13) and
  0x2ff5f..0x2ff60 (header CRC, member +0x27).  The texture stream is identical to `bis_v1`.
* `skh_discdiff.py fix_v1 bis_e`: one changed file, `SCDRF.BIN`, 10,747 bytes = the 10,743 texture bytes + those 4.
* `hrd_members.py fix_v1`: member valid (header CRC and data CRC16); `hrd_walk.py`: the walker passes and the list holds the repainted payload.

So the one defect that separates the hanging disc from the working one is gone on `fix_v1`.  **Not yet booted**: `fix_v1` should reach the scout choice with
the English sheet; if it still hangs, the cause is not (only) the CRC and the junk handle of section 2 would have to be explained some other way.

## 4. Which installed textures are of this kind

9 of the 237 installed texture files are tables embedded in overlays (`@hex#i` ids).  The defect needs a stored ZSARC member around the table:

| file | table | enclosing stored member | old discs |
|---|---|---|---|
| `SCDRF.BIN/@2ff64#0` | 0x2ff64 | `scda.tbd` @0x2ff38 | **stale** |
| `SEARCH.BIN/@2c58c#0` | 0x2c58c | `schme1.tbd` @0x2c55c | **stale** |
| `SEARCH.BIN/@2fcf0#0` | 0x2fcf0 | `scda.tbd` @0x2fcc4 | **stale** |
| `NEWCON.BIN/@293f0#0` | 0x293f0 | `newcon.tbd` @0x293c0 | **stale** |
| `RECON.BIN/@25758#0` | 0x25758 | `selb.tbd` @0x2572c | **stale** |
| `ESTABLIS.BIN/@1ee08#0`, `#1` | 0x1ee08 | none | not affected |
| `LOADBAR.BIN/@1ec#0` | 0x1ec | none | not affected |
| `YOUTH.BIN/@36114#0` | 0x36114 | none | not affected |

`hrd_members.py prop8 --all` (every `FLOW_PRG/*.BIN` of the disc): 26 embedded members, **5 stale**, exactly the five above; `bis_e`: 0 stale.  The other 228
textures live in containers whose CRCs were always rewritten (`zs_replace_member`) or that have none (whole-file TBD, plain PVR).  Every disc built with
textures before the fix (prop7, prop8, `bis_a`, `bis_b`, `bis_d`, `bis_s*`, `bis_u*`, `bis_v*`) carries the stale members and must be rebuilt.  NEWCON and
RECON would have shown the same failure on their own screens (new contract, contract renewal).

Stored members with tables that no texture touches yet, where the same rule will apply (now handled by the injector): ABROAD / EVENT / SEARCH
`earth.tbd` and `yaji.tbd`, NEWCON `f1.tbd` `f2.tbd` `f3.tbd`.  The survey only covers overlays; the build guard sits in the texture stage only, so a text or
code patch that lands inside an embedded member would not be caught (none does today: `bis_e` has 0 stale members).

## 5. Helper scripts (prefix `hrd`, read-only)

`hrd_scdrf.py A B [RAM]` (a file of two discs vs the original and vs RAM: ranges, table, neighbours), `hrd_members.py SPEC [FILE..|--all]` (embedded ZSARC
members and their CRC state in the original, a disc, a dump dir or a RAM dump), `hrd_walk.py FILE OFF SPEC..` (the game's walker and list builder on a
member), `hrd_ram.py DUMP w|b|find|findw|dis|slots` (RAM peeks, SH-4 listing), `hrd_pvrsha.py` (PVR header and payload hash).
