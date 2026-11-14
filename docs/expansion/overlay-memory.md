# Expansion study: overlay and RAM headroom

Area: FLOW_PRG overlays, `1ST_READ.BIN`, fixed RAM text buffers, and the "append / new file" options.
Read-only study. Nothing was run in an emulator; Ghidra was used headless on the existing `memmap` project copy (`<GHIDRA_PROJECTS>\ghproj_memmap`, read-only mode).
Status words: **PROVEN** = read from decompiled code, a data table or a RAM dump and re-checked by a script here; **INFERRED** = follows from PROVEN facts, never run in the game; **UNKNOWN** = needs a dynamic test.
New small read-only scripts (prefix `ovmem`): `tools/re/ovmem_scan.py ovmem_dump.py ovmem_cmp.py ovmem_dir.py ovmem_desc.py ovmem_rows.py ovmem_stats.py ovmem_table.py ovmem_refs.py ovmem_refs2.py ovmem_grep.py ovmem_w.py ovmem_gs.py ovmem_ghidra.ps1`.
Most of the memory model was already written down by the earlier `memmap`, `bank` and `synth` agents (`docs/memory-map.md`, `docs/capacity-design.md`, `docs/text-engine.md` s6); this note re-verifies the parts that matter for "grow the disc / break compatibility" and adds what was missing (who decides the load address, the directory-cache limit, the generic file loader, the fixed name fields).

## 0. Result in ten lines

1. **RAM is not the binding limit; the fixed-size string slots are.** The overlay arena (0x8c2b0000-0x8cd5c000, 11.2 MB) is almost all malloc heap: median heap per overlay 1,785,888 B (min 58,784 HELP, max 8,570,976 ENDING), against a total English need of about 317 KB external bytes at natural English (`docs/capacity-design.md` s0). PROVEN (static) for the heap sizes, INFERRED for sufficiency.
2. **An overlay file may be any size.** Its size is read from the ISO9660 directory record at load time (sector count, handle+0x2c); no size table, no hard-coded size in the loader or in the 1ST_READ scene table. The only coupling is the slot span: the file plus its heap must sit inside the `count` slots written in the overlay's own descriptor (`desc[1] & 0x7f`). PROVEN (decompiled `FUN_8c162848`, `FUN_8c162570`, `FUN_8c162ac0`).
3. **The load address is a slot base chosen by the caller, not by the overlay.** The 1ST_READ scene table (5-word records, 103 FLOW_PRG names) carries the slot index in the low byte of its third word; for all 103 records that slot's base equals the base the overlay image itself assumes. INFERRED (103/103 agree; the call site that reads the word is not decompiled). So an overlay cannot be moved to another slot without editing both its image (absolute pointers) and the table; there is no reason to.
4. **Growing an overlay needs three things**: raise the `_end` word (heap start = `round32(_end)+0x20`), keep BSS addresses valid (so the file must carry a zero pad up to the old `_end`), and stay inside the slot span. Disc cost of the pad dominates: 8,844,107 B if every BSS overlay were padded, but only the overlays that actually grow need it. INFERRED (loader formulas PROVEN; never booted).
5. **Safe growth is large for almost every overlay** (table in s3). Only MEETING, TRAINING, HELP, DRAFT-class prose overlays and the stub-special ones (GAME, ESTABLIS, MOVIE*, 7 non-slot overlays) need care. The slot count can be raised by editing one byte per overlay (+1 MiB heap each) if the following slot is free when it runs (UNKNOWN which are free).
6. **1ST_READ.BIN cannot usefully grow.** It is 2,949,120 B, loaded at 0x8c010000, ends at 0x8c2e0000 and therefore already overlaps slot 0 and slot 1 (the last 0x30000 bytes are overwritten once the arena is used). Anything appended lands in the overlay arena. Only its zero/filler gaps (about 260 KB, bank agent) and the FONT.BIN tail are usable. PROVEN (arithmetic + dumps).
7. **New files are loadable on demand with an existing engine routine**: the generic file loader `FUN_8c15eede` (function-table entry 0x8c159060, used by 10 overlays: CLUBEDIT ENDING EVENT GAME JSCEVENT MON_INST NEWS SPT_CLUB SS_EDIT TRAINING) opens a file by name, takes its size from the file system and either reads into a given address or mallocs `sectors*2048` bytes. PROVEN (decompile). Calling it from patched overlay code is INFERRED.
8. **Adding a file to a directory is limited by a hard-coded directory cache**: 1ST_READ holds a table (name, entry count) per directory, e.g. FLOW_PRG 182 entries for 176 files on disc (6 spare), ETC_DATA 162/153, GAME 82/74, EVENT 202/175, GAME2 32/13, MASCOT 34/11, BCAST 10/3. PROVEN (table + decompiled `FUN_8c15c18c` allocates `count*0x2c+0x10`); behaviour when exceeded UNKNOWN. The count is a data word, patchable.
9. **Fixed name fields live in the global game-state block in 1ST_READ BSS**: manager name at 0x8c23242c and club name at 0x8c23243a, 14 bytes apart (seen in `build/emu/pt1_ram.bin` after typing ABCDEFGHIJ twice). Widening them moves other state and almost certainly the save format. INFERRED (adjacent data not decoded, save layout not analysed).
10. **Text already placed by the pipeline never needed memory**: `textrepack` keeps the image size, `--append-safe` is the only growth path and it has no budget check (see s7).

## 1. How overlays are loaded (PROVEN unless marked)

