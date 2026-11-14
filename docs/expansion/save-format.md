# Save format, name storage and a display-time name bank (read-only reverse engineering)

Status words: **PROVEN** = read from decompiled/disassembled code, from the data on the disc or from a RAM dump, with the script named;
**INFERRED** = follows from proven facts; **UNKNOWN** = not determined, cheapest test named.  No emulator was started; no game file,
extracted file or existing tool was changed.  Sources: Ghidra 12.2 (`SuperH4:LE:32`, JDK 25) headless on `AUTOSAVE.BIN` (project
`build/svfmt/proj`, built by `tools/re/svfmt_mkimg.py`, `svfmt_imp.ps1`, `svfmt_impov.ps1`; decompile with `svfmt_dec.ps1`, disassemble with
`svfmt_dis.ps1`), plus the four existing RAM dumps `build/emu/{pt1,t1,live1,live3}_ram.bin` (all dumps agree on every address quoted).
`CSAVE`, `CSAVE3`, `SONGSAVE` were imported but **not** decompiled; they carry the same save library (same `SAKATOK2.` literals, 8 uses of the
CRC vtable slot each, same name accessor in CSAVE/SONGSAVE, see section 7), so the statements about AUTOSAVE are INFERRED for them.

## 1. Short answers

| question | answer | tag |
|---|---|---|
| Does the save hold name strings? | **Yes.** The main save (types G and A) is a raw 64 KiB RAM block that contains the 14-byte `#YOU#` and `#sname#` strings, 14-byte person names inside ~48 runtime player structs, and the list header carries a 21-byte club word and the 14-byte user name.  Names of the other ~5,270 players are **not** stored: only numbers/flags (C/D/L files carry 5,332 bytes, about one byte per player). | PROVEN (code + dump) |
| Struct sizes serialised | 0x180-byte header + **0x10000-byte arena copy** (file type G/A, total 0x10180 = 129 VMU blocks); other types: P 896 bytes (312 payload), C/D/L 6,016 bytes (5,332 payload).  Section table: section 8 byte entries, 15 sections (section 4). | PROVEN (literals) |
| Checksum / CRC | File level: the **Sega bu library** (CRC16 CCITT table at 1ST_READ 0x8c10ee8c); game code only maps its error code to `drive%d,file CRC error`.  Inside RAM: **CRC-16/X-25 per arena section** (same routine as ZSARC, `0x8c15b028`), table in 1ST_READ BSS, not in the file.  Header fields (savetime x2, checksum, savecount, money, year, club word, owner name) are compared by the "exe check". | PROVEN (sections, exe check) / INFERRED (file CRC algorithm) |
| Can a display-time name bank work without changing a serialised struct? | **Yes for players, staff, towns, sponsors** (static, disc-resident data: nothing to save).  For user and club name a bank is only needed if the entry limit is raised; the 14-byte fields stay as they are.  The obstacle is not the save but the **number of name-read sites** (section 6). | PROVEN (save) / INFERRED (rest) |
| Where is the 12-character cut of player names? | **Not found in code.**  Evidence excludes most candidates (section 5); the decisive RAM-dump test is named there. | UNKNOWN (narrowed) |

## 2. What was decompiled (AUTOSAVE.BIN, base 0x8c8d0000)

