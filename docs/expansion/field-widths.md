# Widening fixed-stride record fields and name limits: feasibility study

Author: agent `fieldwidth` (read-only study, nothing under `translation/` or `tools/` changed except new analysis scripts `tools/re/fw_*.py`).
No emulator was started, no screenshot of a window was taken; the RAM dumps already in `build/emu/` and the screenshots 46-51 of the
playtest were only read.  Status words: **PROVEN** = read from code, disassembly, data or a script run here (script named),
**INFERRED** = follows from proven facts, **UNKNOWN** = not determined, with the cheapest test named.

## 0. Verdicts in one screen

| # | Verdict |
|---|---|
| V1 | **PROVEN** The municipality record (HOMETOWN.BIN, stride 126) already has a **35-byte** name field; the English `Hirats.` / `Fujisa.` in the Hometown list is a translation-memory artefact (one English per Japanese string, so the 126-byte records got the 8-byte short-table spelling), not an engine limit. Cost to show full names: data only, no code, no save impact. |
| V2 | **PROVEN** `Kagoshi`+`Mythos`, `Yokoh`+`Shadows`, `Kanaga`+`Shadows` (screenshots 46, 47) are produced by code, not by slots: the town short-name helper cuts the **last 2 bytes** (the Japanese suffix 市/町/村/郡) of the short name (`add #-2,r5`, HOMETOWN 0x8c2e069c). It exists as the same byte-identical routine in **20 overlays**; the `#to#` sponsor expander has the same `add #-2,r0` in **16 overlays**. Both are one-halfword patches (`fe 75 -> 00 75`, `fe 70 -> 00 70`), no cave needed (section 4). |
| V3 | **PROVEN/INFERRED** Removing the cut is not free: the composed club name is stored in a **14-byte** game-state field (`#sname#`, struct offset 0x103a, 13 characters + NUL); the cut is what keeps `Town + Word` under 13 characters today.  The field neighbours are used by thousands of code sites, so it cannot be widened in place (section 3).  **STATUS (stage 3): guard IMPLEMENTED** - `tools/layoutpatch.py` bounds the composer of the 20 overlays to 13 characters + NUL (town cut to a dotted prefix, the word kept); simulator-proven on the real prop6 / prop6r overlays, 0 overflows in 142,670 runs; 46.7 % / 48.6 % of the 68,640 town + word pairs are cut; see `docs/layout-issues.md` section 9 (the stage-2 figure of 7,873 over 13 does not reproduce).  Not yet seen in Flycast. |
| V4 | **PROVEN** All half-width-kana pools (club words, nations, leagues, foreign name parts: 99 % of 114,074 records) are **pointer-referenced** strings in pointer tables; they are slot-forced only because our tooling writes them in place.  They can be relocated like normal strings.  Their real limit is where the string ends up (club name 14 bytes, person name 14 bytes). |
| V5 | **PROVEN** Person names are 14-byte fields (13 characters) everywhere: BPINFO 92-byte records, 288-byte runtime player structs in the heap, five static player-name table layouts (S=29/30/60/240) in 17 save/load/match overlays, staff arrays (S=28/56/112) in 15 files, user name (`#YOU#`, 0x102c).  Widening any of them in place shifts a struct that thousands of sites index. **Recommended instead: leave the stored field alone and substitute the long English at display time (name bank), where the display path allows it.** |
| V6 | **PROVEN** Save files are BUP files `SAKATOK2.<G|A|P|C|D|L|E>NN` in 512-byte VMU blocks with a **file CRC check** (`drive%d,file CRC error`, `CRC:%04x`, `CRYPTCRC:%04x`).  Anything stored as a name string in a save is limited by the same 14-byte fields; changing a saved structure changes the file layout and breaks Japanese saves (list in section 5). |
| V7 | **UNKNOWN** Whether the main save contains name strings (user, club, generated players) or only IDs; whether the player table is saved as a whole.  Cheapest test: decompile the save writer in AUTOSAVE.BIN (callers of `FUN_8c8d32ec` / the BUP write call), or diff two saves made after renaming. |

