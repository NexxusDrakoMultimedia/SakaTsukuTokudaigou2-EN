# Texture injection: putting a repainted texture back (tools/texinject.py)

Scope: the INJECT half of image translation. A texture whose Japanese is baked into the art is decoded, repainted with English,
re-encoded in the SAME pixel format and size (not part of this document, see section 9 for what is prepared) and then put back
into the container it came from. This document says exactly what the game's loader accepts, what it ignores, and what
`tools/texinject.py` does about it.

Status words: **PROVEN** = read in the decompiled/disassembled loader of `1ST_READ.BIN` (Ghidra 12.2 headless, SuperH4:LE:32, base
0x8c010000) or measured by a script over all of `extracted/`; **INFERRED** = follows from code/data but was not traced to the end or
not run; **UNKNOWN** = not investigated. No emulator was started (rule of this task): everything about real in-game behaviour is
static analysis, and the loader checks are re-implemented in `texinject.game_walk_zsarc` / `game_load_tbd`, not executed by the game.

Evidence index: `tools/re/texinject/README.txt` (scripts, Ghidra outputs `t1..t8.txt`, `d_tbd.txt`, reused `tools/re/ghidra/d2.txt`, `d3.txt`).
Self-test: `python -I -X utf8 tools/test_texinject.py` (273 checks, ~30 s). Disc sweep: `tools/re/texinject/sweep.py`.

## 0. Short answers

| question | answer |
|---|---|
| Where does a texture live? | six places (section 1): plain `.PVR` file, `.pvr` member of a ZSARC container, TBD bundle as a ZSARC member, whole-file TBD bundle (`.TBD/.DAT/...`), TBD table in the tail of `GAME/STD_*.ZAR`, TBD table embedded in an overlay/blob (`FLOW_PRG/*.BIN`, `FACE/*.BIN`, `ESTABLIS.ARC`, `GAMEETC.ZAR`). `1ST_READ.BIN` holds none. 34,941 textures (19,651 distinct payloads) in 573 files. |
| May a member change its decompressed size? | No, and it never needs to: pixel format, data type, width and height fix the payload length; `texinject` refuses any other size. |
| May its compressed size change? | Yes, wherever there is room: every size the loader uses comes from the member header (ZSARC) or from the next record's offset (TBD), and the decoders stop at their own end token. Smaller streams are zero-padded; larger ones need the container to be laid out again (section 7). |
| Does the loader read sizes from a table elsewhere? | No table was found: sizes of files come from the ISO directory record through the GDFS file handle, sizes of members from their headers, TBD records have no size field at all. No file size or LBA is hard-coded in the code images (section 3.7). |
| Can members be stored uncompressed? | Yes: `-nc--` members (22,382 of 30,259) and raw TBD records (flag bits clear) are supported by the loader. Cost: the file grows, so it is only a way to avoid the compressor where growth is allowed. |
| What does the loader do with PVR headers? | For `.pvr` members/files it reads pixel format, data type, width, height and the GBIX index from the header at run time (so a different header would be honoured and change VRAM use and UV mapping). For TBD records the same four fields come from the 16-byte table record and the stamp is the GBIX. A replacement must therefore keep all of them. |
| Does the repainted image fit? | Exact-length injection needs the new packed stream to be no larger than the old slot (slack is 0..3 bytes). The original tool's streams are not optimal: an optimal-parse encoder (written here) packs 2-3 % smaller; of 2,302 sampled UNCHANGED compressed textures, 100 % re-encode into their slot (greedy `bzlib`: 40-88 %). A repaint with similar entropy normally fits; one that does not raises `FitError` with the overflow in bytes. |
| Texture memory budget? | Unchanged by construction (same format and size): VRAM and the decode buffer see an identical texture. Only the size of the container file in RAM can change, and only under policy `grow` (section 7). |

## 1. Where textures live (PROVEN, `census.py`, `texinject.py index`)

