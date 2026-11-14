# English-vs-Japanese byte ratio, measured on real translations

Author: agent `ratio`. Everything below was produced by the scripts in `tools/re/capacity/ratio/`
(static analysis of `translation/*.jsonl`; nothing run on an emulator). Status words: **PROVEN** = computed by
a script here from the data, **INFERRED** = follows from the numbers plus code facts in `text-engine.md`,
**UNKNOWN** = needs a dynamic test (section 9).

## 0. Headline

| Question | Answer (natural, faithful translations; ASCII; Given-Family names) |
|---|---|
| English bytes per Japanese byte (incl. NUL), whole overlay text, population-weighted | **1.22** (95 % bootstrap CI 1.20 - 1.24) |
| ... for the prose that carries the volume (MEETING, NEWS, EVENT, TRAINING, other prose, HELP = 70.5 % of JP bytes) | **1.15** (MEETING 1.06, HELP 1.08, NEWS 1.17, TRAINING 1.18, EVENT 1.20, other prose 1.20) |
| ... short strings | names 1.46, places 1.33, labels 1.33, numbers/units 1.15 |
| Strings that fit their own original slot (`max_bytes`) | **41.9 % of records**, 28.1 % of JP bytes. Prose only: 27.0 % of records, 22.2 % of bytes |
| Fit if every movable string could be repacked into its overlay's pooled slots (ideal packing) | adds **26.0 %** of records (22.4 % of bytes); prose-only adds 25.2 % / 21.3 % |
| Still does not fit (needs extra memory, shortening, or stays Japanese) | **32.1 % of records, 49.5 % of JP bytes**; prose-only 47.7 % / 56.5 % |
| Extra memory if all text is translated naturally and repacked per overlay | about **319 KB** summed over 114 overlays (3.35 MB English need vs 2.34 MB movable pool); 112 of 114 overlays exceed their movable pool. Biggest: NEWS +51.2 KB, MEETING +23.8 KB, DRAFT +21.7 KB, TRAINING +19.8 KB, HELP +8.5 KB per copy (two copies), SCDRF +14.2 KB, EVENT +11.7 KB, GAME +9.8 KB, NEWS_ED +9.6 KB |
| Edit pressure that removes the problem | pooled English must shrink to **0.84-0.94 of my natural length** (break-even, section 5). At 0.80x almost everything fits after repacking (A 77.8 %, B 18.3 %, C 3.8 % of records); at 0.90x C is still 17.2 % |
| Line budget | with the Japanese line count as limit and 39 cells/line, **37.2 %** of prose/help strings need more lines than the Japanese had (59 % TRAINING, 53 % NEWS, 44 % other prose, 40 % EVENT, 19 % HELP, 4 % MEETING); 26.5 % of the <=3-line strings would need a 4th line |

In one sentence: **natural English is about 1.15x (prose) to 1.46x (names) the size of the Japanese, so a pure in-place build
translates only ~42 % of the records and ~28 % of the bytes; repacking alone (zero new memory) raises that to ~68 % of
records / ~50 % of bytes; the rest needs either ~320 KB of extra memory across the overlays or English edited to ~85 % of
natural length.** A terse, hand-edited style (section 6) reaches 0.75 x JP and fits in place for 93 %.

## 1. Scope and population

Population = every record of `translation/FLOW_PRG__*.jsonl` (112 files) + `ATFIRST__HELP/TITLE.BIN.jsonl`:
**119,946 records, 2,749,078 JP bytes (string + NUL), 3,019,121 bytes of slots (sum of `max_bytes`)**. Not in scope:
ETC_DATA/BPINFO (5,321), ROOT/1ST_READ (157), DPETC/MESSAGE.INI (849): other formats with their own limits.
A record is *movable* if it is referenced, not interior-pointed and not in a fixed-stride table (`ctx` has no
`stride-table`/`interior-ptrs`, no `orphan`): 81,988 records. The other 37,958 (orphans, name tables, TRAINING tactic blocks)
can only be patched in place (`overlay-text.md` section 4).

Categories (`common.py:category`, heuristic on file, length, characters; rules in the script):

