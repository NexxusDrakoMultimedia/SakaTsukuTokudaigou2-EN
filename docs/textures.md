# Textures: where they live, how they are stored, how to decode / re-encode them

Labels: **PROVEN** = checked by code over the whole disc (`tools/test_pvr.py`, 0 failures in its last full run,
223 s); **INFERRED** = deduced, not exhaustively verified; **UNKNOWN** = not investigated.

Tools: `tools/pvr.py` (decode/encode library + CLI), `tools/pvr_scan.py` (finds every texture, writes
`build/textures/inventory.tsv`), `tools/test_pvr.py` (self test, report in `build/textures/test_report.txt`),
`tools/pvr_stats.py`, `pvr_sizes.py`, `pvr_notex.py` (reports). `pvr_explore.py` / `pvr_probe.py` / `pvr_smoke.py`
are throw-away investigation scripts (kept for reproducibility). Pillow 13.0.0 and numpy 2.5.4 are present; `pvr.py`
needs numpy (Pillow only for PNG helpers).

Correction to docs/formats.md: in a texture-table record the flag byte is `0x80 -> bz (byte LZ)`,
`0x40 -> bzw (word LZ)`, `0 -> stored` (bit31 = bz, bit30 = bzw), the opposite of the guess in formats.md section 1
"Unparsed tails". PROVEN: all 10,617+892+664 table records decode to exactly the length implied by their format.

## 1. Texture carriers (PROVEN, `pvr_scan.py`, 37,052 texture records + 6 palette files)