| kind (`TexInfo.kind`) | files | textures | storage of the pixels | id grammar |
|---|---:|---:|---|---|
| `pvr-file` | 24 | 24 | whole file = GBIX + PVRT (`0GDTEX.PVR`, `DPTEX/*.PVR`) | `''` |
| `zs-pvr` | 14 | 24,749 | ZSARC member whose plaintext is a PVR file: 20,387 `-nc--`, 4,277 `-bz--`, 85 `-bzw-` (`GAME/BIND*.BIN`, `ALL*.BIN`, `JPHOTO.BIN`, `STAFFLST.ZAR`, `GAMEEFF.ZAR`, `KSPAPET.ZAR`, `SKINCOMM.ZAR`) | `name` or `[k]` |
| `zs-tbd` | 249 | 5,076 | ZSARC member that is a TBD bundle (843 stored, 1 `-bz--`); the records inside are raw 328 / `bz` 4,022 / `bzw` 726 (`FLOW_PRG/*.ZAR`, `ETC_DATA/*.ZAR`, `ATFIRST/SHTEX0.ZAR`, `SECFTEX0.ZAR`, ...) | `name#i` |
| `tbd-file` | 217 | 2,348 | the file is a TBD bundle (`ETC_DATA/*.TBD/.DAT`, `ATFIRST/TITLE.DAT`, `NEWS/*.TBD`, ...): raw 191 / bz 1,840 / bzw 317 | `#i` |
| `tbd-tail` | 28 | 892 | `GAME/STD_*.ZAR`: the ZSARC member list ends, then a TBD table (so the "unparsed tail" of docs/formats.md is a texture table: PROVEN) | `@<hex>#i` or `@tail#i` |
| `tbd-embedded` | 41 | 1,852 | TBD tables inside blobs: 18 overlays `FLOW_PRG/*.BIN` (67 tables, 52 of them referenced by an absolute pointer to the table start in the image: `ovl_tbl_ptrs.py`), `FACE/*DATA.BIN`/`*_X2.BIN` (table at 0x18), `ETC_DATA/ESTABLIS.ARC` (sector aligned, 1,188), `GAME/GAMEETC.ZAR` | `@<hex>#i` |

`1ST_READ.BIN` and `2_DP.BIN`: the `GBIX`/`PVRT` byte strings in them are literal-pool constants that the chunk parsers compare against (Ghidra shows READ
references from the code at 0x8c02672c, 0x8c02680a, 0x8c027776, 0x8c0278ee, 0x8c028700, 0x8c028a02, 0x8c029aa2, ...), not images (`scan_pvr.py`:
real `GBIX..PVRT` pairs exist only inside the 8 containers above plus the plain `.PVR` files). **No texture bank in `1ST_READ.BIN`.**
`FLOW_PRG` data = the 249 `*.ZAR` containers (`zs-tbd`) and the tables embedded in the overlay images.

Format histogram (pixfmt/datatype): 1/3 (RGB565 VQ) 21,137; 1/4 4,004; 1/16 (small VQ) 3,884; 2/3 (ARGB4444 VQ) 2,040; ...; the UI atlases that matter for translation are
mostly ARGB4444 twiddled (`fmt 2, dt 1`), rectangle (`dt 9`), twiddled-rectangle (`dt 0xD`) and VQ (`dt 3`: the 62 staff name plates and 66
club-name plates are 128x128 VQ). The full list is `build/texindex.tsv` (`python -I -X utf8 tools/texinject.py index`).

Duplicates are common: 5,407 payloads appear in more than one place (e.g. the title logo `ATFIRST/TITLE.DAT #9` and `ETC_DATA/TITLE.DAT #9`).
`texinject.py dups ATFIRST/TITLE.DAT '#9'` lists every copy: repaint once, inject everywhere.

## 2. File formats involved

* **TBD bundle** (PROVEN, disassembly of FUN_8c15a776, `d_tbd.txt`): `u32 count; count x { u32 flags, u16 w, u16 h, u32 offset, u32 stamp }`; flags =
  `pixfmt | datatype<<8 | ...`, bit 30 -> `-bzw-` (FUN_8c15aae4), bit 31 -> `-bz--` (FUN_8c15a9f4), both clear -> stored raw
  (`rotl; rotl; and #3` at 0x8c15a7aa..0x8c15a7b2: 1 -> bzw, 2 -> bz). **docs/formats.md had these swapped; corrected.** Offsets are relative to the table
  start, always 4-aligned (5,561 records: 4,994 not 32-aligned, 259 of the 274 raw ones are not 32-aligned: the loader does not need 32-byte alignment), record 0 starts at 4+16n,
  data of record i = [off_i, off_(i+1)), the last one to the end of its stream. There is **no size field**. 0 records share an offset.
  After the end token of a compressed record there are 0..3 bytes (alignment) before the next record: zero slack in practice (`analyze_tbd.py`: 4,910 of 4,913
  compressed records; the other 3 are the last records of `KENPIC.BIN`, `SP_DATA.DAT`, `EVENTBG.DAT`, which have more data behind them).