| category | records | distinct ja | JP bytes | movable records | sample n (usable) |
|---|---|---|---|---|---|
| prose_other (DRAFT, SCDRF, GAME, ESTABLIS, RECON, YOUTH, CLUBEDIT, ... >= 12 chars) | 10,290 | 5,984 | 694,320 | 10,173 | 135 (136 drawn, 1 junk) |
| prose_meeting (MEETING.BIN) | 7,318 | 5,439 | 373,382 | 7,316 | 72 |
| prose_news (NEWS, NEWS_ED) | 3,628 | 2,492 | 340,385 | 3,626 | 62 |
| name (person names, 14-byte fixed fields) | 34,333 | 2,499 | 340,537 | 1,741 | 68 |
| place (市/区/郡/町/村/県/府 names) | 43,676 | 1,315 | 323,276 | 42,184 | 56 |
| prose_training (TRAINING.BIN descriptions + orphan tactic text) | 2,664 | 1,478 | 253,309 | 1,110 | 49 |
| help (HELP.BIN, both copies) | 1,330 | 661 | 219,358 | 1,330 | 42 |
| label (short UI labels, readings, province names, screen names) | 13,027 | 4,060 | 118,840 | 10,925 | 41 (45 drawn, 4 junk) |
| prose_event (EVENT.BIN) | 814 | 814 | 56,753 | 813 | 40 |
| numunit (digits, `%d`, 円/位/週 ...) | 2,866 | 904 | 28,918 | 2,770 | 40 |

(`stats2.py`, `analyze.py`.) Names/places repeat across ~50 overlays (2,499 distinct names, 34,333 records), so record-weighted
numbers are dominated by tables of short strings, byte-weighted numbers by prose; both are given.

## 2. Sample (PROVEN)

`draw.py` (seed 20261110) + `draw_extra.py` -> `sample_src.tsv`: **609 strings drawn, 605 usable** (4 records are garbage
(`麹倹月`, `覧藍楓舶`, `L徹敬`, the kinsoku character list) kept in `sample.jsonl` with `"skip": true`, excluded from all statistics).
Allocation: proportional to JP character volume with a floor of 40 (`N0=520`), no duplicate `ja` in the sample, and for prose/
help/label/numunit a top-up so at least `max(5, population share)` of each category carries control tokens (population share
of tokens: help 97 %, news 67 %, training 40 %, event 36 %, other 20 %, meeting 1 %). Sample token share is within a few
points of the population share except meeting (7 % vs 1 %) and label (17 % vs 11 %).
Strings carry `@Y/..@ @O/..@ @P/..@ @M/..@ @K/..@`, `=w/..=`, `%s %d %D %m`, `$1`..`$4`, `#sname# #tkNN# #chi# #ken# #kyu#`, `<09>`.

Translations (`tr/*.txt`, hand-written by me, natural British English per `docs/style-guide.md`; Hepburn names Given-Family,
-gun/-cho/-mura suffixes, 市 dropped). Checks run by `build_sample.py` / `check_lines.py`: all 605 `en` are ASCII, contain no
`\ ~ #`(outside tokens), the control-token multiset equals the Japanese in every record, **no wrapped line exceeds 39 cells
(1,226 prose/help lines, max 39)**. English is stored word-wrapped at 39 cells (`en`) and flat (`en_flat`); wrapping only turns a
space into `\n` so byte counts are unaffected. `sample.jsonl` fields: `idx cat id max_bytes ja en en_flat skip`.

## 3. Ratios by category (PROVEN; `analyze_out.txt`)

EN/JP = English bytes (+NUL) / Japanese bytes (+NUL). "pooled" = sum(EN)/sum(JP). "fit" = EN <= own `max_bytes` (slots include
the original padding). Percentiles are over per-string ratios. CI = bootstrap 95 % of the pooled ratio (2000 resamples).

