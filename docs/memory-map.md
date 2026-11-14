# RAM map, overlay heaps and free memory (agent `memmap`)

Every number below was produced by code in this repo and can be regenerated:

```
python -I -X utf8 tools/memmap.py all                       # overlays.tsv, maps, diffs, heaps, free_candidates
python -I -X utf8 tools/re/capacity/memmap/holes.py         # clean 1ST_READ zero holes
python -I -X utf8 tools/re/capacity/memmap/summary.py       # every aggregate figure quoted here -> build/memmap/summary.txt
```

Inputs: the four 16 MB dumps in `build/emu/` (base 0x8C000000), `extracted/`, `translation/*.jsonl` (text sizes), Ghidra decompiles of
`1ST_READ.BIN` (own project copy `<GHIDRA_PROJECTS>\ghproj_memmap`, raw output `tools/re/capacity/memmap/d1.txt d2.txt d5.txt dis*.txt`).
`tools/sh4stub.py` is a ~380-line SH-4 interpreter that runs an overlay's entry stub up to its first external call (used to read the real
`desc`, `base`, `_end` argument values instead of guessing). Status words: **PROVEN** = read from code/data and cross-checked by a script,
**INFERRED** = follows from PROVEN facts but never run, **UNKNOWN** = needs the dynamic test in section 9.

Generated files (`build/memmap/`): `overlays.tsv` (119 rows), `map_<dump>.txt` (4 KB-page maps), `classes.txt` (which file sits where),
`diffs.txt`, `heaps.txt` (every malloc block of every slot, 4 dumps), `free_candidates.tsv`, `holes.tsv`, `summary.txt`.

## 0. Answers in one table

| Question | Answer |
|---|---|
| Is there a heap at the end of an overlay? | Yes. `heap = [round32(_end)+0x20 .. slot_end)`, a best-fit malloc arena (PROVEN, 7 overlays: computed start+size == the live slot struct in the dumps). `slot_end` = base of the overlay's slot + sum of the sizes of the next `desc[1] & 0x7f` slots. |
| How big are these heaps? | 58,784 B (HELP) .. 8,570,976 B (ENDING); median 1,784,768 B (109 overlays with a slot span). 17 rows are < 1 MiB, the interesting ones: HELP 58,784, FLOW10 246,592, FLOW9 574,272, WEEKLY 607,232, TOWNDATA 956,672, MEETING 972,576, N_ENTRY 977,312. |
| Is appending to an overlay file safe? | Only after the end of its BSS and with the `_end` word raised by the same amount. 36 of 109 overlays have no BSS, 73 have BSS (sum 8,920,859 B, max NEWS 1,286,758 B); the loader neither loads nor clears BSS beyond the file's last sector, so for those the file must carry the BSS as a zero pad. `GAME.BIN` additionally needs a stub patch (its stub zeroes `[start,_end)`), `ESTABLIS.BIN` is a special case (section 6). |
| How much can be appended? | Per overlay: `append_hard` (heap minus 64 KiB, theoretical) and `append_cons` (policy, section 6) in `overlays.tsv`. `append_cons`: min 4,096 (an ATFIRST/HELP copy that is not even loaded), median 221,184, max 1,855,488. Overlays whose JA text is larger than `append_cons`: MEETING (376,951 vs 118,784), TRAINING (254,598 vs 151,552), HELP (110,032 vs 20,480). |
| Globally free RAM for a boot-loaded bank? | Best: zero "linker padding" holes inside `1ST_READ.BIN` itself, 557,056 B in 14 clean segments (largest 163,840 B), loaded by the BIOS, no loader change. Next: 0x8ce68000-0x8ce80000 (98,304 B, after SECFTEX0.ZAR). Everything inside slots 0x8c2b0000-0x8cd5c000 is arena memory. Details and ranking in section 7. |
| Surprising facts | The loaded font is the **root /FONT.BIN** (100 % match), not ATFIRST/FONT.BIN (96.8 %). The loaded TITLE.BIN / HELP.BIN are the **FLOW_PRG** copies. `[0x8c239000,0x8c299400)` looks free (376,832 zero bytes in all 4 dumps) but is a vertex/work pool. |

## 1. RAM map from the four dumps

