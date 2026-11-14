# Formats learned so far (SakaTsuku Tokudaigou 2, Dreamcast)

Status legend: **PROVEN** = checked by running code over the whole disc;
**INFERRED** = deduced from code/statistics, not exhaustively verified;
**UNKNOWN** = not investigated.

Code: `tools/bzlib.py` (members/codecs), `tools/overlay.py` (FLOW_PRG),
`tools/unpack_all.py` (batch extraction), `tools/test_bzlib.py` (self-test).
Decoders were transcribed from the game's own code in 1ST_READ.BIN
(load address 0x8C010000): loader "ZSARC".

## 1. Member archives ("ZSARC") — PROVEN

A container file is a sequence of member records: `header | packed data | zero pad to 4`.
Between records zero bytes are skipped (a header starts with a non-zero byte since
hdrlen >= 28). `GAME/BINDFLAG.BIN` and similar "bind" files hold several archives,
each padded with zeros to a 2048-byte sector; skipping zeros handles that. A u16
hdrlen of 0 ends an archive in the loader. 342 files on the disc start with a
member at offset 0 (30259 members: 22382 `-nc--`, 7539 `-bz--`, 338 `-bzw-`).

### Header (little endian, offsets from record start)

| off | size | field |
|-----|------|-------|
| +0  | u16  | hdrlen, includes itself; data starts at record+hdrlen (44/48/52 seen, multiple of 4) |
| +2  | 5 B  | method: `-nc--` stored, `-bz--` byte LZ, `-bzw-` word LZ |
| +7  | u32  | packed_size (bytes after header, incl. end token) |
| +11 | u32  | orig_size |
| +15 | u32  | mtime (looks like a Unix timestamp; the loader ignores it) |
| +19 | u16  | CRC-16/X-25 of the DECOMPRESSED data (loader checks it) |
| +21 | 3 B  | always 00 00 00 |
| +24 | ...  | LHA-level-2-style extension chain: `u16 size (incl. itself), u8 type, size-3 bytes`. Type 1 = file name (cp932, sometimes NUL-terminated). Type 0 = header CRC (u16 + 1 pad byte, size 6). Chain ends with `u16 0`; then zero pad to hdrlen. |

Header CRC = same CRC-16 over the whole hdrlen bytes with the two CRC bytes zeroed.
All 30259 header CRCs verify, and `bzlib.build_header` rebuilds every header on the disc
byte-for-byte (default layout: ext [name, hdr-crc], hdrlen = align4(24 + chain + 2)).

CRC-16/X-25: init 0xFFFF, reflected poly 0x8408, xorout 0xFFFF (check("123456789") = 0x906E).
Game function FUN_8c15b028; table at 0x8c16937c.

### `-nc--`
Data is stored verbatim; packed_size == orig_size.

### `-bz--` (game FUN_8c15a9f4)
Flag byte, consumed LSB first (8 per flag byte). Bit 1: one literal byte. Bit 0: token:
* first byte b >= 0x80: length = (b & 7) + 2 (2..9), distance = 16 - ((b >> 3) & 15) (1..16)
* else second byte b2: b2 == 0 -> END (regardless of b); else length = b2 + 1 (2..256),
  distance = 128 - b (1..128)

Copy byte by byte from already written output (overlap allowed). No ring buffer or
prefill; the decoder writes straight into a buffer of orig_size and does no bounds
checks, so an encoder must emit exactly orig_size bytes and no distance beyond the
output so far. The end token lives in the flag stream like any other match, so the
stream always ends with `.. 00 00`.

### `-bzw-` (game FUN_8c15aae4)
Same idea in 16-bit units; orig_size is even. Flag word is a BIG-endian u16 (first file
byte is the high byte), consumed LSB first (16 per word). Bit 1: literal word (2 bytes).
Bit 0: token bytes (lo, hi): hi == 0 -> END; else count = hi + 1 words (2..256),
source = out_pos - 512 + lo*2 bytes (distance 1..256 words). Word-wise forward copy.

### Cross-check
Three independent implementations (ghidra agent, plaintext agent, bzlib) agree on all 7877
compressed members. One semantic difference: the plaintext agent only ended on a token with
both bytes zero; the game ends on the second byte == 0. Identical on all disc data and
bzlib follows the game.