| category | n | pooled EN/JP [CI] | p50 | p75 | p90 | p99 | fit own slot | EN <= JP bytes | movable fit / pinned fit |
|---|---|---|---|---|---|---|---|---|---|
| prose_meeting | 72 | 1.062 [1.014-1.110] | 1.05 | 1.20 | 1.34 | 1.56 | 45.8 % | 45.8 % | 46 % / - |
| prose_news | 62 | 1.171 [1.133-1.208] | 1.18 | 1.26 | 1.38 | 1.46 | 12.9 % | 12.9 % | 13 % / - |
| prose_event | 40 | 1.197 [1.142-1.253] | 1.17 | 1.32 | 1.46 | 1.68 | 27.5 % | 22.5 % | 28 % / - |
| prose_training | 49 | 1.182 [1.146-1.221] | 1.17 | 1.29 | 1.33 | 1.47 | 10.2 % | 10.2 % | 5 % (22) / 15 % (27) |
| prose_other | 135 | 1.197 [1.162-1.234] | 1.19 | 1.34 | 1.51 | 1.85 | 21.5 % | 18.5 % | 21 % / - |
| help | 42 | 1.077 [1.034-1.123] | 1.05 | 1.14 | 1.19 | 1.41 | 35.7 % | 35.7 % | 36 % / - |
| label | 41 | 1.325 [1.210-1.440] | 1.32 | 1.52 | 1.80 | 2.04 | 53.7 % | 29.3 % | 47 % (36) / 100 % (5) |
| name | 68 | 1.463 [1.409-1.513] | 1.48 | 1.60 | 1.80 | 1.93 | 47.1 % | 2.9 % | - / 48 % (66) |
| place | 56 | 1.332 [1.225-1.438] | 1.29 | 1.60 | 1.78 | 2.20 | 41.1 % | 26.8 % | 40 % / - |
| numunit | 40 | 1.154 [1.032-1.265] | 0.91 | 1.25 | 1.47 | 1.78 | 62.5 % | 55.0 % | 65 % / 33 % |
| prose + help (6 cats, n=400) | 400 | 1.151 (population-weighted) | 1.14 | 1.29 | 1.41 | 1.70 | - | - | - |
| all sampled strings (unweighted, n=605) | 605 | 1.159 | 1.18 | 1.36 | 1.60 | 1.91 | 33.6 % | - | - |
| **population-weighted (post-stratified)** | | **1.218 [1.200-1.237]** | | | | | **41.6 % of records, 28.0 % of bytes** | | |

English bytes per Japanese character: meeting 2.24, help 2.26, other prose 2.44, training 2.44, event 2.47, news 2.62,
numunit 2.75, names 2.92, places 3.08, labels 3.15. Fit rate by JP size (bytes): 0-8 59 %, 8-17 48 %, 17-40 31 %,
40-80 33 %, 80-120 **14 %**, >=120 26 %; the long strings are the ones with ~0 padding (mean pad 0.0-0.3 bytes) so they are
fit-by-luck only. The 8-17 byte bucket has 3.4 bytes mean padding and still only 48 % fit.

Per-overlay pooled sample ratios (files with >= 10 sampled strings): MEETING 1.062 (n=73), NEWS 1.186 (65), TRAINING 1.182 (49),
HELP 1.078 (22) / ATFIRST/HELP 1.077 (20), EVENT 1.200 (42), DRAFT 1.226 (15), YOUTH 1.370 (15), ESTABLIS 1.203 (12),
CHALMODE 1.153 (12), VTRLOAD 1.574 (10, mostly names), FREELOAD 1.378 (10, mostly names).

Names: 14-byte fields (64 of 68 sampled; 12-13 in 4). "Given Family" fits 32/68 (47 %); the style-guide ladder `G. Family`
rescues all remaining 36 (0 need Family-only). Places: slots 8 (48 of 56) or 12 bytes; 23/56 fit; 38/56 would fit if the
`-gun/-cho/-mura` suffix were dropped (a style decision with a cost in disambiguation).

## 4. Pooled per overlay and extrapolation (PROVEN model, INFERRED reliability)

Model: for every record of the whole DB, estimated English bytes = JP bytes x pooled ratio of its category (table above).
Per overlay: `pool` = sum of `max_bytes`, `slack` = pool - JP bytes, `need` = estimated English. "movable" restricts to movable
records (the only ones that can be repacked). Script `analyze.py` (table of all 114 images in `analyze_out.txt`, raw numbers in
`analyze_out.json`).