* **Scene/overlay table** in `1ST_READ.BIN` at 0x8c16c2cc..0x8c16cb00 (referenced from the table-init call at 0x8c164a78, `FUN_8c15c18c`). Records are 5 words: `dir(1=FLOW_PRG)`, `a`, `b`, `0`, `name ptr` (e.g. CLUBEDIT at 0x8c16c42c, name string 0x8c16add0). `ovmem_dump.py` lists 121 name pointers, 103 of them FLOW_PRG overlays. Word `a` is 0xa, 0x14, 0x32, 0x64, 0x1f4 or 0x2bc and does not correlate with file size (GAME 2.39 MB has 0xa, DRSKIYA 45 KB has 0x64): **not a size** (meaning UNKNOWN, probably a loading-bar weight). Word `b` low byte = slot index (1..11); the high byte is 0, 1, 3 or 5 (0x103, 0x107, 0x307, 0x501): meaning UNKNOWN (companion or must-stay-resident slot?). `ovmem_cmp.py`: for all 103 FLOW_PRG records the slot base of the low byte equals the overlay's base in `build/memmap/overlays.tsv`; 10 overlays have no record at all (COMM CON_REP NF_CON PASS_PL J1_REP PL_CON LOADBAR CSAVE3 EXFLAG NEW_YEAR; SECBND is not an overlay): they are loaded by another path (UNKNOWN).
* **Load**: `FUN_8c162848(?, ?, name, dir, load_addr)` opens the file through the directory cache, reads `(len+0x7ff)>>11` whole sectors, and walks the slot array: the slot that contains `load_addr` must be state 1 (free) else `MODULE READ ERROR TYPE1` is printed; every further slot whose base lies inside `[load_addr, load_addr+sectors*0x800)` must also be free (`TYPE2`) and is marked as covered (state 7). Size source: `*(*(handle+0x28)+0x2c)*0x800`, i.e. the sector count from the file system. No other size exists. (`tools/re/capacity/memmap/d1.txt` lines 749-840.)
* **Module open** `FUN_8c162570(?, base, desc, ...)`: requires all `desc[1]&0x7f` slots (`desc[0]` = first slot) to be state 1 (`MODULE OPEN ERROR TYPE1`), stores `base`, sets state 4, `slot+0x40 = desc[4]` (heap start) and `slot+0x14 = (sum of slot sizes + base) - desc[4]` (heap size). If `desc[4]==0` the heap start is the slot base. `desc[1]&0x80` (GAME only: 0x8a = 10 slots + flag) makes the loader calloc 0x24 bytes.
* **State machine** `FUN_8c162ac0`: after the read it calls the image's entry stub (offset 0), which loads the function pointer at 0x8c159144 and calls it as `hook(desc, base, r6)` with `r6 = ((*ENDVAR | 0x80000000) & ~0x1f) + 0x20` (stub bytes at CLUBEDIT 0x8c2d0000..0x8c2d001c, `shdis.py`). It then compares `FUN_8c1631be(load)` with the descriptor's `desc[0]`; the hook rewrites `desc[0]` from the address (N_ENTRY's image has desc[0]=1 but runs in slot 7), so the "address miss" check does not constrain us. Stub bytes 0x38..0xff are zero padding (about 200 B free for patch code); the descriptor sits near the end of each image (CLUBEDIT +0x1ecd0, GAME +0x10ebc0).
* **Slot table** at 0x8c16bf9c (8-byte entries base,size): slot 0 0x8c2b0000/0x20000; slots 1-8 0x8c2d0000 + n*0x100000 (1 MiB); slot 9 0x8cad0000/0x90000; slot 10 0x8cb60000/0x40000 (HELP); slot 11 0x8cba0000/0x1bc000 (FACEMDUL); ends 0x8cd5c000 = root FONT.BIN. Read directly here (`ovmem_w.py 8c16bf9c ...`).
* **Who allocates**: the loader allocates slots (state array of 12 x 0x60 B at 0x8c228384) and creates one malloc arena per opened module covering `[heap start, end of its last slot)`; `malloc` = `FUN_8c16325a` (best fit, request rounding `(n+0x3f)&~0x1f`, 0x20 B headers, requests > 0x1000 from the low end, <= 0x1000 from the high end), free = `FUN_8c163496`. There is **no common heap**: every overlay group has its own arena (only the 0x8c2b0000 slot 0 and the three 1ST_READ pools are global). Out of memory prints a debug line, sets byte 0x8c230bd6 and returns NULL (no halt; the caller decides, UNKNOWN). Details and 7 measured arenas: `docs/memory-map.md` s3 and s5.
* **BSS**: nothing clears BSS beyond the file's last sector (PROVEN for N_ENTRY: its BSS holds leftovers of earlier overlays); only GAME's stub clears `[*0x8c4bc88c,*ENDVAR)` (hand-disassembled, INFERRED).
* **Directory cache** (new here): the loader finds files through a directory cache initialised by `FUN_8c15c18c` from a 16-byte-entry table at 0x8c16c104 (name ptr, entry count, 0, 0): `ovmem_dir.py` prints it. Counts are capacities (>= files on disc): SOUND 34/20, FLOW_PRG 182/176, ETC_DATA 162/153, GAME 82/74, BCAST 10/3, FACE 23/21, TRAINING 18/12, NEWS 74/67, EVENT 202/175, GAME2 32/13, MASCOT 34/11, SSONG 382/364, ATFIRST 22/15. `FUN_8c15c18c` mallocs `count*0x2c+0x10` per directory and reads the directory into it. So the FLOW_PRG directory may take 6 more entries unchanged (INFERRED), more after editing the count word.

## 2. What sits where in RAM (PROVEN from `docs/memory-map.md`, four dumps, re-read)

| address | content |
|---|---|
| 0x8c000000-0x8c010000 | BIOS / IP.BIN work area |
| 0x8c010000-0x8c2e0000 | `1ST_READ.BIN` (2,949,120 B); crt0 zero-fills [0x8c16f800,0x8c299400) (BSS: loader globals, slot structs, global game state, e.g. the OOM flag byte 0x8c230bd6, the name block at 0x8c23242c) |
| 0x8c2b0000-0x8c2d0000 | slot 0 system arena (128 KiB), **under the file tail** |
| 0x8c2d0000-0x8cad0000 | slots 1-8 (1 MiB each) |
| 0x8cad0000-0x8cb60000 | slot 9 (0x90000), zero in all dumps but part of 9 overlays' heaps |
| 0x8cb60000-0x8cba0000 | slot 10 HELP (resident, heap 58,784 B) |
| 0x8cba0000-0x8cd5c000 | slot 11 FACEMDUL (resident, heap 1,050,880 B) |
| 0x8cd5c000-0x8ce02000 | root FONT.BIN (663,324 B, 16,612 B spare tail) |
| 0x8ce02000-0x8ce80000 | SHTEX0.ZAR, BAR.TBD, SECFTEX0.ZAR, then 98,304 B spare |
| 0x8ce80000-0x8d000000 | 1.5 MB block, stack at the top |

After an overlay's file end: BSS `[file_end,_end)` (3..0x3f bytes of rounding in between), then heap `[round32(_end)+0x20, slot_end)`, then the base of the next slot (either free state or another overlay's file; which one depends on the game flow: UNKNOWN except the four dumps: S_SELECT(1-4)+N_ENTRY(7), MOVIE_BG(1-4)+TITLE(5-8), CLUBEDIT(1-5), HELP and FACEMDUL always). Between the file end and the heap start there is no free byte for a no-BSS overlay.

