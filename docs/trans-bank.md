# External translation bank (overflow strings that do not fit in place)

> **Status note (docs, 2026-11-11).** **Design only, not built.** The external bank was never implemented. Overflowing strings are handled by pool repacking (`tools/textrepack.py`, `--repack on --share dup`), `--append-safe`, half-width relocation (docs/hw-relocation.md) and the refit forms (`translation/refit/`); `--grow-overlays` (docs/pipeline.md 9.5) is the opt-in growth path. Kept as the reference for the on-demand bank idea that docs/expansion/save-format.md section 6 builds on.

Author: agent `bank`.  Static analysis only: Ghidra 12.2 on `1ST_READ.BIN` (own project copy `<GHIDRA_PROJECTS>\ghproj_bank`, programs
`1ST_READ.BIN` and `1ST_READ_HOOK.BIN`), the four RAM dumps in `build/emu/`, the overlays in `extracted/`, `translation/*.jsonl`.
**No emulator was started.**  Every number below was produced by a script in `tools/re/capacity/bank/` (outputs saved next to them as `*.txt`).
Status words: **PROVEN** = computed/decompiled and re-checked here; **INFERRED** = follows from code, never run; **UNKNOWN** = needs the dynamic test in s8.

Code: `tools/re/capacity/bank/bankbuild.py` (bank builder), `hookpatch.py` (boot-hook patch), `canary.py` (soak-test helper), `lua_poke.py`
(live pointer redirect), `tools/sh4asm.py` (tiny assembler).  Re-runnable analysis scripts are listed in s9.

## 0. Result in six lines

1. A boot-time `TRANSBANK.BIN` is **not needed for the first 260 KB**: `1ST_READ.BIN` already contains **243,159 bytes of never-referenced padding** that the BIOS
   loads with the executable, plus **16,612 bytes** behind the glyph data of the (loaded) root `FONT.BIN`: **259,771 bytes** in total, zero code patches, no new file,
   no ISO change, same file sizes.  Region list in s2.4 (bytes, addresses, evidence, risk).
2. All large RAM areas that *look* free in the four dumps are not (s2.5): `0x8c239000..0x8c299000` is inside the crt0 BSS clear and holds 3D data,
   `0x8ce68000..0x8ce9a000` are four referenced work buffers, `0x8cd40000..0x8cd5c000` is the FACEMDUL arena, every `0x8cX0000` slot is managed by the
   overlay allocator (FLOW1..11 sit at the slot bases).  So **no free destination for a bigger boot-loaded file was found**; the hook route (a) is verified
   as a mechanism (s4, patch bytes + Ghidra listing) but has nothing to load into yet.
3. A shared bank of 259,771 B serves **70.5 % of the overflow strings / 37.6 % of the overflow bytes** in the r=1.5 model (s3, `bankbuild.py --stress 1.5`),
   because 24,943 unique Japanese texts stand behind 119,946 overlay strings (strings used by >=5 overlays: 1,673 unique, 32.9 KB, serve 63 % of all overflow strings).
4. The rest (r=1.5: 2.21 MB in 89 overlays, MEETING 559 KB, NEWS 437 KB, DRAFT 155 KB, TRAINING 155 KB, HELP x2 ~165 KB each) needs **route (d) per-overlay tail**
   (`_end` word raised; BSS overlays get their BSS as explicit zeros in the file).  Prototyped and self-tested on CHALDANI (no BSS) and MEETING (BSS), s5.
5. **26,576 strings (26 %) at r=1.5 overflow but are not relocatable** (orphans without pointers, stride tables, interior pointers: 37,960 of 119,946 strings, 505 KB of
   Japanese): no bank can hold them, the translation must fit in place (r<=1.0) for those.  This is the biggest hard limit; see s3.2.
6. New dynamic tests (s8): soak a canary pattern through every game mode (`canary.py`), boot-hook test with `NAMIHEI.DRV`, route-(d) BSS append, heap high-water, odd-address pointer render.

## 1. Corrections to earlier documents (found while tracing the loader)