| overlay | records | JP bytes | pool | slack (pool-JP) | est. EN need | need/pool | movable pool | movable need | extra bytes if repacked | pinned records, % fit in place |
|---|---|---|---|---|---|---|---|---|---|---|
| MEETING | 7,548 | 376,714 | 376,951 | 237 | 400,807 | 1.06 | 376,541 | 400,367 | 23,826 | 27 (64 %) |
| NEWS | 3,702 | 302,574 | 303,165 | 591 | 354,357 | 1.17 | 303,031 | 354,205 | 51,174 | 9 (76 %) |
| TRAINING | 2,791 | 254,338 | 254,598 | 260 | 300,739 | 1.18 | 109,725 | 129,505 | 19,780 | **1,570 (16 %)** |
| HELP (each of 2 copies) | 700 | 109,939 | 110,032 | 93 | 118,514 | 1.08 | 109,794 | 118,268 | 8,474 | 17 (48 %) |
| DRAFT | 1,563 | 118,757 | 120,588 | 1,831 | 142,299 | 1.18 | 120,421 | 142,101 | 21,680 | 8 (90 %) |
| SCDRF | 861 | 73,022 | 73,307 | 285 | 87,574 | 1.19 | 72,991 | 87,237 | 14,246 | 26 (64 %) |
| EVENT | 2,606 | 71,970 | 76,173 | 4,203 | 87,946 | 1.15 | 75,722 | 87,444 | 11,722 | 29 (65 %) |
| NEWS_ED | 2,047 | 59,969 | 62,456 | 2,487 | 72,079 | 1.15 | 62,419 | 72,035 | 9,616 | 5 (100 %) |
| GAME | 1,137 | 57,637 | 58,322 | 685 | 69,624 | 1.19 | 53,017 | 62,855 | 9,838 | 276 (84 %) |
| name-table overlays (BPMATCH, CHALMODE, ENDOPT, DMCLBEDT, BACKUP, EXTRADE, LOAD, CSAVE*, SONGSAVE, VTRLOAD, FREELOAD, AUTOSAVE, EXFLAG, ... ~3,450 records each) | ~3,450 | ~32,000 | ~42,500 | ~10,400 | ~45,500 | 1.06-1.07 | ~13,500 | ~15,000 | ~1,550 each | ~2,070 (49 %) |
| **all 114 images** | 119,946 | 2,749,078 | 3,019,121 | 270,043 (8.9 %; 77.6 % = 209,687 bytes of it sits in the 19 overlays with > 1,000 pinned records) | 3,349,285 (1.218 x JP, 1.109 x pool) | | 2,338,270 | 2,657,180 | **318,916 total**, 112 of 114 overlays short | 37,958 (50 % fit) |

Reading: the big prose overlays have **0.0-0.7 % slack** (MEETING 237 bytes, NEWS 591, HELP 93, TRAINING 260) while needing
+6 % (MEETING) to +19 % (SCDRF, GAME, DRSLIST, NEWCON). The only large slack lives in the fixed-record table overlays
(about 10.4 KB each, 2,070 pinned name records at 14 bytes), and those are pinned, i.e. unusable as shared space
(`HOMETOWN.BIN` pool 69,438 vs JP 25,966: 43 KB of padding in tables). The six big prose images (MEETING, NEWS, TRAINING, DRAFT,
HELP x2) hold only **3,103 bytes** of slack in total. Overall *in-place* record fit (this model): 41.8 %
of records, 31.3 % of JP bytes (`analyze.py`; the 41.9 %/28.1 % in section 0 come from `analyze2.py` classes A, same quantity,
different weighting of the small movable/pinned subsamples).

Uncertainty (INFERRED): (a) sampling error, bootstrap CI of the pooled population ratio +-0.02, of single categories +-0.03-0.06;
(b) category ratios from 40-135 strings, MEETING has only 72 strings of 7,318; (c) the estimator assumes every string of a
category is like the sample (unequal: e.g. the `#tkNN#` headline strings are shorter than the training tactic text); (d)
**translation style**: mine is faithful and unabridged and the style guide asks for the same; a terse style changes the
ratio by -30 % (section 6), a more literal/honorific one would raise it; (e) token expansion is irrelevant to bytes (tokens are
kept verbatim) but matters for width (section 7); (f) junk/debug strings (dummy, flag names) are translated like text and
count at ~1.1-1.4.

## 5. Repack model and what it takes to fit (PROVEN model; `analyze2.py`)

Best case, no new memory: all movable strings of a category share their pooled slots, strings are switched Japanese -> English
cheapest first (EN - JP bytes) while the free pool (slack + savings) lasts. Pinned records must fit in place.
`scale` multiplies my English byte lengths (simulates harder editing).