| address | role | tag |
|---|---|---|
| `0x8c8d71e0` | **save-buffer builder**: allocates `0x10180` bytes (`mov.w 0x180` header size, literal `0x00010180`), byte-copies **0x10000 bytes from RAM `0x8ce4c000` to buffer+0x180**, then copies **0x100 bytes from `gsp+0x102c`** (`gsp = *(0x8c159220)`, the game-state object, `0x8c231400` in the dumps) to the buffer position of the arena section pointed to by `gsp+0x6c`, and 0x20 bytes from `*(0x8c159234)+0x316` to the section at `gsp+0x84`; callers `0x8c8d04b0`, `0x8c8d05f4` | PROVEN (`dis1.txt`) |
| `0x8c8d728a` | **load**: the exact reverse (buffer+0x180 -> `0x8ce4c000`, 0x100 bytes back to `gsp+0x102c`, 0x20 bytes back); callers `0x8c8d9640`, `0x8c8d96fc` | PROVEN |
| `0x8c8d72c8`, `0x8c8d73bc`, `0x8c8d74de`, `0x8c8d7644`, `0x8c8d7740`, `0x8c8d77fa`, `0x8c8d78ea` | per file type writers (type 0 G, 1 A, 2 P, 3 C, 4 D, 5 L, `_VM`/E): fill the info, pick a random icon/title byte (`0x8c8d7122`), call `0x8c8d3fc2` (allocate "Savefile size %d blocks", header init `0x8c8d32fa`) | PROVEN |
| `0x8c8dfcce` | file-name builder: `SAKATOK2.G%02d` / `A` / `P` / `C` / `D` / `L` (slots 00..07, 8 per drive), `SAKATOK2._VM`, `SAKATOK2.E%s`; writes a NUL at offset 12 (**12-character BUP file name**) | PROVEN |
| `0x8c8dfd7c` | list-info builder: reads the saved buffer (positions `ptr - 0x8ce4c000 + 0x180`) or live state; copies the **21-byte club word** (`*(0x8c159234)+0x2e0`) and the **14-byte user name** (`gsp+0x102c`), date bytes `gsp+0x104c..0x104f`, etc. | PROVEN |
| `0x8c8da056` | **exe check** ("EXE check start!"): header +0x22 savetime1, +0x26 savetime2, +0x2a checksum, +0x2e savecount, +0x32 money ("sikin"), +0x37 year, then bytes 0..0x14 = club word text (hw katakana, `sprintf("%s")` from the pointer table `0x8c8f47a8` indexed by a game-state field), 0x14..0x22 = the user name, all space-padded and compared with live state | PROVEN (`a1.txt`) |
| `0x8c8dccfc` area | Dp/Dc/Vtr "password" encoders: size check, CRC16 over the payload, `-bz-` LZSS, XOR with a 256-byte key (byte `i & 0xff`), `DpDecode:CRC missmatch` | PROVEN (structure) |
| `0x8c8ea100` | **name-by-ID accessor** (see section 6) | PROVEN |

## 3. Save file anatomy (types G and A)

```
file (VMU/BUP, SAKATOK2.G00..07 / A00..07)      size 0x10180 = 65,920 bytes = 129 blocks of 512
  +0x00000  header block, 0x180 bytes: VMS-style header built by 0x8c8d32fa (descriptions at +0x00 / +0x12 / +0x34, icon count 3 at +0x4c, speed 5 at +0x4e)
  +0x00180  arena copy, 0x10000 bytes = RAM 0x8ce4c000..0x8ce5c000, no compression, no encoding
```
* PROVEN: size literals (`0x00010180`, `mov.w 0x180`), the byte loop count (0x10000), no compressor in the path (`FUN_8c8d3fc2`), same bytes both directions.
* INFERRED: the first 0x60 bytes follow the Sega `bus_header` layout (strings `bus_header mismatch`, `myheader mismatch`, `header size %d , max %d`).

### 3.1 The arena: 15 sections (all four dumps agree; table built at boot by 1ST_READ `0x8c164272`)

`gsp+0x24 + 8*i = { u32 ptr, u16 size, u16 crc16 }`, `ptr[0] = 0x8ce4c004`, `ptr[i+1] = (ptr[i] + size[i] + 3) & ~3` (PROVEN: decompile of `0x8c164272`
and the arithmetic on the dump).  Each section is zero-filled at boot and its CRC stored with `0x8c15b028`.