| Earlier claim | Finding (PROVEN) |
|---|---|
| docs/font.md, text-engine.md: the font that is loaded is `ATFIRST/FONT.BIN` (INFERRED) | **Root `/FONT.BIN` (663,324 B) is the loaded copy**: `fontwhich.py` - RAM at 0x8cd5c000 equals the root file 663,324/663,324 bytes in both dumps; `ATFIRST/FONT.BIN` (663,096 B) matches 97.6 %, first difference at byte 12.  The boot call is `FUN_8c15eeb8(name, 0, dest)`: 2nd argument 0 = root directory; SHTEX0.ZAR/BAR.TBD/SECFTEX0.ZAR use `FUN_8c15f63c(2)` = directory-table entry 2 = **ETC_DATA** (dump: table entry 2 name "ETC_DATA", 162 records), not ATFIRST (ETC_DATA/SHTEX0.ZAR is byte-identical to ATFIRST/SHTEX0.ZAR).  Patching the ATFIRST copy of FONT.BIN has no effect on these boots (keep both patched, it is harmless). |
| docs/overlay-text.md: BSS "zero runs" of `1ST_READ.BIN` as free space | The zero run `0x8c16eebb..0x8c2a0000` (1,249,605 B) is **BSS that crt0 (`FUN_8c017160`) zero-fills at start**: `[0x8c16f800,0x8c299400)` and `[0x8c193c30,0x8c1fc180)` (`crt0.py`).  Anything stored there in the file is destroyed before `main`.  Only bytes **outside** these ranges are usable as in-file storage. |
| docs/text-engine.md s6: the overlay heap is `[_end, slot end)` | The arena runs from `_end` to the **end of the free slot run behind it**: slot descriptors in the dump (0x8c2283a0..) show CLUBEDIT's arena `0x8c3062a0..0x8c7d0000` (slots 2-6) and N_ENTRY's up to 0x8cad0000.  `heap_now` in s6 is therefore a lower bound.  Heap block format (PROVEN, `FUN_8c16325a`, `heapwalk.py`): `{size, state, prev, next}` 0x20-byte header, state `0xfeedfeed` = used, `0xdeaddead` = free. |
| pipeline.md: files cannot be added | Confirmed: `discbuild.py` line 367 raises `KeyError("no such file on disc")`.  A boot-loaded bank must replace an existing file (s3, route a). |

## 2. Memory facts (all PROVEN unless marked)

### 2.1 How 1ST_READ.BIN is loaded
`1ST_READ.BIN` = 2,949,120 B = 1,440 sectors exactly, load address 0x8c010000, so it ends at **0x8c2e0000**.  The BIOS loads the whole directory-record size (IP.BIN has no
size field).  In RAM the file is intact up to 0x8c2b0000 (`ramcmp.py`: mostly 98-100 % per 64 KB block; lower where BSS/data is written, e.g. 54 % at 0x8c1c0000); `0x8c2b0000..0x8c2d0000` is overwritten at boot by the
directory cache (slot 0, 0x20000 B: 13 directory tables, heap blocks `{size,0xfeedfeed,prev,next}` from 0x8c2b0000), `0x8c2d0000..0x8c2e0000` by the first overlay
(slot 1, 0% match).  The last 262,144 B of the file (file offset 0x290000 = address 0x8c2a0000 up to 0x8c2e0000) are a **repeating 64-byte filler** (4,096 repeats, `bsscan2.py`; `31 31 09 12 43 53 13 90 ...`).

### 2.2 crt0 (FUN_8c017160, `crt0.py`)
```
zero-fill words  [0x8c16f800, 0x8c299400)      zero-fill bytes [0x8c193c30, 0x8c1fc180)      (copy loops are empty: src==dst range)
section table 0x8c10dbdc: 8c010000 8c010060 8c010060 8c010080 8c134b24 8c13ba60 8c13bae0 x4 8c193c30 8c1f9fc0 8c1f9fc0 8c1fc180 8c2e0000 x3
pool table    0x8c016b68: 8c017100 8c017120 x5 8c16f800 8c193c30 8c239000 8c299400 8c2e0000 x4
```
BSS ends at 0x8c299400.  Boot function `FUN_8c15ffcc` additionally zero-fills `[0x8c227000,0x8c239000)` (literals 0x8c16001c/20).

### 2.3 Slot map (PROVEN: slot table 0x8c16bf9c, descriptors in the dump)
Slots: `0x8c2b0000/0x20000` (dir cache), then 1 MB slots 0x8c2d0000, 3d, 4d, 5d, 6d, 7d, 8d, 9d, `0x8cad0000/0x90000`, `0x8cb60000/0x40000` (HELP), `0x8cba0000/0x1bc000` (FACEMDUL)
up to 0x8cd5c000 (FONT).  FLOW2..FLOW11 (12,211 B stubs) occupy the base of slots 0x8c3d0000 .. 0x8cba0000, so every slot is used by *some* overlay.