| scale (EN vs natural) | records: A in place | B only repacked | C still no | bytes: A | B | C | prose+help only (records A/B/C) |
|---|---|---|---|---|---|---|---|
| 1.00 (natural) | 41.9 % | 26.0 % | **32.1 %** | 28.1 % | 22.4 % | **49.5 %** | 27.0 / 25.2 / 47.7 % |
| 0.90 | 48.9 % | 33.9 % | 17.2 % | 44.9 % | 32.8 % | 22.3 % | 46.1 / 35.6 / 18.3 % |
| 0.80 | 77.8 % | 18.3 % | 3.8 % | 72.5 % | 23.9 % | 3.6 % | 69.8 / 28.0 / 2.2 % |
| 0.70 | 90.9 % | 9.0 % | 0.0 % | 93.0 % | 6.8 % | 0.2 % | 91.7 / 8.1 / 0.2 % |

Break-even scale (pooled English = pooled slots, movable strings): MEETING 0.942 (cut 5.8 %), HELP 0.928 (7.2 %), NEWS 0.855
(14.5 %), EVENT 0.855 (14.5 %), TRAINING 0.851 (14.9 %), other prose 0.838 (16.2 %), places 0.889 (11.1 %), labels 0.898
(10.2 %), numunit 0.980 (2.0 %). Names are pinned: ladder `G. Family` fits 68/68.
Consequences (INFERRED): (1) a 100 % repack of the natural text needs ~14-16 % more room for news/event/training/other
prose and 6-7 % for MEETING/HELP; (2) repacking is required for any outcome above ~48 % of records, because at scale 0.90 only
49 % fit in place; (3) **TRAINING's 1,565 orphan tactic texts (144 KB, 16 % fit) cannot be relocated at all** (addressing unknown,
`overlay-text.md` section 2) so they are the single largest in-place-only block; they need either the addressing reverse
engineered or English at ~0.7x their Japanese size.

## 6. How far editing alone goes (PROVEN on 60 strings; `analyze_tight.py`, `tight/tight.txt`)

For a random 60-string subset of prose+help I wrote a **tight** variant (telegraphic, secondary clauses dropped, still the
same facts). Result: tight/natural = 0.675 (tight = 0.755 x JP vs natural 1.120 x JP); fit in own slot 93 % vs 27 %
(prose >= 30 JP bytes: 96 % vs 23 %; MEETING/NEWS/EVENT/TRAINING/HELP 100 %, other prose 81 %); line overflow vs the Japanese
line count 0/52 vs 16/52. This is a floor on size, not a recommended style (it drops nuance, e.g. HELP loses the second-order
explanations); the realistic target is between the two (0.80-0.90 of natural from the table above).

## 7. Line-length feasibility (PROVEN given the assumptions; `analyze.py`)

Window geometry (`text-engine.md` 4.3-4.4): default window 20 cells -> 39 ASCII cells/line, 3 rows, no word wrap, no clipping,
no paging in the library. Japanese uses 27.8 cells per non-empty line on average (p50 30, p90 36, max 40): 71 % of the line.
JP line counts of the 400 sampled prose/help strings: 1 line 73, 2 lines 111, 3 lines 178, 4+ lines 38 (help lists up to 9).
English flat width: mean 91 cells per string vs 75 for the Japanese (1.21x), p90 144, max 402.

Greedy word wrap at 39 cells (minimum possible line count), substitution tokens expanded to assumed widths
(`#sname#`/`#tkNN#` 10, `$N` 6, `%s` 8, `%d` 3, `%D` 6; the real widths are UNKNOWN; without expansion the numbers are in
brackets):

| result | all 400 | meeting | news | event | training | other prose | help |
|---|---|---|---|---|---|---|---|
| English needs more lines than the Japanese had | **149 (37.2 %)** [135, 33.8 %] | 3/72 (4 %) | 33/62 (53 %) | 16/40 (40 %) | 29/49 (59 %) | 60/135 (44 %) | 8/42 (19 %) |

Extra-lines histogram (EN lines - JP lines): -2: 1, -1: 33, 0: 217, +1: 137, +2: 11, +3: 1. Of 362 strings whose Japanese is
<= 3 lines, **96 (26.5 %)** need a 4th line or more in English [85, 23.5 % without token expansion]. So faithful translation
does not fit the existing line structure in about one third of the prose; the overflow is almost always +1 line (137 of 149).
MEETING (short, 2 lines of ~15 JP chars) is the only category that fits, 96 %.
What this implies (INFERRED): (1) windows are 3 rows (`+0x3d=3`, not enforced), so a 4th line either spills below the frame
or is clipped/overdrawn: **needs a dynamic test (section 9, test 3)**; (2) shortening to the tight variant removes the overflow
(0/52); (3) the byte problem and the line problem are the same problem here: both are ~15-20 % too long.
Also: lines ending in `. , ! ?` at column 39 cannot hang (text-engine 3), so the true limit for those is 38 cells; my wrap
did not enforce that: 123 of 1,226 wrapped lines are exactly 39 cells wide and 19 of them end in `. , ! ?` (1.5 % of lines; each
would move one word down, adding a line in a few strings; not included in the 37.2 % figure, `check_misc.py`).

