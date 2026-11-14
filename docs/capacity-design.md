# Capacity design: how the English fits (synthesis of the four capacity reports)

> **Status note (docs, 2026-11-11).** **Stage-1 synthesis.** Its plan was carried out as pool repacking, `--append-safe`, half-width relocation and refit forms; the external bank (route c) was not built (docs/trans-bank.md). The figures describe the stage-1 database (126,273 records, no English); the current database has 368,492 records, 99.6 % with English (`python -I -X utf8 tools/transmerge.py status`).

Author: agent `synth`.  Inputs: `docs/capacity-ratio.md` (agent `ratio`), `docs/string-pools.md` + `tools/textrepack.py` (agent `pool`),
`docs/memory-map.md` + `tools/memmap.py` (agent `memmap`), `docs/trans-bank.md` + `tools/re/capacity/bank/` (agent `bank`).
Every figure below was produced by a script that was run for this document; the scripts and their raw outputs are in
`tools/re/capacity/synth/` (`*_out.txt`).  **Nothing was run in an emulator.**
Status words: **PROVEN** = computed/decompiled and re-run here, **INFERRED** = follows from proven facts, never run in the game,
**UNKNOWN** = needs one of the dynamic tests of section 7.

## 0. Result in twelve lines

1. **Memory is not the binding constraint; fixed strings are.**  37,960 of 119,946 overlay strings (31.6 %, 505,232 JP bytes) are
   orphans / stride-table entries / interior pointers: they can only be overwritten in place.  With natural English (1.214 x JP bytes) **18,673
   of them (15.6 % of ALL strings) overflow** whatever we do with memory; at English scaled to 0.85 of natural (1.033 x JP) 6,674 (5.6 %) still do.
   16,021 of the 18,673 are person-name table entries (2,757 distinct texts in total) and 1,383 are TRAINING tactic texts (`fixedcat_out.txt`).
2. **Movable strings (81,986) need external memory only if English stays natural**: lower bound of external bytes = sum of pool deficits =
   **316,638 B** at natural English (225,853 B with identical-string sharing), 91,981 B at 0.90, 24,398 B at 0.85, 3,156 B at 0.80 (`deficit_out.txt`).
   The ratio agent's independent estimate (318,916 B) agrees within 0.7 %.
3. **Default pipeline = Layer 0 + Layer 1** (in-place + pool repacking, no memory assumption).  Integrated in `tools/build_patch.py` (`--repack on`, the default);
   `tools/test_pipeline.py`: **110 checks, 0 failed** (was 65).  At natural English it houses 69.1 % of the strings (55.0 % of the JP bytes); at 0.85 x natural 93.8 % (93.9 %).
4. **Layer 3 (shared bank, 259,771 B in the padding of `1ST_READ.BIN` + the tail of the root `FONT.BIN`, no code patch, no disc growth)** covers all movable
   overflow once English is <= 0.90 x natural, and most of it at natural.  **Layer 2 (append behind a raised `_end`)** is only needed above that, for a few big prose
   overlays.  Both are INFERRED: tests T4-T8 below decide.  They are **not** in the default build.
5. **Layer 4 (shorter English, name ladder `G. Family`, no place suffixes, tactic texts at slot length) is mandatory**, not a fallback: it is the only
   thing that helps the fixed strings.  Target style: **0.85 x natural for prose (about 1.0-1.05 x JP bytes)**.
6. **Single biggest risk**: relocating text inside the overlays (Layer 1 moves untranslated strings too) was never executed in the game.  A hidden reference to
   a string (relative offset, 16-bit literal, pointer from another image) would show as garbled text exactly where it is hardest to notice.  Test **T1** (forced
   identity rewrite, no translation) decides it in one boot; if it fails the project falls back to in-place only (Layer 0, 44 % of strings).

## 1. Cross-check of the four reports (all figures recomputed here)