* **PVR file/member** (PROVEN, `analyze_pvr.py`: 24,773 images): `GBIX` chunk (len 8: index, 0) + `PVRT` chunk (len = payload+8; pixfmt, datatype, 0, 0, w, h) + payload; no
  trailing bytes in any of them; payload length = `w*h*2` (dt 1/9/0xD, 2 = +mips >=), `2048+w*h/4` (VQ dt 3, 4>=), codebook(16/32/128/256 entries)*8 + w*h/4 (small VQ dt 0x10, 0x11>=). All 24,769 non-palette
  images match; 4 palette images (pixfmt 6, dt 7) have no formula in `payload_size` and are only accepted with an equal payload length.
* **ZSARC member** (docs/formats.md): header (hdrlen, method, packed, orig, mtime, CRC16 of the DECOMPRESSED data, extension chain with name and header CRC), data, zero pad to 4.

## 3. What the loader does (PROVEN unless marked)

### 3.1 Reading a file (FUN_8c15eede, FUN_8c15f0f4, GDFS wrappers; `t5.txt`, `t8.txt`)
`FUN_8c15eede(name, ?, dest, ?)` opens the file by NAME (GDFS open, "FILE OPEN ERROR (%s)"), asks the handle for the file size
(`FUN_8c01cb18`: `*size = handle->+0xc`, the length the GDFS took from the ISO directory record: **INFERRED** last link, standard GDFS), rounds to sectors and then
* `dest == 0`: allocates `sectors << 11` bytes from the heap and reads the whole file (`FILE MEMORY RESERVE ERROR` if the heap cannot);
* `dest != 0` (caller-provided buffer): `FUN_8c15f0f4` checks it. If the buffer is one of the registered fixed areas nothing is checked; if it is a heap block the
  block header (size at `dest-0x20`) is compared with the file size and "illegal memory for fileread LARGER FILESIZE" is raised when `size + 0x20 > block size`.
So a bigger file is accepted where the buffer comes from the directory size; where it is a preallocated block the original size (or the block) is the limit.
Boot-loaded files at fixed RAM addresses (`ATFIRST/SHTEX0.ZAR` 0x8ce02000, `BAR.TBD` 0x8ce2c000, `SECFTEX0.ZAR` 0x8ce5c000, root `FONT.BIN` 0x8cd5c000) have only
the gap up to the next fixed region (16,234 / 8,488 / 100,818 spare bytes, docs/memory-map.md, INFERRED from RAM dumps); beyond that a bigger file would overwrite its neighbour.

### 3.2 ZSARC walk (FUN_8c15a45a, FUN_8c15a1cc; `tools/re/ghidra/d2.txt`)
Starting at the pointer it is given, per member: read u16 hdrlen (0 = end of the archive, > 0x400 = "illegal archive format"); parse the header (method must be one of the 3 strings, packed = u32 at +7,
orig = u32 at +0xb, CRC16 at +0x13, extension chain); the header length computed from the chain (+2 if it is not a multiple of 4) **must equal hdrlen** ("headersize mismatch");
the header CRC (extension type 0) must match; then `-nc--` is copied (`packed` bytes), `-bz--`/`-bzw-` are decoded; **the number of decoded bytes must equal orig** ("exFilesize mismatch") and the
CRC16 of the decoded data must equal the header's ("exFileCRC mismatch"). The next member is at `+ hdrlen + packed` rounded up using the PACKED size (`4 - (packed & 3)`). Nothing else is
consulted: no size table, no offset table, no total length. Consequences: `packed` may be larger than the stream (zero padding after the end token is legal);
a stored member must have `packed == orig`; zero bytes between members are NOT skipped by the game (a zero hdrlen ends the archive; the bind files rely on that: each archive ends with `00 00`, followed by padding up to the next one).

### 3.3 Decoders (FUN_8c15a9f4 bz, FUN_8c15aae4 bzw; `tools/re/ghidra/d3.txt`)
Both run until their end token (second token byte == 0) and return the number of bytes written. They do not know the source length or the destination size.
Trailing bytes behind the end token are never read. `-bzw-` reads and writes 16-bit units, so source and destination must be 2-byte aligned (INFERRED from `ushort*` accesses; all streams are
4-aligned on the disc and `texinject` keeps it). The encoder must emit exactly the right number of bytes: nothing checks bounds.

