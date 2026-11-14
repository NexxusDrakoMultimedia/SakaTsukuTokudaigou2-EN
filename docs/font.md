# FONT.BIN / DPFONT: format, glyph mapping, English strategy

Status legend: **PROVEN** = checked by running code / read directly from the game code;
**INFERRED** = deduced, not verified end to end; **UNKNOWN** = not investigated.

Code: `tools/font.py` (parser, builder, SJIS->glyph mapping, renderer, PNG import/export).
Generated previews: `build/font/` (`python -I -X utf8 tools/font.py sheets|sample|export|dpfont`).
Ghidra helpers/outputs: `tools/re/font/` (own project copy `<GHIDRA_PROJECTS>\ghproj_font`, which also holds
`COMM.BIN` imported at 0x8c2e0000 as a sample overlay).

## 1. FONT.BIN layout (PROVEN)

`extracted/FONT.BIN` (663324 B) and `extracted/ATFIRST/FONT.BIN` (663096 B) share the layout. All u32 little endian.

| off | meaning |
|-----|---------|
| 0x00 | `0xE40` = 3648 = number of full-width glyphs |
| 0x04 | `0x10` = file offset of the offset table |
| 0x08 | `0x3910` = 0x10 + 4*3648 = start of glyph data (offsets are relative to this) |
| 0x0C | `0x9C51C` (ATFIRST: `0x9C438`) = end of the glyph data = start of the half-width block |
| 0x10 | 3648 x u32 offsets (monotonic, glyph i = bytes [off[i], off[i+1]) of the glyph data; last glyph ends at header[3]) |
| 0x3910 | 3648 packed glyphs |
| header[3] | half-width block: 23040 B = 160 glyphs x 144 B, raw (not packed) |

The game's own init (1ST_READ `0x8c15e72c`) reads exactly these four header words
(`*0x8c22835c`=count, `base+[2]` -> glyph data, `base+[3]` -> half block, `base+[1]` -> offset table), so nothing
else (sizes, offsets) is hard-coded.

### Full-width glyph: 24x24, 4 bpp, packed with the game's `-bz--` LZ (PROVEN)

Each glyph record is a bare `-bz--` stream (no ZSARC header; the decoder is `bzlib.decompress_bz`,
game FUN_8c15a9f4 - the glyph fetch `FUN_8c15eca4` calls it with the offset table and decodes into a
288-byte buffer at 0x8c227a32). Verified: all 3648 glyphs in both files decode to exactly 288 bytes.
288 B = 24 rows x 12 B; each byte holds two pixels, **high nibble = left pixel**; **0 = ink (black), 15 = paper**
(all 16 grey levels are used, i.e. anti-aliased; 1 115 195 of 2 101 248 pixels are paper in the whole set). Verified by
rendering (`build/font/full_*.png`). The game's fetch converts nibbles to a 16-bit texel (`FUN_8c15eca4`).

The glyph streams have a trailing end token (`00 00`); the last glyph of FONT.BIN has one extra pad byte
(9 bytes instead of 8) which is why the packed bytes are kept for unchanged glyphs.

### Half-width glyph: 12x24, 4 bpp, raw (PROVEN)

160 glyphs at `header[3] + 144*i`, 6 bytes per row, same nibble convention
(`FUN_8c15eca4`: `glyph = base_half + idx*0x90`). Byte -> index: `0x20..0x7f -> 0..95`, `0xA0..0xDF -> 96..159`
(`c-0x20` below 0xA0, else `c-0x40`; verified in `FUN_8c15e9c6`/`FUN_8c15eca4`). Contents (render: `build/font/half.png`):
ASCII 0x21-0x7e (JIS-Roman: **0x5c is a yen sign, 0x7e is an overline** - no backslash/tilde), half-width katakana
0xA1-0xDF (incl. ｡｢｣､･ and ﾞﾟ). Blank: idx 0 (space), 95 (0x7f), 96 (0xA0) -> 157 of 160 non-blank.