Every 32-byte chunk of RAM is classified by content: zero, equal to a byte range of an extracted file (index of 1,408,880 distinct
chunks of 1ST_READ + ATFIRST + FLOW_PRG + TRAINING + GAME2 + root FONT.BIN; a "placement" = file @ address with >= 30 % verified match),
inside a walked malloc block (used / free), or other. Page maps: `build/memmap/map_<dump>.txt`.

| dump | zero 4 KB pages | non-zero by class (MB): K=1ST_READ, O=overlay image, Z=other known file, F=FONT.BIN, a=heap block in use, f=stale data in free block, #=other |
|---|---|---|
| ram_2400 (title) | 1873 (7.3 MB) | K 1.31, O 1.69, Z 1.80, F 0.63, a 0.69, f 0.53, # 1.44 |
| ram_5400 (title attract) | 1872 (7.3 MB) | identical to 2400 within 42 pages |
| live1 (Club Edit > Name Entry) | 1002 (3.9 MB) | K 1.31, O 2.36, Z 1.76, F 0.63, a 2.78, f 1.08, # 1.45 |
| live3 (Club Edit > Name&Mascot) | 915 (3.6 MB) | K 1.31, O 1.90, Z 1.76, F 0.63, a 4.02, f 0.59, # 1.47 |

Resident layout (identical in all four dumps; PROVEN by content match, `classes.txt`):

| address | content |
|---|---|
| 0x8c000000-0x8c010000 | BIOS/IP.BIN area and system variables (non-zero, "other") |
| 0x8c010000-0x8c2e0000 | `1ST_READ.BIN` as loaded (2,949,120 B, ends 0x8c2e0000). Match 91.4 %. Its last 0x40000 bytes lie **under** slot 0 (0x8c2b0000) and slot 1 (0x8c2d0000): RAM != file there in 4/4 dumps for 0x8c2b0000-0x8c2e0000; 0x8c2a0000-0x8c2b0000 is still equal to the file (64 KiB of boot-time data). |
| 0x8c227000-0x8c2e0000 | three memory pools described by literal (start,end) pairs in 1ST_READ (`0x8c16001c`: 0x8c227000..0x8c239000; `0x8c016b88`: 0x8c239000..0x8c299400; `0x8c016b8c`: 0x8c299400..0x8c2e0000). The loader globals and the 12 slot structs (0x8c228384) live in the first. |
| 0x8c2b0000-0x8cd5c000 | the overlay arena: 12 slots (section 3), 11,190,272 bytes, contiguous. |
| 0x8cd5c000 | root `/FONT.BIN` (663,324 B), window limit 0x8ce02000 |
| 0x8ce02000 / 0x8ce2c000 / 0x8ce5c000 | `ATFIRST/SHTEX0.ZAR` (155,798) / `BAR.TBD` (122,584) / `SECFTEX0.ZAR` (46,638), all 100 % match; 0x8ce4c000/4 is a BAR work pointer in 1ST_READ literals |
| 0x8ce80000-0x8d000000 | 1.5 MB block named by a literal pair (size 0x180000, base 0x8ce80000, function `0x8c159e5a` neighbourhood); non-zero from 0x8ce9b000 on, stack at the very top (last non-zero byte 0x8cfffffb, saved frame pointer 0x8cffffe4 and return address 0x8c00d840 in the last 16 bytes) |

Differences between states (`diffs.txt`): 2400 -> 5400: 42 pages; 2400 -> live1: 1,188 pages (879 zero->data, 301 data->data), almost all
in slot 1 (S_SELECT replaces MOVIE_BG; 0x8c2d0000-0x8c65f000 changes) and slot 7 (N_ENTRY, 0x8c8d0000-0x8c9c3000); live1 -> live3: 855 pages
(CLUBEDIT replaces S_SELECT; 0x8c2d0000-0x8c5e4000, N_ENTRY area becomes the 2 MB arena below); 2400 -> live3: 1,299 pages. Resident
stuff (FONT, ZARs, HELP, FACEMDUL, TITLE/TITLEM leftovers) does not change.

## 2. The 12 slots and which overlay is where

Slot table (read from 1ST_READ at 0x8c16bf9c, PROVEN): 0 `0x8c2b0000/0x20000`, 1..8 `0x8c2d0000 + n*0x100000` (1 MiB each), 9 `0x8cad0000/0x90000`,
10 `0x8cb60000/0x40000` (HELP), 11 `0x8cba0000/0x1bc000` (FACEMDUL); each ends exactly where the next begins and slot 11 ends at 0x8cd5c000
(FONT.BIN). Slot structs: array pointer at 0x8c230804 -> 0x8c228384, 12 x 0x60 bytes.

