# Overlay text (FLOW_PRG/*.BIN, ATFIRST/*.BIN, 1ST_READ.BIN)

> **Status note (docs, 2026-11-11).** Written at stage 1, when every `en` was empty (as the next paragraph says). The database now carries English for 99.6 % of its 368,492 records and also holds table records (docs/uncovered-text.md); `tools/textdb.py` still reads and writes the format described here.

Code: `tools/textdb.py` (extract / insert / stats), `tools/test_textdb.py` (self-test),
database: `translation/FLOW_PRG__<name>.jsonl` (112 files) and `translation/ATFIRST__{HELP,TITLE}.BIN.jsonl`.
All `en` fields are empty. Status words: PROVEN = run and checked here, INFERRED = follows
from data but not tested on hardware/emulator, UNKNOWN.

Run: `python -I -X utf8 tools/textdb.py extract | insert | stats`, `python -I -X utf8 tools/test_textdb.py [--quick]`.

## 1. Which images contain Japanese text (PROVEN by extraction)

| image | base | text? |
|---|---|---|
| FLOW_PRG/*.BIN (113 parse as overlays) | stub literal (see below) | 112 yes, FACEMDUL.BIN no (only noise), SECBND.BIN is not an overlay |
| ATFIRST/HELP.BIN, ATFIRST/TITLE.BIN | 0x8cb60000 / 0x8c6d0000 | yes (683+17 / 493+22 strings; same text as the FLOW_PRG copies, which differ in a few bytes) |
| ATFIRST/FACEMDUL.BIN | 0x8cba0000 | no |
| ATFIRST/BPINFO.BIN, FONT.BIN | - | not SH-4 overlays (handled by other tools) |
| 1ST_READ.BIN | 0x8C010000 | yes but small: 206 referenced strings, 1372 JP chars (menu/news-category labels at 0x157898..). Supported by the code, jsonl NOT written here: `translation/ROOT__1ST_READ.BIN.jsonl` belongs to the textfmt_* tools |
| FLOW_PRG/*.ZAR | - | containers, their members live under build/unpacked and are not covered |

Base correction: `overlay.unpack_overlay` trusts the stub literal when < 10 pointers hit strings.
For FLOW_PRG/GETREP.BIN that picks 0x8c2f0000 (4 hits); under 0x8c2d0000 269 distinct pointers
hit accepted strings, so `textdb.load_image` uses 0x8c2d0000 (`refine_base`). LOADBAR.BIN has
no strings either way. GAME.BIN: the ~400 KB tail beyond 0x1ec890 contains no accepted text
(0 strings with offset >= 0x1ec890); all 863+274 strings use base 0x8c2d0000.

## 2. What a "string" is

Pointers: every 4-byte aligned little-endian word whose value is in [base, base+size) is a pointer
(pointer tables, structure fields and `mov.l @(disp,pc)` literal pools are all just aligned words).
A pointer target t starts a string if the bytes up to the next NUL are plausible cp932 text:

* all bytes are ASCII 0x20..0x7e, 0x0a, half-width katakana, or valid cp932 double bytes
  (leads 0x81..0x9f/0xe0..0xea, but not row 0x87 and not 0xeb..0xfc), at least one double-byte char,
  no strictly increasing byte run >= 8 (sorted code tables), no in-image pointer pattern;
* control bytes (< 0x20 except 0x0a) only if >= 3 full-width chars, <= 4 control bytes and mostly text;
* strings without any hiragana/katakana (kanji names, half-width words) only with common kanji
  (JIS level 1 at least half of the characters) and little ASCII besides the game markup;
* a target not preceded by NUL (record tables) is accepted only if it is clean text (no half-width
  kana, no level 2 kanji) or sits in a pointer table next to accepted neighbours.

Pointers lying inside an accepted string are text, not pointers. A pointer into the middle of an
accepted string is an "interior pointer" (35 strings); such strings are pinned in place.

**Orphans** (`"orphan": true`, `refs: null`): strict NUL-bounded runs (>= 2 full-width chars,
no control bytes, no pointer pattern, few level 2 kanji / ASCII) that no pointer references. They
are mostly fixed-size name records (player names in a 14-byte field followed by the half-width kana
reading) and packed prose blocks that are reached by index/offset computation (TRAINING.BIN tactic
texts at 0x44f00.., GAME.BIN commentary labels at 0x80400..). How they are addressed is UNKNOWN
(no u16/u32 offset table with matching spacing was found for TRAINING.BIN 0x4500f..). They can only
be patched in place, never relocated. Names with leading control bytes (HELP.BIN 0x296d3..) and
half-width-only strings are not extracted by the textdb scan itself (known gaps) - since the coverage audit they are written by
`textdb.py extract` as separate records (`fmt` = `hwptr` / `recarr`, stat-preceded record fields and half-width pools, in place only;
docs/uncovered-text.md, docs/pipeline.md s8).  `1ST_READ.BIN` has `translation/ROOT__1ST_READ.BIN.jsonl` (ptrblob handler).

Statistics (`textdb.py stats`, PROVEN): 115 images, **120152 strings** (82267 referenced, 37885
orphans = 31.5 %), 1,246,593 non-ASCII chars, 2,631,925 raw bytes. Only **25147 distinct** `ja`
texts (20.9 %): the big overlays statically link the same library (about 1400 strings and about 2070
player/town names appear in every one of ~50 overlays), so translate by unique text; `tools/textdb.py`
keeps one record per place, a translation-memory pass can fill duplicates (same `ja`).
Top 20 by JP chars (ref / orphan / chars / bytes):
MEETING 7523/25/180255/369166, NEWS 3695/7/131946/298872, TRAINING 1226/1565/121701/251547,
DRAFT 1556/7/57535, ATFIRST/HELP 683/17/51926 (FLOW_PRG/HELP identical size), SCDRF 836/25/35252,
EVENT 2579/27/32010, NEWS_ED 2042/5/27858, GAME 863/274/26324, SPF_READ 1892/2095/18013,
ESTABLIS 1798/0/16547, BPMATCH 1491/2078/15186, CHALMODE 1583/2067/14917, DMCLBEDT 1420/2078/14181,
ENDOPT 1449/2063/14166, BACKUP 1414/2073/13468, EXTRADE 1407/2073/13424, SPONSOR and SPONSOR2
1756/6/13421. Full table: `python -I -X utf8 tools/textdb.py stats`.

## 3. Text encoding in the database (`ja` / `en`)

Real characters for cp932 text, `\n` for 0x0a, `<XX>` (upper-case hex) for every other byte
(control bytes, invalid sequences, double bytes that do not round-trip through Python cp932),
`<3C>` for a literal `<`. decode/encode is exact for all 120152 strings (PROVEN, test).
The game's own inline markup is plain ASCII inside the text and must be kept verbatim in `en`:
`@Y/..@`, `@O/..@`, `@R/..@`, `@K/..@` (colour/emphasis spans), `#tk20#`, `#chi#`, `#kyu#`, `#to#`,
`#ken#`, `#sname#` (name/title substitution tokens), `%s %d %2d` printf formats.
`max_bytes` = string + NUL + following zero bytes up to the next non-zero byte, the next pointer
target or the next accepted string (`--pad-mode full`, default, = what the jsonl shows);
`--pad-mode safe` counts only the fill up to the next 4-byte boundary. Measured: the padding is
tiny - for referenced strings the sum of `max_bytes` is only 0.02 %..1.3 % above the sum of
(length+1) for MEETING/NEWS/TRAINING/HELP/GAME and 5.7 % for EVENT; the text is packed.
(Risk, INFERRED: a zero word after a string could be real data; use `safe` if in doubt.)

## 4. Reinsertion (`insert_image`, `textdb.py insert`)

1. Strings whose English (+NUL) fits `max_bytes` are written in place (tail zero filled).
2. The others are relocated: all pointer words of that string are rewritten and the string is
   placed in free space = the freed regions of relocated strings and the tails of shortened
   strings (best fit, strategy A); if that fails the pooled regions of *all* translated strings are
   re-allocated at once (strategy B, merges the space), after dropping the strings with the
   largest overshoot when the demand exceeds the pool. Free bytes are zeroed. Byte strings need no
   alignment. Pointer words are only rewritten at positions found in the original image.
3. Not relocatable (reported as failed, original Japanese kept): orphans, interior-pointer strings,
   and members of a fixed-stride table that contains un-pointed entries (`pinned`, 34868 strings
   incl. orphans: name tables of ~2040 records per overlay).
4. `--append`: strings that still do not fit are appended after the image (4-byte aligned, image
   grows, pointers rewritten). Off by default; never done for 1ST_READ.BIN. Whether the loader
   tolerates a longer file (read size, memory after the image, BSS clear range) is UNKNOWN (the
   textengine work decides); the stub's end literal is NOT patched.
5. `--zero-runs MIN`: UNSAFE opt-in, also uses zero runs >= MIN bytes outside strings. Not tested
   on hardware; such runs may be zero-initialised variables (GAME.BIN has 436 KB of them,
   1ST_READ 1.4 MB, the other big overlays only ~2-6 KB).

Report line per image: translated / in_place / relocated / appended / failed (with reasons).
Stale entries (id or `ja` not matching the image) are skipped and reported.

## 5. Capacity (the real constraint)

Slack-only reinsertion is a pure capacity problem: it succeeds only while the total English
(each string + NUL) is <= the total JP region (~0.99x), measured by translating *all* referenced
strings with random length factors (PROVEN, synthetic ASCII):

| image | EN/JP-bytes, uniform factor | failed | mixed U(0.4,1.4)/U(0.5,1.5)/U(0.6,1.6), need/pool 0.90/0.99/1.09 |
|---|---|---|---|
| MEETING | 1.0 all in place; 1.1+ : ~99 % fail | | 0 % / 0.0 % / 48 % failed |
| NEWS | - | | 0 % / 0.0 % / 43 % |
| HELP | 1.1+ : 97 % | | 0 % / 0 % / 51 % |
| TRAINING | 1.1: 90 % | | - |
| EVENT | 1.1: 29 %, 1.2: 37 %, 1.4: 75 % | | - |

English is normally longer than 2-byte Japanese (INFERRED rule of thumb 1.1-1.6 bytes of English per
Japanese byte for prose; names and labels are shorter) - there are no translations yet, so the
real ratio is UNKNOWN. Consequence: for the prose files (MEETING, NEWS, TRAINING, DRAFT, HELP,
EVENT, SCDRF) slack alone will not carry a full translation; either the English must average
<= the Japanese byte size, or `--append` (or another memory area chosen by the engine work) is
needed.

## 6. Tests (PROVEN, `tools/test_textdb.py`, 44 s, 0 failures)

* codec round trip of every string (117 images, 120152 strings, 2,631,925 bytes);
* extract -> jsonl text -> insert with all `en` empty: every one of the 117 images is
  byte-identical to the original; the jsonl files on disc equal a fresh extraction;
* synthetic: 300 random referenced strings each in MEETING, EVENT, TRAINING, HELP, GAME (206 in
  1ST_READ) get ASCII text of lengths {1, L/2, L-1, L, L+1, 2L, 4L, 3}: all pointers of all
  translated strings resolve to the new text, every other string and pointer is unchanged,
  every changed byte lies in a translated string's region or is its pointer word, image size
  unchanged (and 4-aligned growth with `--append`; appended mode leaves no failures);
* stress: all 7523 referenced MEETING strings at factor 1.0 (all in place) and 1.3.

Not tested: running the patched overlays (no emulator in this work); re-extracting a patched
image does not rediscover ASCII text as Japanese by design.

## 7. Open points / handover

* Ownership clash: `tools/textfmt_ptrblob.py` (datatext) also lists ATFIRST/HELP.BIN and TITLE.BIN;
  `translation/ATFIRST__*.jsonl` are written by `textdb.py extract` (whoever runs last wins; the
  ids and `ja` agree because the other tool imitates the same convention).
* Orphan addressing (names, TRAINING/GAME blocks), references from other images (e.g. 1ST_READ
  tables pointing into overlays) and half-width-only strings are not resolved.
* Some accepted strings are probably junk (short strings in data tables); sampling 45 random
  referenced and 60 random orphan strings found none, but there is no ground truth.
