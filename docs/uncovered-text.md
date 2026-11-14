# Uncovered text: coverage audit and the table records it led to

Tools: `tools/uncovered.py` (audit), `tools/textfmt_recarray.py` and `tools/textfmt_hwkana.py` (extract / apply),
`tools/textdb.py extract` (writes the records), `tools/build_patch.py` (`do_extra`), `tools/test_uncovered.py` (self-test).
Research helpers (`tools/re/`): `uncovered_find.py`, `findenc.py`, `covcheck.py`, `ramfind.py`, `ramjp.py`, `ramjp2.py`,
`ram_resident.py`, `arrptrs.py`, `codereaders.py`, `hexrec.py`, `ctx.py`, `namescan.py`, `hwprobe.py`, `hwstat.py`,
`recarr_survey.py`, `hwpool_survey.py`, `extra_report.py`, `extra_tables.py`, `extra_sources.py`, `extra_overlap.py`, `extra_sample.py`
(all read-only; none launches the emulator).
Status words as everywhere: PROVEN = ran code over the whole disc / file and checked; INFERRED = deduced, not run in the game; UNKNOWN.

## 1. Why: playtest finding 1

The playtest showed Japanese where the text database already held English: the rival club ("サリーレ"), hometown names
(`Izu Is.青ヶ島村`), club-name suffixes (`Aogashi` + ミュートス), manager / coach names in the Event list (織田 道三, 前田 満, 横池 拳,
ﾋﾞﾗｶｽ, ﾙﾄﾞﾅｯﾌﾟ).  The first suspicion (the text DB does not know these strings) was wrong for the town: every pointer-table copy of
青ヶ島村 was already translated (`Aogashima`, 34 overlays, RAM dump `build/emu/pt1_ram.bin` shows `Yokoha.\0Aogashima\0Oshima`).
The drawn strings come from **other copies of the same data** that `tools/textdb.py` cannot see, because its acceptance
rules are "NUL-preceded orphan" or "pointer target with at least one full-width character":

| gap | rule that rejects it | what is behind it |
|---|---|---|
| fixed-size records whose text field follows a **non-zero stat byte** | orphan scan needs a NUL (or start of run) in front | municipality records, manager / coach / player records |
| **half-width katakana only** strings | `accept_referenced` / `accept_orphan` need a full-width char (docs/overlay-text.md s2, "known gap") | club-name pool, countries, leagues, foreign player name parts, industries |
| strings in pools **nothing points at** and that mix hw kana with ASCII / full-width | orphan rules | NENREP competition names |
| `1ST_READ.BIN` | `textdb extract` skips it (`--with-1st-read` off), ptrblob `WRITE` only had 2_DP | 204 report / news category labels |

## 2. Where the named strings live (PROVEN unless marked)

Method: every string searched as cp932, EUC-JP, UTF-8, UTF-16 and ISO-2022-JP in `extracted/`, `build/unpacked/` and the RAM dump
(`tools/re/uncovered_find.py`, `findenc.py`).  Result: the strings exist only in the overlays / `1ST_READ.BIN` / `2_DP.BIN`
(2_DP: the IME dictionary, not UI); none is in a container member, a texture bundle or an `ETC_DATA/*` table
(ETC_DATA/BPINFO.BIN holds player names only).