Pain-to-fix ranking (details in section 6): 1 municipality English split (V1), 2 `%s%s` separators in hometown/club messages (text),
3 chop patches paired with a club-name guard (V2/V3), 4 hw club-word relocation, 5 staff names, 6 player names, 7 user name (do nothing).

## 1. Method and scripts

All scripts are read-only analysis helpers with the prefix `fw_` in `tools/re/` (run as `python -I -X utf8 tools/re/<name>.py`):

| script | purpose |
|---|---|
| `fw_census.py`, `fw_tables.py`, `fw_arrays.py` | census of translation records by format, slot size, pointer table, array stride |
| `fw_arrsites.py` | for every fixed-stride array: pointer words into it and the `mov.l @(disp,PC)` loader sites (lower bound of code to change) |
| `fw_sig.py` | masked-instruction signature scan: how many overlays carry a byte-identical copy of a routine |
| `fw_wlit.py`, `fw_wsites.py`, `fw_imm.py`, `fw_findword.py` | counts and addresses of 16-bit literal loads, `mov #imm`, 32-bit literal words (struct offsets, strides) |
| `fw_chopcheck.py` | verifies the exact bytes of the two chop instructions in all 36 copies |
| `fw_grepbin.py`, `fw_grepja.py`, `fw_listja.py`, `fw_hexdump.py`, `fw_ram.py`, `fw_ramfind.py` | grep / dump helpers |

Ghidra 12.2 (JDK 25) was used headless on HOMETOWN.BIN, N_ENTRY.BIN and AUTOSAVE.BIN in a scratch project in the session scratchpad
(not in the repo); decompiler output was only used for the facts named below, the instruction listings (`Dis.java`) were used for the patch bytes.

## 2. Field families

Legend for "save": **none** = no save involvement expected, **break** = Japanese saves stop loading or change meaning, **?** = UNKNOWN.

### 2.1 HOMETOWN municipality records (name 35 bytes, stride 126)

* Layout (PROVEN, `fw_hexdump.py extracted/FLOW_PRG/HOMETOWN.BIN 0x15970`): record = `u16 town ID` (record 0 has 0x033e = 830), `name[35]` cp932 at +2,
  `reading[35]` hiragana at +37, numeric block from +72 (+0x48, +0x49, +0x4a are bytes loaded by code). 1270 records at 0x15970 (160,020 bytes).
* Readers (PROVEN): array base words 0x8c2e5970 / 0x8c2e5972 / 0x8c2e59b8-59ba; **31 `mov #126,Rn` immediates** (`fw_imm.py`) and 8 `add #126` in HOMETOWN.BIN
  plus 28 loader sites for the base (`fw_arrsites.py`).  Only HOMETOWN.BIN has this array (S=126 in 1 file).  The list builder justification routine
  (4/6-byte cases) is already patched (docs/layout-issues.md section 2).
* The town ID (record +0) is the join key to the **short-name pointer table** `tbl@43858` (1270 pointers, 8- or 12-byte slots, 1-based: the code loads `base-4` and indexes `4*id`).
  In HOMETOWN.BIN this table is read by exactly two routines, both of which cut 2 bytes: the helper `FUN_8c2e0648` (called from the club-name list builder
  at 0x8c2d1b6c / 0x8c2d1ccc, PROVEN by decompile and by `arrptrs.py`: 5 words only, two of them `0x8c313854`) and the `#to#` branch of `FUN_8c2e4e1a`.
* English today: the same English is in the 35-byte record and the 8-byte short slot (`Hirats.` both, grep of `translation/FLOW_PRG__HOMETOWN.BIN.jsonl`),
  because `transmerge.py` writes one English per Japanese text. **The 35-byte field accepts `Hiratsuka` (34 characters) today.**
