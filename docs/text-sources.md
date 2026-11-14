# Text sources outside the SH-4 overlays (agent "datatext")

Status words: **PROVEN** = ran code over the whole disc/file and checked the result;
**INFERRED** = deduced, not verified; **UNKNOWN** = not investigated / not understood.
Everything here was produced by tools in `tools/textfmt_*.py` and `tools/re/datatext/`.

## 0. Headline finding

Almost no Japanese text lives in data files. The disc is ~97 % textures, 3D models,
motions and audio. The player-visible text (event dialogue, news, meetings, training,
help, ...) is in the SH-4 overlays (`FLOW_PRG/*.BIN`, `ATFIRST/{HELP,TITLE}.BIN`,
`1ST_READ.BIN`), which are another agent's job (`tools/textdb.py`).
What exists outside the overlays:

* `DPETC/MESSAGE.INI` - 849 strings (Dream Passport network browser UI)
* `ETC_DATA/BPINFO.BIN` + `ATFIRST/BPINFO.BIN` - 5321 player names (fixed 14-byte fields)
* `2_DP.BIN` - 157 pointer-referenced UI strings (+ an IME dictionary that is not UI text)
* **`/BCAST/BCAST.BIN` voice-clip subtitles (30,083 segments, section 6; the match commentary box and the attract demo): found only after the first playtest, the survey skipped the file** 
* Japanese **baked into textures** (art): menu atlases, title logo, club/national-team
  name plates, staff name plates (section 3).