| text | file(s) | format | what reads it |
|---|---|---|---|
| 青ヶ島村, 延岡市 and all ~1270 municipalities, record array copy | `FLOW_PRG/HOMETOWN.BIN` `#159f0 ... #3ca0x`, id of 青ヶ島村 = `#15c66` (behind stat byte 0xC9), 延岡市 `#322b0` | 1270 records of **126 bytes**: kanji name field **35 bytes** at the record start, hiragana reading 35 bytes behind it, numbers; 256 names had a 0 byte in front (already orphan records, translated), **1014 had a stat byte (new records, fmt `recarr`)** | array base words `0x8c2e5972` (= first name, 4 `mov.l` sites, first at `0x8c2d0e12`) and `0x8c2e5970` (11 sites) in HOMETOWN.BIN (`tools/re/arrptrs.py`) |
| 青ヶ島村 ... pointer-table copy | 34 overlays, `tbl@...[456/1270]` | pointer table of 12-byte slots | translated (`Aogashima`), resident in pt1 RAM (`0x8c527086`, `0x8c703e9e`); **not** the copy that printed Japanese (INFERRED from the screenshot: prefecture `Izu Is.` is from this table, the municipality is not) |
| サリーレ = `ｻﾘｰﾚ`, ミュートス = `ﾐｭｰﾄｽ` and the whole club-name pool (`ﾀﾞﾐｰﾁｰﾑ ﾃﾝﾍﾟｽﾄ ｳﾞｧﾙｶﾝ ... ﾊﾟﾚﾝﾃｨｰｱ`, 55 names) | stored **half-width**; in 30+ overlays, e.g. `AUTOSAVE.BIN#33024` (ﾐｭｰﾄｽ) `#33044` (ｻﾘｰﾚ), pointer table `tbl@247a8[0..54]` | NUL-terminated cp932, 4-aligned, slots 4 / 8 / 12 bytes (`fmt hwptr`); in `NENREP.BIN#2a568 / #2a588` the same pool without pointers (8-byte slots, `hwpool`) | the table (address `0x8c8f47a8` in AUTOSAVE) is loaded at 4 sites (`0x8c8da384`, `0x8c8e0124`, `0x8c8e133a`, `0x8c8ea022`); pt1 RAM holds the pool at `0x8c2f9510` / `0x8c2f94f0` (+2 copies) |
| club = town short name + suffix (`Aogashiミュートス`) | composed at run time from the two sources above | UNKNOWN: which buffer holds the composed name and its width | the screenshot text; the translation stage must keep both parts short (s5) |
| 織田 道三, 前田 満, 横池 拳, ﾋﾞﾗｶｽ, ﾙﾄﾞﾅｯﾌﾟ (managers / coaches / foreign staff) | `EVENT.BIN#d604c / #d58a4 / #d5bb4 / #d7d9c / #d8f54` (S=56 also in `TITLE` (both copies), `SEARCH`, `SCDRF`, `LOCAL`, `WEEKLY`, `MEETING`, `NENREP`, `SPF_READ`; S=112 in `ENDING`, `HELP` (both copies); S=28 in `NENREP`, `SPF_READ`) | arrays of **56-byte records** (112 / 28 bytes in the others): name field **14 bytes** at the start of the record, 42 bytes of ability / contract numbers behind it, the previous record's last stat byte in front (non-zero) -> the orphan scan found only 17 of the 778 members in EVENT.BIN (small ability bytes, 0x04-0x1c, sit in front of the name) | array base words `0x8c3a55cc`, `0x8c3aa184` loaded in EVENT.BIN at `0x8c2d1a8c`, `0x8c2d1a6a`, `0x8c2d2ed6`, `0x8c2d2f12`, `0x8c2e6162`, `0x8c2e6182`; pt1 RAM: copies at `0x8c50b6c8` (overlay at 0x8c4d0000), `0x8cb85614` (HELP) and the **working copy in the heap** `0x8ce4e400` (the Event list builds from it; Japanese because the source was) |
| player name + reading (~5300 players) in 17 overlays | S=30: `AUTOSAVE, BPMATCH, CSAVE, CSAVE4, DMCLBEDT, ENDOPT, EXFLAG, EXTRADE, LOAD, SPF_READ`; S=29: `CSAVE3`; S=60: `BACKUP, CHALMODE, FREELOAD, SONGSAVE, VTRLOAD` (+ S=240 in BACKUP) | arrays of 30 (29 / 60 / 240) bytes: hw-katakana reading `W=16`, name `W=14` (kanji, or hw for foreign players) | player database copy linked into the overlay (UNKNOWN which screens show the reading) |
| `1ST_READ.BIN` category labels (テスト用, サポーターズクラブ設立, スカウト報告 ...) | `1ST_READ.BIN#157898 ...` | 204 pointer-referenced strings | `translation/ROOT__1ST_READ.BIN.jsonl` is new (ptrblob `WRITE` now includes it) |

The half-width storage versus the full-width look of サリーレ in the screenshot: the game must convert half-width to full-width
before drawing (the string is half-width in every copy on the disc) - UNKNOWN where.  **Check in the emulator whether English
ASCII written into these slots is drawn as ASCII or widened** (a conversion routine that adds 0x8240 to every byte would draw
full-width Latin); if it widens, the hw pools need the conversion hook, not only a slot.

## 3. The audit (`tools/uncovered.py`)