### 2.4 Usable shared storage (the "bank regions")
| name | RAM address | file / offset | bytes | evidence | risk |
|---|---|---|---|---|---|
| `tail` | 0x8c299400..0x8c2b0000 | 1ST_READ.BIN +0x289400 | **93,184** (27,648 zero + 65,536 filler) | after crt0's BSS end, before slot 0; zero/filler in file (`crt0.py`); identical to the file in all 4 dumps (`bsscan2.py`: filler identical, highest touched byte below it 0x8c2992bf); no real literal refs (`litscan.py`: hits in this range are words inside compressed/SJIS/offset-table data: ABROAD/EVENT/SEARCH 0x8c2a6de0 sits in a shared random blob, OFFICE 0x8c2a7ba9 inside Shift-JIS text, GAME 0x172df0.. is a monotone table 0x8c1bc2b4..0x8c33635c) | **lowest** |
| `gap1` | 0x8c13bb80..0x8c159000 | 1ST_READ.BIN +0x12bb80 | **119,936** (the first 0x80 bytes of the 120,096-byte hole are kept for the hook cave) | zero hole between `.text` end (section table 0x8c13bae0) and the 0x8c159000 jump table; zero in the file, zero in all 4 dumps; the only literal refs are the 4 section-table words equal to 0x8c13bae0 (`zeroruns.py`); below crt0's BSS | low (a GBR-relative variable access cannot be excluded statically) |
| `gap2` | 0x8c1196a0..0x8c11cafa | +0x1096a0 | **13,402** (13,466 - 0x40) | zero hole, zero in all dumps; literal pool word 0x8c11cb04 points near its end -> last 0x40 bytes kept | medium |
| `gap3` | 0x8c1289e8..0x8c12cae5 | +0x1189e8 | **16,637** (16,701 - 0x40) | same; pool word 0x8c12cb24 | medium |
| `font` | 0x8cdfdf1c..0x8ce02000 | root FONT.BIN +663,324 | **16,612** | font init reads only the 4 header words (docs/font.md); zero in RAM before the load in all dumps, no refs (`gaps.py`); FONT limit 679,936 = next load SHTEX0.ZAR @0x8ce02000 | low-medium (font may grow; bank is placed behind the final font size: `make_regions(['font'], font_size=...)`) |
| total | | | **259,771** | | |

### 2.5 Candidate free areas that were checked and REJECTED
| area | looked free because | rejected because (script) |
|---|---|---|
| 0x8c239000..0x8c299000 (384 KB) | zero in 4 dumps beyond 0x8c23d000 | inside crt0 BSS; pool table lists [0x8c239000,0x8c299400); first pages hold float vertex/matrix data (`0x4303c50f 0x42f802fc 0x3ea1e5a3 0x3f000000`); Ninja matrix init `FUN_8c15e1b0` passes 0x8c239000 (size 0x1000) and 0x8c299000 to the 3D library |
| 0x8ce68000..0x8ce9a000 | zero in 4 dumps | `hiscan.py`: 4 buffer bases with many literal refs: 0x8ce68000 (13 refs/3 sources), 0x8ce78000 (36/13), 0x8ce88000 (18/9), 0x8ce98000 (24/13) |
| 0x8ce4c000..0x8ce5c000 (after BAR.TBD) | zero gap | 0x8ce4c000 is referenced (100 literal words into the gap) |
| 0x8cd40000..0x8cd5c000 | 114,609 of 114,688 B zero | 159 literal refs (0x8cd40000, 0x8cd5139f...); live3 dump 77 % non-zero at 0x8cd30000; it is FACEMDUL's arena |
| 0x8c9d0000..0x8cac0000, 0x8c660000..0x8c6d0000 | zero in all 4 dumps | slots managed by the overlay allocator; FLOW8/FLOW9/FLOW5 etc. load there; N_ENTRY's arena covers slot 8 |
| 0x8c260000..0x8c2a0000 | zero in all dumps | crt0 BSS |
| after the end of 1ST_READ (>= 0x8c2e0000) | "enlarge the executable" | slots 0x8c2d0000.. are overwritten by the first overlay load; growth would also move 1ST_READ (last file on the disc, 150 free sectors behind it) - see route (c) |