| dump | slot 0 | 1-4 | 5-8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|
| title | system arena (128 KiB) | MOVIE_BG (count 4, heap 3,718,496) | TITLE (count 4, heap 3,941,408) | free | HELP | FACEMDUL |
| live1 | same | S_SELECT (count 4, heap 3,831,200) | 5,6,8 free, 7 = N_ENTRY (count 1, 977,312) | free | HELP | FACEMDUL |
| live3 | same | CLUBEDIT (count 5: slots 1-5, heap 5,021,024) | 7 = a 2 MiB arena without overlay (slots 7+8) | free | HELP | FACEMDUL |

Loaded copies (PROVEN): `FLOW_PRG/TITLE.BIN` (99.8 % content match; the slot struct's descriptor pointer is 0x8c6ea5f8 = the FLOW_PRG copy's descriptor, the `ATFIRST/TITLE.BIN` copy has 0x8c6ea50c),
`FLOW_PRG/HELP.BIN` 100 % (`ATFIRST/HELP.BIN` 44 %), `FACEMDUL.BIN` both copies identical, root `/FONT.BIN` 100 % vs `ATFIRST/FONT.BIN` 96.8 % (`classes.txt`, `overlays.tsv` m_img_match_pct).

## 3. Loader and allocator (Ghidra, PROVEN unless marked)

* **Descriptor** (in the overlay image, address = stub literal 0x34): byte 0 slot index (overwritten by the hook), byte 1 = slot count (low 7 bits;
  `0x80` flag only on GAME.BIN: loader callocs a 0x24-byte block), word +4 = heap start (overwritten with `r6`).
