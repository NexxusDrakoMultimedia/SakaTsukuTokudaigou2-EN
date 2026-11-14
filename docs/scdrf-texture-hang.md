# SCDRF / SEARCH texture hang: stale ZSARC member CRC (owner `hsd`, 2026-11-12)

Static analysis plus offline builds only; no emulator was started.  Result: **a definite build defect was found and fixed.**  Every overlay-embedded texture that sits inside a
STORED ZSARC member of its overlay was injected without refreshing that member's CRC16 / header CRC.  The game's ZSARC walker rejects such a member.  This matches the
bisect exactly (the 3 files of `bis_u1` are the only injected tables of SCDRF / SEARCH, and all three sit in stored members).

## 1. The finding

`FLOW_PRG/SCDRF.BIN` and `FLOW_PRG/SEARCH.BIN` do not hold "a texture in a container of its own".  The tables `@2ff64`, `@2c58c`, `@2fcf0` live inside **stored (`-nc--`) ZSARC members**
that are embedded in the overlay image:

| overlay | member (offset) | name | data size | table inside | stored CRC16 | CRC16 of the data in `bis_u1` |
|---|---|---|---|---|---|---|
| SCDRF | 0x2ff38 | `scda.tbd` | 0x2a34 | `@2ff64` | bb66 | 6a46 (STALE) |
| SEARCH | 0x2c55c | `schme1.tbd` | 0x3738 | `@2c58c` (2 records, #0 injected) | 77f3 | dfd0 (STALE) |
| SEARCH | 0x2fcc4 | `scda.tbd` | 0x2a34 | `@2fcf0` | bb66 | 6a46 (STALE) |

(`tools/re/hsd_zs.py`, `tools/re/hsd_scan.py`.)  `texinject.inject` handled `@hex#i` ids as a bare table in a blob (`tbd-embedded`): it re-encoded the record in place and never looked at the
member around it.  The member header (24 byte fixed part + extension chain) holds the CRC16 of the member data at +0x13 and a header CRC (extension type 0).  The game checks both (`docs/texture-injection.md`
3.2, `tools/re/ghidra/d2.txt`: FUN_8c15a45a / FUN_8c15a1cc, strings "crc_mismatch", "CRC_mismatch %d", "exFileCRC_mismatch"): on a mismatch it calls FUN_8c159f78 (a logging printf wrapper,
disassembled here: it forwards to 0x8c011084 and returns) and the walker **returns NULL**.  Other members of the same overlays (`bis_e`, no
texture) are valid: 1 member in SCDRF and 4 in SEARCH, all OK (`hsd_scan.py` on the bis_e files).

**Call chain and NULL handling (skeptic pass, PROVEN by disassembly and by running the game's own walker, section 5a).**  SCDRF.BIN (base 0x8c2d0000) at 0x1108 calls the 1ST_READ jump-table slot 0x8c159000+0x3d4 (-> 0x8c15a87c)
with `r4 = 0, r5 = 0x8c2fff38` (the literal at file 0x120c = the member HEADER address).  0x8c15a87c is a 5-instruction wrapper that calls `FUN_8c15a45a(0, member, 0, 2)`: mode `param_4 = 2` = "first member, stored, in place": header
size and header CRC (FUN_8c15a1cc), `exFilesize`, data CRC16 ("CRC_mismatch"), and it **returns a pointer to the member data (= the TBD table, member+0x2c / +0x30), or NULL on any mismatch**.  SCDRF stores that result and passes it
as `r4` to jump-table slot 0x38c (-> 0x8c15a942, the texture-list builder), whose first action is `mov.l @r4,r2` (the table's record count) and a malloc of count * 12 bytes.  With NULL that reads address 0 (BIOS area, not a table); the builder then either fails (returns -1 without writing its output slot, which the caller ignores and later stores as the texture list: SCDRF 0x1134..0x1138 store the stack word to 0x8c33b780) or
builds a list of garbage size.  So a stale member does not "skip" the table, it hands the screen an uninitialised / garbage texture list.  That a garbage list causes the silent empty-message-window hang was not traced further (UNVERIFIED), but the mechanism is no longer a guess.  SEARCH.BIN (base 0x8c4d0000) refers to `schme1.tbd` (0x8c4fc55c) from its literal at 0x18a0 in
the same pattern (a loop over slot 0x38c at 0x1740..0x1880).  **No literal for `scda.tbd` @0x2fcc4 (0x8c4ffcc4 / 0x8c4ffcf0) was found in SEARCH.BIN**, so it may be reached indirectly or not used at all; `bis_v3` alone
may therefore not hang even if the theory is right.  (SCDRF's other literal hit, 0x8c302f38 at 0x9ea0, is a coincidence of the base search.)

The same defect hit the other overlays whose tables are in stored members: NEWCON (`newcon.tbd` @0x293c0, CRC b7bb -> data 6043) and RECON (`selb.tbd` @0x2572c, 16fa -> a91b).  ESTABLIS, LOADBAR and
YOUTH have no ZSARC member around their tables and were never affected.  That makes 5 broken members of 7 overlay-embedded texture files in `bis_s1` and the full builds (prop7, prop8): SCDRF, SEARCH (2), NEWCON, RECON.
Every texture in a proper container kind (plain PVR, ZSARC member by name, `name#i`, whole-file TBD, TBD tail, ESTABLIS.ARC, FACE data) was fine: `zs_replace_member` refreshes the CRC.

## 2. What was checked and found NOT to be the cause

1. **Bytes written (bis_u1 vs bis_e, read back from the disc tracks, `tools/re/hsd_diff.py`; re-derived independently with `hsd_sk_diff.py`: of the 1,215 files exactly SCDRF.BIN (109 exact ranges, 10,610 bytes) and SEARCH.BIN (196 ranges, 20,624 bytes) differ, same LBAs, same sizes)**: SCDRF.BIN differs within 0x2ff93..0x30c81 and 0x30c8a..0x32993 (spans of 10,743 bytes = the re-encoded bz stream of record #0, 0x2ff78 on);
SEARCH.BIN in 0x2c5b0..0x2ed27, 0x2fd1f..0x30a0d, 0x30a16..0x3271f.  Nothing else differs from bis_e in these two files: no text pool, pointer word, club / money / font patch overlaps the ranges.
Text and the proportional font patch do not touch the member data (all 5 members are CRC-valid in bis_e).
2. **Header / structure**: the table words are byte-identical to the original in all three (SCDRF `01000000 00010080 80008000 14000000 3ef00a54`: count 1, pixfmt 0 ARGB1555, datatype 1 twiddled, bit 31 = `-bz--`, 128x128, offset 0x14, stamp 0x540af03e).
SEARCH `@2c58c` has 2 records (#0 ARGB1555 128x128, #1 ARGB4444 128x128): #0 injected, #1 untouched and decoded identical.  No GBIX / PVRT / size field exists for these records (the table record is the header), so there is no VQ, mipmap, stride or
alpha-format difference possible: the payload is a plain 32,768 byte twiddled 1555 image, 16-bit word for word the same length, only the bz stream differs (4,171 / 6,248 of 16,384 words differ from the original in the repainted areas).
The texture does end at the slot end; the bytes behind the stream are zero fill inside the member (the member end is at 0x32998 for SCDRF).  The "texture" is not code, a sprite table or an animation list: what follows the member
(0x329a0 on) is untouched UV / sprite coordinate data.
3. **Compression**: the game's own bz decoder run in `sh4sim` (`tools/re/hng_texdec.py`, section 2.1 of `docs/hang-investigation.md`) reproduces the intended data; `texinject.game_load_tbd` agrees.  The stream is fine, only the CRC of the enclosing member is wrong.
4. **Loader**: the overlay is read as a plain file; no checksum, decompression or relocation of the overlay image is involved.  The only content-dependent check is the ZSARC walker's CRC on the member it walks.  The hunt for `scda.tbd` / `schme1.tbd` strings in the code found none:
the code refers to the archive by address (SCDRF pointer to the member header 0x2ff38 at file 0x120c, base 0x8c2d0000) and hands it to the walker in mode 2 (see section 1), in which the data CRC16 and the header CRC are verified.
5. The bis_u1 diff of text-side bytes against the original: only 3 + 2 more ranges than bis_e, all texture.

## 3. Hypotheses, ranked

| # | hypothesis | evidence | status |
|---|---|---|---|
| H1 | stale member CRC16 + header CRC after in-place table edit in a stored ZSARC member | all 3 hanging files have it, and nothing else differs; the loader checks it (PROVEN in the decompilation); fixed disc has valid CRCs | **definite defect, fixed** |
| H2 | bz stream wrong / too long | decoded in the game's decoder: identical | excluded |
| H3 | header words differ (format, size, stamp) | byte-identical | excluded |
| H4 | the text / font stages touch the same bytes | diff ranges disjoint; members valid in bis_e | excluded |
| H5 | other overlays still wrong after the fix (NEWCON, RECON were broken too) | fixed by the same code; `hsd_verify_all.py` | fixed |
| H6 | something else on the second Event screen (not textures) | bis_c / bis_e do not hang, so the texture class is the trigger | only if hsd_u1fix still hangs |

## 4. The fix (this pass edited tools, as the rules say it must be mentioned)

* `tools/texinject.py`: new `enclosing_stored_member`, `refresh_stored_member`, `stale_stored_members`.  `inject()` for a `tbd` (`@hex#i`) id of kind `embedded` now rewrites the data CRC16 and the header CRC of the stored member
around the table (the header is first rebuilt with the old CRC and must reproduce the original bytes, otherwise `TexInjectError`; only the two CRC fields change, nothing else).  `info['member_crc_refreshed']` names the member.
* `tools/build_patch.py` `apply_textures`: after the textures of a container are applied, any stored member that was valid before and is stale afterwards is reported as a problem (the build with `--strict` stops).
* `tools/test_texinject.py`: section G (SCDRF, SEARCH x2, NEWCON, RECON): member parses, header CRC valid, data CRC16 matches, only the record and the member header bytes changed, no-op still byte identical, the guard flags an un-refreshed edit.
The existing ABROAD sample of section B/C now allows the 4 member-CRC bytes (ABROAD's table is also in a stored member).  Result: `310 checks passed, 0 failed` (`--quick --no-plan`).
* No texture file under `translation/textures` was changed.

## 5. Offline verification done

* `tools/re/hsd_verify_all.py`: all 9 `@hex#i` textures of the repository applied to the extracted overlays: 0 stale members (NEWCON, RECON, SCDRF, SEARCH x2 refreshed; ESTABLIS, LOADBAR, YOUTH have no member).
* New trial disc **`build/trial/hsd_u1fix`** (log `build/trial/hsd_u1fix.log`; same flags and textures dir `build/int/tsub/u1` as `bis_u1`: standard flags, money and guard OFF, the 3 textures; 0 failed, 0 skipped, V7 / V9 OK, digest 9911788b77).
Read back from the disc tracks (`hsd_diff.py`, `hsd_scan.py`): SCDRF.BIN and SEARCH.BIN differ from bis_u1 in exactly 2 + 2 bytes per member (data CRC16 at member+0x13 and header CRC at the end of the extension chain, member+0x27 for the `scda.tbd` members and member+0x29 for `schme1.tbd`, of each of the 3 members: 0x2ff4b / 0x2ff5f; 0x2c56f / 0x2c585; 0x2fcd7 / 0x2fceb; re-checked with `hsd_sk_diff.py`: 12 bytes in all, no other file differs),
the texture streams are identical to bis_u1, all members CRC-valid (SCDRF 1 of 1, SEARCH 4 of 4).

## 5a. Independent verification (skeptic pass, `tools/re/hsd_sk_*.py`, nothing booted)

* **The game's own walker, run in `tools/sh4sim.py`** (`hsd_sk_walk.py`: 1ST_READ.BIN loaded, jump-table slot 0x3d4 = 0x8c15a87c called with r4 = 0, r5 = the member as read back from the disc track, r6 = 0; only the allocator and the logging printf are stubbed).
Return value r0 (pointer = member data, NULL = rejected):

| member | original | bis_e | bis_u1 | bis_v1 | bis_v2 | bis_v3 | hsd_u1fix | prop8 | hsk_full1 |
|---|---|---|---|---|---|---|---|---|---|
| SCDRF `scda.tbd` @2ff38 | ptr | ptr | **NULL** | **NULL** | - | - | ptr | **NULL** | ptr |
| SEARCH `schme1.tbd` @2c55c | - | ptr | **NULL** | - | **NULL** | ptr | ptr | **NULL** | ptr |
| SEARCH `scda.tbd` @2fcc4 | - | ptr | **NULL** | - | ptr | **NULL** | ptr | **NULL** | ptr |
| NEWCON `newcon.tbd` @293c0 | - | - | - | - | - | - | - | **NULL** | ptr |
| RECON `selb.tbd` @2572c | - | - | - | - | - | - | - | **NULL** | ptr |

  The walker rejects exactly the stale members and accepts every member of the fixed discs; the logged-message count is 1 on a rejection and 0 otherwise.  This turns "the loader checks the CRC" from a reading of the decompilation into an observed result.
* **Whole-disc scan** (`hsd_sk_allmem.py`: every ZSARC member of every method valid in the original file, compared at the same offset in the disc's file; header CRC and decoded-data CRC16): `bis_e` (text only) 0 stale, `bis_c` 0, `prop8` exactly **5** (NEWCON, RECON,
SCDRF, SEARCH x2), `fix_v1` 0, `hsk_full1` 0.  The only file whose size differs from the original in these discs is `DPETC/MESSAGE.INI` (a plain INI, no ZSARC).  So no other container kind is affected, text patching does not break members, and no further member class is waiting behind this one.
* **The fix is surgical**: `bis_u1` vs `hsd_u1fix` = 12 bytes in 6 CRC fields; a full standard-flags build with the fixed injector (`build/trial/hsk_full1`, `--repack on --share dup --append-safe --proportional-font on --strict`, money / club options left at their
defaults, 85 texture notes, verify_disc OK, V7 OK) differs from `prop8` in exactly 4 files and 20 bytes (NEWCON 4, RECON 4, SCDRF 4, SEARCH 8: the 5 members' two CRC fields each, nothing else).  `test_texinject.py --quick --no-plan`: 310 passed, 0 failed (re-run).
* **Not verifiable offline**: that the garbage texture list produces the silent hang (section 1), and which of the three single-file discs hangs: `bis_v1` and `bis_v2` should (their member is referenced by a literal), `bis_v3` may not (no code reference to `scda.tbd` @2fcc4 found).
`bis_u2` (DRAFT/DRAFTK, NEWCON, RECON) also carries two stale members; whether the user's run of it hung says only whether NEWCON / RECON are reached before the second Event screen.

## 6. What to boot

1. `build/trial/hsd_u1fix/hsd_u1fix.gdi`: expected NOT to hang (same 3 textures as bis_u1).
2. The single-file discs `bis_v1`, `bis_v2`, `bis_v3` were built BEFORE the fix: `bis_v1` and `bis_v2` expected to hang (each holds one stale, code-referenced member); `bis_v3` may hang or not (see 5a).  If `bis_v1` or `bis_v2` boots, the hypothesis is incomplete for that file.
3. `build/trial/hsk_full1/hsk_full1.gdi` is a complete textured disc from the current tree with the fix (all 5 members valid); it is the real test.  A hang there with a good `hsd_u1fix` would mean a second, unrelated cause (H6).  Then the earlier decision tree (`docs/hang-investigation.md` section 5) is moot.
Every earlier disc with textures (prop7, prop8, bis_h, bis_s*, bis_u*, bis_v*) carries stale CRCs in SCDRF, SEARCH, NEWCON and RECON and must be rebuilt.

## 7. Helper scripts (prefix `hsd`, read-only on the project, scratch output in `build/hsd/`)

`hsd_diff.py` (original vs two discs, differing ranges; extracts the file copies to `build/hsd/`), `hsd_hex.py`, `hsd_zs.py` (ZSARC walk of a member with CRC check), `hsd_scan.py` (all stored / compressed member headers in an image and their CRC state),
`hsd_find.py` (byte / word search), `hsd_texcmp.py` (table header and decoded payload original vs new), `hsd_verify_all.py` (every `@` texture of the repository against the current injector).
Skeptic pass: `hsd_sk_diff.py` (every differing file and exact byte ranges between two trial discs), `hsd_sk_walk.py` (the game's ZSARC walker in the simulator on a member of a disc), `hsd_sk_allmem.py` (every stale ZSARC member of a disc vs the original), `hsd_sk_ptr.py` (pointer-literal search for an
offset under any base), `hsd_sk_slot.py` (1ST_READ jump-table slot lookup).