## 3. Per-overlay table (generated by `ovmem_table.py` from `build/memmap/overlays.tsv`; PROVEN: base, file size, slot count, BSS, heap; INFERRED: safe growth)

Columns: **safe growth** = `append_cons` of the memmap agent (policy: 0.5 x the free bytes of the dumped moment for the 7 measured arenas, heap/8 for the rest; a rule no observed state violates, not a guarantee); **hard limit** = heap minus 64 KiB (theoretical); **extra disc** = BSS pad (only overlays with BSS) + growth, i.e. what the file grows by on the disc. The heap loses only the growth, not the pad (BSS is already carved out of the heap). Evidence for every row: loader formulas of s1 + `overlays.tsv` (stub emulation `sh4stub.py`, agrees with the independent survey for 108 of 113; live slot structs for 7 of 7). "Slots" is the descriptor count, i.e. the span of the arena.

| overlay | load addr | file B | slots | BSS B | heap B (after BSS) | safe growth B (heap-limited) | hard limit B | extra disc B (BSS pad + growth) | JA text B | note |
|---|---|---|---|---|---|---|---|---|---|---|
| ABROAD | 0x8c2d0000 | 527546 | 2 | 46386 | 1523200 | 188416 | 1457664 | 234802 | 13771 |  |
| AUTOSAVE | 0x8c8d0000 | 575218 | 3 | 310255 | 1801472 | 221184 | 1735936 | 531439 | 41571 |  |
| BACKUP | 0x8c4d0000 | 598690 | 2 | 310911 | 1187520 | 147456 | 1121984 | 458367 | 43326 |  |
| BPMATCH | 0x8c2d0000 | 686106 | 6 | 678538 | 4926784 | 614400 | 4861248 | 1292938 | 47311 |  |
| BPMWEEK | 0x8c2d0000 | 133922 | 2 | 10058 | 1953152 | 241664 | 1887616 | 251722 | 470 |  |
| CAP_SLCT | 0x8c2d0000 | 273682 | 2 | 55051 | 1768416 | 217088 | 1702880 | 272139 | 2964 |  |
| CE_VS | 0x8c2d0000 | 461769 | 2 | 0 | 1635360 | 200704 | 1569824 | 200704 | 911 |  |
| CHALDANI | 0x8c4d0000 | 55392 | 4 | 0 | 4138880 | 516096 | 4073344 | 516096 | 5493 |  |
| CHALMODE | 0x8c4d0000 | 944573 | 4 | 0 | 3249728 | 405504 | 3184192 | 405504 | 46765 |  |
| CLUBEDIT | 0x8c2d0000 | 221853 | 5 | 0 | 5021024 | 634880 | 4955488 | 634880 | 7307 |  |
| COMM | 0x8c2e0000 | 10929 | 1 | 3307 | - | - | - | - | - | slot span unknown (base not slot aligned) |
| CON_REP | 0x8c2e0000 | 10929 | 1 | 3307 | - | - | - | - | - | slot span unknown (base not slot aligned) |
| CSAVE | 0x8c4d0000 | 591474 | 2 | 311395 | 1194272 | 147456 | 1128736 | 458851 | 42105 |  |
| CSAVE3 | 0x8c4d0000 | 543272 | 2 | 311969 | 1241888 | 151552 | 1176352 | 463521 | 31727 |  |
| CSAVE4 | 0x8c4d0000 | 600770 | 2 | 312491 | 1183872 | 147456 | 1118336 | 459947 | 42745 |  |
| DATAROOM | 0x8c2d0000 | 387036 | 2 | 0 | 1710112 | 212992 | 1644576 | 212992 | 8905 |  |
| DMCLBEDT | 0x8c2d0000 | 736270 | 6 | 342378 | 5212800 | 651264 | 5147264 | 993642 | 44675 |  |
| DRAFT | 0x8c2d0000 | 480458 | 2 | 49542 | 1567136 | 192512 | 1501600 | 242054 | 120588 |  |
| DRSBEST | 0x8c4d0000 | 153705 | 2 | 0 | 1943424 | 241664 | 1877888 | 241664 | 12719 |  |
| DRSDENDO | 0x8c4d0000 | 430684 | 2 | 0 | 1666464 | 204800 | 1600928 | 204800 | 8628 |  |
| DRSGP | 0x8c4d0000 | 75740 | 2 | 0 | 2021408 | 249856 | 1955872 | 249856 | 8161 |  |
| DRSGRF | 0x8c4d0000 | 141788 | 2 | 0 | 1955360 | 241664 | 1889824 | 241664 | 8123 |  |
| DRSGRFJ | 0x8c4d0000 | 64564 | 2 | 0 | 2032576 | 253952 | 1967040 | 253952 | 7973 |  |
| DRSHRANK | 0x8c4d0000 | 126940 | 2 | 0 | 1970208 | 245760 | 1904672 | 245760 | 23005 |  |
| DRSISEKI | 0x8c4d0000 | 142389 | 2 | 0 | 1954752 | 241664 | 1889216 | 241664 | 8599 |  |
| DRSJAPAN | 0x8c4d0000 | 48608 | 2 | 0 | 2048512 | 253952 | 1982976 | 253952 | 7921 |  |
| DRSKIYA | 0x8c4d0000 | 45832 | 2 | 0 | 2051296 | 253952 | 1985760 | 253952 | 7817 |  |
| DRSLIST | 0x8c4d0000 | 342256 | 2 | 0 | 1754880 | 217088 | 1689344 | 217088 | 16246 |  |
| DRSOLIST | 0x8c4d0000 | 349156 | 2 | 0 | 1747968 | 217088 | 1682432 | 217088 | 16186 |  |
| DRSRANK | 0x8c4d0000 | 151393 | 2 | 0 | 1945728 | 241664 | 1880192 | 241664 | 5011 |  |
| DRSSRANK | 0x8c4d0000 | 70212 | 2 | 0 | 2026912 | 249856 | 1961376 | 249856 | 8013 |  |
| ENDING | 0x8c2d0000 | 601078 | 10 | 68519 | 8570976 | 1069056 | 8505440 | 1137575 | 1414 |  |
| ENDOPT | 0x8c8d0000 | 685460 | 3 | 385132 | 1616352 | 200704 | 1550816 | 585836 | 44997 |  |
| ESTABLIS | 0x8c2d0000 | 242028 | 4 | 0 | 2097120 | 0 | 0 | - | 39249 | stub ignores _end, private area |
| EVENT | 0x8c2d0000 | 1389382 | 9 | 154366 | 7434656 | 925696 | 7369120 | 1080062 | 76173 |  |
| EXFLAG | 0x8c4d0000 | 592974 | 2 | 313191 | 1190976 | 147456 | 1125440 | 460647 | 41965 |  |
| EXTRADE | 0x8c4d0000 | 596938 | 2 | 317187 | 1183008 | 147456 | 1117472 | 464643 | 43181 |  |
| FACEMDUL | 0x8cba0000 | 710656 | 1 | 57067 | 1050880 | 53248 | 985344 | 110315 | - |  |
| FIRE | 0x8c2d0000 | 274518 | 2 | 45966 | 1776640 | 221184 | 1711104 | 267150 | 12232 |  |
| FLOW1 | 0x8c2d0000 | 12211 | 1 | 3309 | 1033024 | 126976 | 967488 | 130285 | 1152 |  |
| FLOW10 | 0x8cb60000 | 12211 | 1 | 3309 | 246592 | 28672 | 181056 | 31981 | 1152 |  |
| FLOW11 | 0x8cba0000 | 12211 | 1 | 3309 | 1803072 | 225280 | 1737536 | 228589 | 1152 |  |
| FLOW2 | 0x8c3d0000 | 12211 | 1 | 3309 | 1033024 | 126976 | 967488 | 130285 | 1152 |  |
| FLOW3 | 0x8c4d0000 | 12211 | 1 | 3309 | 1033024 | 126976 | 967488 | 130285 | 1152 |  |
| FLOW4 | 0x8c5d0000 | 12211 | 1 | 3309 | 1033024 | 126976 | 967488 | 130285 | 1152 |  |
| FLOW5 | 0x8c6d0000 | 12211 | 1 | 3309 | 1033024 | 126976 | 967488 | 130285 | 1152 |  |
| FLOW6 | 0x8c7d0000 | 12211 | 1 | 3309 | 1033024 | 126976 | 967488 | 130285 | 1152 |  |
| FLOW7 | 0x8c8d0000 | 12211 | 1 | 3309 | 1033024 | 126976 | 967488 | 130285 | 1152 |  |
| FLOW8 | 0x8c9d0000 | 12211 | 1 | 3309 | 1033024 | 126976 | 967488 | 130285 | 1152 |  |
| FLOW9 | 0x8cad0000 | 12211 | 1 | 3309 | 574272 | 69632 | 508736 | 72941 | 1152 |  |
| FREELOAD | 0x8c8d0000 | 590146 | 3 | 310911 | 1785888 | 221184 | 1720352 | 532095 | 41860 |  |
| GAME | 0x8c2d0000 | 2389512 | 10 | 0 | 6851040 | 856064 | 6785504 | 856064 | 58322 | stub zeroes [?,_end): needs stub patch |
| GAMEOVER | 0x8c4d0000 | 673990 | 2 | 45155 | 1377984 | 172032 | 1312448 | 217187 | 1220 |  |
| GETREP | 0x8c2d0000 | 210468 | 2 | 0 | 1886656 | 233472 | 1821120 | 233472 | 8943 |  |
| GMSHOW00 | 0x8c2d0000 | 19263 | 2 | 3441 | 2074432 | 258048 | 2008896 | 261489 | 420 |  |
| GMSHOW01 | 0x8c2d0000 | 19635 | 2 | 3441 | 2074048 | 258048 | 2008512 | 261489 | 412 |  |
| GMSHOW02 | 0x8c2d0000 | 19271 | 2 | 3441 | 2074432 | 258048 | 2008896 | 261489 | 428 |  |
| G_INCOME | 0x8c4d0000 | 217829 | 2 | 74731 | 1804576 | 225280 | 1739040 | 300011 | 15723 |  |
| G_RESULT | 0x8c6d0000 | 213459 | 2 | 25321 | 1858368 | 229376 | 1792832 | 254697 | 1310 |  |
| HELP | 0x8cb60000 | 195381 | 1 | 7947 | 58784 | 20480 | 0 | 28427 | 110032 |  |
| HEREWEGO | 0x8c2d0000 | 485318 | 3 | 53227 | 2607168 | 323584 | 2541632 | 376811 | 1280 |  |
| HOMETOWN | 0x8c2d0000 | 414385 | 4 | 21187 | 3758720 | 466944 | 3693184 | 488131 | 69438 |  |
| INITCON | 0x8c6d0000 | 72848 | 2 | 3322 | 2020960 | 249856 | 1955424 | 253178 | 557 |  |
| INVEST | 0x8c4d0000 | 97236 | 2 | 0 | 1999904 | 249856 | 1934368 | 249856 | 15485 |  |
| J1_REP | 0x8c4e0000 | 10929 | 1 | 3307 | - | - | - | - | - | slot span unknown (base not slot aligned) |
| JSCEVENT | 0x8c2d0000 | 64464 | 2 | 0 | 2032672 | 253952 | 1967136 | 253952 | 1397 |  |
| LOAD | 0x8c4d0000 | 596554 | 2 | 317187 | 1183392 | 147456 | 1117856 | 464643 | 42873 |  |
| LOADBAR | 0x8c800000 | 122196 | 2 | 0 | - | - | - | - | - | slot span unknown (base not slot aligned) |
| LOCAL | 0x8c2d0000 | 143011 | 2 | 8621 | 1945504 | 241664 | 1879968 | 250285 | 28894 |  |
| LOGO | 0x8c2d0000 | 7855 | 2 | 245 | 2089024 | 258048 | 2023488 | 258293 | 63 |  |
| MEETING | 0x8c2d0000 | 874298 | 2 | 250262 | 972576 | 118784 | 907040 | 369046 | 376951 |  |
| MON_INST | 0x8c4d0000 | 195656 | 2 | 0 | 1901472 | 237568 | 1835936 | 237568 | 3103 |  |
| MOVIE | 0x8c2d0000 | 474480 | 4 | -96 | 3718880 | 462848 | 3653344 | 462848 | 8 | stub adds 0x400, title-time |
| MOVIE_BG | 0x8c2d0000 | 474876 | 4 | -96 | 3718496 | 1855488 | 3652960 | 1855488 | 8 | stub adds 0x400, title-time |
| NENREP | 0x8c2d0000 | 225796 | 2 | 0 | 1871328 | 233472 | 1805792 | 233472 | 15457 |  |
| NEWCON | 0x8c6d0000 | 329462 | 2 | 65234 | 1702432 | 208896 | 1636896 | 274130 | 16218 |  |
| NEWMONTH | 0x8c2d0000 | 641092 | 2 | 0 | 1456032 | 180224 | 1390496 | 180224 | 138 |  |
| NEWS | 0x8c2d0000 | 1396458 | 6 | 1286758 | 3608224 | 450560 | 3542688 | 1737318 | 303165 |  |
| NEWS_ED | 0x8c8d0000 | 636862 | 3 | 107114 | 1942976 | 241664 | 1877440 | 348778 | 62456 |  |
| NEWS_OP | 0x8c8d0000 | 578463 | 3 | 46021 | 2062464 | 253952 | 1996928 | 299973 | 25558 |  |
| NEWUNIF | 0x8c2d0000 | 195309 | 2 | 0 | 1901824 | 237568 | 1836288 | 237568 | 891 |  |
| NEW_YEAR | 0x8c4d0000 | 26348 | 2 | 0 | 2070784 | 258048 | 2005248 | 258048 | 281 |  |
| NF_CON | 0x8c2e0000 | 10929 | 1 | 3307 | - | - | - | - | - | slot span unknown (base not slot aligned) |
| N_ENTRY | 0x8c8d0000 | 67320 | 1 | 3932 | 977312 | 368640 | 911776 | 372572 | 1652 |  |
| OFFICE | 0x8c6d0000 | 668231 | 2 | 133661 | 1295232 | 159744 | 1229696 | 293405 | 15704 |  |
| OPTION | 0x8c8d0000 | 36515 | 1 | 3605 | 1008448 | 122880 | 942912 | 126485 | 1576 |  |
| PASS_PL | 0x8c2e0000 | 10929 | 1 | 3307 | - | - | - | - | - | slot span unknown (base not slot aligned) |
| PLNUMSET | 0x8c2d0000 | 357810 | 2 | 45531 | 1693792 | 208896 | 1628256 | 254427 | 14992 |  |
| PL_CON | 0x8c4e0000 | 10929 | 1 | 3307 | - | - | - | - | - | slot span unknown (base not slot aligned) |
| PL_EDIT | 0x8c4d0000 | 390505 | 2 | 0 | 1706624 | 212992 | 1641088 | 212992 | 23478 |  |
| PWK_EDIT | 0x8c2d0000 | 395425 | 2 | 129227 | 1572480 | 192512 | 1506944 | 321739 | 7875 |  |
| RECON | 0x8c4d0000 | 339854 | 2 | 46314 | 1710976 | 212992 | 1645440 | 259306 | 17136 |  |
| SCDRF | 0x8c2d0000 | 410142 | 2 | 46071 | 1640928 | 204800 | 1575392 | 250871 | 73307 |  |
| SCHE0 | 0x8c4d0000 | 390724 | 2 | 89836 | 1616576 | 200704 | 1551040 | 290540 | 30655 |  |
| SCHE1 | 0x8c4d0000 | 390724 | 2 | 89832 | 1616576 | 200704 | 1551040 | 290536 | 30655 |  |
| SEARCH | 0x8c4d0000 | 603106 | 2 | 46006 | 1448032 | 180224 | 1382496 | 226230 | 8877 |  |
| SELNAT | 0x8c2d0000 | 188020 | 2 | 0 | 1909120 | 237568 | 1843584 | 237568 | 2159 |  |
| SONGSAVE | 0x8c8d0000 | 591286 | 3 | 310911 | 1784768 | 221184 | 1719232 | 532095 | 42299 |  |
| SPF_READ | 0x8c2d0000 | 712317 | 4 | 311399 | 3170560 | 393216 | 3105024 | 704615 | 53085 |  |
| SPONSOR | 0x8c6d0000 | 256094 | 2 | 77110 | 1763936 | 217088 | 1698400 | 294198 | 31851 |  |
| SPONSOR2 | 0x8c4d0000 | 256162 | 2 | 77110 | 1763872 | 217088 | 1698336 | 294198 | 31851 |  |
| SPT_CLUB | 0x8c2d0000 | 58800 | 2 | 0 | 2038336 | 253952 | 1972800 | 253952 | 2001 |  |
| SS_EDIT | 0x8c4d0000 | 102044 | 4 | 0 | 4092256 | 507904 | 4026720 | 507904 | 6709 |  |
| SUPPORT | 0x8c2d0000 | 139206 | 2 | 13231 | 1944704 | 241664 | 1879168 | 254895 | 3671 |  |
| S_SELECT | 0x8c2d0000 | 363080 | 4 | 0 | 3831200 | 847872 | 3765664 | 847872 | 2289 |  |
| TITLE | 0x8c6d0000 | 241138 | 4 | 11738 | 3941408 | 1069056 | 3875872 | 1080794 | 6206 |  |
| TOWN | 0x8c4d0000 | 433459 | 2 | 106177 | 1557504 | 192512 | 1491968 | 298689 | 16183 |  |
| TOWNDATA | 0x8c4d0000 | 83746 | 1 | 8126 | 956672 | 118784 | 891136 | 126910 | 14375 |  |
| TRAINING | 0x8c2d0000 | 770218 | 2 | 91150 | 1235776 | 151552 | 1170240 | 242702 | 254598 |  |
| TV_EVENT | 0x8c2d0000 | 52616 | 2 | 0 | 2044512 | 253952 | 1978976 | 253952 | 3345 |  |
| VTRLOAD | 0x8c2d0000 | 590706 | 2 | 310915 | 1195520 | 147456 | 1129984 | 458371 | 42190 |  |
| WEEKLY | 0x8c2d0000 | 369256 | 1 | 72084 | 607232 | 73728 | 541696 | 145812 | 16939 |  |
| YOUTH | 0x8c2d0000 | 478398 | 2 | 69774 | 1548960 | 192512 | 1483424 | 262286 | 26362 |  |