* Widening cost: **0 stride work**. Needed: (a) split the translation memory per field (record vs short table), (b) check the list window width (INFERRED fine: `S. Ashigara`, 11 characters, already shows in the list box of screenshot 46).
* Save: none (the save stores the town ID, INFERRED from the `#to#` token taking an ID and from the table being indexed by ID; UNKNOWN until the writer is read).
* Overlays touched: 0 code, 1 data file (HOMETOWN.BIN).  Pain: high (first thing a new player sees).

### 2.2 Town short-name table and prefecture pieces

* Short names: pointer table `tbl@43858`, 1270 entries, slots 8 (994), 12 (253), 16 (1) (`fw_tables.py`); copies of the table sit in 34 overlays (docs/layout-issues.md).
  Strings are ordinary pointer-referenced strings (ctx has no `stride-table`), so they are **relocatable**; current limits (`Wadoma.`, `Hirats.`) come from the 8-byte slot plus the TM policy.
* Consumers of the code kind: the 20-overlay helper (`Illegal townID`) and the 16-overlay `#to#` expander, **both cut 2 bytes** (PROVEN, `fw_sig.py`, `fw_chopcheck.py`).
* Prefecture / region pieces: `tbl@42200` (50 prefectures, slots 8 and 12; `Kanagawa` sits in a 12-byte slot), loaded at 8 sites in HOMETOWN.BIN (0x8c2d0e2e ...).  The `#ken#` branch of the expander treats Hokkaido / Tokyo / Osaka / Kyoto specially (6/4/4-byte compares of Japanese strings) (PROVEN decompile, FUN_8c2e4e1a); in English these compares never match, so `#ken#` copies the table string: harmless.
* `%s%s` in the messages `Our home town is "%s%s"` / `The rival club has chosen "%s%s"` (HOMETOWN msg table 0x412d4): two table strings concatenated with no separator in Japanese -> `KagoshimaKagoshima`, `KanagawaYokoha.` (screenshots 46, 47).  Text-only fix (`"%s %s"`); the strings are movable pointer-table strings.

### 2.3 Club name (composed) and club word pool