| carrier | layout | records | where |
|---|---|---:|---|
| **PVR file** (`GBIX`+`PVRT`) | 16-byte GBIX chunk (`GBIX`, u32 8, u32 index, 4 bytes of padding: spaces `20 20 20 20` in 13,578 files, `30 00 00 00` in 4 DPTEX files) then `PVRT`, u32 size (= 8 + payload), u8 pix, u8 dat, u16 0, u16 w, u16 h, payload. Payload length always equals what the (pix,dat,w,h) formula gives (PROVEN, all 24,873). | 24,873 | root `0GDTEX.PVR` (BIOS boot art, 256x256 twiddled), `DPTEX/*.PVR` (23, Dream Passport UI), members `*.pvr` of ZSARC containers (GAME/BIND*.BIN etc: 24,785, nearly all 128x128 RGB565 VQ uniform/flag/photo textures), `ATFIRST` (63, e.g. TITLE logos, FACEMDUL.DAT embedded `tex.pvr`), 1 in FLOW_PRG |
| **PVR embedded** | GBIX+PVRT chunk found inside another blob | 6 | GAME/* (embedded run members) |
| **PVP palette** (`PVPL`) | `PVPL`, u32 size, u8 entry format (6 = ARGB8888 B,G,R,A bytes; 2 = ARGB4444), 3 bytes 0, u16 first, u16 count, entries. Rebuilt byte-exact (PROVEN). | 6 files | `DPTEX/BANK00-03.PVP` (256 x ARGB8888, belong to `WALLPAPER00-03.PVR`, INFERRED by number), `TRAINING/BFGAME.ZAR/bg_barx.pvp`, `bg_pcom3.pvp` (256 x ARGB4444) |
| **TBD bundle** (texture table) | `u32 count`, `count` x 16-byte record `{u8 pix, u8 dat, u8 0, u8 flags (0x80 bz, 0x40 bzw, 0 stored), u16 w, u16 h, u32 offset, u32 id}`, offsets relative to the table start, first offset = 4+16*count; payload i = bytes `[off_i, off_i+1)` (last: to end), compressed on its own with the `bzlib` bz/bzw streams (no header, no size field: decode until the end token), content = the bare PVR payload without PVRT header. Methods seen: bz 9,966, bzw 1,467, stored 746 (all in overlays/FACE). | 10,617 | whole files `*.TBD` / `*.DAT` (ETC_DATA 3,970, EVENT 2,390, NEWS 350, TRAINING 132, GAME2 28, MASCOT 11, ATFIRST 55) and members `*.tbd` of containers (FLOW_PRG 3,374 inside `*.ZAR`/overlay-embedded members, GAME 307) |
| **TBD-tail** | the same table as the unparsed tail of 28 `GAME/STD_*.ZAR` style containers (starts after the last ZSARC member; count e.g. 0x24). Explains formats.md "Unparsed tails". | 892 | GAME/*.ZAR |
| **TBD-embedded** | the same table at a 4-aligned offset inside a non-container blob: `FACE/*DATA.BIN` and `*_X2.BIN` (21 files; header `u32 tbd_region_size, u32 0x18, u32, u32 offset_of_secdata_member, 8 zero bytes`, table at **0x18**, offsets relative to 0x18, 497 textures, face skins), `GAME/GAMEETC.ZAR` (61, embedded run members), **overlays** `FLOW_PRG/{OFFICE,GAME,S_SELECT,SEARCH,EVENT,NEWS*,TRAINING,NEWCON,ABROAD,ESTABLIS,...}.BIN` (106 textures; e.g. OFFICE.BIN @0x5aa80, 29 stored VQ/twiddled textures = *textures inside an overlay*), `INITCON.BIN@0x5b08`, `LOADBAR.BIN@0x1ec` (512x512) | 664 | see left |
| **ARC archive** | `ETC_DATA/ESTABLIS.ARC`: `u32 count (0x57)`, then count x `{name NUL, u32 offset, u32 size}`, entries are `*.bin` (3D models) and `*.tbd` (bundles, parsed as TBD) | within TBD counts | ETC_DATA |

Every record's decoded length equals the formula size (PROVEN: `size != expected` is empty for all 37,052).
Several files appear more than once on the disc (ETC_DATA vs ATFIRST copies of SHTEX0.ZAR, X2/DATA FACE files):
19,919 distinct (format, payload) pairs.

### Headerless raw texture members (format not stored; INFERRED from sizes + rendering)
ZSARC members `*.bin` that are bare payloads, format fixed by game code: `GAME/GMSPONTX.ZAR` (149) and `JSPONTX.ZAR` (27):
2048 bytes = **64x64 RGB565 small VQ** (`dat 0x10`), sponsor/advertising boards that contain **Japanese company names**
(e.g. kanji electric-company logo) -> translation candidates; `HAIRBEAR.ZAR` (6144 = 128x128 RGB565 VQ hair/skin,
2048 = 64x64 small VQ beards); `ACCESSRY.ZAR` (2048/1024 glasses, UNKNOWN layout); `NEWS/SUIT0TEX.ZAR` (32768 =
128x128, 131072 = 256x256 RGB565 twiddled suit textures); `GAME/FACEPART.ZAR` (238 small face-part dumps, 16384 /
3224 / 960 ... bytes, layout UNKNOWN, no text expected). Decode with `pvr.decode(payload, 1, 0x10, 64, 64)` etc.
Pillow-viewable examples: `build/textures/explore/raw_*.png`.

### Not PVR / not textures
`DPSS/*.GIF` (55) and `DPWWW/*.GIF` (4): ordinary GIFs of the bundled Dream Passport browser (Pillow handles them);
`DPFONT/*.DAT` bitmap fonts; `FONT.BIN` (font, see docs/font.md); `BCAST/ENDING_L/R.P04` are 4-bit ADPCM audio
(INFERRED from content), not images; `MCH*.TBD` etc. are TBD. `ATFIRST/{TITLE,HELP,FACEMDUL}.BIN`, the other FLOW_PRG
overlays, `GAME2/*.BIN`, `EVENT/*MTN.BIN`: no textures found (code/data/motions).

## 2. Pixel and data formats on this disc (PROVEN counts; records incl. duplicates)

| pixel | data format | records | |
|---|---|---:|---|
| ARGB1555 | twiddled 158, VQ 37, VQ+mips 250, rectangle 65, rect-twiddled 7, small VQ+mips 12 | 529 | |
| RGB565 | twiddled 354, twiddled+mips 50, **VQ 21,331**, VQ+mips 4,844, rectangle 291, rect-twiddled 87, small VQ 4,283, small VQ+mips 548 | 31,788 | |
| ARGB4444 | twiddled 538, twiddled+mips 18, VQ 2,088, VQ+mips 1,358, rectangle 417, rect-twiddled 65, small VQ 167, small VQ+mips 78, **8-bit paletted 2** | 4,731 | |
| PAL8 (header pixfmt 6) | 8-bit paletted twiddled 4 (`DPTEX/WALLPAPER0n.PVR`, 256x256, palette in `BANKn.PVP`) | 4 | |

Not present on the disc (implemented, tested only on synthetic data, INFERRED layouts): YUV422, BUMP, 4bpp paletted,
stride (0x0B decodes as linear, width = w). Not implemented: rectangle+mips (0x0A), 4bpp/8bpp paletted+mips
(`PVRError`). Sizes: 128x128 22,695, 64x64 8,437, 32x32 2,354, 256x256 2,335, 512x512 203, 1024x1024 21, strips such as
256x32, 512x128 (rectangle/rect-twiddled), 8x8 and 16x16 icons.
Total payload 353 MB with duplicates.

## 3. Layouts (all PROVEN by decoding every texture; views in `build/textures/smoke/*.png`)

* **Twiddle**: texel (x,y) sits at stream position with x bits on odd and y bits on even bit positions (Morton, y lowest).
  Rectangular twiddled (0x0D): square tiles of min(w,h), tiles laid in sequence along the long side, each tile twiddled.
  16-bit texels little endian. ARGB1555 `A15 R14-10 G9-5 B4-0`, RGB565, ARGB4444 `A15-12 R11-8 G7-4 B3-0`.
  Channel expansion: 5->8 bit `(v<<3)|(v>>2)`, 6->8 `(v<<2)|(v>>4)`, 4->8 `v*17`, 1555 alpha 0/255. The word <-> RGBA
  map is a bijection over all 65,536 words for all three formats (so re-encoding decoded art is lossless).
* **Rectangle (9) / stride (0xB)**: row-major linear.
* **VQ (3, 4)**: 256-entry codebook (2048 B) of 2x2 blocks (4 texel words in order (x,y) = (0,0),(0,1),(1,0),(1,1)),
  then one index byte per block, indices in twiddled order of the (w/2)x(h/2) grid. Square only.
* **Small VQ (0x10)**: codebook entries 16 / 32 / 128 for 16x16 / 32x32 / 64x64 (PROVEN by sizes 192/512/2048);
  **(0x11, +mips)**: 16 / 64 entries for 16x16 / 32x32 (sizes 224/864). Other sizes INFERRED (8x8:16, 64+ mips:128,
  128+:256). (docs/text-sources.md said small VQ renders garbled: it decodes cleanly with this layout.)
  One texture (`ETC_DATA/MCH06W.TBD#13`, 64x64 ARGB4444) contains indices >= 128; the GPU reads past the codebook into
  the index bytes, `pvr.ext_codebook` reproduces that; it is only promised to re-encode bit-exact when unchanged.
* **Mip chains** (levels 1x1 ... w): twiddled+mips = 2 pad bytes, then levels smallest first, full size LAST
  (sizes: 8x8 172 B, 128x128 43,692 B; stored level 1 matches the box-filtered top to 0.3-1.8 grey levels, so the layout is
  right). VQ+mips = codebook, then index levels 1x1(1 B),2x2(1 B),4x4(4 B)...full(w/2)^2 B ascending, then **10 trailing
  bytes** (PROVEN by a smoothness scan: top level is at `len-10-(w/2)^2`; 64x64 VQ+mip = 3424 B, 128x128 = 7520 B).
  The lower levels are VQ-coded with the same codebook.
* **Paletted 8-bit (7)**: one index byte per texel, twiddled; palette is external (PVP, or UNKNOWN association for the
  two ARGB4444 `bfgame.tbd` 512x512 textures: `TRAINING/BFGAME.ZAR/bg_barx.pvp` / `bg_pcom3.pvp` guessed by order).

## 4. `tools/pvr.py` API and encoder behaviour

```python
import sys; sys.path.insert(0, 'tools'); import pvr
img = pvr.decode(file_or_payload, pix=None, dat=None, w=None, h=None, palette=None, level=0)  # (h,w,4) uint8 RGBA
pvr.encode(img, original=old_bytes)            # same format, same byte length (file in -> file out)
pvr.encode(img, pix, dat, w, h)                # bare payload from scratch; with original= pads/header/codebook reused
r = pvr.encode_ex(img, original=..., palette=..., mips='auto'|'regen', retrain=False, new_palette=False, reserve=0.25)
r.data, r.codebook, r.palette, r.info          # info: mode unchanged|direct|preserve|palette, merged_codes, new_codes
pvr.parse_file / build_file / parse_pvp / build_pvp / data_size / quantize_palette / vq_quantize / to_png / from_png
```
CLI: `python -I -X utf8 tools/pvr.py decode|encode|info ...`. The encoder never changes the length (it raises
`PVRError` otherwise). `original` may be a whole GBIX/PVRT file (header and trailing bytes kept verbatim) or a payload.

* Lossless formats (twiddled, rect, rect-twiddled, stride, twiddled+mips): straight conversion with rounding; lower
  mip levels are regenerated by 2x2 box filter when the full-size level changed (kept verbatim when it did not).
* **VQ / small VQ (+mips)**: the codebook size/structure is always the original. If nothing changed the original bytes
  are returned. Otherwise: unchanged blocks keep their code, changed blocks use exact matches of old codes or new codes;
  free slots are trained with weighted k-means (k-means++ seeding, numpy) on the changed blocks; when too few slots are
  free the cheapest pairs of old codes are merged (pairwise-nearest-neighbour, weighted) until `reserve` * N (default
  25 %) are free. `retrain=True` (or no original) runs a full k-means over all blocks; if an image has <= N distinct
  blocks the codebook is exact (this is why `decode(encode(decode(x))) == decode(x)`).
* **Paletted**: the palette is kept (nearest colour, alpha weighted double); `new_palette=True` derives a k-means palette
  (exact when <= 256 colours). Choose it only when the PVP is private to that texture (BANKn.PVP is not shared by
  WALLPAPERs of other numbers; INFERRED).

## 5. Proofs from `tools/test_pvr.py` (full run, 0 failures)

* Unit: twiddle bijection for n = 1..1024; all 65,536 words x 3 formats identity; 14 known sizes; GBIX/PVRT build/parse;
  synthetic PAL4 / PAL8 / BUMP bit-exact, YUV422 within +-3.
* Corpus: **all 37,052 records decode** (19,919 distinct); for every distinct texture of every lossless format
  `encode(decode(x), original=x) == x` and `encode(decode(x)) == x` (no original) bit-exact (non-mip), top level and
  decode identical (mips); every VQ / small VQ / +mips texture: `encode(decode(x), original=x) == x` (both through the
  shortcut and through the real preserve path with `mips='regen'`: codebook and full-size level identical),
  from-scratch `retrain=True`: `decode(encode(decode(x))) == decode(x)` and a second generation gives identical bytes.
  Counts (distinct, all passed): ARGB1555 twid 81 / VQ 27 / VQ+mip 45 / rect 35 / rect-twid 2 / sVQ+mip 1; RGB565 twid
  247 / twid+mip 8 / VQ 14,689 / VQ+mip 732 / rect 172 / rect-twid 26 / sVQ 1,285 / sVQ+mip 88; ARGB4444 twid 304 /
  twid+mip 8 / VQ 1,489 / VQ+mip 224 / rect 320 / rect-twid 37 / sVQ 86 / sVQ+mip 13.
  All 18,807 PVR files re-encode to the identical file. 6 PVP files rebuild identically. Paletted: WALLPAPER00-03
  bit-exact with their BANK palette; `bfgame` textures decode-stable (the guessed palette has duplicate colours).
* Repaint tests (real text textures, white English text on a blue box, PNGs in `build/textures/test/repaint_*.png`):
  `HELP.DAT` VQ4444 256x256: area PSNR 43.6 dB, 100 % of the other pixels identical; `OPTION02.PVR` VQ4444 512x512
  41.1 dB / 98.3 % identical (merged 38 old codes); small VQ 565 skin 33.5 dB / 83.2 % (full retrain 37.0 dB);
  VQ+mips 565 area exact / 90.9 % identical; twiddled and rectangle exact; PAL8 wallpaper 24.9 dB with the fixed palette
  (use `new_palette=True` or a palette-aware art style).

## 6. Notes for the image-translation step

* Repaint workflow: `pvr.decode_ex(blob)` -> edit RGBA with Pillow -> `pvr.encode(img, original=blob)` -> put the bytes
  back into the carrier: PVR members via `bzlib.pack_member`/`member_record`; TBD entries need the table offsets rebuilt
  and each entry re-compressed (bz/bzw/stored; compressed size may differ, the table has no size field: rewrite offsets).
  Rebuilding TBD tables/containers is NOT implemented in this task.
* The 2 px merge cost: preserving unchanged art costs codebook slots; text-heavy replacement of a whole atlas is better
  served by `retrain=True` (all blocks re-clustered, MAE ~0.1-0.8 on the tests).
* Same-size constraint: replacement text must fit the existing atlas cell; the byte length of every payload is fixed by
  (pix,dat,w,h), so no container growth is needed beyond re-compression differences.
* Candidate Japanese-in-art sources are listed in docs/text-sources.md section 3 (decoder there is superseded by
  `pvr.py`); add: sponsor boards (GMSPONTX/JSPONTX), DPTEX UI, FLOW_PRG overlay-embedded tables.
* UNKNOWN: pairing of TRAINING palettes; layouts of paletted+mips, 0x0A rectangle+mips; whether the game reads the 10 VQ
  trailing bytes / 2 twiddled pad bytes (they are copied from the original when re-encoding).