### 2.6 Loader facts for the hook route
* `FUN_8c15eeb8(name, dir, dest)` (0x8c15eeb8..0x8c15eed1, Ghidra listing in s4) = `FUN_8c15eede(name, dir, dest, 0)` returning 0 (ok) / -1; `dir` 0 = root, else a directory record pointer
  from the table at 0x8c16c104 (13 entries: SOUND FLOW_PRG ETC_DATA GAME BCAST FACE TRAINING NEWS EVENT GAME2 MASCOT SSONG ATFIRST; `FUN_8c15f63c(i)`).
* `FUN_8c15eede` reads `(len+0x7ff)>>11` sectors to `dest`.  With an explicit `dest` it calls `FUN_8c15f0f4(dest, len, name)`, which accepts a slot base (table at 0x8c16bf9c) or any
  address whose header words are not `deaddead`/(`feedfeed` with a smaller block); it only complains ("illegal memory for fileread") for a *free* heap block or a too-small used block.
  An address inside the in-file regions passes the check (their `dest-0x1c` words are zero / filler).

## 3. Demand model and route comparison

### 3.1 How much text, how much must go to a bank (`dbstats2.py`, `demand.py`, `dedupe.py`, saved `*.txt`)
* 119,946 overlay records, 2,749,078 B of Japanese text (encode_text, incl. NUL); 24,943 globally unique Japanese strings (1,321,557 B).
* Relocatable (has pointers, not a stride table, no interior pointers): 81,986 strings / 2,243,846 B; **non-relocatable 37,960 / 505,232 B** (37,885 are orphans).
* English = r x Japanese bytes.  Overflow of relocatable strings (must go to a bank), no dedupe / dedupe by identical Japanese:

| r | strings to bank | bytes (no dedupe) | bytes (dedupe by ja) | non-relocatable strings that overflow (cannot be banked) |
|---|---|---|---|---|
| 1.00 | 0 | 0 | 0 | 0 |
| 1.25 | 66,053 | 2,665,485 | 1,584,835 | 7,193 |
| 1.50 | 76,577 | 3,299,549 | 1,909,468 | 30,835 |
| 1.75 | 78,247 | 3,865,526 | 2,226,897 | 31,182 |
| 2.00 | 81,928 | 4,405,110 | 2,538,519 | 36,400 |

A single bank for everything would be 1.9..2.5 MB: no RAM block that size exists (s2.5), so the bank must be **tiered** (shared RAM-resident part + per-overlay tails).
* Duplicates are the lever (r=1.5): strings present in >= 2 overlays: 5,325 unique (335,663 B) serve 57,940 overflow strings (75.7 %); >= 3: 2,713 (80,763 B) serve 68.8 %; >= 5: 1,673 (32,918 B) serve 63.0 %;
  >= 20: 1,303 (14,225 B) serve 56.5 %.

### 3.2 Hard limit: non-relocatable strings
At r=1.5 there are 26,576 overflow strings (stress run) with no pointer to rewrite or in an index-addressed table; the bank cannot help them (they would need the
engine-side fixes of docs/text-engine.md, or shorter English).  `tools/textdb.py` marks them (`orphan`, `stride-table(in-place only)`, `interior-ptrs`).

### 3.3 Routes
Capacity numbers: bytes usable by English.  "Code" = new SH-4 code.