Reading the table: 106 overlays have a derivable heap; 92 of them end at or before 0x8cad0000 (slot 9), 14 reach slot 9 or beyond. Overlays whose safe growth is below 1.5 x their Japanese text bytes (the only ones where a natural-English overflow could exceed the budget): MEETING (text 376,951, growth 118,784, heap 972,576, pad 250,262), TRAINING (254,598 / 151,552 / 1,235,776 / pad 91,150), HELP (110,032 / 20,480 / 58,784 / pad 7,947; hard limit 0), ESTABLIS (39,249 / 0: stub ignores `_end`), NEWS (303,165 / 450,560 but BSS pad 1,286,758). The external bytes actually needed are far smaller than the text (pool deficits, `docs/capacity-design.md` s2: 316,638 B at natural English over the whole game; per overlay `deficit_out.txt`), so these are tight only if English is not shortened.

Special cases (all PROVEN as stubs, INFERRED as consequences):
* **GAME.BIN** (2,389,512 B, 10 slots, no BSS): its stub zeroes `[*0x8c4bc88c, *ENDVAR)`; raising `_end` would zero the appended bytes. Needs a stub patch (second literal for the clear end; stub padding 0x5c..0xff is free). Its text is 58,322 B (growth 856,064 would be ample).
* **ESTABLIS.BIN**: the stub takes the heap start from the slot table (base of slot 3 = 0x8c4d0000), ignoring `_end`; the 1,855,124 B between its image end 0x8c30b16c and 0x8c4d0000 are private and unexamined. Growth must be done in the image up to 0x8c4d0000 after proving the area unused (UNKNOWN) or by moving its text elsewhere.
* **MOVIE / MOVIE_BG** (title-time): `_end` is 96 B before the file end and the stub adds 0x400. Excluded.
* **COMM CON_REP NF_CON PASS_PL (0x8c2e0000), J1_REP PL_CON (0x8c4e0000), LOADBAR (0x8c800000)**: bases are not slot aligned, no scene record, loader path UNKNOWN. Budget 0.
* **HELP.BIN** (slot 10, 0x40000 = 262,144 B window, file 195,381 B): slot 11 (FACEMDUL) is resident behind it, so its span cannot be raised; its only growth is the 20,480 B policy (heap 58,784, 48,320 measured free). INFERRED. The ATFIRST copies of HELP and TITLE are not loaded (the FLOW_PRG copies are): never budget for them.