### Compressor (bzlib.compress) caveats
Greedy longest-match encoder (hash of last 24 candidates, window 128 B / 256 words), no
lazy parsing. On a sample of 60 real members the packed size was within 0.3 % of the
original tool's (259304 -> 258569 bytes). It never emits a 2-byte token with b2 == 0
(min match 3 bytes for 2-byte tokens, 2 words for bzw). Output decodes identically with
three decoders. Packed size only matters through the header's packed_size field; the
loader allocates by orig_size. NOT verified: any disc-slot or buffer size limit of the
game for a repacked file (growth of a file inside a fixed sector layout, e.g. BINDFLAG
archives padded to 2048, must be handled by the repacker).

### Embedded / non-offset-0 records — PROVEN (extraction), structure UNKNOWN
Header-CRC-validated records also occur at non-zero offsets in 31 non-container files
(FACE/*DATA.BIN, FACE/SEC*_X2.BIN, ATFIRST/FACEMDUL.DAT, GAME/GAMEETC.ZAR, some FLOW_PRG
overlays e.g. GAME/EVENT/SEARCH/NEWCON/ABROAD.BIN) and in the tails of 7 container files:
1085 members, all decode with matching length and CRC (`unpack_all.py --scan-embedded`,
output in `<file>/@<hexoffset>/`). The surrounding structure (offset tables before them,
e.g. GAMEETC.ZAR and FACE/*DATA.BIN begin with u32 tables) is UNKNOWN.

### Unparsed tails — UNKNOWN
28 containers (GAME/STD_*.ZAR etc.) end their member list before EOF. The tail starts
`24 00 00 00 | 01 04 00 80 | 40 00 40 00 | 44 02 00 00 | <u32> ...`: apparently a table of
16-byte records (flags 0x80000401, 0x40x0x40 dimensions?, size, stamp) followed by data.
This is a TBD texture table (the one FUN_8c15a776 reads): PROVEN, see docs/texture-injection.md. CORRECTION of an earlier
guess: flag bit 30 (0x40000000) -> `-bzw-` (FUN_8c15aae4), bit 31 (0x80000000) -> `-bz--` (FUN_8c15a9f4); both clear = stored
(disassembly of 0x8c15a7a6..0x8c15a7ba: two `rotl`, `and #3`, 1 -> bzw, 2 -> bz).

## 2. FLOW_PRG overlays — PROVEN: not compressed

`FLOW_PRG/*.BIN` (114 files) are flat SH-4 memory images, read verbatim into RAM; no header,
no packing. Layout: word 0 is the entry stub (~0x38 bytes, a dozen variants), then zero
padding up to ~0x100, then code and data. The stub loads literals and calls the helper at
0x8c159144 (value 0x8c163194, undecompiled; INFERRED cache flush / BSS clear) with
r4 = some address, r5 = load base, r6 = image end rounded to 32 bytes (|0x80000000 = uncached).
GAME.BIN and TRAINING.BIN also have a clearing loop.

Load address is the 0x8cXX0000 literal in the stub (r5). Bases: 0x8c2d0000 (42 files),
0x8c4d0000 (37), 0x8c8d0000 (9), 0x8c6d0000 (7), 0x8c2e0000 (5), HELP 0x8cb60000,
LOADBAR 0x8c800000, plus singles. Pointers inside are absolute: file offset = ptr - base.
`overlay.unpack_overlay` parses 113 of 114 (SECBND.BIN is a different data format starting
`18 01 00 00 14 02 00 00`, UNKNOWN). Base is text-proven (>= 10 pointers landing on
NUL-preceded Shift-JIS string starts) for 111; GETREP.BIN (4) and LOADBAR.BIN (0) rest on
the stub literal / pointers. `pack_overlay(unpack_overlay(x)) == x` for all 113.

Text: Shift-JIS (cp932), NUL-terminated, 0x0a line break, referenced through absolute
pointer tables (e.g. MEETING.BIN table at file 0x2366c, stride 4; strings from 0x3f204).
Growing text requires relocating strings and fixing pointers (not implemented).

Open: GAME.BIN (2389512 B) — stub literal 0x8c4bc890 is the image end (file offset
0x1ec890 = 1984656) while embedded members start at 1984992; most string pointers fit base
0x8c350000 rather than 0x8c2d0000, so the tail (~400 KB) is probably an appended data area
copied to another address (INFERRED, not confirmed). The exact load-address selection in
1ST_READ (table keyed by filename?) was not traced. FLOW_PRG/HELP.BIN vs ATFIRST/HELP.BIN differ.

## 3. Everything else — UNKNOWN
873 other files (DPTEX, DPMODEL, SOUND, SSONG, FACE, EVENT, ...) are not ZSARC containers
at offset 0; their formats are not analysed. 0GDTEX.PVR etc. are plain PVR textures.
BCAST.BIN is skipped by tooling.