## 2. Mapping: Shift-JIS code -> glyph index (PROVEN, transcribed from game code)

The 2-byte lookup is **one shared function in 1ST_READ.BIN at 0x8c15e7a0** (library jump-table slot `0x8c1593ac`
= table base 0x8c159000 + 0x3ac). Overlays call it through the slot (checked in COMM.BIN; 110 of the 114
FLOW_PRG overlays contain the slot offset 0x03ac). Implemented as `font.sjis_to_index`:

```
code > 0x9890            -> index = 3530 + position of code in the 51-entry u16 table at 0x8c169f04
                            (not found -> 0x17 = fallback glyph); table = font.EXTRA_TABLE, compared with 1ST_READ: equal
lead = code>>8, trail = code&0xff, t = trail-0x40 (trail<0x7f) else trail-0x41      # 0x7f gap skipped => 188 per lead
lead == 0x88             -> index = 406 + trail                  (0x889F -> 565)
lead >  0x88             -> index = (lead-0x89)*188 + 659 + t    (JIS level 1 kanji, contiguous: 0x8940 -> 659)
lead <  0x88             -> index = (lead-0x81)*188 + t          (0x8140 -> 0 ... 0x83FC -> 563)
index < 0 or >= 3648     -> 0x17
```

So the glyph set is:

| index | content |
|-------|---------|
| 0-563 | leads 0x81-0x83: symbols, **full-width Latin** (digits 0x824F-0x8258 = 203-212, A-Z 0x8260 = 220-245, a-z 0x8281 = 252-277), hiragana (0x829F..=282-364), katakana (0x8340..=376-461), Greek (470-525). 425 non-blank, 139 blank |
| 564 | blank (would be 0x8440; there is no Cyrillic; 0x84xx codes actually land on kanji indices) |
| 565-3529 | all 2965 JIS X 0208 level-1 kanji in JIS order (亜 .. 腕), none blank |
| 3530-3580 | 51 extra kanji (level-2/NEC characters: 儂 凛 寳 嶽 ... 數), reached only via the table (0x9873-0x9890 also hit 3530-3557 as invalid codes) |
| 3581-3647 | 67 blank, unreachable by any code |

Facts: 3441 glyphs non-blank, 207 blank. Table duplicate: 0xe54d (藪) appears twice, so glyph 3577 is unreachable via the table.
Level-2 kanji beyond the 51 are not in the font: scanning the `ja` fields of `translation/*.jsonl` (119 files at the time of
the run) gives 2503 distinct non-ASCII characters; 69 of them (e.g. 俑 傚 劔 哭 嚮 ...) cannot be drawn (map to fallback
glyph 0x17); that is a property of the original game text/font, not an error of the tool.
Check done: all 3489 valid cp932 codes with lead 0x81-0x84/0x88-0x98 (level-1 range) map to non-blank glyphs except 0x8140 (space) and 0x8440.

ATFIRST/FONT.BIN: the half block and 3647 of 3648 glyphs are identical; glyph 3580 is blank there and the last glyph
has no pad byte (so 228 B smaller).

### Single bytes (PROVEN in COMM.BIN, INFERRED for the other overlays)

Text strings are compiled by an overlay-local routine (COMM.BIN `FUN_8c2e059e`) into u16 codes:
* byte < 0x21 -> control code `0x2000|b` (0x20 space is drawn as an empty half-width cell, 0x0a = new line);
* bytes 0x21-0x7f and 0xA0-0xDF -> `0x8000|b` = **half-width glyph (12x24 block)**; `0x4000` is OR-ed when the byte is in a per-overlay list
  (`FUN_8c2e051a`, purpose UNKNOWN: probably a position/style tweak - the glyph fetch masks it off with 0xbfff);