| route | required changes | capacity | risk | discbuild / build_patch |
|---|---|---|---|---|
| **R0 in-file regions** (new; recommended first) - bytes in `1ST_READ.BIN` padding + FONT.BIN tail, loaded by the BIOS / the existing font load | none in code; overlay pointer words rewritten | **259,771 B** (s2.4) | see s2.4; UNKNOWN: runtime stores into the gaps (soak test T1) | `patches['/1ST_READ.BIN']` same size (in place), `patches['/FONT.BIN']` padded to a sector multiple <= 679,936.  `bankbuild.apply_regions()` |
| **(a) boot hook + donor file** | 1ST_READ.BIN: 1 literal + 128-byte cave (s4); donor file replaced by the bank | limited by a free RAM block (none proven, s2.5); donor file size is free (discbuild relocates) | hook is a proven-minimal 4+128 byte patch, single call site; donor = `/NAMIHEI.DRV` (32,512 B, SDRV driver format, **named nowhere**: not in 1ST_READ, any of 114 overlays, 2_DP.BIN, MANATEE.DRV, SG_DPLDR.BIN, `donor.py`); other root candidates `/MAIGO.BIN` (named only by 2_DP), `/SG_DPLDR.BIN`+`/MANATEE.DRV` (named by 1ST_READ: loaded) - do not use; `/0GDTEX.PVR` (not named but BIOS boot art, do not touch); DP* directories belong to the browser 2_DP (MESSAGE.INI is translated: keep) | `build_disc({'/NAMIHEI.DRV': bank_bytes, '/1ST_READ.BIN': patched})`; the name cannot be changed without a new file, so the cave carries `"NAMIHEI.DRV"` |
| **(b) piggy-back on an early file** | none for FONT.BIN (R0); SHTEX0/BAR/SECFTEX are archives (ZSARC / TBD) | FONT.BIN tail 16,612; SHTEX0.ZAR gap 14,336 (after sector round-up) but a ZAR parser may read trailing bytes as a member header; BAR.TBD gap 74,024 but 0x8ce4c000.. is a referenced buffer (rejected); SECFTEX0.ZAR 2,514 | only FONT.BIN is safe by construction | font build in `build_patch.py` already limits to 679,936 |
| **(c) enlarge 1ST_READ.BIN** | none | **0 useful**: RAM after 0x8c2e0000 is slot 1+ (overwritten by the first overlay); the file already extends 0x30000 B *into* slots 0/1 (dir cache 0x8c2b0000.., first overlay 0x8c2d0000..).  Useful bytes are only the 93,184 B `tail` that already exist. | growing the file moves it (it is the last file, 150 free sectors behind it, then past the GD-R end) | not worth it |
| **(d) per-overlay tail** (`_end` raised) | `ENDVAR` u32 of the overlay += bank bytes; BSS overlays: BSS written as explicit zeros so the bank sits behind `_end` | per overlay: heap lower bound behind `_end` (s6); e.g. MEETING 972,592, NEWS 462,512, TRAINING 187,208, DRAFT 518,576, HELP 58,816 | INFERRED (loader formulas); the arena shrinks by the bank; BSS overlays start with zeroed BSS (stale RAM before) | `bankbuild.overlay_tail_for/apply_overlay_tail`; build_patch `--append-safe` exists for no-BSS only, extend it to BSS (zero fill) |
| (e) compress text, expand at overlay load | engine work (game has `-bz--` decoder FUN_8c15a9f4) | ~2x | big | not analysed |

**Recommendation**: R0 (shared, deduplicated, 259 KB) + (d) per overlay for the long prose.  Keep (a) as a ready, verified mechanism (it is the only way to add
capacity beyond R0 for *shared* strings once a free block is demonstrated, e.g. by shrinking a data buffer) but do not rely on it.

## 4. The boot hook (route a): exact patch + Ghidra-verified listing

Boot code (original, `FUN_8c15ffcc`, Ghidra decompile/disassembly, `d1.txt`):
```
8c160258  mov.l 0x8c160340,r4     ; "FONT.BIN"            8c160268 .. 8c160284: three more loads (SHTEX0.ZAR @8ce02000, BAR.TBD @8ce2c000, SECFTEX0.ZAR @8ce5c000; r5 = FUN_8c15f63c(2))
8c160288  mov.l 0x8c160360,r3     ; = &FUN_8c163984     (empty function: rts; nop)
8c16028a  jsr @r3
8c16028c  _nop
8c16028e  mov.l 0x8c160364,r2     ; FUN_8c15e72c = font init
```
`hookrefs.py`: exactly **one** `mov.l` loads the literal 0x8c160360 (at 0x8c160288) and the only aligned word equal to 0x8c163984 is that literal, so redirecting it changes one call site.
`FUN_8c163984` is 4 bytes (`0b00 0900`), its callers: 0x8c16028a only.

Patch (2 hunks, `hook_patches.json`, produced by `hookpatch.py`):
| file offset | addr | old | new |
|---|---|---|---|
| 0x150360 | 0x8c160360 | `8439168c` (0x8c163984) | `00bb138c` (0x8c13bb00) |
| 0x12bb00 | 0x8c13bb00 | 128 zero bytes | `224f 04d4 04d6 05d3 0b43 00e5 264f 0b00 0900 0000 | 20bb138c 00c0138c b8ee158c | "NAMIHEI.DRV\0" | zeros` |