### 3.4 TBD table loader (FUN_8c15a776, `d_tbd.txt`; called by FUN_8c15a942 = "make texture list from the TBD at this pointer")
For record i: data pointer = table + offset; flag bits select the decoder, which decodes into ONE scratch buffer shared by all records (`param_3`, reused for every record) and the
decoded pointer is used; raw records are used IN PLACE inside the file buffer. Then `FUN_8c02985c(desc, dataptr, flags & 0x3fffffff, w, h)` builds the 0x2c-byte texture
descriptor: control word = `(flags & 0x3fffffff) << 16` (pixfmt and datatype), `w`, `h`; `FUN_8c02986a(list entry, desc, stamp, flag)` registers it under the stamp (stamp == -1: flag 0x40000000,
else 0x40800000) and `FUN_8c026520(i)` uploads/registers it. So for TBD textures **the table record is the PVR header**: pixfmt, datatype, w, h, GBIX (= stamp). The record has no CRC and no size.
A second consumer of ZSARC members (FUN_8c15a3b0, `local_5c` mode of FUN_8c15a45a) builds descriptors from raw TBD members without the decoder; we never change which records are raw.
That whole-file, ZSARC-member, tail and overlay-embedded tables are all read by this one function is PROVEN for the layout (identical fields; `texverify.py`: all 7,501 records of the bundles that parse decode to the size implied by their header, `analyze_tbd.py`: 0 stream errors in 5,561 records including tails and embedded tables) but INFERRED for the call sites:
the callers inside the overlays (which pass `overlay base + table offset`) were not traced; 52 of the 67 embedded tables have an absolute pointer to their start in their overlay image (`ovl_tbl_ptrs.py`).

### 3.5 PVR images in memory (FUN_8c029a90, FUN_8c0a6024; `t2.txt`, `t3.txt`)
`FUN_8c0a6024` creates a texture from a descriptor whose data pointer points at a PVR file image. It calls `FUN_8c029a90(&ctrl, &gbix, ptr)`: loop over chunks; `PVRT`: copy 8 bytes (pixfmt, datatype, 0, 0, w, h)
into the descriptor and return a pointer 16 bytes after the chunk start (the PVRT length field is **not used**); `GBIX`: take the u32 at +8 as the global index and skip `8 + (len & ~3)`;
any other tag -> not a PVR (returns 0, descriptor untouched). The descriptor then gets `data = after header`, `ctrl = fmt/dt`, `w`, `h` **from the file**, and the texture is looked up/stored by the GBIX
(`-1` = none -> a new texture every time; an index that is already resident reuses that texture and bumps a reference count: INFERRED from FUN_8c0a6024, not traced end to end).
=> the format of a replacement PVR is honoured by the loader, so a different pixfmt/datatype/size would silently change VRAM use and the UV mapping that the code derived from the original; and GBIX must be kept so the cache keys do not move.

### 3.6 What cannot be checked statically
UNKNOWN: the size of the scratch buffer behind FUN_8c15a776 (caller supplied; irrelevant for same-size textures), who owns the texture VRAM budget (the texture slot table is `(count+3) * 0x44` bytes, FLOW opcode 0x11),
whether any retail FLOW script uses the "CRC block" opcode (FUN_8c1648f0 compares up to 15 script-registered RAM blocks with expected CRCs: it can only fire for blocks a script registered; not found relevant to textures).

### 3.7 No hard-coded sizes or addresses (INFERRED, negative scan)
`hardcoded_sizes.py` / `lbahits.py`: aligned u32 words of 121 code/data images (`1ST_READ.BIN`, `2_DP.BIN`, `FLOW_PRG/*.BIN`, `ATFIRST/*.BIN`) equal to a file's size, sector count or start LBA: only coincidences inside code bytes or packed u16 coordinate tables
(e.g. the LBAs of `SECFTEX0/1/2.ZAR` appear three times in one overlay as parts of u16 sprite coordinates). The file loader is name based (section 3.1). This does not exclude values computed at run time.

## 4. Constraints, one by one

1. **Decompressed size** is fixed by (pixfmt, datatype, w, h) and by the descriptor the code expects; `texinject` rejects a replacement whose header or payload length differs
   (`FormatMismatch`). ZSARC `orig_size`, the TBD record, the CRC16 and every destination buffer therefore keep their values.
2. **Compressed size** may differ. ZSARC: `packed` is rewritten in the header (header CRC and data CRC16 recomputed); TBD: the next record's offset bounds the slot.
3. **Stored vs compressed**: both are loader-legal. A stored `-nc--` member must have `packed == orig` (checked by the loader); a raw TBD record is used in place. `texinject` keeps the original method; an optimal-parse
   encoder (section 5) makes switching to stored unnecessary for exact-size injection.
4. **PVR header**: keep pixfmt, datatype, w, h, payload length, GBIX index (default `keep_gbix=True`: the GBIX chunk of the ORIGINAL is reused). TBD stamp and flag bits are never touched.
5. **CRCs**: ZSARC header CRC and data CRC16 are checked on every load -> always recomputed (`bzlib.build_header`; headers rebuilt this way match the disc byte for byte for all 30,259 members).
   TBD has none. No whole-file checksum was found for any texture container (UNKNOWN for save-game / BPINFO, not texture related).