Raising the slot count: `desc[1]` is one byte inside the image; each +1 adds 1 MiB (slots 1-8) of heap and requires that slot to be state 1 whenever the overlay opens (`MODULE OPEN ERROR TYPE1` otherwise). The practical ceiling is slot 9 end (0x8cb60000) because HELP is resident at slot 10, and GAME (count 10) already spans it. Candidates: MEETING 2 -> 3, TRAINING 2 -> 3 (heap +1,048,576). Which slots are free at that moment is UNKNOWN (high byte of record word `b` may encode it, UNKNOWN). Cheap to test: raise the byte, open the overlay.

Decoupling the heap start from the file end (INFERRED, needs a stub patch): the heap start is only `r6`, computed by the stub from `*ENDVAR`. A patched stub could pass any `r6` it likes, so appended data does not have to follow the BSS pad immediately; but the file is contiguous, so text behind the BSS still means a zero pad in the file. The pad cannot be avoided by this; it can only be avoided by putting the text in another file (s6) or in the image itself.

## 4. `1ST_READ.BIN`

* Size 2,949,120 B = 0x2d0000 = 1440 sectors (ISO extent LBA 547560, last file on the disc), load address 0x8c010000, end 0x8c2e0000. PROVEN (`extracted/_filelist.tsv`, 91.4 % content match at 0x8c010000 in all four dumps, entry via the boot file name in IP.BIN; the BIOS loads the whole file by its ISO length, INFERRED).
* After it in RAM: slot 0 (0x8c2b0000-0x8c2d0000) and slot 1 (0x8c2d0000...). The file already reaches 0x30000 B into slot 0/1: RAM differs from the file for 0x8c2b0000-0x8c2e0000 in 4/4 dumps, while 0x8c2a0000-0x8c2b0000 still equals the file (boot-time data). PROVEN.
* Growth: bytes added at the end of the file land at >= 0x8c2e0000, i.e. inside the arena that the first overlay load overwrites (MOVIE_BG at 0x8c2d0000 at the title). Use as a boot-time stager only; there is no free RAM to stage into (largest candidates: 98,304 B at 0x8ce68000 and 102,400 B at 0x8ce81000, both unproven and the second rejected by memmap). So `1ST_READ` growth is **not a text lever**. Its existing zero/filler gaps (259,771 B with the FONT tail, `docs/trans-bank.md`) stay the only bank; 434,176 B of memmap's "holes" are inside crt0's zero fill and must not be used (`docs/capacity-design.md` s1).
* BIOS acceptance of a modified 1ST_READ is UNKNOWN (no checksum known; the IP.BIN CRC covers header fields only; the 4 dumps and the bank tests T6/T8 would decide).