```
python -I -X utf8 tools/uncovered.py [--tdb DIR] [--members build/unpacked] [--out build/uncovered] [--only SUBSTR ..]
```
Scans every file of `extracted/` (containers at offset 0 are replaced by their decompressed members under `build/unpacked`, made by
`tools/unpack_all.py`; high-entropy files and media are skipped and counted), finds NUL-terminated cp932 runs (kana, kanji,
half-width katakana, `Family Given` names, and kanji / kana runs behind a stat byte, class `kanji*` / `kana*`) and compares the byte
range of each run with the record ranges of `translation/*.jsonl` (covered = at least half of the run's bytes inside records of the same
source; `ATFIRST/BPINFO.BIN` counts as covered by `ETC_DATA/BPINFO.BIN`).  Output (`build/uncovered/`): `summary.tsv` (file, class,
runs, chars, bytes, visibility weight, examples; sorted by weight then size), `runs.tsv` (every uncovered run), `audit.md`.
48 s.  Limits: text split by control codes, text in compressed streams `unpack_all` does not open, non-cp932 text.  Code and tables
that merely decode as kana are the bulk of what is left (rules for `hw` and `kanji` runs are strict, but not perfect).

Result (same scanner, 337,280 Japanese runs on the disc):

| | DB records | covered runs | uncovered runs | of which hw | name | kanji / kanji* |
|---|---:|---:|---:|---:|---:|---:|
| before (DB without the extra records, `build/translation_backup`) | 126,477 | 125,523 | 211,757 | 180,120 | 23,864 | 6,378 |
| after (this change) | 368,492 | 311,543 | 25,737 | 16,206 | 2,777 | 5,370 |

Most of the 25,737 are noise: 9.5 k runs lie in container members (models, textures, motion tables that decode as kana), the rest is code and
data tables (`ｿｿｿｿ`, `気ni昔`, ...).  The audit is a tripwire, not a proof: a new real table shows up as a cluster with the same offsets in
many overlays.

### 3.1 Ranked list (player visibility)

Rank by what the player meets, then size.  "now" = status after this change.

| # | where | what | runs | visibility | status now |
|--:|---|---|---:|---|---|
| 1 | `HOMETOWN.BIN` (and the N_ENTRY / HEREWEGO flow that shows it) | 1270 municipality records, name + reading | 1014 new | new game, Event text, news, report headers | records `recarr S=126 W=35` |
| 2 | EVENT, TITLE, ENDING, HELP, SPF_READ, SEARCH, SCDRF, LOCAL, WEEKLY, MEETING, NENREP (15 sources with the ATFIRST copies) | 56 / 112 / 28-byte person records (managers, coaches, foreign staff) | 6,153 + 2,280 + 1,010 | Event list, staff screens, ending credits | `recarr S=56/112/28 W=14` |
| 3 | 78 overlays | half-width pools: club names, nations, leagues, cups, foreign player name parts, sponsor industries | 114,074 | new game (rival, club suffix), news, tournaments | `hwptr` (pointer) and `hwpool` (index-addressed) records |
| 4 | 17 save-family / match overlays (AUTOSAVE, CSAVE*, BACKUP, CHALMODE, BPMATCH, SONGSAVE, ...) | player database copies: name W=14 / reading W=16 | 117,440 | player lists, search by name | `recarr S=30/29/60/240` |
| 5 | `1ST_READ.BIN` | 204 report / news labels | 204 | reports | `ROOT__1ST_READ.BIN.jsonl` |
| 6 | `NENREP.BIN` | competition names with hw + full-width digits, club pool in 8-byte slots (index-addressed) | 290 | annual report | `hwpool` records; the advice sentences at `#23290..#24100` are index-addressed and only partly covered (RESIDUAL, ~100 characters) |
| 7 | `ATFIRST/HELP.BIN#8ab8`, `FLOW_PRG/HELP.BIN` | `@R/選ばれていない@` (markup glued to the previous string) | 2 | help | RESIDUAL |
| 8 | `GAME.BIN` 0x8038a ... | `ｼｭｰﾀｰ名前・速め`, `エラー用BOX` developer labels | ~30 | debug only | RESIDUAL, skip-class |
| 9 | `2_DP.BIN` | IME dictionary (564 kana + 514 kanji runs) | 1,100 | not UI (browser) | leave |
| 10 | textures / `GAME/*.ZAR` members | no text (the hits are texture and model bytes) | - | - | art workflow |

## 4. The new record kinds