## 8. PROVEN / INFERRED / UNKNOWN

PROVEN (scripts in `tools/re/capacity/ratio/`): population counts, the sampling, the 605 translations' technical validity,
all ratios, percentiles, fit rates, per-overlay extrapolation arithmetic, repack model results, line feasibility under the stated
width assumptions, names ladder, tight-variant measurement.
INFERRED: that the category ratios generalise to the whole DB (CI +-0.02 pooled, style dependent); that the optimal-repack model
is achievable (needs `textdb.insert_image` strategy B to place every movable string; it packs byte-exact, no alignment needed);
that pinned/orphan records cannot be moved; 4th-line behaviour.
UNKNOWN: actual widths of `#sname#`, `#tkNN#`, `$N`, `%s`, `%m`; the row limit per window (only the default 3-row window was
read); how many extra bytes each overlay may legally gain (heap/BSS, owned by the capacity-design agents); whether
`%D`/`%m` outputs (full-width digits, 万/円 text) widen the English; the `skip` junk records' count in the full DB.

## 9. Dynamic tests the orchestrator should run (no emulator was used here)

1. **Fit sanity of the byte model**: in a RAM-write test, put the English of 3-4 sample strings (e.g. idx 258, 603, 591 in
   `sample.jsonl`) at original pointers with unchanged length and confirm display (existing live proof covers ASCII).
2. **Token widths**: show `#sname#`, `#tk00#`..`#tk25#`, `$1`..`$4` in a MEETING/NEWS/EVENT message and measure the rendered
   width (pixels) with a 12-px grid; settle the 10/10/6 assumptions in section 7.
3. **4th line**: show a 4-line English string in the default window (NEWS and TRAINING messages, which are the worst cases at 53-59 %
   overflow) and record: overdraw below the frame, clipping, or crash. If it is clipped, 37 % of faithful prose must be edited
   to the Japanese line count.
4. **Window row/col per overlay**: dump `+0x3c/+0x3d` of the live windows in NEWS, TRAINING, HELP, EVENT (HELP uses up to 9-10 lines
   per page; the sample says JP lines per string up to 9).
5. **Append safety** (text-engine 8.1) decides whether the ~319 KB shortfall (NEWS +51 KB, MEETING +24 KB, DRAFT +22 KB, TRAINING +20 KB,
   HELP +8.5 KB x2, SCDRF +14 KB, EVENT +12 KB) can be housed by growing the files.

## 10. Reproduction

```
python -I -X utf8 tools/re/capacity/ratio/draw.py            # sample_src.tsv (609 -> first 605 rows; draw_extra.py appends 4)
python -I -X utf8 tools/re/capacity/ratio/draw_extra.py
python -I -X utf8 tools/re/capacity/ratio/build_sample.py    # merges tr/*.txt -> sample.jsonl (validates tokens, ASCII, wraps)
python -I -X utf8 tools/re/capacity/ratio/analyze.py  > tools/re/capacity/ratio/analyze_out.txt
python -I -X utf8 tools/re/capacity/ratio/analyze2.py > tools/re/capacity/ratio/analyze2_out.txt
python -I -X utf8 tools/re/capacity/ratio/analyze_tight.py > tools/re/capacity/ratio/analyze_tight_out.txt
python -I -X utf8 tools/re/capacity/ratio/check_lines.py
```
(`draw.py` rewrites `sample_src.tsv` without the 4 top-up rows, so always run `draw_extra.py` after it. The translation text itself
is in `tr/*.txt`, idx -> English, `|` = forced line break, `SKIP` = junk; `tight/tight.txt` is the terse variant.)
Files: `common.py` (loader, category and movable rules), `stats0/1/2.py` and `peek.py` (exploration), `sample.jsonl`,
`sample_src.tsv`, `analyze_out.txt/json`, `analyze2_out.txt`, `analyze_tight_out.txt`.