Ghidra disassembly of the **patched** binary (imported as `1ST_READ_HOOK.BIN`, `ghidra_hook_listing.txt`; bytes as in the file, little endian):
```
8c160288  d335  mov.l 0x8c160360,r3          ; unchanged (word; bytes 35 d3)
8c16028a  430b  jsr @r3                      ; unchanged
8c160360  .long 0x8c13bb00                     ; literal now points at the cave
8c13bb00  4f22  sts.l PR,@-r15
8c13bb02  d404  mov.l 0x8c13bb14,r4            ; r4 = &"NAMIHEI.DRV"
8c13bb04  d604  mov.l 0x8c13bb18,r6            ; r6 = dest
8c13bb06  d305  mov.l 0x8c13bb1c,r3            ; r3 = FUN_8c15eeb8
8c13bb08  430b  jsr @r3
8c13bb0a  e500  _mov #0x0,r5                   ; dir = 0 (root)
8c13bb0c  4f26  lds.l @r15+,PR
8c13bb0e  000b  rts
8c13bb10  0009  _nop
8c13bb14  .long 0x8c13bb20   8c13bb18 .long 0x8c13c000 (dest, parameter)   8c13bb1c .long 0x8c15eeb8
8c13bb20  .string "NAMIHEI.DRV"
```
Ghidra's disassembly of the unmodified callee confirms the wrapper: `8c15eeb8 sts.l PR,@-r15; bsr 0x8c15eede; _mov #0,r7; mov r0,r4; tst r4,r4; bf; ...; rts` (returns 0 / -1).
r13/r14/r15 are not changed (r14 = FUN_8c15eeb8 of the caller is not used after this point); the cave sits in the zero hole (checked: 128 bytes zero).  The default `dest` 0x8c13c000 (inside
`gap1`) is only meant for the dynamic hook test (T2): the donor file is read into the hole, which proves the mechanism with no free-RAM assumption.  For a real bank pass `--dest`.

## 5. Bank builder (`tools/re/capacity/bank/bankbuild.py`)

Input entries `(source, string_offset, english)`; uses `textdb.extract_image` to find the string, its pointer words (`refs`) and `max_bytes`; rejects non-relocatable ones with the reason.
* dedupe: identical byte strings once; a string that is a NUL-terminated suffix of another shares it (`pointer = root + delta`; rare with real text: 136-207 aliases of 20,631 at the stress runs);
* placement: shared strings (most overlays first, then longest) into the shared regions in preference order `tail, gap1, gap2, gap3, font`; strings of one overlay may also use a private
  `ovl_tail` region (`overlay_tail_for`); nothing straddles regions; `--align N` (default 1; odd addresses are UNKNOWN, T6);
* outputs: region images, `patches` (`{source, off, old, new}` pointer words, `old` is checked on apply), `wipes` (old Japanese slots that become free for in-place reuse), `unplaced`, stats;
* `apply_regions()` writes regions into `1ST_READ.BIN` / `FONT.BIN` (asserts the destination is zero/filler, FONT padded to a sector), `apply_pointer_patches()`, `apply_overlay_tail()` (extends the image,
  raises the ENDVAR word), `RamView` reads strings back at absolute addresses for verification.

Self-tests (`selftest.txt`):
* `--selftest`: 5 overlays (CHALDANI, CLUBEDIT, N_ENTRY, SCDRF, EVENT), 3,513 overflow strings (synthetic English, 1.5x), 22 non-relocatable rejected, 3,491 resolved -> **3,497 strings read back from the patched RAM view == expected, 0 bad**,
  3,814 pointer words, every overlay differs from the original only at pointer words, `1ST_READ.BIN` size unchanged, changed bytes (227,960) <= bank bytes written (231,075).
* `--selftest-tail`: CHALDANI (no BSS): 178 strings, 7,494 B, file 55,392 -> 62,888, `_end` 0x8c4dd860 -> 0x8c4df5a8 = base + new length; MEETING (BSS 250,262): 131,072 B tail, file 874,298 -> 1,255,632, `_end` 0x8c3e28d0 -> 0x8c4028d0; strings read back from the new images; ENDVAR word checked.
* `--stress R` (all 116 parseable overlays, synthetic English from real Japanese lengths, same Japanese -> same English), shared regions 259,771 B (`stress_all.txt`):