* Composition (PROVEN from behaviour + code): `town short name (cut by 2) + club word` or `club word + town`, in 4 variants (popup in screenshot 47: `YokohShadows`, `ShadowsYokoh`, `KanagaShadows`, `ShadowsKanaga`; the popup width clips the 13th/14th letters).
* Destination: `#sname#` = game-state struct offset **0x103a**; `#YOU#` = **0x102c**; the next field is used at **0x1048** (INFERRED: 0x1048 is loaded as a 16-bit offset 276 times in 57 overlays and nothing between 0x103a and 0x1048 is; so sname is 14 bytes = 13 characters).
  `KagoshiMythos` (13 characters) is exactly the maximum.  The name-entry commit copies with an unbounded string copy (N_ENTRY 0x8c8d0cea-0x8c8d0cf8: `strcpy`-style call with `+1` source, destination = struct+0x102c and +0x103a; INFERRED that the call target is strcpy), so the **entry limit is the only guard**: N_ENTRY text says 6 full-width / 13 half-width characters (`translation/FLOW_PRG__N_ENTRY.BIN.jsonl` #10100).
* The club-word pool (55 words, `ﾐｭｰﾄｽ` ...): hw pointer table `tbl@247a8` etc., slots 4 / 8 / 12; 99.4 % of the 84,856 slot-8 records and 99.8 % of the slot-4 records are pointer-referenced (`fw_arrays.py`).  Relocation is possible; the effective limit is the 14-byte `sname`.
* Widening cost: see 3 (struct).  Pain: high but contained to new game / rival club / news / match intro.

### 2.4 Person records: staff (56 / 112 / 28), players (BPINFO 92, runtime 288, static 30 / 29 / 60 / 240)

All name fields are 14 bytes (13 characters); readings (hw katakana) 16 bytes.

| family | stride | name field | where | arrays / files | loader sites (lower bound) | distinct texts |
|---|---|---|---|---|---|---|
| staff (managers, coaches, foreign staff) | 56 | 14 | EVENT, LOCAL, MEETING, SCDRF, SEARCH, TITLE (+ATFIRST/TITLE), WEEKLY | 16 arrays / 9 files | 150 sites, 157 literal words | 762 |
| staff | 112 | 14 | HELP (+ATFIRST/HELP), ENDING | 8 arrays / 3 files | 86 sites | 760 |
| staff | 28 | 14 | NENREP (34-49 sites per array!), SPF_READ | 3 arrays / 2 files | 238 sites | 724 |
| player name tables | 30 (reading 16 + name 14) | 14 | AUTOSAVE, BPMATCH, CSAVE, CSAVE4, DMCLBEDT, ENDOPT, EXFLAG, EXTRADE, LOAD, SPF_READ | 10 files, 5320 records each = 159,600 bytes | 5 loader sites per file | 5,275 |
| player name tables | 29 / 60 / 240 | 13 / 14 | CSAVE3 / BACKUP, CHALMODE, FREELOAD, SONGSAVE, VTRLOAD / BACKUP | 7 files | 3-11 sites per file | same players |
| BPINFO.BIN (ETC_DATA and ATFIRST copy) | **92** | 14 at +0 | disc file, 64-byte header (u16 count 5321, 26-byte header table of unknown meaning), no checksum found (docs/text-sources.md) | 2 files | n/a | 5,321 |
| runtime player struct | **288 (0x120)** | 14 at +0 | heap table, e.g. 0x8ce4c004 in `build/emu/pt1_ram.bin`, next name at +0x120 (`Ryo Minazuki` 0x8ce4c124) (PROVEN by `fw_ram.py`) | 5321 x 288 = 1.53 MB | literal 0x120 loaded 5,421 times in 86 files (noisy: also coordinates), literal 0x5c (92) 7,793 times in 120 files (very noisy) | |
| user name `#YOU#` | 14 | 14 | game-state struct 0x102c | 1 | 0x102c loaded 323 times in 101 overlays, 0x103a 199 times in 98 | |

* The same ~760 staff persons and the same 5,321 players are copied into every overlay: **widening an in-image table means 9-17 overlay files each**; BSS overlays cannot grow (docs/text-engine.md section 6), so a table that gets bigger has to **move** (new bank), not grow.
* Runtime copy: the Event list builds from a working copy in the heap (0x8ce4e400 in pt1, docs/uncovered-text.md), whose layout and stride are UNKNOWN; widening only the static source tables would not help unless the copy loop and the copy's stride change too.
* The 12-character on-screen limit (`Isao Nakagak`) has two candidate mechanisms (7-cell window or 12-byte copy buffer, docs/layout-issues.md section 3): **UNKNOWN**, test is a RAM dump with the Event list open (`wintext.py ... Nakaga`).  The on-pitch labels clipped to 4 letters (`Kenj`, `Dais`, `Akir`, playtest log part 2) are INFERRED to be a 4-byte (2 kanji) copy of the Japanese family name; code location **UNKNOWN** (candidates PWK_EDIT.BIN, TRAINING.BIN).
* Save: PROVEN that the VM trade / bonus-file path moves players by number (`** %d番目の人は居なくなりました **`, `Nation error! %d , %d`, CSAVE.BIN), and that the static name tables sit in the save/load overlays so the load screen can print names without loading BPINFO (INFERRED).  So **player-name text widening via a bank keyed by player ID keeps saves unchanged**; widening the 288-byte struct or the BPINFO record changes the in-memory layout and, if the struct is saved whole (V7, UNKNOWN), breaks saves.

### 2.5 Foreign / Japanese name parts, nicknames

* Surname / given-name pools (hw katakana, slots 4, 8, 12): pointer tables in the same 74-78 overlays as the club pool, relocatable (see V4).  They are assembled into the 14-byte person name at run time (INFERRED from `Nation error` / generated players), so the cap is the person name field, not the pool slot.
* "Nicknames": the only nickname feature on the disc is the DreamPassport chat nickname (`DPETC/MESSAGE.INI`, browser, `2_DP.BIN`), outside the game; on-pitch short labels are the 4-letter case above.  Nothing to widen in the game proper.

### 2.6 User name (13 characters)

* PROVEN: the N_ENTRY prompt says 6 full-width or 13 half-width characters; the commit path copies into `#YOU#` (14 bytes) with no length check; English names of up to 13 characters are enough (`Nexxus`, screenshot 48).  Pain: low.  Cost of widening: same as the club name (section 3).

## 3. The game-state struct and why it cannot be widened in place

Offsets the code uses as 16-bit literals (`fw_wlit.py`, exact decode of every `mov.w @(disp,PC)` in 114 overlays + 1ST_READ):

| offset | meaning | sites / files |
|---|---|---|
| 0x102c | `#YOU#` user name (14 B) | 323 / 101 |
| 0x103a | `#sname#` club name (14 B) | 199 / 98 |
| 0x1048 | next field | 276 / 57 |
| 0x104c | next field | **1,985 / 81** |
| 0x1054 | next field | **1,669 / 65** |

So the 14-byte strings sit between fields that are indexed thousands of times, in the library code that is statically copied into every overlay.
Options, cheapest first:

1. **Do nothing to the struct, constrain the English**: club name <= 13 characters (town short <= 13 minus the club word); today's behaviour, now ENFORCED by the composer guard (layout-issues.md section 9: the town is cut to a dotted prefix when the pair is over 13).
2. **Side buffer for the long form**: allocate a new buffer (outside the struct, e.g. at the end of the struct's allocation or in a free RAM bank), have the commit path (N_ENTRY, 2 sites) and the club-name chooser write the long form there, and change the **expander** (`#sname#`, `#YOU#`: 2 literals per overlay copy, ~100 overlays but the same routine, signature-patchable like the font hook, docs/font-patch-design.md) to read the side buffer when it is valid, else the 14-byte field.  Save format unchanged; long names are lost on load unless the save is extended (then **break**, see 5).  Cave space: one small stub per overlay copy (the font patch already established the bank/cave machinery); INFERRED ~20-30 bytes of SH-4 per copy.
3. **Relayout the struct** (new offsets): rewrite ~4,000 literal sites in 100 overlays and the save format; **not recommended**.

## 4. Patch catalogue that is already proven

| patch | file offsets | bytes | overlays | cave | save |
|---|---|---|---|---|---|
| town short-name helper: do not cut 2 bytes (`add #-2,r5` -> `add #0,r5`) | sig + 0x54, e.g. HOMETOWN 0x1069c (VA 0x8c2e069c) | `fe 75` -> `00 75` | 20: AUTOSAVE BACKUP BPMATCH CHALMODE CSAVE CSAVE3 CSAVE4 DMCLBEDT ENDOPT EVENT EXFLAG EXTRADE FREELOAD HOMETOWN LOAD SCHE0 SCHE1 SONGSAVE SPF_READ VTRLOAD | none | none |
| `#to#` branch: do not cut 2 bytes (`add #-2,r0` -> `add #0,r0`) | sig + 0x54, e.g. HOMETOWN 0x14e6e (VA 0x8c2e4e6e) | `fe 70` -> `00 70` | 16: DRSHRANK ESTABLIS EVENT G_INCOME HOMETOWN INVEST LOCAL NEWS_ED OFFICE SCHE0 SCHE1 SPONSOR SPONSOR2 TOWN TOWNDATA WEEKLY | none | none |

(`python -I -X utf8 tools/re/fw_chopcheck.py`: 20 of 20 and 16 of 16 match; the full offset list is its output.)  After the helper patch the function writes the NUL at the end of the full string and returns the full length (instruction listing in the scratchpad `d1.txt`, HOMETOWN 0x8c2e0648-0x8c2e06af).
**Data-only alternative (INFERRED, zero code patches)**: because in HOMETOWN.BIN every consumer of the short table cuts exactly 2 bytes, append two spaces to every English short name (`Kagoshima  `); the cut then removes the padding.  Needs +2 bytes per string (relocation, 34 overlay copies, pool slack to be checked with `textrepack`), and un-cut consumers in the 14 other overlays that hold the table (UNKNOWN whether any) would show two invisible trailing spaces.  Either way the **13-character club-name ceiling remains** (section 3).

## 5. Save compatibility map

PROVEN facts: files `SAKATOK2.<type letter G A P C D L E><2 digits>`, `SAKATOK2._VM`, `ICONDATA_VMS`, `SAKATUKU.A`, `SAKATOKU.A` (AUTOSAVE.BIN 0x32040-0x32080, decompile of `FUN_8c8d4c00`); the Katana BUP area uses 512-byte blocks (`n*0x200 + n*0x20` work buffer in `FUN_8c8d32ec`); user-visible sizes: bonus / club data file **2 blocks**, VM game **40 blocks** (`ENDOPT.BIN#49a90`), main save `$D` blocks (variable, UNKNOWN value); file CRC check and a second `CRYPTCRC` variant (strings at AUTOSAVE.BIN 0x32649, 0x32c35, 0x32c45), so the saved image is verified by the game and the BUP library on load.

| change | Japanese save still loads? | why |
|---|---|---|
| English text in tables, messages, pointer-table strings, relocated strings | yes | saves hold IDs and numbers; no string layout changes (INFERRED from the BUP / trade strings; V7 test pending) |
| name bank keyed by player / staff / town ID, display-time substitution | yes | struct and save untouched |
| chop patches (section 4) | yes | display only |
| side buffer for the club / user name (3, option 2), long names not saved | yes, names fall back to the 14-byte field | save format unchanged |
| side buffer **and** save extension (new chunk or bigger file) | **no: breaks** | file size and CRC range change (expected size constants in the save overlays: UNKNOWN) |
| widen `#YOU#` / `#sname#` inside the struct (3, option 3) | **no: breaks** | every later offset moves |
| widen the 288-byte player struct or the BPINFO 92-byte record | **no: breaks if the struct or BPINFO-derived data is saved** (UNKNOWN), always breaks the code | stride constants in ~86-120 overlays |
| widen staff / player static tables (S=28..240) | yes for saves (static data), but needs a bank (BSS overlays cannot grow) | |

## 6. Ranking: pain against cost

Pain from `docs/playtest-log.md` and screenshots 46-51: 46/47 Hometown (truncated list, `KagoshiMythos`, `KagoshimaKagoshima`, popup `YokohShadows`),
48-51 Event list and player card (names fit at 12; the right card clips `19 yr`, `Season`, `Average`; money `Y 24M`, `3200M50000000` are number formats, not widths), sponsor names, on-pitch labels (log part 2).

| rank | item | pain | cost (patch points / overlays / cave) | save | risk |
|---|---|---|---|---|---|
| 1 | Municipality English split: 35-byte records get full English, short table keeps the short one | high | 0 code; TM change in `transmerge` / DB; 1 overlay data | none | low; verify list width |
| 2 | `%s%s` -> `%s %s` and club-name join strings (text) | medium-high | 0 code; ~4 messages in HOMETOWN, data of the club popup format (location UNKNOWN: literal at `PTR_DAT_8c2d1cd4` area) | none | low |
| 3 | Do not cut 2 bytes: 36 one-halfword patches (or the trailing-space trick) **plus** a club-name guard | high (every club / sponsor name) | 36 halfwords, 0 cave; guard = choose club words so `town + word <= 13` or option 2 of section 3 | none | medium: overflow of the 14-byte `sname` into the field at 0x1048 if unguarded (the guard now exists: `layoutpatch` guard=True, default in `build_patch.py`, `--club-guard off` disables it) |
| 4 | Relocate hw club-word / nation / league pools (pointer strings) instead of in place | medium | tooling only (`textdb` relocation for `hwptr`), 74 overlays, 0 code | none | low; pool slack per overlay to check |
| 5 | Side buffer for club and user name (option 2) | medium | ~100 expander copies (one signature), 2 N_ENTRY sites, stub in cave | none / break if saved | medium |
| 6 | Staff names (762 persons) via bank | medium-low (Event list, ending credits) | copy loops and 15 files of arrays; a bank needs a new file plus a loader call (1ST_READ `FUN_8c15eede`) | none | high effort |
| 7 | Player names (5,321) via bank keyed by ID at the display accessor | medium-high (lists, cards, news, on-pitch) | unknown number of name-read sites; hook the accessor if one exists | none if display-only | high; V7 |
| 8 | Widen the 288 / 92-byte player records | high | ~5,000 sites in 86-120 overlays, header / count, save | **breaks** | very high: not recommended |
| 9 | User name beyond 13 | low | as 5 | | do nothing |

## 7. Recommended steps (also returned in the reply)

1. Split TM per field and write full English into the 126-byte municipality names (rank 1).
2. Text pass: separators in `%s%s` messages; decide whether the club popup should put a space (13-character budget) (rank 2).
3. Ship the 36 chop patches only together with a club-name length check on the content side (each `town short + club word` <= 13 characters), or use the trailing-space trick; verify in Flycast with a RAM dump that `sname` is not overrun (rank 3).
4. Teach `build_patch.do_extra` to relocate pointer-referenced `hwptr` strings (rank 4).
5. Decompile the save writer (AUTOSAVE.BIN) and the player-name accessor (V7) before deciding on ranks 5-8; both questions have 0 cost in disc space and decide whether bank substitution is possible.

## 8. UNKNOWN list with the cheapest test

| UNKNOWN | test |
|---|---|
| content of the main save (names or IDs, length, CRC range, expected size) | decompile the writer reached from `FUN_8c8d32ec` callers in AUTOSAVE.BIN; or diff two saves in a VMU image after changing only the club name |
| 12-character cut: narrow window vs 12-byte buffer | RAM dump of the Event list, `wintext.py ... Nakaga` (docs/layout-issues.md section 3) |
| on-pitch 4-letter label code | find the draw in PWK_EDIT / TRAINING / GAME with `%s`-style copy of 4 bytes; dump of the placement screen |
| width of the composed club-name buffer in HOMETOWN (before copy to `sname`) | decompile `FUN_8c2d1b5c` (0x8c2d1b5c) destination buffers; run with a long club word |
| whether any un-cut consumer of the short table exists | decompile the 14 other overlays that carry the table without the helper, or the trailing-space build in Flycast |
| width of the Hometown list column | screenshot with `Hiratsuka` / 20-character names |

## Status after stage 3 (docs, 2026-11-11)

See `docs/expansion/status.md` for the table of what was built from this study, its flag or file, how far it is proven, and what is still open.  The summary for this study:

* Done: ranks 1-4 (municipality full names, `%s %s`, chop patches plus the 13-character club-name guard, half-width relocation `--hw-relocate`) and the refit forms (`--refit on`); the guard and relocation are proven only offline (simulator, read-back of the built disc), not yet seen in Flycast.
* Not done: ranks 5-7 (side buffers, staff and player name banks); rank 8 is not recommended.  V7 is answered in `docs/expansion/save-format.md`: the main save stores the user and club names and the names inside ~48 runtime player structs, not the names of the other players.