**EVENT/*.DAT (175 files) contain no text at all**: 168 are ZSARC containers of 3D
models / textures / motions (`texmodmt.zar`, `stat.zar`, `pic.tbd`, `name17.tbd`,
`motion.bin`, ...), the rest texture bundles / motion tables. Event scripts and
dialogue are in `FLOW_PRG/EVENT.BIN` and friends. Likewise `NEWS/*` (67 files) are
65 texture bundles + 2 ZSARC of textures (headline *graphics*, studio backgrounds);
the news *text* is in `FLOW_PRG/NEWS*.BIN`.

## 1. Ranked table of text sources (my scope)

"#JP chars" counts characters that are not ASCII (kana, kanji, full-width, half-width
kana) in the extracted `ja` fields.

| # | source | format status | #strings | #JP chars | handler | what remains |
|---|--------|---------------|---------:|----------:|---------|--------------|
| 1 | `ETC_DATA/BPINFO.BIN` and `ATFIRST/BPINFO.BIN` (player database) | PROVEN (size == 64 + 5321*92 for both files; all names decode; both copies have identical name fields) | 5321 (5320 distinct) | 26104 | `tools/textfmt_bpinfo.py` -> `translation/ETC_DATA__BPINFO.BIN.jsonl` (same entries patch both files) | names are limited to **13 ASCII chars** (14-byte field, fixed 92-byte stride). UNKNOWN whether the game could cope with longer names; the other 78 bytes of each record are numeric stats, not analysed. Needs romanisation policy (e.g. "K. Kawamoto"). |
| 2 | `DPETC/MESSAGE.INI` | PROVEN (plain cp932 INI, CRLF, `N="text"`) | 849 (+1376 comment/blank lines kept verbatim) | 22121 | `tools/textfmt_ini.py` -> `translation/DPETC__MESSAGE.INI.jsonl` | no in-place limit (file is rebuilt); UNKNOWN whether the browser has a per-string buffer. The Dream Passport online service (dricas) is long dead: lowest priority. |
| 3 | `2_DP.BIN` (Dream Passport main program, SH-4, base 0x8C010000) | extraction PROVEN (round trip, relocation self-test); load base INFERRED from pointer voting (150/150 sample strings vote base 0x8C010000) | 157 pointer-referenced | 846 | `tools/textfmt_ptrblob.py` -> `translation/ROOT__2_DP.BIN.jsonl` | Contains noise (some pointed strings are code/IME tables that happen to look like text: single kana, `瀬賀`, ...). A further 5462 kana strings (e.g. `コンピュータエイディッドデザイン`) are an IME/abbreviation **dictionary** reached by index, not UI text; not exported. Relocation (append at image end) untested on hardware. |
| 4 | `ATFIRST/HELP.BIN` (tutorial/command help, ~51.9k JP chars) | PROVEN | 670 (669 pointed + 1 unreferenced) | 51863 | `tools/textfmt_ptrblob.py` (cross-check only, `--write` skips it) | **Owned by tools/textdb.py** (`translation/ATFIRST__HELP.BIN.jsonl`, 698 strings). My independent extraction matches it: 669/669 common strings have identical `ja`, 668/669 identical `max_bytes`; textdb additionally finds 29 more (level-2-kanji names, single digits). `FLOW_PRG/HELP.BIN` is a near twin (4 bytes shorter; 6 strings differ) - both copies need translating. |
| 5 | `ATFIRST/TITLE.BIN` (title/new-game overlay, contains ~460 player/foreign-player names, debug strings) | PROVEN | 466 | 2566 | same | textdb has 512 (superset, 466/466 identical `ja` and `max_bytes`). |
| 6 | `1ST_READ.BIN` (main program; sponsor/report/news headline strings 0x157898..) | PROVEN extraction | 204 | 1364 | same (not written; textdb scans it) | owned by textdb. |
| 7 | `DPETC/*.DPS`, `DP3.INI`, `DPWWW/*.HTML` | PROVEN (read all) | 0 translatable | - | none | `.DPS` = browser skin scripts (JP only in `<!-- -->` comments and in soft-keyboard key literals `keycode=...` such as kana/emoticons, which are input characters, not text to translate). `DPWWW/INDEX.HTML` and `HELP/INDEX.HTML`: 3 `alt`/`title` strings that point to the defunct network. |
| 8 | everything else in `EVENT/ ETC_DATA/ GAME/ GAME2/ NEWS/ MASCOT/ FACE/ TRAINING/ SSONG/ SOUND/ DPFONT/ DPSS/` | PROVEN: classified (section 2) | 0 | 0 | - | `GAME2/SS_SMP.BIN` holds ASCII song-edit sample titles (already English). |

Survey method (`tools/re/datatext/survey3.py`, output `survey3.tsv`): NUL-delimited cp932
strings with >=2 double-byte chars and >=40 % kana, over all 32553 files of `extracted/`
(minus BCAST) and `build/unpacked/`. Result: the only non-noise hits are HELP.BIN, 2_DP.BIN,
1ST_READ.BIN, TITLE.BIN; everything else is <=7 chars of coincidental matches inside
texture/model data. (A naive cp932 scan reports millions of "JP chars" in GAME/ - that is
compressed or texture data and is noise; do not trust unfiltered counts.)

### Format notes

* **MESSAGE.INI**: value = bytes between the first `"` and the last `"` of the line (values
  contain `"` inside `<font color="#CC0000">`). Markup (`<br>`, `<font>`, `%s`, `%d`) must be
  kept. 1 line `<---!...--->` and `[Text]` are kept verbatim; `#16="..."` style
  commented-out strings are not extracted.
* **BPINFO.BIN**: `u16 count`, small header table, records from 0x40, stride 92; name =
  `char[14]` NUL-padded (observed lengths 2..13 bytes), tail after the NUL is always zero
  (checked for all 5321, the extractor raises otherwise). Half-width katakana names
  (`ﾁｮｲ ﾋｼﾞｭﾝ`) occur for foreign players. Header table (u16 at 0x08.. = 1425, 4595, 4621, 4647 ...,
  stride 26) semantics UNKNOWN (looks like section offsets for stats); no checksum was
  found but not ruled out.
* **ptrblob**: see docstring in `tools/textfmt_ptrblob.py`. A string is a NUL-terminated
  cp932 run whose start is the target of an aligned absolute 32-bit pointer. Strict
  filtering (no control bytes except 0x0A, <=10 % level-2 kanji, only kana/kanji/
  full-width/half-width-kana/ASCII) is necessary because pointers to *code* also hit
  byte patterns that decode as cp932 (an unfiltered first version produced 1196 "strings" in TITLE.BIN, most of them code;
  the strict version gives 466 and every one I sampled is real text).
* Common codec (`tools/textfmt_common.py`): `<XX>` tokens for non-text bytes, `<3C>` for a
  literal `<` that would be ambiguous. `encode(decode(b)) == b` for all 65536 two-byte
  strings, all 256 one-byte strings and 20000 random strings (`test_all.py`).

### Round-trip proofs (all in `tools/re/datatext/test_all.py`, run: all OK)

| tool | files | proof |
|------|-------|-------|
| textfmt_ini | MESSAGE.INI | `apply(extract)` byte-identical; `en = ja` byte-identical; mutation (longer English in two lines) re-extracts exactly and leaves the other 847 strings untouched |
| textfmt_bpinfo | both BPINFO.BIN | same; mutation changes only bytes inside name fields (checked over all 489596 bytes); 14-char name rejected |
| textfmt_ptrblob | 2_DP, HELP, TITLE, 1ST_READ | identity, `en = ja` identity, and a mutation test: 3 strings lengthened (relocated, pointers rewritten, expected pointer count matched) + 1 shortened in place; all new strings found again via extract, all others unchanged |

Not tested: running any patched file in an emulator/on hardware.

## 2. Classification of every file outside FLOW_PRG (by magic + structure)

Counts are files in `extracted/` (BCAST/BCAST.BIN skipped; 1215 files total).

| dir | files | contents | text? |
|-----|------:|----------|-------|
| EVENT | 175 | 169 ZSARC (events: `texmodmt*.zar`, `pic.tbd`, `stat.zar`, `motion.bin`, `e_NNNN.zar`...), 4 texture bundles (`EVCOM/ETC/TOPIC.TBD`, `EVENTBG.DAT`), 2 motion tables (`EVMTN.BIN`, `HWGMTN.BIN`) | none |
| ETC_DATA | 153 | 104 texture bundles (`.TBD`/`.DAT`), 43 ZSARC of textures/models, `ESTABLIS.ARC` (plain archive: starts with u32 0x57, then records `name NUL, u32 offset, u32 size` such as `ClubHouse_Bch01.bin/.tbd`, `Ground_grA.bin` ... = 3D models + textures, 6.6 MB; record layout read by eye, not parsed), `CE_MTN.BIN`/`SEC_MTN.BIN` (motion tables, u32 offset tables), `BPFACE.BIN`, `KENPIC.BIN`, `TRADEBIN.BIN` (font-like ASCII table), **`BPINFO.BIN` (text)** | BPINFO only |
| GAME | 74 | 49 ZSARC, 22 texture bundles, `END_MTN.BIN` (motions, offset table), 'BIND*' bind archives of PVR (`BINDUNIF` 20333 uniform textures, `BINDFLAG`, `BINDNAME`, ...), `GAMEETC.ZAR` | none |
| GAME2 | 13 | 8 texture bundles, `GAMEMTN.BIN` motions, `SCN_DATA.BIN`/`CM_TRG*.BIN` SH-4 data tables with absolute pointers (no strings), `SS_SMP.BIN` (ASCII sample song titles) | none |
| NEWS | 67 | 65 texture bundles (`STUDIO*.TBD`, `CHAMP_*.TBD`, `FLEAGUE*.TBD`...), 2 ZSARC (`MATTITLE.ZAR` English title banners) | none |
| ATFIRST | 15 | 5 texture bundles, 3 SH-4 overlays (`HELP/TITLE/FACEMDUL.BIN`), `BPINFO.BIN` (text), `FONT.BIN`, 2 `.MLT`, 2 ZSARC, `FACEMDUL.DAT` | HELP/TITLE (overlay agent), BPINFO |
| TRAINING / MASCOT / FACE | 12 / 11 / 21 | texture bundles, ZSARC models, face data | none |
| DPETC | 9 | `MESSAGE.INI` (text), 6 `.DPS` skin scripts, `MANATEE.DRV`, `DP3SOUND.MLT` | MESSAGE.INI only |
| DPWWW / DPSS / DPFONT / DPTEX / DPMODEL | 5 / 55 / 4 / 27 / 1 | HTML + GIF, screensaver GIFs, bitmap fonts (`S*RM04P.DAT`), 23 PVR + 4 other | 3 alt/title strings (INDEX.HTML) |
| SOUND / SSONG | 20 / 364 | audio banks / song data | none |
| root | 11 | `2_DP.BIN` (text, see table), `1ST_READ.BIN`, `IP.BIN`, `DP3.INI`, `FONT.BIN`, `0GDTEX.PVR`, drivers | 2_DP, 1ST_READ |

## 3. Japanese baked into textures (ART, not text)

### Texture formats (decoder: `tools/re/datatext/pvr.py`)

* **TBD / DAT texture bundle** (7501 textures in the bundles that parse): `u32 count`; `count`
  x 16-byte records `u8 pixfmt, u8 datatype, u8 0, u8 flags | u16 w, u16 h | u32 data offset |
  u32 stamp`; data of record i = `[off_i, off_i+1)`. Flag bit 30 (0x40) -> `bzw` word LZ
  (`FUN_8c15aae4`), bit 31 (0x80) -> `bz` byte LZ (`FUN_8c15a9f4`) - this is the real
  mapping read from `FUN_8c15a776` (the literal pool at 0x8c15a7dc/0x8c15a9cc); it is the
  **opposite** of the guess written in docs/formats.md ("1 = bz, 2 = bzw"), which should be corrected. Same codecs as
  `tools/bzlib.py` (`decompress_bz/_bzw` with `orig_size=None`).
  **PROVEN** (`texverify.py`): all 7501 records decompress; 7499 have exactly the size
  implied by (datatype, w, h) (2 use a palette datatype that is not implemented; mip
  types checked as `>=`). 5937 records are `bz`, 1045 `bzw`, 519 stored.
* **PVR** (GBIX+PVRT, members `*.pvr`, `tex~N.pvr`, `DPTEX/*.PVR`): standard header,
  pixfmt 0/1/2 (ARGB1555/RGB565/ARGB4444), datatypes 1/2 twiddled, 3/4 VQ, 9 rectangle,
  0xD twiddled rectangle, 0x10/0x11 small VQ.
* Pixel layout verified by eye on text-bearing textures (x bits at odd twiddle positions,
  VQ 2x2 blocks): square twiddled, VQ, rectangle and twiddled-rectangle decode cleanly
  (see PNGs). **Small VQ (0x10/0x11, 4307 textures) is NOT verified**: renders look
  striped/garbled, so its codebook-size rule or mip layout is probably wrong (INFERRED
  from PuyoTools numbering only). Palette types (pixfmt 6/datatype 7, 6 textures) are not decoded.
* Re-encoding for translation is not implemented here (the twiddle/VQ encoders are
  not written). Putting a finished payload back into the container IS implemented now:
  `tools/texinject.py`, see `docs/texture-injection.md` (loader constraints, optimal-parse
  re-compression into the original slot, every container kind, self-test).

### Inventory (`tools/re/datatext/texinv.tsv`, 32374 textures incl. duplicates; script `texinv.py`)

JP-in-art column is from *viewing* sampled textures (PNG contact sheets in
`tools/re/datatext/png/`), not an automatic detector. A detector for "contains Japanese"
does not exist; counts are textures per source, not per Japanese text.

| source | textures (unique) | Japanese in art? | evidence |
|--------|------------------:|------------------|----------|
| `GAME/ALLLOGOS.BIN` | 66 (66) | **YES - club/national-team names** (4 names per plate: `ヴェルディ FC東京 F・マリノス フロンターレ`, `ノルウェー代表 モンロビアFC ...`) | `sheet_GAME_etc.png`, `sheet_GAME_photo_unif.png` |
| `GAME/STAFFLST.ZAR` | 62 (62) | **YES - staff name plates** (`保戸塚 哲也`, one texture per person, `s_<name>.pvr`) | `sheet_GAME_photo_unif.png` |
| ETC_DATA UI atlases (`OPTION/G_INCOME/G_RESULT/INVEST/SP_DATA/SPONSOR/HELP/TITLEM/...DAT`, `*.TBD`) | 1613 (786) | **YES** (mixed): `その他 得点者 選手評価点` (G_RESULT), menu items in `HELP.DAT` (`つくろう博士 コマンド解説 育成指南 サッカー用語集`), `サカつく` logos; OPTION atlas is English | `sheet_UI1.png`, `sheet_UI2.png` |
| `ATFIRST/TITLE.DAT` + `ETC_DATA/TITLE*.DAT`, `LOGO.DAT` | 118 incl. rest of ATFIRST | **YES - title logo** `サカつく 特大号 2 J.LEAGUE プロサッカークラブをつくろう!` (TITLE.DAT #9); copyright line is English (#7); SEGA logo | `TITLE_DAT_9.png`, `TITLE_DAT_7.png` |
| `TRAINING/TRAINING.TBD`, `ICON.TBD`, `PAPET.TBD` | 132 (108) | **YES** (menu `練習指示 基本方針変更 練習実行 特別調整 選手配置 システム 戦術 中盤守備 DFタイプ キッカー指定`), formation/instruction icons are English | `sheet_UI3.png` |
| `FLOW_PRG/*.ZAR` members (TWND*, OFFD*, CHSET*, STSET*) | 3375 (726) | **PARTLY**: atlas strips with `日程進行 オフィス 練習場 ミーティングルーム ユース サポーターズクラブ 地元団体 ...` and `大好況 好況 横ばい 不況`; town/office icons carry English captions; STSET = stadium surface textures (no text) | `sheet_FLOW_TWND1.png`, `sheet_FLOW_OFFD1.png` |
| `ETC_DATA/*.ZAR` members (DRSGPPVR, NEWSOPED, GAMEOVER, D_ROOM, DR_TRO, SUPPORT, LOCAL, ...) | 1169 (809) | not sampled in full; DRSGPPVR = coach/staff portraits (no text) | - |
| `ETC_DATA/MCH*.TBD`, `MINILOGO.TBD`, `DATAROOM.TBD`, `CHALDANI.TBD`, `CE_TEX.TBD` | counted in ETC_DATA row | `MCH*` / `CE_TEX` not sampled (UNKNOWN) | - |
| `NEWS/*` (STUDIO1-6, CHAMP_*, MATTITLE.ZAR) | 350 (288) | `MATTITLE.ZAR`: **English** banners ("ASIA CHALLENGE CUP"...); studio sets: no text seen | `sheet_NEWS_MATTITLE.png` |
| `EVENT/*` | 462 (417) | not sampled in full (3D event assets/backdrops) - UNKNOWN | - |
| `GAME/ALLJNAME.BIN`, `ALLPNAME.BIN`, `BINDNAME.BIN`, `BINDMTCH.BIN`, `BINDLOGO.BIN` | 28 / 54 / 103 / 37 / 80 | **NO**: English logos of the fictional clubs (`Tempest`, `VULCAN`, `Avalanche`), competition banners `ASIA TOURNAMENT`, `WORLD CHALLENGE CUP` | `GAME_ALLJNAME.png`, `GAME_ALLPNAME.png`, `sheet_GAME_misc.png` |
| `GAME/BINDFLAG.BIN` + `ALLFLAGS.BIN` | 3193 (2831) | NO in samples (flags, pennants with English club names) | `sheet_GAME_etc.png` |
| `GAME/BINDUNIF.BIN` | 20333 (12071) | NO in samples (kit textures, shirt numbers) | `sheet_GAME_photo_unif.png` |
| `GAME/JPHOTO.BIN` | 726 (726) | NO (player face photos) | `sheet_GAME_photo_unif.png` |
| rest of GAME (`GAMEETC.ZAR`, `SKINCOMM.ZAR`, ENV*.ZAR sky bundles) | 164 + 246 | not sampled (UNKNOWN) | - |
| `DPTEX/*.PVR` (Dream Passport UI) | 23 | **YES** (`OPTION02.PVR`: network settings labels `電話番号1 ログインID プロバイダー ...`, `SKB_KANA.PVR`: soft keyboard); dead feature, lowest priority | `DPTEX_OPTION02.png` |
| `FACE/*`, `MASCOT/*`, `GAME2/*.TBD` | 11 + 28 | faces/mascots/backgrounds, no text expected (UNKNOWN) | - |

Texture-translation workload (INFERRED from the samples): high priority = title logo,
TITLE/OPTION/HELP/G_RESULT/G_INCOME/INVEST/TRAINING menu atlases (each a few tens of
texture cells), FLOW_PRG TWND/OFFD atlas strips; special case = **ALLLOGOS (66) and
STAFFLST (62)**: these are *names* rendered to images - they have to be regenerated with
a Latin font (or the game switched to the BPINFO/overlay name text) rather than painted
over. Needs: encoder for twiddled/VQ 4444/565 and a build step that repacks TBD/PVR
(not implemented).

PNGs (decoded by `pvr.py`, sheet tool `sheet.py`): `tools/re/datatext/png/` (14 files).

## 4. Tools and reproduction

```
python -I -X utf8 tools/re/datatext/test_all.py          # all round trips (codec, INI, BPINFO, ptrblob)
python -I -X utf8 tools/textfmt_ini.py --write            # translation/DPETC__MESSAGE.INI.jsonl
python -I -X utf8 tools/textfmt_bpinfo.py --write         # translation/ETC_DATA__BPINFO.BIN.jsonl
python -I -X utf8 tools/textfmt_ptrblob.py --write        # translation/ROOT__2_DP.BIN.jsonl (only 2_DP.BIN is written)
python -I -X utf8 tools/re/datatext/survey3.py            # survey3.tsv
python -I -X utf8 tools/re/datatext/texinv.py             # texinv.tsv
python -I -X utf8 tools/re/datatext/texverify.py          # TBD decode check
python -I -X utf8 tools/re/datatext/sheet.py out.png <tbd/pvr files...> [--max N --cell 128]
python -I -X utf8 tools/re/datatext/findbase.py <image>   # base-address voting
```

APIs: `textfmt_ini.extract(bytes)/apply(bytes, entries)`, `textfmt_bpinfo.extract(bytes, source)/apply`,
`textfmt_ptrblob.extract(bytes, base, source, unref=False)/apply(bytes, entries, base, relocate=True)`.
`--write` merges existing `en` values (never destroys translations); all writers are deterministic.

JSONL files written by me: `translation/DPETC__MESSAGE.INI.jsonl` (849),
`translation/ETC_DATA__BPINFO.BIN.jsonl` (5321), `translation/ROOT__2_DP.BIN.jsonl` (157).
The `ROOT__` prefix is mine (2_DP.BIN is outside the owned prefixes); ATFIRST/1ST_READ are
deliberately not written to avoid clashing with textdb.

## 5. Open items / UNKNOWN

* No place in this scope holds dialogue; if some event text is not in the overlays it would
  have to be in a format not yet recognised (none of the 175 EVENT files has any
  cp932 text; no alternative encodings were found by inspection, but a custom-encoded
  text table cannot be excluded without tracing the overlay code).
* BPINFO: real in-game buffer width for names (13-char limit) unknown; the game also draws
  player names from textures in some screens (STAFFLST, ALLLOGOS are such cases for staff
  and clubs).
* Small-VQ decoding, palette textures, texture encoders/repackers: not done.
* 2_DP.BIN: which of the 157 pointed strings are really displayed; relocation behaviour.
* The texture "JP-in-art" column is based on viewing ~250 sampled textures, not exhaustive.

## 6. `/BCAST/BCAST.BIN`: the voice-clip subtitles (tx5, 2026-11-11; the blind spot of sections 0-5)

The survey above skipped `BCAST/BCAST.BIN` ("media, not text").  The first real playtest of `prop7` showed the match overlay / attract demo
in Japanese (`なるほど。放送席、解説は水沼貴史さん、実況は八塚浩でお送りいたしました。`), and a cp932 search of `extracted/`, `build/unpacked/` and
the RAM dumps finds that sentence **nowhere except in this 630 MB file** (it is in no `extracted/` folder: `BCAST/` there holds only the two
`ENDING_*.P04` audio files).  PROVEN by `tools/re/tx5_bcast_scan.py` (whole file, 3.8 s) and `tools/textfmt_bcast.py stats`.

| | |
|---|---|
| file | `/BCAST/BCAST.BIN`, LBA 68002, 307,326 sectors (the other 99 % of the data area is its audio), not in `extracted/` |
| structure | 26,635 clips, each ONE 2048-byte header sector + the ADPCM audio sectors; clip folders `kk` 3,525 (commentator Kimura), `mm` 3,267 (Miyazawa), `mt` 3,320 (Mizunuma), `yh` 7,494 (announcer Yatsuka), `name` 9,029 (player callouts) |
| header | `+0x00 "PCM FILE START  "`, `+0x10` name (`yh\yh_end_aisa_0002.p04`), `+0x40 "size:11616"`, `+0x50 "<start sector> - <audio sectors>"`, `+0x60` u32 LE offsets of the text segments (0-terminated, up to 8), `+0x80..` the segments: **cp932 text, NUL terminated, on the 16-byte grid** |
| segments | 30,083 non-empty (24,273 clips have 1, 2,362 have 2-6).  Name clips: segment 0 = reading (hiragana, or half-width katakana for foreign names), the following segments = kanji variants of the same surname (homophones), nothing else in the header |
| what reads it | the match overlay (`FLOW_PRG/GAME.BIN`) draws the segments as the commentary box while the clip plays; consecutive clips of one utterance are shown one behind the other (`mt_aidu_0002` "なるほど。" + `yh_end_aisa_0002`), without a separator |
| the draw engine | `GAME.BIN`'s own message engine (compile `0x8c3200f2`, draw `0x8c3202b0`; docs/font-hook-notes.md s6): monospace 12 px cells, **37 cells per line** (a character is accepted past column 37 only when it is a kinsoku punctuation, hard stop at 39), 3-line ring buffer; markup `@x/..@`; control characters below 0x20 other than space are drawn as glyphs, so **no `\n`**; the proportional-font patch does not cover it |
| distinct text | 19,002 distinct ja (556 KB cp932): 13,618 commentary lines + 5,396 name strings; markup-free (no `@ % #`) |

### 6.1 Pipeline

* `tools/textfmt_bcast.py` (`stats`, `extract [--write]`): header parser, `translation/BCAST__BCAST.BIN.jsonl` (30,083 records, compact JSON like
  textdb, `fmt: "bcast"`, id `BCAST/BCAST.BIN#<hex file offset of the segment>`, `ctx` `clip yh\yh_end_aisa_0002 seg 0/1 slot 64`).
  `max_bytes` is the DISPLAY budget, not the slot: 75 (74 characters + NUL = 2 lines x 37 cells) for commentary, 16 for name callouts.
  Existing `en` / `skip` are kept by id when the `ja` is unchanged.
* `build_patch.do_bcast` (handler `bcast`, `FileReport.kind` `bcast`): reads the clip header from the ORIGINAL disc, checks that the
  segment still holds `ja` (else SKIPPED), `apply_to_header` writes the English in place when it fits the segment's slot, otherwise
  **re-lays the clip out** inside its sector (segments packed on the 16-byte grid from +0x80, offset table at +0x60 rewritten; the room is
  1920 bytes) and FAILS only for newline / non-cp932 / over budget / no room.  **The blank between two clips** (`build_patch.bcast_clip_text`, flag
  `--clip-lead-space {on,off}`, default = `--cell-prop`): the Japanese needs no gap between consecutive clips, English does, and the engine adds none.
  * **ON (standard build, needs `--cell-prop on`): one LEADING blank** in front of every clip whose English starts with a letter, a digit or an opening mark
    (`"`, `(`, `*`), **nothing appended**; a clip that starts with `, . ; : ! ? ) ] }` or `'` (`, isn't it?`, `'s play; how was it?`, `, our sponsors ...`: 3 records) gets none.
    The rule looks only at the first character, **not at the folder**: player names (folder `name\`, 12,480 records), team names (`yh_tm_*` and `yh_new_team_*`,
    1,511 records) and stadiums (`yh_stadi_*`, 283) get a leading blank like every other clip, because they follow `The one to watch in this match,` or `Seoul FC vs`
    (a name or team that got no blank in front would read `match,Suzuki` / `vsGrampus`).  Nothing is appended, so `Suzuki` + ` Cuts it out easily here.` and `Grampus` + `, ...` / `'s ...` read right.
    A clip that ends in `,` `:` `.` or `-` followed by a leading-blank clip gives exactly one blank; two word clips give one; a bare number or unit (`9`, ` points`) one.
    The blank in front of the FIRST clip of an utterance and the blank that a line wrap leaves at the start of the next line are skipped by the `--cell-prop` engine
    (`blank at column 0`, docs/layout-issues.md s19: no cell, no unit; whether the engine's init resets the column for every utterance is not proven statically, at worst the first clip of an utterance shows one mid-line gap), while a
    blank in the middle of a line advances like any other (12 px, the blank advance of the font table); that is why the flag needs `--cell-prop on` (explicit `on` without it is refused).
  * **OFF (`--cell-prop off`, the old recipe): one TRAILING blank** after every clip except the name callouts (folder `name`), as before: names get none, so a clip that follows a name
    reads `SuzukiCuts it out`, and a team name gets one even in front of punctuation (`Grampus , ...`): the two defects that the leading rule removes.
  * Budget: the blank costs one byte like the trailing one did; commentary stays <= 73 characters (+ the blank = 74 + NUL = 75).  A name callout has 16 bytes (15 + NUL): the 14-character
    names fit with their blank, the five 15-character epithet names (`Japan's Big Gun`, `World's Big Gun`, `General Affairs`, `Solo Four Kings`, `Liberia Phantom`, 10 records: nnf / nns) no
    longer did and were shortened (`Japan Big Gun`, `World Big Gun`, `Gen. Affairs`, `Solo 4 Kings`, `Liberia Ghost`; `Asia's Big Gun` -> `Asia Big Gun` for consistency); the four 15-letter names
    of the `obf`/`obs` folders have a 64 byte slot and fit.  `tools/test_bcast.py` writes the whole database in leading mode (all 26,635 real headers, nothing fails).
  * Clips that read after a player name are written as third-person verbs (`Cuts it out easily here.`), and the half-time headers end in a comma (`First half,`).
  * Read back a built disc: `tools/re/tx5_verify_bcast.py build/trial NAME [--blank lead|trail]` (default `lead`).
* `discbuild.plan_patches(..., sparse={iso path: {offset: bytes}})` / `build_disc(..., sparse=)` rewrite only the touched sectors of a file that
  is NOT replaced whole (never changes a size or moves a file); `res.sparse` in `build_patch`; `verify_disc` gets the streamed SHA-1 of the
  patched file (`discbuild.sparse_sha1`) as `expect`; `patches_digest(patches, sparse)` hashes the sparse edits only when there are any
  (default digests unchanged).  The disc is unchanged in size: 13,000+ header sectors are rewritten, no file moves.
* Tests: `tools/test_bcast.py` (header edit in place / re-layout / failures / identity on all real headers / jsonl against the disc /
  sparse plan).  Read-back of a built disc: `tools/re/tx5_verify_bcast.py build/trial/NAME NAME`.

### 6.2 Translation (English written by the text owner, not by a tool)

* Name clips (12,480 segments): `tools/re/tx5_names.py` (Hepburn romanisation of the hiragana reading, no macrons, long vowels not marked;
  half-width katakana from the DB's own translation of the same word, two tokens `Family Given` written `Given Family`; 501 katakana tokens the DB does
  not know are machine-romanised and listed by the script; ~100 nickname clips (`yh_name_nnf_*`, epithets such as 大砲, 守護神) translated by hand
  (`build/tx5/results/names_epithets.tsv`)).  Every kanji variant of a surname gets the same romanisation.
* Proper-noun clips (`yh_tm_*` club / national-team names with particles, `yh_stadi_*` stadiums, 1,070 distinct): `tools/re/tx5_mech.py`, built from the DB's
  half-width word translations plus `tools/re/tx5_mech_override.tsv` (full forms for words the DB only holds as slot-forced abbreviations: `Mars.` -> Marseille ...).
* Numeric clips (minutes, matchdays, points): `tools/re/tx5_gen_numbers.py`.  Equivalent lines that differ only in punctuation or the speech ending
  of the three commentators: `tools/re/tx5_propagate.py` (exact match after normalisation only).
* Everything else by hand in numbered batches (`tools/re/tx5_batches.py`, `tx5_next.py`, `tx5_merge.py`, frozen numbering in `build/tx5/distinct.tsv`).
  Rules: commentary <= 73 characters (+ the builder's clip blank, leading or trailing = 74 = two full 37-cell lines), ASCII, no `@ # %`; names of the commentators in
  full (`Hiroshi Yatsuka`, `Takashi Mizunuma`, `Kazushi Kimura`, `Michel Miyazawa`), honorifics dropped (style guide 2), V-goal and golden goal kept,
  `Match 3`, `Round 2`, `Kick-off!` forms.  The state is in section 6.3 of docs/uncovered-text.md (counts).
* Not done by design: the English is NOT padded / wrapped to the 37-cell lines.  The engine wraps per character (it breaks a word that straddles
  column 37) and the start column of a clip depends on the clips shown before it (UNKNOWN); a wrapper that assumes column 0 would mis-break the
  second clip of an utterance.  If the playtest shows ugly breaks, the builder is the place for a `--bcast-wrap` option.

### 6.3 Proof (trial build `build/trial/tx5_p7`, standard flags + `--strict`, 2026-11-11)

`python -I -X utf8 tools/build_patch.py --repack on --share dup --append-safe --proportional-font on --strict --out build/trial/tx5_p7 --name tx5_p7`
(log `build/trial/tx5_p7.log`): **388,058 strings applied, failed 0, skipped 0**, of which `bcast /BCAST/BCAST.BIN` 20,914 (all in place: no English needed the clip re-layout
in this build; the re-layout path is covered by `tools/test_bcast.py`), 48,841 sectors rewritten, **no file moved, end LBA unchanged (549150)**, `verify_disc` OK (0 errors,
0 warnings, V7: the 198 expected files incl. the streamed SHA-1 of the sparse-patched `BCAST.BIN` read back byte-identical), patch digest `28a9358a8fab31f97f5d0ce91720f7e78d8d0d2f`,
127 s.  `python -I -X utf8 tools/re/tx5_verify_bcast.py build/trial/tx5_p7 tx5_p7`: 26,635 headers found, name / size / tag lines and the table byte-identical to the
original, 20,914 English segments read back equal to the records, every other segment unchanged, 29,278 audio sectors compared equal to the original disc: RESULT OK.
Not run in the game: whether `GAME.BIN` shows the English exactly as the Japanese was shown (the engine reading was by disassembly, section 6 table), and how consecutive
clips are joined and wrapped (6.2 last bullet).