| i | `gsp+` | arena offset | size | content (pt1 dump) |
|---|---|---|---|---|
| 0 | 0x24 | 0x00004 | 0x23fc | **player structs, 288 bytes each (31-32), name at +0 (14 bytes)**; the first 16 are named in pt1 (PROVEN) |
| 1 | 0x2c | 0x02400 | 0x0300 | no text |
| 2 | 0x34 | 0x02700 | 0x0300 | no text |
| 3 | 0x3c | 0x02a00 | 0x0700 | no text (small numeric runs) |
| 4 | 0x44 | 0x03100 | 0x0100 | no text |
| 5 | 0x4c | 0x03200 | 0x1000 | no text |
| 6 | 0x54 | 0x04200 | 0x0200 | no text |
| 7 | 0x5c | 0x04400 | 0x5100 | **72 x 288 bytes exactly**; no named struct in any dump (empty in the dumps; INFERRED array of 72 structs) |
| 8 | 0x64 | 0x09500 | 0x0f00 | no text |
| 9 | 0x6c | 0x0a400 | 0x0100 | **staging chunk of the game-state bytes `gsp+0x102c..0x112c`** (all zero in a live dump; filled by the save builder at `0x8c8d71e0`, restored at `0x8c8d728a`) |
| 10 | 0x74 | 0x0a500 | 0x0100 | no text |
| 11 | 0x7c | 0x0a600 | 0x0100 | no text |
| 12 | 0x84 | 0x0a700 | 0x0300 | target of the 0x20-byte copy (UNKNOWN meaning) |
| 13 | 0x8c | 0x0aa00 | 0x1300 | **second person-struct array, 16-17 x 288, names at +0** (`K. Hiramatsu`, `T. Kitamura`, ...), role UNKNOWN |
| 14 | 0x94 | 0x0bd00 | 0x2500 | no text |

* The arena ends at `0xe200`; bytes `0xe200..0x10000` (7,680) belong to no section and are **zero in all four dumps**, but the file copies them (PROVEN: both loops run 0x10000 bytes).
* The CRC halves of all 15 entries equal CRC-16/X-25 (init ffff, reflected 0x8408, xorout ffff) of the section bytes: **15 of 15 on pt1** (`svfmt_sec.py`).
* `gsp+0x102c` = user name (14 bytes: 12 characters, **space-padded to 12 in the dump** (`ABCDEFGHIJ  `), then two NULs), `gsp+0x103a` = club name (14 bytes), `+0x104c..` date/state bytes: PROVEN by dump `pt1` (test names) and `live3` (Japanese).
* The player struct is a copy of the 92-byte BPINFO record in the first 0x5c bytes (byte `+0x0f` differs, 0 -> 1), extended to 288 bytes.  The 14-byte name at +0 is a **copy**, not a reference (pt1: BPINFO 0x8c353724 and struct 0x8ce4c004 hold the same string): **names inside an existing save never follow a later change of the static tables.**  PROVEN (dump).  The player ID field inside the 288-byte struct: UNKNOWN (cheapest test: diff two structs of known IDs in a dump with `NEWCON` join data: `FUN_8c6d12ac` passes `id` as `*(short*)record`, name `id*0x5c + BPINFO`).

### 3.2 Other file types (sizes PROVEN, meaning INFERRED)

| file | total | payload at +0x180 | note |
|---|---|---|---|
| `_VM`, `E%s` | small | | VM icon / extra |
| P | 896 (0x380) | 312 | password-type record |
| C, D, L | 6,016 (0x1780) | **5,332 = 5,321 + 11** | one byte per player plus 11: flags, no names (INFERRED); written through Dp/Dc/Vtr encoders (CRC16, `-bz-`, XOR key) |

## 4. Checksums in detail

1. **File CRC** (`drive%d,file CRC error`): produced by the Sega bu library inside 1ST_READ (strings `BUD_ERR_*`, `VMS File System for Application`, CCITT table at `0x8c10ee8c`); AUTOSAVE compares an error code (`0x8c8d92b..`) and prints the message.  No CRC loop for the main file exists in the overlay.  Algorithm standard VMS: INFERRED.
2. **Section CRCs** (above): table in RAM (1ST_READ BSS, `gsp+0x24..`), **not written to the file** (the table bytes occur once in all dumps, at `0x8c231424`).  Verifier `0x8c16490a`: compares stored and recomputed CRC for 15 sections, message `blk:%d CRC error!`, return -1 (partial decompile, entry in the middle of the function).  Who refreshes the table after changes and whether a load runs the verifier: UNKNOWN; sites using the CRC vtable slot (`mov.w 0x3a4`): 1ST_READ 2, GAME 9, YOUTH 1, LOADBAR 1, 12 save-type overlays 8 each (`svfmt_vslot.py 3a4`).  **Consequence: a patch must never write into arena sections at run time** (display-time substitution does not).
3. **Exe check** (section 2): equality of header and live state; club word and **owner name must match** the live strings for the autosave to be accepted as "this game".  If a patch ever changes how the stored 14 bytes are produced (for example a token), header and state must use the same bytes.
4. Password files: CRC16 over payload, `CRYPTCRC:%04x`, XOR with the 256-byte key.