* **Entry stub** (offset 0, 102 of 116 are byte-identical): `r6 = ((*ENDVAR | 0x80000000) & ~0x1f) + 0x20; hook(desc, base, r6)`. `*ENDVAR` is the
  `_end` word in the image. `tools/sh4stub.py` reproduces `r6` and agrees with the independent survey (`tools/re/textengine/survey_overlays.tsv`)
  for 108 of 113 FLOW_PRG overlays; the other 5 are: GETREP/NENREP (alternate stub that stores `r6` into `desc[4]` itself, not in the survey),
  MOVIE/MOVIE_BG (`+0x400` reserve; MOVIE_BG verified against RAM) and ESTABLIS (heap start = base of slot 3 read from the slot table, see section 6).
  The `ENDVAR` address occurs exactly once as a 32-bit word in each of the 116 overlay images (the stub's own literal): **nothing else reads `_end`**
  (4-aligned word search; MOVIE/MOVIE_BG hold the value three times, as parts of copied malloc sentinels).
* **FUN_8c162ac0** (state machine after load): `slot.+0x40 = desc[4]`; `slot.+0x14 = (sum of sizes of the count slots) + slot.base - desc[4]` -> heap size.
  Validated: 7 overlays (CLUBEDIT, S_SELECT, N_ENTRY, TITLE, MOVIE_BG, HELP, FACEMDUL) have static heap start+size equal to the live slot struct (no mismatch in `overlays.tsv`).
* **FUN_8c162570/8c162848**: opening requires every slot of the count to be state 1 (free) (`MODULE OPEN ERROR TYPE1`), and every slot covered by the file read must be free
  (`MODULE READ ERROR TYPE1/2`). So the file (image + appended data) must stay inside the `count` slots. The loader reads whole 2048-byte sectors: the disc's sector tail is zero
  (N_ENTRY 264 B, HELP 1,227 B, checked on the disc image), the 264 B after N_ENTRY's file end were all non-zero in the title dump and only 38 are non-zero in live1 (the first BSS variables).
  Beyond the file's last sector **nothing is loaded or cleared**: N_ENTRY's BSS part 0x8c8e0800-0x8c8e1654 (3,668 B) is 3,341 bytes identical to the title dump (3,610 non-zero there, 3,526 in live1), i.e.
  leftovers of whatever occupied that RAM before (PROVEN for N_ENTRY). The only stub with a clear loop is GAME.BIN's: `[*0x8c4bc88c, *ENDVAR)` (found by scanning all 116 stubs for backward branches).
* **malloc** (`FUN_8c16325a`, free `FUN_8c163496`, 1ST_READ jump table 0x8c159004/0x8c15900c): block header 0x20 bytes = `size` (incl. header, multiple of 0x20), `tag`
  (0xdeaddead free / 0xfeedfeed used), `prev`, `next` (address-ordered circular list through a sentinel inside the slot struct), 4 guard words 0x77777777. Request rounding `(n+0x3f)&~0x1f`,
  best fit. **Requests > 0x1000 are cut from the low end of a free block, <= 0x1000 from the high end** (visible in the dumps: big blocks at the heap start, 0x60-byte blocks at the heap end). Free merges both neighbours.
  Every block chain of every slot in all 4 dumps is consistent from `heap_start` to `heap_end` (no bad tag, sizes sum to the heap size).
* **Out of memory**: `can't alloc size:0x%x rest size:0x%x rest maxsize:0x%x` is passed to the debug print `FUN_8c0111b4` (which prints only if two flags are set; both were 0 in the dumps), the free list
  is dumped, the byte `0x8c230bd6` is set to 1 and **NULL is returned**. The allocator does not halt; what happens next depends on the caller (UNKNOWN; tsString windows contain a `malloc error` path).
  The byte `0x8c230bd6` is a ready-made detector for a dynamic test (it is 0 in all four dumps).
* **Other consumers of `[_end, slot_end)`**: none found besides malloc. The slot table is contiguous so the heap end coincides with the next slot's base; the stack is at the top of RAM (0x8d000000, not in any slot);
  the framebuffers are in VRAM (not in main RAM). Overlay-private use of RAM outside malloc is possible (ESTABLIS does it) and invisible to a dump: see section 6.
* **Slot 9 and friends are free only by state**: slot 9 (0x8cad0000-0x8cb60000) is state 1 with 589,792 zero bytes in all four dumps, but the heaps of 9 overlays (AUTOSAVE, ENDING, ENDOPT, EVENT, FREELOAD,
  GAME, NEWS_ED, NEWS_OP, SONGSAVE) include it.

## 4. Overlay table (`build/memmap/overlays.tsv`)

Columns: `base`, `desc`, `desc_count`, `file_end`, `end_value` (the `_end` word), `end_rounded` (heap start), `bss_bytes` (`_end - file_end`), `has_bss`, `slot_end`, `heap_bytes`
(= `slot_end - end_rounded`), `tail_after_file` (`slot_end - file_end`), budgets (section 6), JA text size from `translation/`, and `m_*` measurements where a dump has that overlay loaded.

Counts: 119 rows = 113 FLOW_PRG overlays + 3 ATFIRST overlays (TITLE, HELP, FACEMDUL; the FLOW_PRG copies are the loaded ones) + 3 non-overlays (FLOW_PRG/SECBND.BIN, ATFIRST/BPINFO.BIN, ATFIRST/FONT.BIN).
109 overlays have a slot-aligned base and therefore a computable slot span; 7 have not (COMM, CON_REP, NF_CON, PASS_PL at 0x8c2e0000, J1_REP, PL_CON at 0x8c4e0000, LOADBAR at 0x8c800000: loader path UNKNOWN,
their heap cannot be derived). `desc_count`: 1 slot x19, 2 x65, 3 x7, 4 x11, 5 x1, 6 x3, 9 x1, 10 x2. Files larger than their first slot: EVENT 1,389,382, NEWS 1,396,458, GAME 2,389,512 (all declare enough slots).
Overlays with no BSS (36): CE_VS CHALDANI CHALMODE CLUBEDIT DATAROOM DRSBEST DRSDENDO DRSGP DRSGRF DRSGRFJ DRSHRANK DRSISEKI DRSJAPAN DRSKIYA DRSLIST DRSOLIST DRSRANK DRSSRANK ESTABLIS GAME GETREP INVEST JSCEVENT
MON_INST MOVIE MOVIE_BG NENREP NEWMONTH NEWUNIF NEW_YEAR PL_EDIT SELNAT SPT_CLUB SS_EDIT S_SELECT TV_EVENT (MOVIE/MOVIE_BG: `_end` is 96 B before the file end and the stub adds 0x400).
Between `file_end` and the heap start there are always 3..0x3f bytes (`_end` rounding + 0x20), i.e. a no-BSS overlay has no free byte after its image.

## 5. Measured heap behaviour (7 overlays, `heaps.txt`, `overlays.tsv` m_*)

| overlay (dump) | heap | in use | free | largest free | stale non-zero bytes inside free blocks | longest zero run in largest free block | BSS (len / non-zero) |
|---|---|---|---|---|---|---|---|
| MOVIE_BG (title) | 3,718,496 | 192 | 3,718,304 | 3,718,304 | 152,129 | 1,048,352 | 640 / 592 |
| TITLE (title) | 3,941,408 | 1,796,256 | 2,145,152 | 2,123,552 | 395,438 | 1,022,432 | 11,200 / 253 |
| S_SELECT (live1) | 3,831,200 | 2,134,208 | 1,696,992 | 1,696,992 (0x8c531b20) | 756,877 | 431,488 | none |
| N_ENTRY (live1) | 977,312 | 233,632 | 743,680 | 743,328 | 397,161 | 32,736 | 3,648 / 3,506 (stale, = title dump) |
| CLUBEDIT (live3) | 5,021,024 | 3,745,440 | 1,275,584 | 1,275,584 (0x8c693c20) | 889,708 | 211,744 | none |
| HELP (resident) | 58,784 | 10,464 | 48,320 | 48,320 | 2,665 (0 in title) | 41,856 | 6,720 / 237 |
| FACEMDUL (resident) | 1,050,880 | 943,488 | 107,392 | 107,392 (0x8cd41c20) | 0 | 107,360 | 57,056 / 2,047 |

Reading these honestly:
* "In use" is one instant. CLUBEDIT is only 25.4 % free in the "Name&Mascot" screen, S_SELECT 44.3 %, N_ENTRY 76.1 %, TITLE 54.4 %. The peak of CLUBEDIT in its other screens is UNKNOWN.
* "Stale non-zero inside free blocks" is **not** this overlay's high-water mark: the same RAM was used by earlier overlays (MOVIE, LOGO, S_SELECT, TITLE, the 1ST_READ tail). It only shows
  that those bytes were written at least once since boot. The only clean statement is the zero run: the largest never-written extent of the free block (e.g. 211,744 B for CLUBEDIT).
* Slot 11's free tail (0x8cd41c20-0x8cd5bfa0, 107,360 zero bytes) and slot 10's (0x8cb94280, 48,288) are untouched since boot in all 4 dumps but belong to resident overlay heaps that allocate on demand.
* Small allocations (<= 0x1000) pile up at the heap end: CLUBEDIT has 165 blocks, the last ones at 0x8c7cfb20..0x8c7cffa0; appended data that shrinks the heap at the **low** end therefore
  mostly competes with the big (> 0x1000) allocations, i.e. textures/data loaded from disc.

## 6. Append budget

Model (PROVEN parts: loader; INFERRED: that nothing reads the bytes between image and `_end`): new file = old file + zero pad up to the old `_end` (only if BSS exists; `bss_pad_cost` = `_end - file_end`)
+ X data bytes; the `_end` word is raised by `pad + X` (so BSS addresses stay valid and the heap start moves up by X). Constraints: (a) heap must keep enough room, (b) new file end <= `slot_end`
(<= the file read must not reach a slot outside the count), (c) the disc is full: 6,431 spare sectors (13.2 MB) in total (`docs/disc-layout.md`), and if every BSS overlay were padded that alone is 8,920,859 B = 4,356 sectors.

* `append_hard` = heap_bytes - 64 KiB (the theoretical maximum; INFERRED; 0 for HELP).
* `append_cons` (policy, INFERRED): for overlays measured above = 0.5 x the free bytes of the dumped moment (CLUBEDIT 634,880, S_SELECT 847,872, N_ENTRY 368,640, TITLE 1,069,056, MOVIE_BG 1,855,488,
  HELP 20,480, FACEMDUL 53,248); for all others heap/8, i.e. half of the smallest free fraction observed (25.4 %, CLUBEDIT). Not a guarantee, just a rule that no observed state violates; the real guarantee needs test 9.2.
  Total `append_cons` over the 108 overlays that have one: 29.9 MB (29.4 MB FLOW_PRG only; not additive: slots are shared); median 221,184.
* Where it matters (JA text size = sum of `max_bytes` in `translation/`, English is not measured yet): MEETING 376,951 vs 118,784 (BSS pad 250,262, heap 972,576), TRAINING 254,598 vs 151,552 (pad 91,150),
  HELP 110,032 vs 20,480 (heap 58,784, `append_hard` 0), NEWS 303,165 vs 450,560 (but BSS pad 1,286,758), DRAFT 120,588 vs 192,512. All other overlays have cons >= text. Total JA text in FLOW_PRG overlays: 2,895,830 B.
* Levers if an overlay is short: raise `desc[1]` (slot count) by one if the following slot is free whenever that overlay runs (+1 MiB heap; the loader refuses with MODULE OPEN ERROR TYPE1 otherwise; UNKNOWN which overlays
  run concurrently with a resident neighbour: S_SELECT + N_ENTRY do, see live1); or keep the original strings in place and relocate only the ones that do not fit.
* **GAME.BIN**: its stub zeroes `[*0x8c4bc88c, *0x8c4bc890)` where `*0x8c4bc890` is the same `_end` word. Raising `_end` would zero the appended bytes. Needs a stub patch (second literal for the clear end;
  the stub has zero padding 0x5c..0xff for a new variable). Also GAME's text is only 58,322 B.
* **ESTABLIS.BIN**: the stub sets the heap start from the slot table (`*(0x8c16bf9c + 0x18)` = base of slot 3 = 0x8c4d0000 -> heap 0x8c4d0020-0x8c6d0000, 2,097,120 B) and ignores `_end`. The 1,855,124 B between its
  image end (0x8c30b16c) and 0x8c4d0000 are overlay-private; whether they are in use is UNKNOWN (that overlay was not dumped). No budget given.
* MOVIE/MOVIE_BG/LOGO-type overlays (title-time) and the 7 non-slot-aligned overlays: no budget derivable for the latter.

## 7. Globally free RAM for a bank loaded once at boot

"Zero in all 4 dumps" is the only runtime evidence; the states not dumped (match/season/week simulation, training, news, ending...) are exactly the ones in the big overlays.
Static evidence: 32-bit words in `1ST_READ.BIN` (code literal pools + data) that point into a page (`build/memmap/holes.py`), and literal (start,end) region descriptors.

**Rejected although zero in all dumps**
* `0x8c239000-0x8c299400` (and the three pools of section 1): the descriptor pair `0x8c016b88` names it, and live3 contains vertex data (IEEE floats 131.0, 0.5 ...) at 0x8c239000-0x8c23d000; a 3D/sprite pool whose
  high-water in a match is unknown. 376,832 zero bytes there are NOT free.
* Slot 9 (585,728 zero bytes 0x8cad1000-0x8cb60000), slot 5/6/8 gaps, slot 10/11 free tails: heap of overlays (section 3).
* `0x8ce81000-0x8ce9a000` (102,400 B): inside the 1.5 MB block 0x8ce80000-0x8d000000.

**Candidates** (ranked)

| # | region | size | where it lives in the file system | evidence of non-use | what could use it in an undumped state |
|---|---|---|---|---|---|
| 1 | 1ST_READ holes: `0x8c1fe000-0x8c226000` 163,840; `0x8c13d000-0x8c158000` 110,592; `0x8c1cf000-0x8c1e4000` 86,016; `0x8c1e7000-0x8c1f7000` 65,536; `0x8c18a000-0x8c192000` 32,768; `0x8c17f000-0x8c186000` 28,672; `0x8c199000-0x8c19e000` 20,480; `0x8c1b9000-0x8c1be000` 20,480; plus 6 small ones. **Total 557,056 B in 14 segments** (`holes.tsv`). | up to 163,840 contiguous | inside `1ST_READ.BIN` (BIOS loads it at boot; no new file, no loader patch; size unchanged) | zero in the file, zero in 4/4 dumps, no 1ST_READ word points into the pages or the page before/after (margin 4 KiB). `0x8c13c000-0x8c159000` ends exactly at the fixed jump-table page 0x8c159000 = looks like section padding. | BSS reached by pointer+offset instead of by its own literal (nearest referenced page is only 8 KiB away for most; farther for 0x8c17f000 (16 KiB), 0x8c129000 (53 KiB)), or code in GAME/EVENT/NEWS. |
| 2 | `0x8ce68000-0x8ce80000` | 98,304 | after `ATFIRST/SECFTEX0.ZAR` (ends 0x8ce6762e); append to that ZAR (spare to 0x8ce80000: 100,818 B) or add a boot load (needs code patch) | zero in 4/4 dumps; the only 1ST_READ literals between 0x8ce5c000 and 0x8ce80000 are the ZAR's own destination and the 1.5 MB block base | decode/scratch buffer of the texture archives or BAR code; ZAR parser tolerance of trailing bytes UNKNOWN |
| 3 | spare tails of boot-loaded files: root FONT.BIN 16,612 B (0x8cdfdf1c-0x8ce02000), SHTEX0.ZAR 16,234, BAR.TBD 8,488 (0x8ce49ed8-0x8ce4c000) | 41,334 total | inside those files (no code) | next fixed load address is the limit (loader dest literals 0x8ce02000/0x8ce2c000/0x8ce4c000) | loader sector rounding writes up to the sector end (0x8cdfe000 etc.); FONT window already documented as 679,936 B |
| 4 | slot 9 `0x8cad1000-0x8cb60000` | 585,728 | needs a loader hook | zero in 4/4 dumps | heaps of 9 overlays incl. GAME/EVENT (section 3): **unsafe** |

Capacity check: JA text of all overlays is 2.9 MB; hosts 1-3 together hold ~0.7 MB, so a single boot bank cannot carry the whole translation (it could carry the shared/menu text or a compressed bank); overlay-local appends remain necessary.
Correction of an earlier claim (`docs/text-engine.md` section 2): the font that is in RAM is the **root /FONT.BIN** (663,324 B, 20,636/20,636 chunks equal); the ATFIRST copy (663,096 B) matches 19,974/20,633. Patch the root file (and keep both identical).

## 8. How the numbers were verified

* Heap walks: every block chain consistent in 4 dumps x 7 arenas (`heaps.txt`).
* Stub emulation vs three independent sources: survey tsv (108/113), live slot structs (7/7), manual disassembly of GAME/MEETING/ESTABLIS/NEWS/TRAINING/SONGSAVE/S_SELECT/OFFICE/TOWN/INVEST/MOVIE stubs (`tools/re/capacity/memmap/shdis.py`).
* Page classification: placements verified byte-exactly against the file (`classes.txt`), 218 files indexed, shadowed placements (shared library code, e.g. FLOW1-11 at 0x8cb64280) suppressed.

## 9. UNKNOWN items and the dynamic tests that settle them (for the orchestrator)

1. **Append mechanics (cheap)**: build CLUBEDIT with `_end` word `+0x1000` and 0x1000 bytes appended (no BSS). Boot to Name&Mascot, dump RAM: expect slot 1 heap start `0x8c3072a0`
   (was 0x8c3062a0), appended bytes intact at 0x8c30629d.., first block header at the new heap start. Then N_ENTRY (BSS 3,932 B: file + zero pad + data, `_end` raised by pad+X).
2. **Heap sufficiency without changing the file**: raise only the `_end` word of an overlay by its `append_cons`, play every screen of that overlay, poll byte `0x8c230bd6` (becomes 1 on the first failed malloc).
   Start with the tight ones: MEETING (118,784 / 376,951), N_ENTRY, HELP (20,480), CLUBEDIT (all its screens), then GAME/EVENT/NEWS.
3. **Bank holes**: patch 1ST_READ.BIN with a canary pattern in the 14 segments (and 0x8ce68000-0x8ce80000 by appending to SECFTEX0.ZAR), play title -> new game -> a match -> several weeks -> training/news/ending,
   dump RAM and compare; any changed byte disqualifies that segment. This is the only way to prove "never used in states we did not dump".
4. Does the BIOS accept a 1ST_READ.BIN with modified zero regions (no checksum is known to exist; IP.BIN CRC covers header fields only), and does Flycast load it identically?
5. ESTABLIS private area (0x8c30b16c-0x8c4d0000) and the 7 non-slot-aligned overlays: dump while they run.
6. Which slots are free when each overlay runs (needed before raising a `desc` count).
7. ZAR parser: does `SECFTEX0.ZAR` with appended bytes still load (decides candidate 2 without a code patch)?

## 10. Risks

* All budget numbers except the 7 measured heaps and the heap-size formula are INFERRED; `append_cons` rests on snapshots of two Club Edit screens.
* A stale-data hazard: BSS beyond the last loaded sector contains leftovers of the previous overlay (not zero); an overlay that implicitly relied on zeroed BSS would already misbehave today, but a changed file layout (zero pad now loaded from disc) changes what it sees there: the pad makes BSS zero, which is the safer value.
* Pointer scans of overlay images have many false positives (e.g. GAME.BIN `0x8c442da0..` is a table of 40 pseudo-random numbers in 0x8c0fa344..0x8c33635c); only 1ST_READ literals were used as evidence for holes.