6. **Offsets**: ZSARC: none (sequential walk) except for containers that are indexed from outside (section 7). TBD: relative offsets in the table, rewritten on growth. Overlay-embedded tables: referenced by
   absolute pointers (52 of 67 tables have an absolute pointer to their start in the image), so nothing inside an overlay may move or change size: exact policy only.
7. **ISO directory record**: holds the file length (both-endian) and extent; `discbuild.build_disc` rewrites it when a patched file changes length and keeps the extent while the sector count does not grow.
8. **Alignment**: members and records stay 4-aligned (bzw needs 2).
9. **Texture memory budget**: identical for identical headers (VQ/twiddled payload length is a function of the header). The things that DO change with file growth are the read buffer (directory size) and, for boot-loaded files, the room up to the next fixed region (section 3.1). A texture that gets a bigger packed stream
   does not need more decode buffer (decoded size unchanged).

## 5. Fitting the repainted data into the old slot

Slot sizes are tight: the gap between a compressed record's end token and the next record is 0..3 bytes in 4,910 of 4,913 records; ZSARC members are followed by 0..3 alignment bytes (`texinject` uses them: the loader's step is `hdrlen + align4(packed)`).
`tools/bzlib.py`'s greedy encoder is about as good as the original tool but not better (`cmp_compress.py`: 34 of 40 records <= original), which is not enough for zero-slack slots, so `texinject` adds
**optimal-parse encoders** for both formats (`compress_bz_opt`: literal 9 bits, 2-byte token 9, 3-byte token 17 over distances 1..16/1..128; `compress_bzw_opt`: items of 17 bits), verified to round-trip through `bzlib` and the
independent decoders of the tests. They are 2-3 % smaller than the original streams (4-7 s for a 512x512 texture, pure python).

`fitstats.py` (every 6th compressed texture of the disc, plain <= 140,000 bytes; unchanged data re-encoded and compared with the original slot):

| kind | n | greedy `bzlib` fits | optimal parse fits | mean packed/slot | worst |
|---|---:|---:|---:|---:|---:|
| tbd-embedded record | 295 | 88 % | **100 %** | 0.977 | 1.000 |
| tbd-file record | 343 | 78 % | **100 %** | 0.970 | 1.000 |
| tbd-tail record | 148 | 76 % | **100 %** | 0.977 | 1.000 |
| zs-pvr member -bz-- | 713 | 49 % | **100 %** | 0.980 | 0.997 |
| zs-pvr member -bzw- | 15 | 40 % | **100 %** | 0.995 | 1.000 |
| zs-tbd record | 788 | 81 % | **100 %** | 0.981 | 1.000 |

So a repaint of similar entropy has ~2 % head-room on average and none in the worst case. Real limits exist: `GAME/ALLFLAGS.BIN [48]` is a 6,144-byte texture packed to 220 bytes; no single-word edit fits
(`test_texinject.py` prints this case: 222-224 bytes needed). `fit_check(source, id, pvr)` answers "does it fit and by how much" without raising; when it does not, flatten the art (fewer colours, solid backgrounds, repeated tiles; VQ textures: fewer distinct codebook
vectors), or use policy `grow` where allowed.

## 6. tools/texinject.py

```python
import sys; sys.path.insert(0, 'tools'); import texinject as T
T.list_textures(data_or_path)                         # [TexInfo(tid, kind, fmt, dt, w, h, method, plain_len, slot, growable, gbix, sha1)]
pvr = T.extract_pvr('ATFIRST/TITLE.DAT', '#9')        # PVR file bytes (TBD records get a synthesised GBIX+PVRT)
T.fit_check('ATFIRST/TITLE.DAT', '#9', new_pvr)       # dict(fits, packed, slot, over, growable, ...)
new = T.replace_texture('ATFIRST/TITLE.DAT', '#9', new_pvr)               # bytes of the patched FILE, same length (policy 'exact')
new = T.replace_texture(src, id, new_pvr, policy='grow')                 # allowed to change the file length where the layout permits
patches = T.make_patches({'ATFIRST/TITLE.DAT': {'#9': new_pvr}})        # {'/ATFIRST/TITLE.DAT': bytes} -> discbuild.build_disc(patches, ...)
```
`source_file` may be bytes, a path, or an ISO-style path below `extracted/`. Ids: `''` (plain PVR), `name` / `[k]` (PVR member), `name#i` / `[k]#i` (record i of a TBD member), `#i` (whole-file TBD), `@tail#i`, `@<hex>#i`
(table at that file offset; overlays, tails). CLI: `list`, `extract FILE ID OUT.pvr`, `inject FILE ID IN.pvr OUT [--policy grow] [--new-gbix] [--force]`, `info FILE`, `index`, `dups FILE ID`.