## 5. The 12-character cut (UNKNOWN, narrowed)

Facts (PROVEN unless marked):
* The name is intact in every store: BPINFO record, the 288-byte struct, the 30-byte static table (`pt1`: `Isao Nakagaki\0`), the save.
* Neither `%.12s`-style precision nor any truncating format exists: `svfmt_fmts.py '%[-0-9]*\.[0-9]+s'` finds **no** string in 1ST_READ or any overlay.  Name formats are `" %s"`, `"%s "`, `"@Y/%s@"`, `"%s %2d"`, `"%d %s"` and similar, written into stack buffers of 68 bytes and more (AUTOSAVE `0x8c8e9fde` uses `auStack_60[68]`).  All `%-12s` / `%-13s` / `%-14s` formats are **debug prints** (`ep suppl old=%4d:%-12s`, `JoinCheck:[%-12s]<-[%-14s]`).
* `strncpy(...,12)` (1ST_READ `0x8c013294`, `mov #12,r6` near the call; `svfmt_ncpy.py`) occurs at 325 sites in 17 overlays (the 15 accessor overlays, SCDRF, SEARCH).  The AUTOSAVE ones belong to the 12-character VMU file name (`0x8c8dfcce`); in SEARCH the checked ones are number-to-text helpers.  **No person-name copy of 12 bytes was found.**  So candidate (b) of docs/layout-issues.md section 3 (12-byte copy buffer) has **no code evidence**.
* Window cell counts stored as immediates into `+0x3c` (`svfmt_cells.py`): 17 cells (70 sites), 20 cells (169), others 5, 8, 9, 10, 21 once or twice, **no 7**.  So candidate (a) (narrow 7-cell label window, 13 units = blank + 6 full-width) is not the generic list window; MEETING's 7-cell label is set by another route.
* The Japanese design fits "blank + 6 full-width characters" = 13 units (user name stored as 12 characters, space-padded to 12; name formats `%-12s`; field 14 = 12 + 2 NUL).  INFERRED: the Event list column / player card was laid out for 12 half-width characters after a blank, and the cut is a **draw/column clip or a per-screen window**, not a data copy.