## 5. Text copied into fixed RAM buffers

| buffer | where / size | evidence | consequence of longer English |
|---|---|---|---|
| message scratch buffers (expander output, code array) | MEETING: 0x8c3deadc and 0x8c3deedc, 0x400 apart, both inside that overlay's BSS (file end 0x8c3a573a, `_end` 0x8c3e28d0) | `docs/text-engine.md` s4.1 (INFERRED sizes), address arithmetic PROVEN here | expanded message must stay below about 1 KB, no bound check; each overlay carries its own copy of the tsString library (104 of 114), so a limit change is a per-overlay code patch (97 of 114 byte-identical, patchable by signature) |
| `#...#` token buffer | 20-byte stack buffer | `docs/text-engine.md` s4.2 | a lone `#` overflows; never emit `#` |
| window code array | `+0x22` u16 code count, `+0x2a` glyph slots | `docs/text-engine.md` s4.3 | UNKNOWN max |
| manager name, club name | global state block, 0x8c23242c (14 bytes) and 0x8c23243a, in 1ST_READ BSS | `ovmem_gs.py build/emu/pt1_ram.bin 8c232420 0x60`: ABCDEFGHIJ at both addresses, 14 bytes apart; matches the `#YOU#` (+0x102c) and `#sname#` (+0x103a) offsets from base 0x8c231400 of `docs/text-engine.md` | PROVEN location; field width 14 B INFERRED; the block is plausibly serialised into the save file (UNKNOWN). Widening shifts everything behind it |
| player names | ETC_DATA/BPINFO.BIN, 5321 records x 92 B, 14-byte name field | `docs/text-sources.md` | loaded through malloc: the same data sits at 0x8c77b420 (TITLE heap) and 0x8c5c51a0 (CLUBEDIT heap) in the dumps, so growing the record only costs heap (5321 x 32 B = 170 KB for 46-byte names), but the stride 92 is hard-coded in code of every overlay that indexes it (not counted here) |
| other pinned table entries (clubs, towns, tactics) | stride tables inside the overlay images | `docs/capacity-design.md` s0 (37,960 fixed strings) | cannot be grown by repacking; need code or table-layout changes, see the string-pool/field agents |