Both go through `tools/textdb.py extract` (`extra_records`; `--no-extra` switches them off), land in `translation/<source>.jsonl`
with `"en": ""` and an extra key `"fmt"`, never overlap a textdb string or each other, and keep `en` of existing ids
(`preserve_en`; it now also keeps `skip` on untranslated records - before this change `extract` silently dropped those flags).
`build_patch` writes them **in place, after the pool repacking**, which never sees them: `do_extra` checks that the field
still holds `ja` (else SKIPPED), that `len(en)+1 <= max_bytes` (else FAILED; no relocation) and pads with NUL.
Every extra record carries `stride-table(in-place only)` in `ctx`, so `translib.is_fixed` and `transwork` treat it as a fixed slot
(`budget_fixed = max_bytes`, `max_chars_fixed = max_bytes - 1`).

### 4.1 `recarr` (`tools/textfmt_recarray.py`)

Fixed-stride record arrays; data-driven detection (module docstring): maximal NUL-terminated text runs, spacing histogram of
the "first non-zero byte behind the run" (= start of the next field), a chain per (stride, phase), field width W = mode of
(next field start - run start) (>= 85 % of the chain), slot walk in both directions.  A member is accepted only if everything between
its text and the slot end is 0, so a write can never touch a neighbouring field.  Rejected: pools of pointer-referenced strings, arrays
whose members start inside longer text (glued share > 30 %), near-identical entries, noise that decodes as kana.
PROVEN: `en = ja` is the identity for all 127,941 records; a mutation changes only slot bytes (`tools/test_uncovered.py`).
INFERRED: W is the *measured* distance to the next non-zero byte; if a numeric field behind the text always starts with 0 the real
slot is narrower (names are <= 13 characters in practice, W = 14 matches BPINFO's `name[14]`).

### 4.2 `hwptr` (`tools/textfmt_hwkana.py`)

Half-width katakana strings referenced by a pointer (ctx `hwptr tbl@<first word>[i/n]`, `refs` >= 1) and strings in abutting pools
nothing points at (ctx `hwpool run=N`, `refs` 0).  Slot = string + NUL + zero padding up to the next non-zero byte / pointed offset
(4-aligned pools: 4, 8, 12, 16 ...).  Pointer-referenced strings could be relocated like textdb strings; not implemented
(in place only), see s5.

### 4.3 Counts and byte budgets (`tools/re/extra_tables.py translation`)

Slot = `max_bytes` (string + NUL); English must be <= slot - 1 characters.  "distinct" = distinct `ja`; records are per place.

| table | S (stride) | slot | records | in overlays | distinct ja | slot bytes | example |
|---|---:|---:|---:|---:|---:|---:|---|
| hw pointer strings | - | 8 | 84,514 | 70 | 4,823 | 676,105 | ｱｼﾞｬﾗ R, ｱﾙﾃﾞｨﾚｽ, ｻﾘｰﾚ, ﾐｭｰﾄｽ |
| hw pointer strings | - | 4 | 16,413 | 70 | 924 | 65,652 | ﾁｬﾓ, ﾛｱ, ｶﾌｰ |
| hw pointer strings | - | 12 | 11,664 | 74 | 928 | 139,779 | ｶｳﾞｧｼﾞｪﾛ, ﾃﾞｨｽﾃﾌｧﾉ |
| hw pointer strings | - | 16 / 20 / 32 | 391 | 45 | 37 | 6,348 | ﾀﾞﾑｲ, ﾜｰﾙﾄﾞﾁｬﾝﾋﾟｵﾝｽﾞﾘｰｸﾞ |
| hw pools (no pointer) | - | 4 ... 36 | 1,092 | 78 | ~380 | ~13,100 | ﾛｰｶﾙｽﾎﾟｰﾂﾆｭｰｽ, J1ﾌｧｰｽﾄｽﾃｰｼﾞ, `#to#ﾌﾟﾛﾊﾟﾝ`, `%s ｹﾞｰﾑ %s` (keep `%s`, `#..#`) |
| person records, reading (hw) | 30 | 16 | 53,200 | 10 | 5,275 | 851,200 | ﾋﾗﾂｶ ﾛｳﾏ |
| person records, name | 30 | 14 | 32,450 | 10 | 3,257 | 454,300 | ﾗｺﾞｽ 武威, 上田 克己 |
| person records, reading (hw) | 60 | 16 | 13,300 | 5 | 2,652 | 212,800 | ｽｷﾞｼﾀ ﾘｭｳｼﾞ |
| person records, name | 60 | 14 | 8,133 | 5 | 1,635 | 113,862 | 佐藤 弘光 |
| staff records | 56 | 14 | 6,153 | 10 | 762 | 86,142 | 末吉 光, 織田 道三, ﾋﾞﾗｶｽ |
| staff records | 112 | 14 | 2,280 | 3 | 760 | 31,920 | (ENDING / HELP / ...) |
| staff records | 28 | 14 | 1,010 | 2 | 724 | 14,140 | (NENREP) |
| person records CSAVE3 | 29 | 16 / 13 | 7,548 | 1 | 7,511 | 111,519 | |
| person records BACKUP | 240 | 16 / 14 | 2,809 | 1 | 2,803 | 43,316 | |
| **municipalities** | 126 | **35** | 1,014 | 1 | 998 | 35,490 | 愛甲郡, 青ヶ島村, 延岡市 |
| player list (PL_EDIT) | 92 | 14 | 44 | 1 | 44 | 616 | ｱﾚｯｻﾝﾄﾞﾛ ﾛｯｼ |
| **total** | | | **242,015** (127,941 recarr + 114,074 hwptr) | | **10,881** | | |

Of the 10,881 distinct texts, **4,307 already occur in older records that have English** (player names translated through BPINFO and the
older orphan records): `transmerge.py merge` writes a result to every record with the same `ja`, so these need no translator, only a
merge of the existing translation (that is a translation-stage step; nothing here writes `en`).  About **6,570 distinct texts are new**.
Whole DB: 368,492 records, **35,898 distinct texts** (was 29,122), 15,978 with a fixed in-place slot; `transwork.py plan` on the new DB:
320 shards (shard numbers move when the plan is rebuilt; the keys `sha1(ja)` do not).  Do **not** re-plan while shards are being worked on; the plan used here went to `build/trans_tmp`.

## 5. For the translation stage

* **Slots are hard.**  A name in a W=14 field is at most 13 characters; the Event list and player card show 12 (docs/style-guide s7.1).
  hw pool slots are 3 / 7 / 11 / 15 characters.  Municipality records W=35 are not the limit: the same names in the pointer
  tables are 8 / 12 bytes, so use the **same English** for the same `ja` everywhere (translation memory does) and keep it <= the
  smaller slot.  Ladder per table kind: docs/style-guide.md section 12.
* **Club names** are composed (`<town short> <suffix>`): keep suffix <= 7 characters (8-byte slot), the composed club-name buffer is UNKNOWN.
* **Readings** (`recarr ... W=16`, hw) are probably only sorting / search keys: low priority; if displayed they must equal the English of
  their kanji sibling, not a second romanisation.
* `%s`, `%d`, `#ken#`, `#to#`, `#chi#` tokens in hw pool strings (`%s ｹﾞｰﾑ %s`, `#to#ﾌﾟﾛﾊﾟﾝ`) are format / substitution tokens: keep them (transcheck does).
* Open engine questions, to settle with an emulator: (1) is ASCII in a hw slot drawn as ASCII or widened (s2); (2) do the readings show
  anywhere; (3) the width of the composed club name.

## 6. Reproduce / maintain

```
python -I -X utf8 tools/uncovered.py                         # audit -> build/uncovered/, 48 s
python -I -X utf8 tools/textdb.py extract                    # overlays + extra records (keeps en / skip), 50 s
python -I -X utf8 tools/textfmt_ptrblob.py --write --only 1ST_READ.BIN   # ROOT__1ST_READ.BIN.jsonl
python -I -X utf8 tools/test_uncovered.py                    # 18 s of checks incl. build_patch.do_extra
python -I -X utf8 tools/build_patch.py --dry-run --out build/<yours>     # failed 0, skipped 0
```
`tools/test_textdb.py` now compares core records with a fresh extraction and extra records with `extra_records`; it also checks that extra
records never overlap a textdb string.  `tools/test_pipeline.py` part A (`test_noop`) asserts that the real DB has no English and has been
failing since the translation work began (unrelated to this change); parts B-G pass (340 checks, run with a private output directory).

## 7. Status after stage 3 (docs, 2026-11-11; numbers re-counted from `translation/*.jsonl`)

| Item | State |
|---|---|
| Table records in the database | 242,015 (127,941 `recarr` + 114,074 `hwptr`), as in section 4.3; **all have English now** (the earlier text of sections 4 and 5, "nothing here writes `en`", describes the audit stage). The core records: 126,477, 124,974 with English, 413 marked `skip` |
| Whole database | 368,492 records, 366,989 with English (99.6 %); 35,898 distinct texts, 35,244 translated (98.2 %); the remainder is mostly debug text (519 distinct texts) and binary labels (107) that carry skip hints and are left Japanese on purpose, plus 14 browser strings (`python -I -X utf8 tools/transmerge.py status` for the live figures) |
| Player-visible gaps of the first playtest | rival club, hometown names, club-name suffixes, manager / coach names, 1ST_READ report labels: all have English in the database and in the build (`--hw-relocate` and `--refit` decide how long the half-width pool forms may be); **not yet seen in game** (`docs/playtest-checklist.md` sections 3, 7, 8) |
| Half-width pools written in place | the English must fit the 4 / 8 / 12-byte slot; with `--hw-relocate on` (forced by `--refit on`) a pointer-referenced pool string can move into the overlay's free pool space (docs/hw-relocation.md).  Index-addressed pools (`hwpool`, 1,092 records, for example the NENREP 8-byte club slots) can never move |
| Open engine question (1) of section 5: is ASCII in a half-width slot drawn as ASCII or widened | still **UNKNOWN**: no screen that draws such a slot has been looked at with English in it; the checklist items for club words and nations (section 7 of the checklist) answer it |
| Open question (2): do the person readings (`W=16`) show anywhere | still UNKNOWN; they carry the same English as their name sibling (translation memory), so a reading that shows will read correctly |
| Open question (3): width of the composed club-name buffer | partly answered: the composer is now bounded to 13 characters + NUL (docs/layout-issues.md section 9), the real buffer size is still UNKNOWN (9.7) |
| Reproduce | the commands of section 6 still work; `python -I -X utf8 tools/test_uncovered.py` is part of the test list in the top-level README |

## 8. tx5 audit after the first real playtest of `prop7` (2026-11-11)

Playtest findings (user, screenshots): (a) the attract demo / match overlay commentary box and the HOME / AWAY labels were still Japanese, (d) `Centre P`
truncated in the Event info panel.  Everything below was measured on `translation/*.jsonl` with `tools/re/tx5_audit.py` (re-run it for current numbers).

### 8.1 Where the match commentary comes from (new source, `BCAST/BCAST.BIN`)

Nothing in `extracted/` holds `なるほど。放送席、解説は水沼貴史さん、実況は八塚浩でお送りいたしました。`: it is the subtitle text in the 2048-byte header of the
voice clips in `/BCAST/BCAST.BIN` (630 MB, skipped by every earlier tool as media).  26,635 clips, 30,083 text segments, 19,002 distinct texts.  Full
description, header layout, draw engine limits (37 cells per line, no newline, monospace) and the pipeline (`tools/textfmt_bcast.py`,
`build_patch.do_bcast`, sparse sector edits in `discbuild`) are in docs/text-sources.md section 6.  The segments sit in `translation/BCAST__BCAST.BIN.jsonl`.

### 8.2 Audit by visibility tier (records of all `translation/*.jsonl`; "ja-only" = no English, "with Japanese" = contains kana / kanji)

| tier | text records | with English | ja-only with Japanese | skip-flagged | note |
|---|---:|---:|---:|---:|---|
| T1 match / commentary / attract | 39,069 | 29,848 | 9,210 (9,168 of them BCAST) | 36 | the BCAST remainder is the long commentator chatter, see 8.3 |
| T2 title / intro / options / help | 3,113 | 3,059 | 45 | 44 | all developer / debug text (below) |
| T3 ending / credits | 5,107 | 5,088 | 16 | 9 | same |
| T4 memory card | 27,060 | 27,007 | 45 | 28 | same: `ダミーのBootRomコメントだがや。`, binary noise decoded as kanji (`HC曙`, `L徹敬` ...) |
| T5 error / system dialogs | 4,378 | 4,359 | 5 | 4 | same |
| T6 everything else | 77,833 | 76,682 | 1,071 | 290 | `PWK_EDIT` 274 (debug editor), `NEWS` 112 / `NEWS_OP` 46 / `NEWS_ED` 41 (printf logs of the result writer), `EVENT` 27, FLOW1..11 15 each (same table) |
| table records (`hwptr` / `recarr`, all tiers) | 242,015 | 242,015 | 0 | 0 | policy, not a gap |
| identity records (`en == ja` with Japanese) | - | - | 0 | - | none exist |

Result (CORRECTED in section 9: the skeptic pass found 23 strings the extractor had missed): **after `BCAST.BIN` there is no player-visible text left in the database that has no English.**  The 1,224 ja-only records with Japanese outside BCAST (all tiers; 1,379 before the debug strings were translated) are `printf`-style
developer logs (`>>>>>>>>>>>EntryTeamPlayerCheck ERROR!!  「８人以下のデータです」`, `bcFunc:不正な選手番号  %d`, `PWK_RESULT j1rank の反映開始`), dummy labels
(`ダミー１`..) and byte noise; the 411 skip-flagged ones are the 4-record money sets (`億 / 万円 / 円 / 0円` in 100+ overlays, money owner).  The match-engine
family (`GAME`, `BPMATCH`, `BPMWEEK`, `G_RESULT`, `GAMEOVER`, `GMSHOW00-02`, `MOVIE*`, `SPF_READ`, `CE_VS`) had 93 + 15 + 5 debug strings; 155 of the developer strings
(match family, `Dummy BootRom comment.`, `TEAM_%d: no such club in J2`, ...) were translated by `tools/re/tx5_fill_ids.py tools/re/tx5_t1_debug.tsv` (all fit their slot,
the build says failed 0); the others (NEWS / PWK_EDIT logs, noise) are left Japanese on purpose and listed by `tools/re/tx5_list_left.py REGEX`.

### 8.3 BCAST.BIN translation state (this run)

| folder | records | with English | note |
|---|---:|---:|---|
| `name` (player callouts, nicknames) | 12,480 | 12,480 (100 %) | romanised by rule / DB lexicon, see docs/text-sources.md 6.2 |
| `yh` (announcer) | 7,498 | 6,173 (82 %) | match flow, goals, fouls, shots, passes, substitutions, penalties, tournaments, club / team / stadium names, numbers, results done; left: the rest of the pre-match talk (`siame_aisa`, about 1,300 distinct yh lines in all), post-match summaries (`end_ntr`), setu_other ... |
| `mt` / `mm` / `kk` (the three commentators) | 3,320 / 3,267 / 3,518 | 808 / 749 / 704 | the first tier (greetings, intro, ending, reactions, set pieces, goals, fouls, tactics talk) is done in the mt wording and reused for equivalent lines of the others; **left: about 2,500 distinct lines per commentator (rplay_in replay talk, play_kai, siama_kai, end_kaise, zatu_* chatter)** |
| total | 30,083 | 20,914 (69.5 %) | the untranslated segments keep their Japanese (identity), nothing fails |

To continue: `python -I -X utf8 tools/re/tx5_next.py 300 [START_N] [yh|mt|mm|kk]` prints the next untranslated distinct lines with their frozen numbers, write
`N<TAB>English` lines to `build/tx5/results/rNNN.tsv`, then `python -I -X utf8 tools/re/tx5_merge.py --write` (checks ASCII, no `@ # %`, <= 73 characters) and
`tools/re/tx5_propagate.py --write` (free reuse for lines that differ only in punctuation / speech ending).  `tools/re/tx5_remaining.py` shows what is left per category.

### 8.4 The two other findings

* **`Centre P`** (Event / scout info panel): the panel draws a 12-cell monospace window (Japanese 2 full-width spaces + 4 full-width characters = 12 cells,
  right-aligned); `    Centre Push` showed `    Centre P`, `    Left Side` showed `    Left Sid`.  The style labels (`SCDRF.BIN#32d28..#32d68`, `SEARCH.BIN#32a90..#32ad0`) are now the same
  words right-aligned to exactly 12 characters (`   Left Side`, `  Right Side`, ` Centre Push`, `     Counter`, `   Post Play`); `tools/re/tx5_fix_tactics.py` made the edit.  The
  other tactic tables (`MEETING` 12 / 16 / 20-byte windows, `GAME`, `TRAINING`) are other windows and were not changed.
* **HOME / AWAY `静観`** (match screen, scoreboard `2nd`): `静観` exists as text **nowhere** on the disc (cp932 near-search, UTF-16 / UTF-8 / EUC / JIS, over `extracted/`
  and `build/unpacked/`: only `2_DP.BIN`, the IME dictionary; `tools/re/tx5_find_seikan.py`).  It is therefore a sprite in a texture bundle of the match overlay (candidates:
  `GAME/GAMEETC.ZAR`, `GAME/GAMEEFF.ZAR`, `GAME2/GM_OTHER.TBD` / `GM_SHORT.TBD`): **an art-owner item**, not text.

## 9. tx5 skeptic pass: strings the textdb scan missed (fmt `gap`, 2026-11-11)

Section 8.2 said no player-visible Japanese is left outside `BCAST.BIN`.  **That was wrong**: it counted only the records of the database, and the
database itself has holes.  `tools/re/tx5s_gap2.py` lists every NUL-bounded cp932 string of every overlay that no record covers
(offset .. offset + `max_bytes`); after removing noise (tile maps, developer logs, strings glued to binary bytes that a record already covers) 23 real
strings remained, all in overlays that the player sees:

| source | strings | what | why the scan missed it |
|---|---:|---|---|
| `NENREP.BIN` (year-end club report) | 17 | table labels (`元チーム`, `新チーム`, `クラブ名`, `Ｊリーグ DIVISION 1/2`, `クラブ参加大会`), `ここでは@Y/#tk01#@の状況を...`, and 11 **heads** of two-part messages (`今年の観客数はまずまずといった\n所でしょうか。\nまだ頑張れる余地は有る` + the tail `はずです。`, `今年は残念な事に負け越してしまいました。` + `このままでは...`, ...) | the head is ONE run with its tail (no NUL between them); a pointer targets the tail, so `textdb` pass 1 made the tail a record and pass 2 dropped the whole run because it contains covered bytes: the head was never extracted, only the tail was translated |
| `RECON.BIN` | 1 | `=w/#sname#さん、おめでとうございます！ ... 契約が成立ですよ ...` (contract signed message) | `_has_image_pointer`: bytes of the string look like a pointer word |
| `TRAINING.BIN` | 2 | `今回の試合で使うｼｽﾃﾑを決定 / 変更しました。` | half-width kana inside prose |
| `HELP.BIN` (both copies, `FLOW_PRG` and `ATFIRST`) | 2 | `@R/選ばれていない@` | too short for the orphan rules |
| `HOMETOWN.BIN` | 1 | `%s%sです。` | same |

Fix (all in place, nothing moves):

* `tools/textfmt_gap.py`: curated table `GAPS` (offset, span, cont) with `extract` / `render` / `apply`; records have `fmt: "gap"` (added to `textdb.EXTRA_FMTS`
  and to `textdb.extra_records`, so `test_textdb` checks that the database equals a fresh extraction; `build_patch.do_extra` applies them, `refit` treats them as
  fixed in-place fields).  `cont: true` = a head that runs into the next record without a NUL: `max_bytes` = span, the English (at most span - 1 bytes) is padded with blanks
  to exactly `span` bytes (in front of its last line break when it has one: blanks at the end of a line are invisible), and the tail record continues the sentence.
* The English of the 11 heads was written together with the 9 tails (they used to be standalone sentences that made no sense after the missing head): a head and its
  tail read as one sentence, e.g. `Not quite a full house.\nIf it stays` + ` like this, it could badly\nhurt club management.`.  Records: `tools/re/tx5s_gap_en.tsv`
  (heads and strings), `tools/re/tx5s_gap_tails.tsv` (tails), applied by `tools/re/tx5s_gapmerge.py` (idempotent; only these records change).
* Proof: trial build `build/trial/skx_gap` (standard flags + `--strict`): 388,081 applied (+23), failed 0, skipped 0, `verify_disc` OK, digest `ded85d9475fe5d3d26e68b4b6fda0391eb240081`;
  `tools/re/tx5s_readback.py skx_gap /FLOW_PRG/NENREP.BIN` shows the strings as the game reads them (head and tail joined).  Tests: `tools/test_gap.py` (9), `test_textdb`, `test_uncovered`,
  `test_transwork`, `test_refit` pass.
* NOT done: `NENREP.BIN#237fd` (`非常に低い視聴率でしたね。 ...世間から忘れられてしまいます。`): the pointer record `#23856` (`ｷよ。`) points at the SECOND byte of the character `す`
  (0x82 0xB7), so the head would have to end inside a character; left Japanese (one annual-report line, low viewing figures).  The other ja-only strings of `tx5s_gap2.py`
  (`GAME.BIN` developer trigger labels `PK戦・GKセーブ ...`, `総合力 経験値 オフ %f ...`, `PWK...書き込み` logs, `0A動物園あり`, kinsoku table) are developer text or data.
* Check that the audit is now clean: `python -I -X utf8 tools/re/tx5s_gap2.py` lists 98 candidates, every one of them noise, developer text or already covered by a
  record that starts 1-2 bytes later (junk byte in front); `tools/re/tx5s_leftover.py NAME` scans a built disc for cp932 Japanese that is not a substring of any `ja` of the database.