Guarantees of `policy='exact'` (the default; tested on every container kind, section 8):
* output length == input length; only bytes of the texture's own slot change, plus (ZSARC members) three fields of that member's header: the CRC16 of the decoded data (+0x13), the header CRC, and
  `packed_size` (+7) when the stream grew into the 0..3 alignment bytes behind it; every other member/record is byte-identical;
* the new data decodes (with `bzlib` and the re-implemented loader checks) to exactly the replacement payload, with `exFilesize`/`exFileCRC`/header CRC/`headersize` conditions satisfied;
* **no-op**: injecting the unchanged texture (`extract_pvr` output, a rebuilt PVR, or the bare payload) returns bytes equal to the input (decided on the decoded payload, so the original encoder's exact stream survives);
* otherwise `FitError(need, have)` (nothing is written), `FormatMismatch` (wrong pixfmt/datatype/size/payload length), `TexInjectError` (bad id, not a PVR).

How it places data: compressed record/member -> optimal packing (greedy tried first), zero-padded to the slot (ZSARC: header `packed` kept, or raised up to the 0..3 alignment bytes);
stored member/raw record -> bytes replaced in place (same length by construction).

### build_patch integration
`translation/textures/<iso path>/<texture id>.pvr` (file name = id + `.pvr`; so the member `s.pvr` is `s.pvr.pvr`, the table record `@5d0a4#1` is `@5d0a4#1.pvr`, a plain PVR file is `@file.pvr`) is applied by the new stage
`apply_textures` of `tools/build_patch.py` (after text/members, before whole-file replacements; composes on the current bytes of the file if an earlier stage patched it). Options `--textures-dir`, `--texture-policy exact|grow`.
A texture that does not fit raises `PipelineError` naming file and texture. Files keep their length under `exact`, so `discbuild` rewrites only the sectors that contain changed bytes plus the directory sector (tested with `plan_patches`: no moves, 17 changed sectors for 3 edited textures).

## 7. Growth and relocation (policy 'grow'; all of it INFERRED, never run)

Levels, cheapest first:
1. **Inside the slot** (default). Nothing else changes.
2. **Inside the last sector of the file**: `iso_slack(len)` = `(-len) % 2048` bytes cost no extent change; `discbuild` only updates the directory record (PROVEN by `test_discbuild.py`: same-LBA rule).
3. **Larger file, same container layout**: only where the container is *sequentially parsed and nothing outside indexes it* (rules in `zs_growable` / `tbd_growable`):
   * ZSARC: <= 128 members, packed back to back (gaps <= 3), nothing after the archive: the stream is rebuilt, later members shift (4-aligned);
   * whole-file TBD / TBD tail with only zero bytes after the last record: later records shift, their table offsets are rewritten; for tails the table base does not move;
   * a plain PVR file: any (equal-length payload anyway).
   Not allowed (raise `FitError`, `force=True` overrides at your risk): overlay-embedded tables (absolute pointers), bind-style containers (`BIND*.BIN`, `ALL*.BIN`, `JPHOTO.BIN`: many one-member archives separated by terminators and padding, almost certainly addressed by offset from outside), `ESTABLIS.ARC` entries (offset/size index at its start, not
   rewritten), 3 whole-file TBDs with data behind the last record (`KENPIC.BIN`, `SP_DATA.DAT`, `EVENTBG.DAT`).
4. **The file leaves its extent**: `discbuild` moves it (first fit into the 12.8 MB of zero sectors 45061..51341, else appended past track 5: emulator-only, the real GD-R ends at LBA 549150). INFERRED safe because the loader opens files by name; the LBA scan found no hard-coded LBAs.
5. **RAM**: files read into a heap block sized from the directory just need heap; boot-loaded fixed-address files (section 3.1) have the spare bytes listed there; `texinject.py info FILE` prints them. A file larger than its preallocated block fails with "LARGER FILESIZE" (or silently overwrites its neighbour in a registered fixed area).
Not a path: changing pixfmt/datatype/size. The loader would accept it (sections 3.4, 3.5) but VRAM use, the decode scratch buffer and the UV coordinates compiled into the overlays were not investigated (UNKNOWN).

## 8. Test results (`tools/test_texinject.py`, 273 checks passed, 0 failed)

* A codecs: 9 synthetic inputs x 2 formats and 11 real records round-trip through `bzlib` and an independent decoder; optimal <= greedy always; unchanged real records fit their slot 11/11.
* B/C per container kind (16 samples: plain PVR, ZSARC pvr in bz / bzw / nc, ZSARC tbd raw / bz / bzw records, whole-file TBD raw / bzw / bz, tail, embedded in an overlay / ESTABLIS.ARC / FACE data): no-op byte-identical (3 ways); an edited texture injected with `exact`: same length, diff
  positions only inside the slot (+ header CRC fields), reads back, loader emulation sees exactly the one changed member/record. One sample (`ALLFLAGS.BIN [48]`, 220-byte slot) rejects every test edit with a correct `FitError` (reported, not hidden).
* D2 alignment room: `GAMEEFF.ZAR ribon.pvr` edited so that the stream needs 1-3 bytes more than the old `packed_size`: file length and every member offset unchanged, `packed_size` raised, loader walk passes (found by the first sweep, which flagged the changed header field).
* D growth: noise does not fit (`FitError.need > have`); `grow` rebuilds a small ZSARC, a whole-file TBD (offsets shifted by exactly the growth, every other record identical) and a TBD tail; bind archive and overlay-embedded table refuse.
* E rejects: wrong pixfmt / datatype / size / payload length / non-PVR / bad ids.
* F `build_patch` stage output == `texinject` output; `discbuild.plan_patches`: no file moves, sectors that differ from the original disc == sectors that contain changed bytes.
* `tools/re/texinject/sweep.py`: see `sweep.txt` (no-op and an exact-length edit on the first, middle and last texture of every texture-bearing file): numbers in section 10.
* `tools/test_pipeline.py` still passes (135 checks).

## 9. Preparing for image translation / conversion (what exists, what is missing)

| step | status |
|---|---|
| find the texture, know its slot and copies | done: `list_textures`, `index`, `dups`, `info` |
| texture -> PNG | `tools/re/datatext/pvr.py decode` handles fmt 0/1/2 x dt 1, 2, 3, 4, 9, 0xD (verified by eye) and 0x10/0x11 (small VQ: NOT verified, renders striped); palette types (dt 7, 4 images) not decoded; YUV/bump not decoded |
| PNG -> payload (twiddle / rectangle / twiddled-rectangle / VQ with a 256-entry codebook / small VQ / ARGB1555-RGB565-ARGB4444 quantisation) | **missing**; contract: produce exactly `payload_size(fmt, dt, w, h)` bytes, call `build_pvr(fmt, dt, w, h, payload, gbix)` or pass the bare payload for TBD records |
| fit feedback while painting | `fit_check` (bytes over/under the slot); VQ re-quantisation should be iterated against it |
| format change (e.g. VQ -> twiddled when VQ cannot hold the English) | not supported (section 7); would need decode-buffer / VRAM / UV analysis |
| fonts for the repaint | the ARGB4444 text in these atlases is drawn in the game's own face; use a Latin font with the same cell grid; the name plates (`STAFFLST.ZAR`, `ALLLOGOS.BIN`) are generated names (docs/text-sources.md section 3) |
| Pillow / numpy | both import fine in this environment (`python -I`); the injection library itself is stdlib only |

## 10. Disc sweep and open items

Sweep (`python -I -X utf8 tools/re/texinject/sweep.py --skip-big 100`, 507 s, output `sweep.txt`): 572 texture-bearing files (all except the 120 MB `GAME/BINDUNIF.BIN`, checked separately by
`big_check.py`: 21,089 members, no-op identical, exact-length edit changes only the member, reads back), 1,366 textures (first, middle and last of each file):

| kind | tried | no-op byte-identical | edited with `exact`: same length, only the slot (+ member header fields) changed, reads back | no test edit fits |
|---|---:|---:|---:|---:|
| pvr-file | 24 | 24 | 24 | 0 |
| zs-pvr | 39 | 39 | 39 (+ whole-file loader walk of the archive OK: 39) | 0 |
| zs-tbd | 600 | 600 | 595 (+ loader walk OK: 595) | 5 |
| tbd-file | 506 | 506 | 504 | 2 |
| tbd-tail | 84 | 84 | 83 | 1 |
| tbd-embedded | 113 | 113 | 113 | 0 |

0 failures. The 8 "no test edit fits" cases are textures whose slot has no room for any of four tiny edits (a 16-byte run, a copied word, a zeroed last word, a 16-byte run of another value): the zero-slack
limit of section 5 in practice (about 0.6 % of the sampled textures). An earlier run of this sweep flagged the `packed_size` header field of members that grew into their alignment bytes; that is now part of the documented, tested behaviour (test D2).

Open / UNKNOWN (cheap to settle with the emulator, not started here):
1. Does the real game accept an exact-length ZSARC member that has zero padding after the end token and an unchanged header `packed` (code says yes, section 3.2/3.3)? Boot with a flattened STAFFLST plate or a title-logo edit.
2. GBIX reuse rules in the texture cache (section 3.5): does a changed payload under an unchanged GBIX replace a texture that is already resident (e.g. a copy in another file)? Inject all `dups` copies to be safe.
3. How the bind archives (`BIND*.BIN`, `ALL*.BIN`) are indexed from outside; until known they stay exact-only.
4. How the loader locates the TBD table behind a `STD_*.ZAR` archive (growth of a tail record never moves the table base, so it should not matter).
5. Hand-off of `texinject` output into `translation/textures/` for a first end-to-end disc build and boot (needs the PNG -> payload encoders).

## 11. Run members (stage 7, package G): `@<hexoffset>/<name>` ids

Three containers hold PVR textures that are not in a table of their own but in RUNS of back-to-back ZSARC members (the game walks a run with
FUN_8c15a45a, member by member, at an offset taken from the container's own (size, offset) list):

| container | runs | PVR members |
|---|---|---|
| `GAME/GAMEETC.ZAR` | one run at `0x110` | `ktss03` (34703), `pk_parts1` (34708), `sakusen` (34716), `sk_parts2` (34719), `taisenhyoji` (34723) and others |
| `ATFIRST/FACEMDUL.DAT` | one run at `0xcb7e0` | the 15 smiley tiles, among them `kao_g_dai` / `kao_r_toku` / `kao_y_gou` (00056 / 00062 / 00065) |
| `ENDING.BIN` | runs inside the blob | see `texinject.py list` |

`tools/texinject.py` now lists them (`list_textures` adds kind `run-pvr`, 100 rows over the disc), extracts them (`extract_pvr`) and injects
them (`inject`).  The id is `@<hex offset of the run>/<member name>` (`[k]` = member index when a name repeats or is empty), the same rule as
`tools/unpack_all.embedded_runs`, so it agrees with `build/tex/index.tsv`.  A run member is written IN PLACE only: the compressed stream must
fit the old slot (`FitError` otherwise, policy `grow` is refused: nothing in the blob may move), the member header is rebuilt with the new
CRC16 and the enclosing STORED ZSARC member's CRC is refreshed by the same code as for the overlay tables (section 4, docs/scdrf-texture-hang.md).
In `translation/textures/` the file is `<iso path>/@<off>/<name>.pvr.pvr` (the member's own `.pvr` plus the extension), e.g.
`GAME/GAMEETC.ZAR/@110/ktss03.pvr.pvr`; `texinject.load_textures_dir` accepts it unchanged.

Equivalence (PROVEN by `tools/re/s7g_equiv.py`): the ORIGINAL texinject and the current one give the same patched container bytes (SHA-1) and
the same inject info for all 407 textures of translation/textures in 203 containers, and the same `list_textures` rows for all 768 containers of
`extracted/` apart from the 100 new run-pvr rows.  `tools/test_texinject.py` got section G2 (run members: no-op byte identical for all 100,
in-place edits keep the length and pass the loader emulation, growth refused).

Because a VQ texture repainted with text rarely compresses as well as the original, check the slot early: `tools/re/s7g_run.py` encodes with a small
reserve/seed search and prints `packed` against `slot`; hard-edged text (`aa: false`) is usually 100-300 bytes smaller than anti-aliased text.


### 11.1 Auditing a built disc: `tools/zsarc_crc_audit.py`

The build checks stale members while it injects (`texinject.stale_stored_members`); `tools/zsarc_crc_audit.py DISC [--all] [--quiet]` checks the FINISHED disc (a .gdi / .cue / volume .iso) independently of what made it:
for every file that differs from its original in `extracted/` (or every file with `--all`) it takes the member offsets from the original (every CRC-valid ZSARC header: container chains and the embedded runs of `GAME/GAMEETC.ZAR`,
`ATFIRST/FACEMDUL.DAT`) and checks the built bytes at those offsets: the member header still parses, its header CRC is right, and the CRC16 of the decoded payload equals the stored one.  A member that was already bad in the original is
counted separately; a member whose header is gone from its offset is reported `MOVED`.  Exit 1 when a member is stale, 0 otherwise; nothing is written.
Measured: `build/trial/hsk_full1` 44 files, 521 members, 0 stale; `build/trial/prop10a` 164 files, 2,482 members, 0 stale (`build/trial/prop10a_audit.log`).  `tools/test_zsarc_crc_audit.py` tests the member checks on synthetic members of all three methods.
It replaces the older, narrower `tools/re/skh_crc.py` (files that differ only, no embedded runs).