There is **no common text buffer limit** in the loader or in malloc; limits are per overlay (BSS layout of the tsString library) and per data format.

## 6. Moving the text pools: append, `--append-safe`, new file

Current code:
* `tools/textrepack.py`: pools are re-laid inside their original byte ranges, **image size never changes** (module docstring, `check()` proves it). Strings that do not fit stay Japanese (`overflow`, `fixed_overflow`). Limit = pool capacity (2,338,194 B in 3,646 pools, slack 4.03 %). No memory assumption at all, which is why it is the default.
* `tools/build_patch.py --append-safe` (opt-in): fallback only when repack left strings Japanese; `append_eligible()` accepts FLOW_PRG overlays classed `no-bss` in `tools/re/textengine/survey_overlays.tsv`, refuses GAME, ESTABLIS, LOADBAR, MOVIE, MOVIE_BG and any image whose `_end` word is not `base+size`; then `textdb.insert_image(append=True)` appends 4-aligned strings behind the image, rewrites the pointer words and the caller raises the `_end` word to `base+new size`. Limits found: (a) BSS overlays (73 of 109) are refused outright, (b) **no budget check** against `append_cons` or `slot_end` exists (listed as OPEN in the skeptic review), (c) never booted, (d) GAME needs a stub patch, (e) disc growth is handled by `discbuild` (relocate to a gap, else past track 5; the disc has 6,431 spare sectors, 13.2 MB, `docs/disc-layout.md`).
* To lift (a): pad the file with zeros up to the old `_end`, append, raise `_end` by the appended bytes (`bankbuild.apply_overlay_tail` exists, static self-tests only, not wired in).