Decisive test (0 code reading needed): Flycast RAM dump with the Event list open (`wintext.py build/emu/<dump>.bin Nakaga`): `cells=N` and all 13 characters in the code array -> window/clip (the fix is that screen's `+0x3c` store or the clip rectangle); name present but letters missing -> a copy in that screen (search the 12/13-byte copy loops of the EVENT overlay near the staff array `EVENT.BIN#d604c` loaders).  Static follow-up if no emulator: decompile the Event-list builder of `EVENT.BIN` (`build/svfmt/ev_all.txt` already holds the full decompile) starting from the staff-array loaders (`EVENT.BIN` offsets `0xd604c`, `0xd58a4`, `0xd5bb4`).

## 6. Display-time name bank (design)

### 6.1 What the save requires
* **Nothing changes in the save.**  All stored name fields stay 14 bytes holding the short English form (<= 13 characters).  Saves keep loading in both directions.
* The bank is **read-only disc data** (new bank region in the 1ST_READ tail, docs/trans-bank.md), keyed by player ID (0..5320), staff index, town ID; it is never written by the game, so the section CRCs and the exe check are unaffected.
* A bank keyed by **ID** works where the ID is at hand at display time.  Where only the 14-byte copy is at hand (the 288-byte structs, the user name) the key has to come from the string: two options, in order of preference:
  1. **Hidden ID after the NUL** (names with <= 11 characters leave two spare bytes in the 14-byte field; BPINFO record, struct, static table and save keep them if copied as blocks): store the short name `T. Watanabe\0` + u16 bank index.  Works only for block copies (BPINFO -> struct copies the first 0x5c bytes: PROVEN identical bytes); `strcpy`-style copies lose it.  INFERRED, needs a dump check that the spare bytes survive in the struct.
  2. **Escape token** in the 14-byte field, e.g. `~` + 4 hex digits (`~0A3F`): ASCII, 5 bytes, survives every copy and compare, visibly harmless if not expanded; expansion by a patched reader.  Collides with nothing in the Japanese strings (cp932 text never uses `~` inside names; check `namescan.py` first).  Needs **every** reader patched; the saved copy carries the token, so a token written by one release must keep its meaning in all later releases (bank index stable).
* **User and club name** (typed by the player): keep the 14-byte rule (entry UI allows 13 half-width / 6 full-width).  If the entry limit is ever raised, the long form needs saved storage.  Candidate: the arena tail `0x8ce5a200..0x8ce5c000` (7,680 bytes, zero in all dumps, **copied by the save**).  **Risk (INFERRED, found by `svfmt_wscan.py`)**: `GAME.BIN` and `SS_EDIT.BIN` hold the literal `0x8ce5a800` (a buffer inside that range, SS_EDIT = the cheering-song editor, `d:\zeus\src\kaifu\ss_edit`), and `TRAINING`, `TV_EVENT`, `VTRLOAD`, `YOUTH` hold `0x8ce5c000`; use only `0x8ce5a200..0x8ce5a7ff` (1,536 bytes) after a canary test, or accept long user names as not saved (falls back to the 14-byte field).  Recommended: **do not raise the user-name limit** (pain low, docs/expansion/field-widths.md V5).

### 6.2 Existing token machinery to reuse
The engine already expands `#YOU#` (user name from `gsp+0x102c`), `#sname#` (club, `gsp+0x103a`), `#to#`, `#ken#`, `#chi#`, `#kyu#` inside message text (`'YOU#'` and `'sname#'` literals in 104 files each; docs/expansion/field-widths.md: `0x102c` loaded 323 times in 101 overlays, `0x103a` 199 times in 98).  New tokens such as `#YOUL#`, `#snameL#` (long forms) or `#pNNNN#` (player name by ID from the bank) can be added in the same expander (one routine per overlay copy, signature-patchable like the font hook) and used in **message text only**.  They do not help list screens, which print with `sprintf("%s")` of the raw field.

### 6.3 The name accessor (the one centralised read path found)
`FUN_8c8ea100(short id)` (AUTOSAVE `0x8c8ea100`; PROVEN decompile + disassembly):
```
if (id < 0 || id > 10990) { print "Illegal ..."; return error string; }
if (id < 5600)  return table + id*30;               // 30-byte records: reading(16) + name(14); table = 0x8c90742e in AUTOSAVE
return ptrtable[id - 5600];                          // ptrtable = 0x8c8f9158, 4-byte pointers, up to id 10990
```
* The same function is present in **15 overlays** (signature `e6 2f 4f 6e 22 4f 11 4e` + `muls.w #0x1e`, `svfmt_acc.py`): AUTOSAVE, BACKUP, BPMATCH, CHALMODE, CSAVE, CSAVE4, DMCLBEDT, ENDOPT, EXFLAG, EXTRADE, FREELOAD, LOAD, SONGSAVE, SPF_READ, VTRLOAD (CSAVE3 holds an older 29-byte-stride variant).  IDs 5321..5599 and 5600..10990 hold other person classes (staff / generated persons: semantics UNKNOWN).
* Returned pointer = record start (the hw-katakana reading at +0 in the AUTOSAVE table); whether callers add `+0x10` for the name: UNKNOWN (callers `0x8c8dff60`, `0x8c8e004c` inside the list-info builder).
* Patch: one cave per overlay replacing the first instructions: `if (bank has id) return &bank[id]`.  One site per overlay, 15 sites, same bytes everywhere.

### 6.4 Ranked patch list (sites are lower bounds)

| rank | patch | covers | sites | risk / status |
|---|---|---|---|---|
| 1 | **keep names <= 12/13 chars** (done, style guide 7.1); no code | all | 0 | none |
| 2 | locate and fix the 12-cut (section 5) once the mechanism is known; if it is a window / clip the fix is a constant | Event list, player card | probably 1-5 constants | UNKNOWN until dump |
| 3 | name accessor bank hook (6.3) | save/load/match-result screens (15 overlays) | 15 (1 per overlay) | low; static tables only |
| 4 | `#YOUL#`/`#snameL#`/`#pNNNN#` tokens in the message expander | message text | ~104 expander copies (1 routine each) + 0 data | low; text only |
| 5 | BPINFO-record readers (`id*0x5c + BPINFO`, e.g. NEWCON `0x8c6d12ac`) | news, contracts, lists | literal 0x5c: 7,793 loads in 120 files (noisy), real count UNKNOWN | high effort |
| 6 | 288-byte struct readers (name at +0, literal 0x120 5,421 loads in 86 files, noisy) | player cards, lineups, match | thousands | not recommended |
| 7 | long user / club name with saved storage (6.1) | N_ENTRY + all `#YOU#` users | 2 commit sites + 104 expanders + arena tail canary | not recommended |
| - | any change of arena sections, header size, file names | | | **forbidden**: breaks Japanese saves and the section CRCs |

## 7. Not decompiled / open questions (with the cheapest test)

| item | tag | test |
|---|---|---|
| CSAVE, CSAVE3, SONGSAVE differences to AUTOSAVE | UNKNOWN | decompile with `svfmt_dec.ps1` after `svfmt_mkimg.py CSAVE` (images and project already prepared for CSAVE/SONGSAVE) |
| Who refreshes the section CRC table; is the verifier `0x8c16490a` run on load | UNKNOWN | callers of the CRC vtable slot in GAME/YOUTH/LOADBAR (`svfmt_vslot.py 3a4`), or a Flycast watchpoint on `0x8c231424+6` while saving |
| Role of arena sections 1-6, 8, 10-14 | UNKNOWN | diff dumps before/after a match / training |
| Player ID field inside the 288-byte struct | UNKNOWN | compare struct bytes of two players whose IDs are known |
| Spare bytes after the NUL survive struct copy | UNKNOWN | read struct and BPINFO name fields of a short-named player in a dump |
| Arena tail `0xe200..` free at run time | INFERRED (zero in 4 dumps; static literals in GAME/SS_EDIT at `0x8ce5a800`) | canary over all modes (docs/trans-bank.md T6) |
| File CRC algorithm | INFERRED (standard VMS CCITT) | recompute over a real VMU image after one save |
| 12-character cut mechanism | UNKNOWN (section 5) | RAM dump with Event list open |

## 8. Files

Scripts (all read-only, `python -I -X utf8 tools/re/<name>.py`): `svfmt_mkimg.py` (combined Ghidra images), `svfmt_imp.ps1` / `svfmt_impov.ps1`
(import into `build/svfmt/proj`), `svfmt_dec.ps1` / `svfmt_dis.ps1` (decompile / disassemble addresses), `svfmt_str.py`, `svfmt_xref.py`,
`svfmt_xrange.py`, `svfmt_words.py`, `svfmt_lit.py`, `svfmt_entries.py` (code); `svfmt_ram.py`, `svfmt_gs.py`, `svfmt_gs2.py`, `svfmt_sec.py`,
`svfmt_arena.py`, `svfmt_arena2.py`, `svfmt_tail.py`, `svfmt_tabcopy.py`, `svfmt_findstr.py`, `svfmt_pt*.py`, `svfmt_bpid.py` (dump checks);
`svfmt_acc.py`, `svfmt_ncpy.py`, `svfmt_cells.py`, `svfmt_vslot.py`, `svfmt_wscan.py`, `svfmt_fmts.py`, `svfmt_grepall.py`, `svfmt_crcscan.py` (censuses).
Decompile output (not committed): `build/svfmt/*.txt` (`all.txt` = whole AUTOSAVE, `ev_all.txt` = whole EVENT).

## Status after stage 3 (docs, 2026-11-11)

See `docs/expansion/status.md` for the table of what was built from this study, its flag or file, how far it is proven, and what is still open.  The summary for this study:

* Findings used by the project: the save keeps the 14-byte user and club names and the names inside ~48 runtime player structs but not the other players' names, so no record is widened and a name bank would be display-only (section 6).  The bank is not built (field-widths ranks 5-7).
* Still open: section 7 (CSAVE / CSAVE3 / SONGSAVE not decompiled, who refreshes the section CRC table, the 12-character cut mechanism).  The decompile output lives under `build/svfmt/` (not committed).