| r | overflow strings | non-reloc. | relocatable | served by shared bank | bytes served | left for route (d) |
|---|---|---|---|---|---|---|
| 1.25 | 63,311 | 6,275 | 57,036 | 37,279 (65.4 %) | 983,051 of 2,577,978 (38.1 %) | 1.64 MB in 87 overlays |
| 1.50 | 101,568 | 26,576 | 74,992 | 52,853 (70.5 %) | 1,229,699 of 3,268,723 (37.6 %) | 2.21 MB in 89 overlays: MEETING 558,565, NEWS 436,831, DRAFT 155,013, TRAINING 154,686, SCDRF 106,176, EVENT 86,787 |
| 2.00 | 116,207 | 35,337 | 80,870 | 57,234 (70.8 %) | 1,492,042 of 4,382,800 (34.0 %) | 3.30 MB; HELP x2 ~160 KB each vs 58,816 B heap bound |

(the placement heuristic is greedy by number of overlays then length; a value-density order would serve somewhat more strings per byte.)

How `build_patch.py` would use it: after `textdb.insert_image` for an overlay, collect `rep.failed` entries whose reason is "does not fit"/"no free space" and are relocatable, feed them with their
`en` to `build_bank(entries, regions)`, run `apply_pointer_patches` on that overlay's bytes, then `apply_regions` on the (ptrblob-patched) `1ST_READ.BIN` and the built `FONT.BIN` (both copies, same bytes);
for leftovers call `overlay_tail_for/apply_overlay_tail` (route d).  The pointer words in `s.refs` are those of the original image; `insert_image` only rewrites pointers of strings it moved, so
banked strings still hold `base + s.off` (`old` is verified).

## 6. Route (d) budget (INFERRED, `overlaycap.txt`, `heapwalk.py`)
Lower-bound heap behind `_end` = end of the slot containing `_end` minus `_end`; real arena is larger (it spans the free slots behind, s1).  Examples: MEETING 972,592; NEWS 462,512 (BSS 1,286,758 B -> file would
grow by that much as zeros); DRAFT 518,576; TRAINING 187,208; SCDRF 592,363; EVENT 553,404; HELP (resident, slot 0x40000 + FACEMDUL behind) **58,816** and needs ~165 KB at r=1.5 -> HELP needs
its own plan (JP region 109,945 B + 58,816 B tail = 168,761 B in total is barely enough); SPF_READ 24,860 (BSS 311 KB).
Measured arena use (live dumps, `heapwalk.py`): N_ENTRY arena used 233,632 B (46 blocks) free 743,680 B; the CLUBEDIT arena spans slots 2-6.  Heap peak per overlay is UNKNOWN (T5).

## 7. Risks (ordered)
1. **Runtime writes into the in-file gaps / filler** (R0): excluded for `tail` by structure (outside BSS, outside slots) and by the 4 dumps, not by execution of a match, training, news, save/load.  T1 settles it.
2. The pointer redirect assumes each overlay reads strings by absolute pointer with byte loads from any address (the live proof of 2026-11-10 wrote English *inside* overlay RAM; a pointer to text outside the overlay image has not been rendered yet).  T6.
3. Odd (unaligned) string addresses (`--align 1`).  T6.
4. Route (d): the loader formulas (INFERRED) and heap shrink; BSS overlays now begin with zeroed BSS.  T4/T5.
5. 26 % of overflow strings are not relocatable (s3.2).
6. GBR-relative variable access into the text gaps: 79 `ldc`-like halfwords in 1ST_READ (not decoded, many are data); only the soak test closes it.

## 8. Dynamic tests for the orchestrator (Lua bridge `tools/emu/live.lua`: `poke(addr,str)`, `peek(addr,n)`, `dump(addr,size,file)`, `say`, `frame()`)