Options, ordered by how far they break compatibility:
1. **Append behind a raised `_end`, all overlays** (BSS pad). Memory: heap shrinks by the growth only. Disc: pad + growth per overlay (table above). Proof status INFERRED; two cheap boots decide it (T4, T5 of `docs/capacity-design.md`).
2. **Raise the slot count** where the heap would get too small (MEETING, TRAINING). One byte per overlay.
3. **Text in a NEW file loaded on demand.** The engine already has the primitive: `FUN_8c15eede(name, dir, dest, heap)` through table entry 0x8c159060: opens by name, size = file length (`local_34 = (len + 0x7ff) >> 11` sectors), if `dest == 0` mallocs `sectors << 11` (from `heap` if given), reads, returns the pointer; error strings "FILE OPEN ERROR", "FILE MEMORY RESERVE ERROR". Used by 10 overlays today. A patched stub (200 B of padding, or a cave) could call it once after the arena exists and write the pointer where the text pointer words expect a base. Costs: a code patch per overlay (about 12 SH-4 instructions plus a name string), an ISO file per pack (or one pack per overlay), the heap block for the pack while the overlay runs, a directory entry (FLOW_PRG cache has 6 spare, then the count word at 0x8c16c118 must be raised), and `discbuild` currently supports only replacing existing files ("no new files/directories", `docs/disc-layout.md`), so it needs an "add file to directory" feature (ISO9660 record, path table untouched). Benefit over option 1: no BSS pad on the disc, no `_end` dependency, GAME/ESTABLIS/HELP could use it, the pack can be compressed (decompressor needed), and the same mechanism could serve a global shared name table. INFERRED feasible; UNKNOWN whether the pack can be requested before the overlay's own init copies text.
4. **Shift work out of 1ST_READ**: not useful (s4).
5. **Reuse an existing large file as carrier** (BCAST/BCAST.BIN is 629 MB and named only by GAME/ENDING; other candidates: unused ETC_DATA entries): possible without touching the directory but the file has real content for GAME/ENDING; not recommended.

## 7. What breaking compatibility buys, and where it breaks saves

* Disc layout: any size is fine for the loader. Real GD-ROM has 549,150 LBAs; the image is already full (6,431 spare sectors). Growth past LBA 549,150 works in emulators and, if the user accepts non-standard layouts, GDEMU; it is the one hard physical limit and belongs to the disc agent.
* Overlay images and stride tables: breaking the original layout is free as long as every absolute pointer and every hard-coded stride in code is patched (not part of this area).
* Save-game compatibility breaks exactly where a RAM struct that is serialised changes size: the global state block around 0x8c231400 (manager and club name 14 B each), BPINFO-derived player records if the 92-byte stride changes, and any table that the AUTOSAVE/CSAVE/SONGSAVE overlays copy. Not analysed (UNKNOWN); the safe statement is that **overlay growth, pointer rewriting and relocating strings do not touch save data**, only widening data fields does.

## 8. UNKNOWN items and the tests that settle them (none run here)

1. Append mechanics: CLUBEDIT with `_end` +0x1000 and 0x1000 B appended; expect first heap header at the new heap start (T4). Then N_ENTRY with BSS pad.
2. Heap sufficiency: raise `_end` by `append_cons` for MEETING, TRAINING, N_ENTRY, HELP, CLUBEDIT; play every screen; poll byte 0x8c230bd6 (T5).
3. Which slots are free for each overlay (needed before raising `desc[1]`): flow-order trace or the meaning of the high byte of scene-record word `b`.
4. Directory cache overflow behaviour: add one dummy file to FLOW_PRG (within the 6 spare) and one beyond.
5. Loader path of the 10 recordless overlays and the 7 non-slot overlays; ESTABLIS private area.
6. Generic file loader callable from a stub before the overlay's own init; arguments of the entry at 0x8c159060 (name, dir id, dest, heap).
7. Save layout around 0x8c231400.

## 9. Recommended order

See the reply field `recommended_steps`; in short: (1) wire and boot-test BSS-pad append with budget checks; (2) test raising slot counts for MEETING and TRAINING; (3) stub patch for GAME; (4) prototype the on-demand pack file on one small overlay with `discbuild` add-file support; (5) leave 1ST_READ growth and global banks to the existing 260 KB bank plan.

## Status after stage 3 (docs, 2026-11-11)

See `docs/expansion/status.md` for the table of what was built from this study, its flag or file, how far it is proven, and what is still open.  The summary for this study:

* Done, opt-in: `--append-safe` (33 no-BSS overlays) and `--grow-overlays N` (option 1 of section 8: BSS pad, raised `_end`, no stub patch; default 0, never booted; docs/pipeline.md 9.5).  Both rely on the loader formulas of section 1, which are PROVEN from decompilation only.
* Not done: raising slot counts, the GAME stub patch, the on-demand pack file and the directory-cache count word (`--add-file` can put a file on the disc but the game never opens it).  The UNKNOWN items 1-7 of section 8 still need a Flycast session; T4 (raise `_end` on CLUBEDIT) and T5 (heap sufficiency while playing every screen) come first.
* 1ST_READ keeps only its tail caves (font and money); nothing was appended to it.