| quantity | reported | recomputed here (script) | verdict |
|---|---|---|---|
| overlay strings / JP bytes incl. NUL | 119,946 / 2,749,078 (ratio, pool, bank) | 119,946 / 2,749,078 (`joint.py`) | agree |
| movable / fixed strings | pool 81,986 / 37,960; bank 81,986 / 37,960; ratio 81,988 / 37,958 | 81,986 / 37,960 (`recount.py`) | agree; ratio's 2-string difference is its `ctx`-flag test |
| pool capacity, pools | 2,338,194 B in 3,646 pools (1,990 single-string), slack 94,348 | identical (`recount_out.txt`); 94,348 = 4.03 % of capacity = 4.20 % of the movable JP bytes | agree (ratio's "movable pool" 2,338,270 differs by 76 B for the same 2-string reason) |
| English bytes, whole game | ratio 3,349,285 (1.218 x JP) | 3,338,514 (1.214 x JP) with the per-category empirical ratio distributions (`joint.py`) | agree within 0.3 % |
| fits own slot | ratio 41.9 % of strings, 28.1 % of JP bytes | model 44.1 % / 30.8 % | agree within 2.7 points (the model ignores the correlation between length and ratio inside a category) |
| extra memory at natural English | ratio 318,916 B (sum over overlays, ideal packing) | **316,638 B** = sum of pool deficits via `textrepack.plan_pools` (`deficit.py`) | agree within 0.7 %: two independent methods |
| bank demand at r=1.25 | bank: 1.58 MB (dedupe by ja) | movable overflow after repacking at natural English: 1,243,509 B (greedy revert) / 764 KB with sharing; true external need 316,638 B | **not comparable**: the bank model counts every string that exceeds ITS OWN slot (no pooling, uniform r); repacking removes most of that, and moving a string out also frees its pool room.  Use 317 KB. |
| memmap "clean 1ST_READ holes 557,056 B" | memmap | **434,176 B (77.9 %) lie inside crt0's zero-fill** [0x8c16f800,0x8c299400) (bank agent, Ghidra): only 122,880 B survive (`holes_vs_crt0_out.txt`) | **memmap's figure must not be used as storage.**  The bank agent's 243,159 B in-file (+16,612 B FONT tail) = 259,771 B is the valid number; it includes the 93,184 B `tail` that memmap did not list |
| bank: loaded font | root `/FONT.BIN` (bank, memmap) | both agree; contradicts `docs/font.md` / `docs/text-engine.md` s2 | keep both FONT copies patched (build_patch already does) |
| ATFIRST/HELP and ATFIRST/TITLE | memmap: FLOW_PRG copies are the loaded ones (100 % vs 44 %) | consistent with bank | **2 of the 114 images are not loaded**: the bank doc counts HELP twice (164,404 + 164,395 B).  Treat ATFIRST/HELP.BIN and ATFIRST/TITLE.BIN as copies of the FLOW_PRG translation; never budget memory for them |
| pipeline vs planner | -- | `build_patches` leaves 37,055 strings Japanese at natural English, the planner 37,054; at 0.85 x: 7,410 vs 7,409 (`gap_100_out.txt`, `gap_085_out.txt`) | agree; the 1-string difference is `NEWS_OP#28f21` (section 3.2) |

Smaller notes: memmap's BSS total 8,920,859 B and the 73 BSS / 36 no-BSS split re-derive from `overlays.tsv`; heap minimum 58,784 B (HELP) reproduces (`recheck/memmap_summary.txt`).

## 2. Joint model (PROVEN as a model; the English is synthetic)

`tools/re/capacity/synth/joint.py`: English length of every one of the 119,946 strings = quantile of the ratio agent's measured per-category EN/JP distribution
(605 hand-written translations, `ratio/sample.jsonl`) x a global `scale`; equal Japanese gives equal English (translation memory).  The pool agent's planner
(`textrepack.plan_pools`, cross-pool moves on) is run on all 114 images.  `fullrun.py` / `gap.py` push the same synthetic English through the REAL pipeline
(`build_patch.build_patches`): the result matches the planner to one string.

| scale (x natural) | English / JP bytes | L0 own slot: strings / JP bytes | L0+L1 pool repack: strings / JP bytes | + sharing (opt-in) | movable overflow left after L1: strings / EN bytes | min external bytes (pool deficit) | fixed strings that overflow |
|---|---|---|---|---|---|---|---|
| 1.00 (natural) | 1.214 | 44.1 % / 30.8 % | **69.1 % / 55.0 %** (82,892) | 73.5 % / 68.7 % | 18,381 / 1,243,509 | 316,638 (225,853 shared) | 18,673 = 15.6 % |
| 0.95 | 1.156 | 50.6 % / 38.4 % | 77.5 % / 68.6 % | 80.1 % / 77.0 % | 11,716 / 784,413 | 196,146 | 15,291 = 12.7 % |
| 0.90 | 1.092 | 63.1 % / 52.1 % | 87.8 % / 82.6 % | 89.0 % / 86.6 % | 4,138 / 362,984 | 91,981 | 10,469 = 8.7 % |
| **0.85** | **1.033** | 73.4 % / 64.7 % | **93.8 % / 93.9 %** (112,537) | 93.9 % / 94.1 % | 735 / 55,537 | 24,398 | 6,674 = 5.6 % |
| 0.80 | 0.971 | 79.5 % / 74.4 % | 96.8 % / 96.8 % | 96.8 % / 96.8 % | 36 / 1,402 | 3,156 | 3,841 = 3.2 % |
| 0.75 | 0.913 | 85.8 % / 85.2 % | 98.1 % / 98.4 % | 98.1 % / 98.4 % | 5 / 143 | ~0 | 2,308 = 1.9 % |

(`joint_out.txt`, `joint_out_b.txt`, `deficit_out.txt`.  The "movable overflow" column is what the CURRENT planner reverts to Japanese: it reverts whole strings, largest
growth first, which is why it is 4-15 x the true external need in the next column; a spill planner, section 8 step 5, closes that gap.)

Reading: the strings that stay Japanese are (a) fixed strings and (b) movable overflow.  Column "fixed" cannot be reduced by any memory layer.
Who the fixed overflow is at natural English (`fixedcat_out.txt`): names 16,021 of 32,592 name-table strings, places 710/1,492, labels 443/2,103,
TRAINING tactic texts 1,383/1,554, other prose 89/118, numbers 26/96.  Only 2,757 distinct Japanese texts stand behind the 18,673 strings (50 table overlays repeat the same names),
so the name problem is ~2.7 k hand-decisions, not 16 k.  With the `G. Family` name ladder (ratio agent: fits 68/68 of its sample) the fixed overflow would shrink to
18,673 - 16,021 = 2,652 strings (2.2 %) at natural English and 6,674 - 5,295 = 1,379 (1.1 %) at 0.85 (arithmetic on the table above; the ladder itself is not simulated).

## 3. Layers

### Layer 0: in place  (textdb semantics; code + tests exist)
A string whose English (+NUL) fits its own region `[off, off+max_bytes)`.  Natural English: 44.1 % of strings, 30.8 % of JP bytes (ratio agent measured 41.9 % / 28.1 %).
Orphans, stride-table entries and interior-pointer strings can ONLY use Layer 0 (and Layer 4).  Fit falls to ~14 % for Japanese strings of 80-120 bytes (0.3 byte of padding).

### Layer 1: pool repacking  (default ON; `tools/textrepack.py`)  PROVEN statically, UNPROVEN in the game
A pool is a maximal run of abutting regions of movable strings (3,646 pools, 2,338,194 B).  The pool is re-laid out back to back, all pointer words are rewritten, the image size never changes,
whole strings can be moved to other pools with room (`cross_pool`), strings that still do not fit stay Japanese and are reported.
* Gain at natural English: +25.0 points of strings (+24.2 points of JP bytes) over Layer 0; at 0.85: +20.4 / +29.2 points.  Slack is only 4.03 %, so the gain comes from mixed lengths (short neighbours lend bytes), not from the average.
* Proofs (all re-run here): identity over all 114 images (share none and dup), forced rewrite of all pools equals the original text behind every pointer (`test_pipeline.py` E1/E5, `test_textrepack.py --quick`: 0 failures, 80.3 s);
  110/110 pipeline checks including a 6,696-string synthetic translation on CLUBEDIT/EVENT/SPF_READ whose changed bytes are all inside string regions or pointer words (independent verifier in the test, not `textrepack.check`), and an output disc in which exactly those 3 files differ and 1,212 are identical.
* Run-time assumptions, evidence from the four RAM dumps (`poolwrite.py`): in all 8 (dump, overlay) pairs (TITLE x2, N_ENTRY, CLUBEDIT, HELP x2 = 109,794 pool bytes, FACEMDUL x2) **0 pool bytes, 0 fixed-string bytes and 0 pointer words differ between RAM and file**.
  Weak evidence (states: title, attract, 2 Club Edit screens): it says nothing about matches, training, news, season.
* **Sharing (`--share dup`, opt-in)**: identical strings of one pool keep one copy.  At natural English it lifts housed strings from 69.1 % to 73.5 % (JP bytes 55.0 % -> 68.7 %), the external need from 316,638 to 225,853 B, and makes MEETING/NEWS fit up to 1.33/1.44 x JP.
  It needs (a) strings never written at run time (UNKNOWN beyond the 8 snapshots) and (b) identical Japanese translated identically (needs a translation-memory propagation step in the DB tooling, not yet written).  Default stays `none`.
* Warts found while integrating (fixed in `build_patch.py`, not in `textrepack.py`): (1) one extraction false positive, `FLOW_PRG/NEWS_OP.BIN#28f21` (4 bytes of a pointer word read as text, `ptroverlap_out.txt`), was overwritten in place and clobbered the pointer of `#28f00`; `build_patch` now refuses every string whose region overlaps a pointer word of another string (reported as failed).  Found only because the real DB was filled completely; the pool agent's synthetic cases never contained it.
  (2) when no string of an overlay can be placed, repack had already moved other strings between pools while trying; `build_patch` keeps the original image in that case.

### Layer 2: append behind a raised `_end`  (INFERRED; opt-in `--append-safe`, no-BSS overlays only)
Mechanism (memmap + bank, both from decompiled loader code): the overlay heap starts at `round32(_end)+0x20`; raising the `_end` word by the appended bytes moves it.  BSS overlays (73 of 109, 8,920,859 B of BSS) additionally need the BSS written as zeros so the appended text lies behind it.
* Budgets (INFERRED policy, `overlays.tsv`): `append_cons` per overlay, e.g. MEETING 118,784, NEWS 450,560, TRAINING 151,552, DRAFT 192,512, SCDRF 204,800, EVENT 925,696, NEWS_ED 241,664, SPF_READ 393,216, CLUBEDIT 634,880 (measured), HELP 20,480 (heap total 58,784).  GAME needs a stub patch (its stub zeroes up to `_end`), ESTABLIS has a private area, 7 overlays have no slot span: treat their budget as 0.
* Disc cost: padding the BSS of the 7 big prose overlays (MEETING, NEWS, TRAINING, DRAFT, SCDRF, EVENT, NEWS_ED) is 1,985,263 B = 970 sectors, plus the appended text; the disc has 6,431 spare sectors (emulator only: the GD-R ends at LBA 549,150).
* Need: only if English stays natural.  Pool deficits not covered by `append_cons` at natural English: 18,533 B (GAME 10,358, ESTABLIS 6,312, HELP 5,335 vs 4,096 for the unloaded ATFIRST copy, 3 tiny overlays) = covered by the Layer-3 bank (`deficit_out.txt`).
* Code: `build_patch.append_eligible` (no-BSS, not GAME) exists and is tested (E6, B/D); BSS padding (`bankbuild.apply_overlay_tail`) exists with static self-tests but is not wired into the pipeline.

### Layer 3: shared bank in `1ST_READ.BIN` padding + FONT tail  (INFERRED; builder tested statically, not integrated)
* Region list (bank agent, re-checked against crt0 clear ranges here): `tail` 0x8c299400..0x8c2b0000 = 93,184 B (27,648 zero + 65,536 filler), `gap1` 0x8c13bb80..0x8c159000 = 119,936, `gap2` 0x8c1196a0.. = 13,402, `gap3` 0x8c1289e8.. = 16,637, root-FONT.BIN tail 0x8cdfdf1c..0x8ce02000 = 16,612: **259,771 B**.  Same file sizes, zero disc growth, no loader patch; overlay pointer words are rewritten to point there.
* Absorbs (model, greedy by strings served per byte, dedupe by Japanese text): natural English after repack: 14,425 strings (12.0 % of all) with 3,855 distinct texts in 259,753 B; at 0.85: all 735 (33,722 B); at 0.90: all 4,138 (243,903 B).  Together with Layer 2 only 413 movable strings (71,044 B) stay Japanese at natural English, all in GAME (24,230), ESTABLIS (15,365) and the HELP copies (7,310 loaded + 24,139 unloaded), which have no Layer-2 budget; routing them to the bank first removes that residue (46,905 B for the loaded ones; bank has room).
* Unproven: no byte of these regions is ever written at run time (canary, T6), the game accepts a pointer to text outside the overlay at an odd address (T7), the BIOS/Flycast accept the modified `1ST_READ.BIN` (T8).  The boot-hook route (a) is verified as a mechanism only; no free RAM block to load a bigger bank into was found.

### Layer 4: English discipline  (mandatory for fixed strings)
* **Names** (16,021 of the 18,673 fixed overflows at natural English): `G. Family` ladder, fixed 14-byte field rule; decide once for ~2.7 k distinct names.
* **Places**: drop the -gun/-cho/-mura suffix where needed (ratio agent: 38/56 fit without it).
* **TRAINING tactic texts** (1,383 orphans, 156 KB of English at natural length, 16 % fit): terse English at <= slot length until their addressing is reverse-engineered (the only block that has no relocation path at all).
* **Prose**: 0.85 x natural (about 1.0-1.05 x JP bytes) keeps every movable string inside Layers 0-1 (93.8 %) and removes most 4-line overflows (ratio agent: 37.2 % of faithful prose needs more lines than the Japanese had; 26.5 % of <= 3-line strings need a 4th).
* Splitting one message into two needs engine changes; not planned.
* Tooling needed: per-record byte budget (`max_bytes`, already in the DB) and a pool-level budget report per overlay; `build_patch --strict` already fails the build when any string cannot be placed.

## 4. Decision matrix

| option | capacity | proof status | main risk | disc cost | code | decision |
|---|---|---|---|---|---|---|
| L0 in place only | 44 % of strings / 31 % of JP bytes at natural English | proven (live: English in RAM renders) | -- | 0 | tested | baseline, always |
| **L1 pool repack, cross-pool** | 69 % / 55 % natural; 93.8 % / 93.9 % at 0.85 | static proof, 8 dump snapshots; run-time relocation never played | hidden string reference | 0 | tested (110 checks) | **default ON** |
| L1 + `--share dup` | 73.5 % / 68.7 % natural; external need -29 % | read-only assumption: 8 snapshots | strings written at run time; needs identical translations | 0 | tested | opt-in until T3 passes |
| L2 append behind `_end` | per overlay `append_cons`, 28.5 MB summed over overlays, needed: <= 317 KB | loader formulas, 7 measured heaps | heap exhaustion (`0x8c230bd6`), BSS stale data | BSS pad 970 sectors for 7 overlays | no-BSS tested statically; BSS not wired | opt-in (flag exists, no-BSS only) |
| **L3 bank in 1ST_READ padding + FONT tail** | 259,771 B, dedup by Japanese: 14,425 strings natural | crt0 clear ranges decompiled; 4 dumps | a store into the padding at some game state; odd-address pointer | 0 | builder + 3,497-string self-test; not integrated | **next step after T6-T8** |
| boot hook + donor file (route a) | unlimited file, but no free RAM block | mechanism verified in Ghidra | nowhere to load | donor file size | patch bytes only | not planned |
| compress text + expand at load (route e) | ~2x | not analysed | engine work | -- | none | rejected for now |
| L4 shorter English / ladder | the only help for 18,673 fixed overflows | n/a | translation quality | 0 | style guide | **mandatory** |
| reverse-engineer orphan addressing (TRAINING tactics, name tables) | would unlock 37,960 fixed strings | UNKNOWN | engine work | 0 | none | worth a spike if names/tactics resist L4 |

## 5. What each layer absorbs (strings of 119,946; planner == pipeline within 1 string)

| | natural English (1.214 x JP) | edited English 0.85 x natural (1.033 x JP) | 0.85 x natural + name ladder (derived) |
|---|---|---|---|
| L0 own slot | 52,863 (44.1 %) | 88,030 (73.4 %) | 88,030 + 5,295 = 93,325 (77.8 %) |
| L1 pool repack, cross-pool | +30,029 -> 82,892 (69.1 %) | +24,507 -> 112,537 (93.8 %) | 112,537 + 5,295 = 117,832 (98.2 %) |
| L1 sharing (opt-in) | +5,264 -> 88,156 (73.5 %) | +87 -> 112,624 (93.9 %) | -- |
| L2 / L3 (movable overflow after L1) | 18,381 strings: L3 14,425 + L2 3,543, 413 left (GAME/HELP/ESTABLIS: route to bank) | 735 strings, all in L3 (33,722 B) | 735 (0.6 %) |
| L4 (fixed overflow, only English discipline) | 18,673 (15.6 %) | 6,674 (5.6 %) | 1,379 (1.1 %) |

The two last columns assume the translators actually reach the length targets; they are the ratio agent's measurements scaled, not a translation.

## 6. What was integrated into the pipeline

`tools/build_patch.py`:
* `--repack on|off` (default **on**): overlay text goes through `textrepack.repack` (cross-pool on), every result is verified by `textrepack.check` and the build aborts on a failed self-check; `off` = the previous `textdb.insert_image` path.
* `--share none|dup` (default none), `--no-cross-pool`.
* `--append-safe` kept, now marked OPT-IN/INFERRED; with repack on it is a fallback only for overlays where repack leaves strings Japanese and the overlay is no-BSS eligible.
* Guard: strings whose region overlaps a pointer word of another string are refused (reported as failed), nothing else changes.
* No-op guarantee unchanged: no `en` -> no patch; `test_pipeline.py` A passes (all 5 tracks sha1-identical, `.cue` identical).
* NOT integrated (no tested pipeline code, or untested in game): the bank (R0 regions, `bankbuild.py`), BSS append, spill planner, translation-memory propagation, `share=dup` as default.

`tools/test_pipeline.py`: 65 -> **110 checks**.  B/C/D now run with `repack=False` (they test the legacy path: in-place + relocation counts, append-safe, BPINFO, font, container).  New test E (default path): identity of all 114 images (share none/dup);
6,696 synthetic strings (x1.2 / x0.8 mixed, mean 1.0) on CLUBEDIT, EVENT, SPF_READ: all applied, none skipped, deterministic, independent pointer-resolution verifier, changed bytes only inside string regions / pointer words, size unchanged; output disc re-read through `gdrom.py`:
exactly 3 files differ, 1,212 identical; `share=dup` not worse; forced rewrite of all pools of the 3 overlays equivalent; an over-long string is reported and leaves the overlay untouched; `--append-safe` fallback after repack appends 1 string (+412 B).
The legacy path also places all 6,696 strings in that mix (it already pools freed regions): repack's advantage shows only once pools are over capacity (full-game run below).

Full-game run with synthetic English of the model (`fullrun.py`, strings left Japanese): natural: legacy per-string 56,620 (47.2 %), repack 37,055 (30.9 %), repack + sharing 31,791 (26.5 %); 0.85 x natural: legacy 8,479 (7.1 %), repack 7,410 (6.2 %), repack + sharing 7,323 (6.1 %) (`fullrun_100.txt`, `fullrun_085.txt`; repack takes about 25 s for all 114 overlays, the legacy path 100-185 s).

## 7. Dynamic test plan (for the orchestrator; Flycast Lua bridge `tools/emu/live.lua`: `poke/peek/dump/say/frame`; discs built with `tools/re/capacity/synth/mkdisc.py`, nothing is committed)

Ordered by "decides the most per boot".  Always take the baseline from an unmodified disc first.

| # | experiment | procedure | expected | if it fails / changes |
|---|---|---|---|---|
| **T1** | relocation safety (Layer 1) | `python -I -X utf8 tools/re/capacity/synth/mkdisc.py forceid` (every pool of CLUBEDIT, MEETING, NEWS, EVENT, TRAINING, HELP rewritten, NO translation; builds `build/out/forceid.gdi`, patched overlays also saved in `build/forceid_files/`).  Boot, play the scripted path of `tools/emu/scenario.lua` to Club Edit > Name Entry / Name&Mascot (CLUBEDIT, N_ENTRY), HELP pages, club meeting (MEETING), weekly news (NEWS), an event (EVENT), a training screen (TRAINING); compare screenshots with the original disc; `dump(0x8c000000,0x1000000,'t1.bin')` in each state, then `python -I -X utf8 tools/re/capacity/synth/poolwrite.py t1.bin FLOW_PRG/MEETING.BIN 8c2d0000 build/forceid_files/FLOW_PRG_MEETING.BIN` (CLUBEDIT, MEETING, NEWS, EVENT, TRAINING all load at 0x8c2d0000, HELP at 8cb60000) | text identical everywhere, no crash; `poolwrite` 0 differing pool/pointer bytes against the patched file | any garbled string: a hidden reference exists; find it from the dump, add it to the pointer scan or mark the owning pool fixed; if unfixable the project is Layer 0 only |
| **T2** | English renders after relocation | `mkdisc.py synth 0.85 --only CLUBEDIT MEETING NEWS TRAINING HELP EVENT` (readable synthetic English, line count = Japanese): same path as T1; record 4th-line / overdraw behaviour in the 3-row window, colour codes `@Y/..@`, typewriter | readable, no overdraw at the Japanese line count | line overflow => length budget per line, not only per byte (ratio agent test 1) |
| **T3** | strings read-only (share=dup) and pointer words stable | on dumps of the ORIGINAL disc, taken in as many states as possible: `python -I -X utf8 tools/re/capacity/synth/poolwrite.py DUMP SOURCE BASEHEX` (bases: `build/memmap/overlays.tsv`, column `base`); states to add beyond the 4 existing dumps: a match with replay, training, news, season change, save/load, ending | 0 differing pool / pointer bytes in all states | any difference: keep `share=none` forever and treat that pool as fixed |
| **T4** | append mechanics (Layer 2) | build CLUBEDIT with +0x1000 B appended and its `_end` word raised (`bankbuild.apply_overlay_tail`, or `build_patch --append-safe` with an over-long CHALDANI string, as in test E6); enter the screen, `dump` the slot.  Then MEETING (BSS padded with zeros + 0x1000 B + `_end` raised).  Negative control: same without raising `_end` | first heap header at `((new_end|0x80000000)&~0x1f)+0x20`, appended bytes intact, screen works; control: header overwrites the appended bytes | formula wrong => Layer 2 unusable, Layer 3 + Layer 4 only |
| **T5** | heap sufficiency | raise only the `_end` word by `append_cons` for MEETING, N_ENTRY, HELP, CLUBEDIT (all screens), then GAME/EVENT/NEWS; play their screens for minutes; `peek(0x8c230bd6,1)` after each screen (becomes 1 on the first failed malloc); `heapwalk.py DUMP ENDVAR ARENA_END` for the high-water mark | byte stays 0 | lower the per-overlay budget to the measured high-water mark |
| **T6** | bank regions (Layer 3) | `canary.py make` (tail, gap1-3, FONT tail; plus memmap's 14 "holes" as a negative control: they are inside crt0's BSS clear and SHOULD be erased); boot, dump after title and after every mode of T1/T3 (match, replay, training, news, save/load, season, ending); `canary.py check` | tail/gap1 intact in all dumps; control holes zeroed (confirms the crt0 decompile) | changed bytes disqualify that region; shrink the bank accordingly (the layer 3 numbers drop proportionally) |
| **T7** | pointer into a bank, odd address | `lua_poke.py FLOW_PRG/CLUBEDIT.BIN 0x20c08 0x8c299401 'Hello from the bank.'` into `cmd.lua`, open the screen; repeat with gap1 (0x8c13bb80) and FONT tail (0x8cdfdf1c) | renders like an in-slot string | odd address fails: rebuild the bank with `--align 4` |
| **T8** | modified `1ST_READ.BIN` / FONT.BIN accepted | the T6 discs themselves | boots to title | BIOS/Flycast rejects: bank layer dead, keep L2 |
| **T9** | BSS-pad semantics | MEETING and N_ENTRY with zero BSS pad: compare behaviour and a BSS dump with the original run | same behaviour (stale-RAM BSS vs zeros) | if an overlay relied on stale BSS: no pad for it, use Layer 3 for it |
| T10 | private areas | dump while ESTABLIS and the 7 non-slot overlays (COMM, CON_REP, NF_CON, PASS_PL, J1_REP, PL_CON, LOADBAR) run | memory accounted | until then budget 0 for them |

T1 and T2 can share one boot per overlay; T3 needs no extra boot beyond the dumps.  T6 + T8 share one disc.

## 8. Implementation order

1. **Done:** Layers 0 + 1 in `build_patch.py` and `test_pipeline.py` (this document).  Translators get the length targets of section 3 (Layer 4) now: they do not depend on any test.
2. **T1, T2, T3** (one forced-identity disc, one synthetic-English disc, dump comparison).  Gate for keeping `--repack on` as default.
3. **Name-table and TRAINING-tactic policy** (Layer 4): decide the `G. Family` ladder and the place-suffix rule once; list the 2,757 distinct fixed Japanese texts that overflow at natural English for the translators (`fixedcat.py` extension); spike on the orphan addressing of TRAINING if the tactics resist 1.0 x.
4. **Length lint** in the DB tooling: per-record `max_bytes` for fixed strings, per-pool budget report for movable ones, line-count check (the ratio agent's 39-cell rule), identical-ja translation-memory propagation (prerequisite for `--share dup`).
5. **Spill planner** in `textrepack` (or a wrapper): instead of reverting overflow strings to Japanese, move whole strings out to an external area, minimizing external bytes (target: close to the 316,638 B lower bound instead of the 1,243,509 B the greedy revert implies); output = list of strings with English bytes for Layers 2/3.
6. **Layer 3** (after T6-T8 pass): wire `bankbuild.build_bank/apply_regions` into `build_patch` (patch `/1ST_READ.BIN` in place, `/FONT.BIN` behind the final font size; bank first for overlays with no Layer-2 budget: GAME, HELP, ESTABLIS, the 3 tiny non-slot ones); extend `test_pipeline.py` with a read-back test.
7. **Layer 2** (after T4, T5, T9 pass): extend `--append-safe` to BSS overlays with zero padding and budgets from `overlays.tsv` (`append_cons`, then the measured high-water marks); never for GAME/ESTABLIS without their special handling.
8. **`--share dup` default** only after T3 covered match/training/news/season states and the translation memory step exists.

## 9. Reproduce

```
python -I -X utf8 tools/test_pipeline.py                                   # 110 checks (about 65-75 s, needs ~3.5 GB in build/out)
python -I -X utf8 tools/test_textrepack.py --quick                         # pool agent's tests (80 s)
python -I -X utf8 tools/re/capacity/synth/joint.py 1.0 0.85 0.80           # layer table (about 30 s per run)
python -I -X utf8 tools/re/capacity/synth/deficit.py                       # external-byte lower bounds
python -I -X utf8 tools/re/capacity/synth/fixedcat.py                      # who the fixed overflow is
python -I -X utf8 tools/re/capacity/synth/fullrun.py 0.85                  # real pipeline on synthetic English (several minutes, legacy path included)
python -I -X utf8 tools/re/capacity/synth/gap.py 0.85                      # pipeline vs planner per overlay
python -I -X utf8 tools/re/capacity/synth/recount.py                       # pool population recount
python -I -X utf8 tools/re/capacity/synth/poolwrite.py                     # 8 RAM-dump pairs: pool / pointer bytes written at run time
python -I -X utf8 tools/re/capacity/synth/ptroverlap.py                    # strings overlapping a pointer word
python -I -X utf8 tools/re/capacity/synth/holes_vs_crt0.py                 # memmap holes vs crt0 BSS clear
python -I -X utf8 tools/re/capacity/synth/mkdisc.py forceid | synth 0.85   # discs for the dynamic tests
```
Opt-in flags: `python -I -X utf8 tools/build_patch.py --repack on --share dup`, `--append-safe` (INFERRED), `--repack off` (legacy path).
`tools/re/capacity/synth/recheck/` holds the re-run outputs of the other agents' scripts (`ratio_analyze.txt` reproduces 3,349,285 / 318,916 / 112 overlays / 41.8 %).

## 9. Skeptic review outcomes (applied / open)

Numbers skeptic: headline totals reproduce exactly. Report string shares as L0 44-49 %, L0+L1 69-76 % at natural
English (+-5 points; they hinge on ~3.8 k distinct fixed name/place texts); the 0.85x shares (73 % / 94 %) are solid
to ~1 point. 0.85x is an assumed target (measured natural sample is 1.20x). 37 % of prose needs more lines than the
Japanese at 39 cells; the byte model does not cover that. Relocation safety (T1) is still unproven in the game.

Memory skeptic: no proven corruption, but:
- APPLIED: `append_eligible()` now refuses ESTABLIS, LOADBAR, MOVIE, MOVIE_BG (ESTABLIS' stub ignores `_end`).
- OPEN: cap append growth per overlay at `append_cons` and at `slot_end - new_end >= heap reserve`; abort when exceeded.
- OPEN: start the 1ST_READ tail bank at 0x8c299800 or later (the Ninja matrix stack ends at 0x8c299400, live3 uses
  11 of 16 slots) and leave the last 0x40 B before 0x8c2b0000 unused.
- OPEN docs fixes: the crt0 words at 0x8c016b88-bac are section bounds, not "memory pools"; SG_DPLDR.BIN is a one-way
  jump (browser mode replaces all RAM, banks are lost); key overlay tables by (directory, name) because TITLE.BIN exists twice.
- Add to T5: largest free block after the `_end` raise must still exceed the largest observed allocation.