* lead 0x81-0x9F / 0xE0-0xFC + trail -> `sjis_to_index(...)` (| 0x4000 if listed in `FUN_8c2e04f0`'s table);
* escapes `@nn/`, `=nn/` etc. produce control codes (not analysed).
The glyph fetch `FUN_8c15e9c6/eca4`: `code & 0xA000 == 0` -> full-width glyph index (offset table + bz); otherwise half-width.
Layout (`FUN_8c2e0934`): advance = `*(char*)(obj+0x36)` (0x18 = 24 px) for full-width and **half of it (12 px) for
half-width**; the line limit (`obj+0x34`, default 20) is counted in 2-per-full-width / 1-per-half-width cells, so 20 full-width = 40 half-width
characters per line by default. **There is no width table: half-width characters are strictly 12 px monospaced.**
Another entry, slot 0x8c1593b0 (`FUN_8c15e88e`, used by ~30 overlays e.g. CE_VS, GAME, NEWS, G_RESULT), maps a single byte to a
*full-width* glyph through a u16 table at 0x8c16a08a (digits -> 0xCB.., A-Z -> 220..): strings drawn that way are 24 px per character.

## 3. Measurements for English

Half-width ASCII 0x21-0x7e: ink widths per glyph - 12 px: 40 glyphs, 11 px: 24, 10: 5, 9: 2, 8: 5, 7: 5, 6: 2, 4: 9, 3: 2. The cell is full: capital letters
use the whole 12 px (no side bearing), so adjacent letters touch (see `build/font/sample_ja.png`, last line). Rows used 0-23 (cap height ~18). Readable, but dense.

## 4. Round trip / encoder (PROVEN, `python -I -X utf8 tools/font.py roundtrip`)

* `Font(data).build()` == original for **both** files (byte exact): unchanged glyphs are written back from their original packed bytes.
* Recompressing every glyph with `bzlib.compress_bz` is *not* byte-identical to the original (the original tool used a different match
  strategy: only 373 of 3648 streams identical) but decodes to identical glyphs+half block and is 968 B smaller (662356 vs 663324).
* A modified full glyph and a modified half glyph are written and read back correctly; all other glyphs unchanged.
* Edit workflow: `font.py export` writes `build/font/edit_full.png` (768x2736, glyph i at column i%32, row i//32, grey = nibble*17) and
  `edit_half.png` (384x120); `font.py import <src FONT.BIN> <full.png|-> <half.png|-> <out FONT.BIN>` writes them back
  (export -> import without edits gives a byte-identical file: checked). API: `Font.set_glyph`, `Font.set_half`, `import_edit_sheet`.
  Not checked: acceptance of rebuilt files by the real game/emulator.

## 5. Strategy for readable English

1. **Zero-code-change baseline**: write English as single-byte ASCII (cp932-compatible). It renders with the 12x24 half-width glyphs, 12 px
   monospaced, 40 characters per default 20-cell line. The 160-glyph half block is plain uncompressed data: redraw it freely
   (e.g. cleaner letterforms with 1 px side bearing so ink <= 10 px, replace `¥`/`‾` by `\`/`~` if needed).
2. **Free half-width slots**: 63 half-width katakana (0xA1-0xDF = idx 97-159) plus 0x7f and 0xA0 = **65 slots** can hold accented letters, symbols or
   icons without touching code (all reachable as single bytes by the string compiler).
3. **Free full-width slots** (24x24, reachable via their own SJIS code): 138 blank unassigned cells in indices 1-563 (0x8140 = ideographic space is index 0, keep it) + index 564;
   67 dead slots 3581-3647 (reachable only after extending EXTRA_TABLE in 1ST_READ - a single copy of the mapping function, so one patch); and
   **921 kanji glyphs (idx >= 565) + 152 non-kanji glyphs that are not used by any text currently in `translation/*.jsonl`** - candidates only; recompute with
   `font.py usage` once all text sources are dumped. Any glyph may be overwritten as long as no remaining Japanese text uses it.
4. **Proportional spacing is not available in the data**: the 12 px advance is code in each overlay's text layout routine (many statically linked copies),
   so proportional text needs a code patch per overlay - not attempted. Cheap alternatives: narrower redrawn glyphs, or abbreviations.
   A "two letters in one 24x24 glyph" digraph scheme using free full-width slots would double density but needs every string rewritten with the
   special codes - judged not worth it unless line length proves to be a problem.
5. Strings drawn through slot 0x3b0 (single byte -> full-width glyph) would show English as 24 px wide letters; the byte->glyph table at 0x8c16a08a is data
   in 1ST_READ and can be re-pointed.

## 6. Size / relocation (partly INFERRED)

* 1ST_READ loads FONT.BIN with the loader FUN_8c15eede(name, 0, dest) with an explicit destination, literal at 0x8c16033c = **0x8cd5c000**
  (same code path for ATFIRST and root FONT.BIN) and reads ceil(size/2048) sectors. Next resource loaded to an explicit address is SHTEX0.ZAR at **0x8ce02000**
  (literal 0x8c16034c), then BAR_TBD 0x8ce2c000, SECFTEX0.ZAR 0x8ce5c000.
* PROVEN: no code hard-codes the font's size or internal offsets (all derived from the header; searched 1ST_READ and the 114 overlays' aligned words for
  0xe40/0x3910/0x9c51c/663324: no code hits). GAME.BIN has a literal pair 0x8cd5c000/0x8cd5c004 in code (file offset 0x5030c): another consumer of the font header, UNKNOWN use.
* INFERRED limit: FONT.BIN may grow to 0x8ce02000 - 0x8cd5c000 = 0xA6000 = **679936 bytes**, i.e. **+16612 bytes** over the current 663324
  (or +17580 after full recompression); beyond that the later SHTEX0.ZAR load overwrites it (the loader literals could be patched in 1ST_READ.BIN, which is itself a disc file).
  Worst case per replaced glyph: ~324 B packed instead of avg 171.5 B, so ~100 incompressible new glyphs fit; typical monochrome glyphs compress far better. The disc image
  must be rebuilt with the new file size anyway (file sizes are free there; LBA of later files shift or the file must stay within its sector slot - disc builder's job).
* Both FONT.BIN copies (root, ATFIRST) are separate files and both need the same edits (they differ only in glyph 3580).

## 7. DPFONT/*.DAT (browser fonts, secondary, INFERRED)

`DPFONT/S18RM04P.DAT S20.. S24.. S26..` (702720 / 780800 / 1124352 / 1421056 B): no header, **7808 glyphs** each, 2 bpp (4 pixels per byte, MSB first,
3 = ink), rows padded to whole bytes: glyph = 90 / 100 / 144 / 182 B for 18 / 20 / 24 / 26 px (the sizes divide the files exactly). Index = cell in SJIS order:
`(lead - 0x81 [lead<=0x9f] or lead - 0xc1)*188 + t` (same 188-per-lead rule with 0x7f skipped), e.g. 亜 (0x889F) = 1410, level-1 kanji end at 4374 (0x9872), level 2 spans
4418-7807 (0xEAA4); a block of 188 half-width/other glyphs sits at 752-939. Renders correctly (`build/font/dp_S*_0000.png`, `dp_S*_1410.png`).
Used by the Dreamcast web browser part (2_DP.BIN refers to FONT), not by the game's own UI: low priority for the translation. Writer not implemented.

## 8. Unknown / not done

* Meaning of the 0x4000 flag lists in the overlays' string compiler; the `@nn/` `=nn/` escape syntax.
* Whether every overlay uses the same 12 px layout constants (verified only in COMM.BIN; the others are statically linked copies, expected identical).
* How the game turns nibbles into texel alpha/colour (text colour) - only seen as a nibble shuffle in `FUN_8c15eca4`.
* No in-game/emulator test of a modified FONT.BIN was possible here.