**T1 canary soak (R0 regions, decisive).**  `python -I -X utf8 tools/re/capacity/bank/canary.py make --out build/canary` then
`python tools/discbuild.py --out build/out --name canary /1ST_READ.BIN=build/canary/1ST_READ_canary.BIN /FONT.BIN=build/canary/FONT_canary.BIN` (or `build_disc` with the two files).
Boot the .gdi; after the title screen `dump(0x8c000000, 0x1000000, 'c0.bin')`; then visit as many modes as possible (new game, club edit, meeting, training, news, a match incl. replay, save/load,
season roll-over, DreamPassport menu if present) and dump again at each; `python -I -X utf8 tools/re/capacity/bank/canary.py check build/emu/c0.bin` prints per region intact/changed
(changed `tail`/`gap1` bytes disqualify that region; `gap2/gap3/font` are optional).  Pass = 0 changed bytes in all dumps and no crash.  Expected: all intact.
**T2 hook mechanism.**  `python -I -X utf8 tools/re/capacity/bank/hookpatch.py --out build/hook`; replace `/NAMIHEI.DRV` with a 4,096-byte file of repeated `A5` and `/1ST_READ.BIN` with `build/hook/1ST_READ_hook.BIN`; boot; at the title screen
`say(peek(0x8c13c000,16))` must be 16 x `A5`; `peek(0x8c13bb00,16)` shows the cave (`22 4f 04 d4 ...`); a second boot without the donor replaced must still reach the title (hook harmless).  Also dump 0x8c13c000..+0x1000 after a game mode change to see it survives.
**T3 FONT tail.**  `canary.py make --regions font` (FONT_canary.BIN, 679,936 B): boot, check text still renders (glyphs OK), `canary.py check` on a dump: tail intact.
**T4 route (d) append (the open question of docs/text-engine.md s8.1, now also BSS).**  Build (a) CHALDANI no-BSS (+0x1000 B, ENDVAR raised) and (b) MEETING (BSS made explicit zeros + 0x1000 B + ENDVAR raised) with
`bankbuild.apply_overlay_tail`.  Enter the screen, `dump` the slot; expected: ENDVAR-derived first heap header (`{size,0xfeedfeed,..}` or `deaddead`) at `((new_end|0x80000000)&~0x1f)+0x20`, the bank bytes intact at old `_end`, the screen works; leave and re-enter (overlay reloaded) - bank bytes come from the file again.
Negative control: same without raising ENDVAR must show the heap header overwriting the first bank bytes (confirms the formula).
**T5 heap high water.**  For the overlays of the route (d) list (MEETING, NEWS, TRAINING, DRAFT, SCDRF, EVENT, HELP, SPF_READ) run their screens for several minutes, `dump` and run
`python -I -X utf8 tools/re/capacity/bank/heapwalk.py DUMP ENDVAR_VALUE ARENA_END` (arena end = base of the next occupied slot): "used" + "highest used block end" give the real budget.
**T6 pointer / alignment / render.**  `lua_poke.py FLOW_PRG/CLUBEDIT.BIN 0x20c08 0x8c299401 "Hello from the bank."` prints a cmd.lua body (poke text at an ODD address in `tail`, rewrite the 2 pointer words); open the screen with that string:
text must render exactly as the in-slot case.  Repeat with `gap1` (0x8c13bb80) and with a target inside FONT's tail (0x8cdfdf1c).  If an odd address fails, rerun the builder with `--align 4`.
**T7 non-reloc census.**  (static, nothing to run) - the 26 % limit above.
**T8 `ATFIRST/FONT.BIN` use.**  Patch only the ATFIRST copy by one glyph (or the tail marker), boot, enter title + club edit: if nothing changes the ATFIRST copy is never loaded (current evidence: it is not at 0x8cd5c000).

## 9. Files
`tools/sh4asm.py`; `tools/re/capacity/bank/`: `bankbuild.py hookpatch.py hook_patches.json canary.py lua_poke.py heapwalk.py`;
analysis: `ramcmp.py ramcmp2.py rammap.py bsscan.py bsscan2.py litscan.py hiscan.py zeroruns.py gaps.py crt0.py hookrefs.py donor.py fontwhich.py lits.py slots.py dbstats*.py demand.py dedupe.py overlaycap.py`;
saved outputs `*.txt` (`selftest.txt stress_all.txt overlaycap.txt demand.txt dedupe.txt donor.txt gaps.txt zeroruns.txt crt0.txt heapwalk.txt hookrefs.txt ghidra_hook_listing.txt`, Ghidra dumps `d1..d6.txt`);
Ghidra helpers `Dec.java Dis.java DisW.java dec.ps1 dis.ps1 disw.ps1 imp.ps1` (project copy `ghproj_bank`).
