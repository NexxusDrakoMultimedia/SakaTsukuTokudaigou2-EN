# String-pool repacking for the SH-4 overlays

Author: agent `pool`. Code: `tools/textrepack.py`, tests `tools/test_textrepack.py`, measurement scripts and raw results
`tools/re/capacity/pool/` (`results/*.json|tsv`). Status words: PROVEN = produced by code run here (script named),
INFERRED = follows from data but not run in the game, UNKNOWN = needs the dynamic test in section 8.
Nothing here was run in an emulator.

## 1. Summary

* `textrepack.repack(image, load_addr, entries, ...) -> (new_image, report)` treats each maximal run of abutting
  string regions as a **pool**, re-lays it out back-to-back (all strings, translated or not), optionally shares
  identical strings, moves whole strings between pools when one pool is full, and rewrites every pointer word.
  Image size never changes. With all `en` empty the output is byte-identical (PROVEN, 114 images).
* Repacking alone (no sharing) only helps where English lengths vary around the Japanese length. It cannot raise the
  ratio at which pools overflow beyond `pool capacity / JP bytes` = **1.042 game-wide** (pools hold only 4.03 % slack).
* The big gain is **sharing identical strings**: 210,694 bytes (9.39 % of all movable JP bytes) are duplicates inside
  one pool, 91,070 of them in MEETING and 89,516 in NEWS. That lifts the overflow-free ratio of MEETING to **1.330**,
  NEWS to **1.438**, YOUTH to 1.380, DRSLIST 1.337; game-wide sum-level bound **1.150**.
* 37,960 of 119,946 strings (31.6 %) are *fixed* (orphans / stride tables / interior pointers) and cannot be moved;
  they overflow as soon as English exceeds their slot, so game-wide nothing helps beyond ratio ~1.0 for those (section 6).
* Headline (movable strings, uniform ratio, step 0.005): per-string 1.001 for almost every one of 113 images; repacking with
  cross-pool moves: median 1.048 (JP-byte weighted mean 1.039); with duplicate sharing: median 1.080, weighted 1.168,
  max 1.438 (NEWS). Per overlay table in section 5.

## 2. Definitions (all from `tools/textdb.py` extraction; nothing new is guessed)

* movable string = referenced by >=1 aligned absolute pointer word, not an orphan, not `pinned` (stride table), no
  interior pointer. Fixed string = anything else.
* region of a string = `[off, off + max_bytes)` = text + NUL + following zero bytes up to the next non-zero byte /
  accepted string / pointer target (textdb "full" pad mode).
* pool = maximal run of movable regions that abut. The pool range `[a, z)` is the only memory the pool may use.
  PROVEN (analyze.py): 114 images (1ST_READ excluded), 119,946 strings = 81,986 movable + 37,960 fixed (37,885 orphan,
  39 pinned, 34 interior); **3,646 pools**, 1,990 of them hold a single string (no gain possible), 79,996 strings sit in
  multi-string pools; capacity 2,338,194 bytes vs 2,243,846 JP bytes (NUL included) = slack 94,348 (4.03 %);
  170 pools >= 1 KB hold 2,099,473 bytes; largest pool 294,210 bytes (MEETING).
* `pad_mode='safe'` (only alignment fill counts as room) gives 3,663 pools, capacity 2,337,365, slack 93,519 (-0.04 %),
  so the "zero bytes might be data" worry costs almost nothing (safepad.py).

## 3. Algorithm (`plan_pools` + `repack`)

1. validate entries like `insert_image` (id / ja must match the image, `en` encoded with `textdb.encode_text`).
2. fixed strings: written in place if `len+1 <= max_bytes`, else listed in `fixed_overflow` and left Japanese.
3. per pool: need = sum of (len+1) of its strings (identical bytes counted once when `share='dup'`).
4. pool over capacity: (a) `cross_pool=True`: move whole sharing groups (smallest group >= deficit, else largest) into
   the pool with the least spare room that still fits it; (b) still over: revert translated strings to Japanese,
   largest growth first (fewest reverts) -> `report.overflow` (id, needed bytes, original bytes, pool deficit).
5. untouched pools (no translation, nothing moved in/out) are not rewritten; touched pools are zeroed and re-laid out in
   original order (moved-in strings last); the pointer words of every string in them are rewritten.
6. `check()` is an independent proof (size, pointer resolution, every changed byte inside a pool range, fixed region or
   rewritten pointer word). `force=True` rewrites every pool even with no translation (equivalence proof: same text
   behind every pointer).

Options: `share` none|dup, `cross_pool`, `pad_mode`, `force`. Deterministic. MEETING (7,548 strings) takes 0.5 s.
Not implemented on purpose: suffix sharing (only 10,982 extra bytes game-wide = 0.49 %, pointers would point
mid-string), moving fixed strings (their addressing is unknown), growing the image (other agents).

## 4. Tests (PROVEN, `python -I -X utf8 tools/test_textrepack.py`: 0 failures, 223 s; `--quick` 81 s)

* unit: hand-built image: exact expected bytes after an in-pool borrow, duplicate sharing saves 21 bytes and the shared
  strings have one address, overflow reverts to Japanese, a cross-pool move works and without `cross_pool` the same input
  overflows, orphan in place / orphan overflow, stale `ja` skipped.
* identity: all 114 images with `en` empty (entries = translation/*.jsonl), share none/dup -> output == input.
  `force=True` (every pool rewritten): `check()` clean for every image (every pointer of every string resolves to
  identical text, only pool bytes and pointer words changed) and a second forced pass is a byte fixed point.
* synthetic: 128 cases = {CLUBEDIT, EVENT, GAME, HELP, TRAINING, MEETING, NEWS, DRAFT} x 4 seeded length mixes
  (mean 0.5/0.9/1.2/1.6, one with 50 % of strings translated) x share none/dup x cross on/off: `check()` clean, no skipped
  entries, every string that stays Japanese is found again by `textdb.extract_image` on the output (except glued
  half-width-kana strings, whose textdb acceptance depends on neighbours; their pointers are covered by `check()`), output
  deterministic, and a second pass over the output's own strings (`report.after`) is a fixed point.
* `beat-per-string`: CLUBEDIT with strings alternately 0.6x / 1.35x: 39 strings fail the per-string slot, repack overflows 0.

## 5. Capacity measurements (PROVEN; `sim.py`, `game.py`, `report_*.py`)

Synthetic English for a string of L JP bytes: `round(r*L)` ASCII characters derived from a hash of the JP bytes (equal
`ja` gives equal `en`, as a translation memory would). **Uniform**: every string exactly r*L. **Mixed**: r*(1+0.5*U(-1,1)),
mean r, deterministic. Modes: **a** per-string in place; **a2** the current `textdb.insert_image` (relocation into pooled
freed regions, its strategy A/B); **b0** pool-local repack; **b1** + cross-pool moves; **b2** + duplicate sharing.
"Overflow" = the string stays Japanese. Full per-overlay files: `results/grid_s0.tsv`, `grid_s0.5.tsv` (+ `.json` with
bytes), `thresh_table.tsv`.

Share of strings that overflow, % (`a / a2 / b0 / b2`):

uniform ratio

| image | strings | r=0.8 | r=1.0 | r=1.2 | r=1.5 | r=2.0 |
|---|---|---|---|---|---|---|
| MEETING | 7548 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 99 / 99 / 99 / 0.1 | 100 / 100 / 99 / 26 | 100 / 100 / 100 / 57 |
| NEWS | 3702 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 97 / 97 / 95 / 0.2 | 99 / 99 / 97 / 10 | 100 / 100 / 99 / 51 |
| TRAINING | 2791 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 96 / 96 / 96 / 95 | 99 / 99 / 98 / 97 | 100 / 100 / 99 / 99 |
| DRAFT | 1563 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 94 / 94 / 86 / 50 | 98 / 98 / 92 / 70 | 100 / 100 / 96 / 85 |
| ATFIRST/HELP | 700 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 95 / 95 / 95 / 86 | 98 / 98 / 98 / 93 | 100 / 100 / 99 / 96 |
| HELP | 700 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 95 / 95 / 95 / 85 | 98 / 98 / 98 / 93 | 100 / 100 / 99 / 96 |
| SCDRF | 861 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 85 / 85 / 85 / 81 | 95 / 95 / 92 / 90 | 100 / 100 / 96 / 95 |
| EVENT | 2606 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 40 / 40 / 32 / 30 | 95 / 95 / 68 / 67 | 100 / 100 / 83 / 83 |
| NEWS_ED | 2047 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 29 / 28 / 25 / 6 | 93 / 93 / 63 / 54 | 100 / 100 / 81 / 76 |
| GAME | 1137 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 86 / 85 / 83 / 81 | 94 / 93 / 90 / 89 | 100 / 99 / 94 / 94 |
| SPF_READ | 3987 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 8 / 8 / 5 / 4 | 90 / 90 / 72 / 72 | 100 / 100 / 90 / 90 |
| ESTABLIS | 1798 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 20 / 20 / 17 / 11 | 93 / 93 / 59 / 56 | 100 / 100 / 78 / 77 |
| **all 114** | 119946 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 26 / 25 / 24 / 11 | 90 / 88 / 70 / 61 | 99 / 97 / 86 / 81 |

mixed ratio (spread 0.5)

| image | strings | r=0.8 | r=1.0 | r=1.2 | r=1.5 | r=2.0 |
|---|---|---|---|---|---|---|
| MEETING | 7548 | 23 / 0.0 / 0.0 / 0.0 | 48 / 0.1 / 1 / 0.1 | 65 / 56 / 32 / 0.1 | 82 / 80 / 65 / 15 | 99 / 99 / 99 / 44 |
| NEWS | 3702 | 21 / 0.1 / 0.2 / 0.1 | 46 / 0.1 / 2 / 0.1 | 64 / 27 / 31 / 0.2 | 82 / 67 / 66 / 7 | 99 / 99 / 96 / 38 |
| TRAINING | 2791 | 23 / 13 / 13 / 13 | 45 / 25 / 27 / 26 | 67 / 63 / 53 / 52 | 83 / 78 / 76 / 76 | 99 / 99 / 97 / 96 |
| DRAFT | 1563 | 22 / 0.1 / 0.1 / 0.1 | 49 / 0.3 / 3 / 0.3 | 65 / 40 / 32 / 17 | 80 / 64 / 61 / 44 | 97 / 97 / 88 / 70 |
| ATFIRST/HELP | 700 | 27 / 0 / 0.1 / 0 | 48 / 36 / 2 / 1 | 63 / 57 / 30 / 29 | 80 / 74 / 62 / 59 | 98 / 98 / 97 / 88 |
| HELP | 700 | 27 / 0 / 0.1 / 0 | 48 / 2 / 2 / 1 | 63 / 55 / 30 / 29 | 80 / 76 / 62 / 59 | 98 / 98 / 97 / 88 |
| SCDRF | 861 | 20 / 0.1 / 0.2 / 0.1 | 44 / 0.3 / 1 / 0.3 | 60 / 49 / 29 / 28 | 78 / 70 / 61 / 59 | 96 / 95 / 92 / 88 |
| EVENT | 2606 | 7 / 0.1 / 1 / 0.1 | 29 / 0.2 / 4 / 0.2 | 46 / 22 / 14 / 13 | 69 / 52 / 41 / 40 | 88 / 88 / 65 / 65 |
| NEWS_ED | 2047 | 7 / 0 / 0.1 / 0 | 28 / 0.0 / 1 / 0.0 | 45 / 14 / 11 / 3 | 68 / 48 / 37 / 29 | 87 / 87 / 64 / 55 |
| GAME | 1137 | 18 / 5 / 6 / 5 | 40 / 11 / 16 / 11 | 57 / 46 / 37 / 35 | 76 / 64 / 64 / 63 | 94 / 93 / 89 / 89 |
| SPF_READ | 3987 | 1 / 0.0 / 0.1 / 0.0 | 14 / 2 / 3 / 2 | 34 / 13 / 16 / 15 | 58 / 54 / 41 / 41 | 80 / 79 / 66 / 66 |
| ESTABLIS | 1798 | 4 / 0 / 0 / 0 | 24 / 0 / 1 / 0 | 42 / 4 / 6 / 4 | 66 / 52 / 32 / 30 | 87 / 87 / 60 / 56 |
| **all 114** | 119946 | 6 / 0.4 / 1 / 0.4 | 22 / 3 / 3 / 2 | 40 / 22 / 17 / 12 | 63 / 56 / 43 / 36 | 83 / 82 / 68 / 62 |

Reading (honest): the existing `insert_image` (a2) already pools freed space (its strategy B), so for mixed lengths with mean
<= 1.0 it is nearly as good as repacking (game-wide 3 % of strings at r=1.0 for a2 and b0, 2 % for b2). Repacking beats it where
a pool is over capacity (mixed r=1.2 game-wide 22 % -> 17 % -> 12 % with sharing; NEWS_ED 14 -> 11 -> 3; MEETING 56 -> 32 -> 0.1;
uniform r=1.2 NEWS_ED 28 -> 25 -> 6), and its output is contiguous, deterministic and has a proof (`check`). a2 is also
erratic: ATFIRST/HELP at mixed r=1.0 fails 36 % under a2 but 2 % for the identical-size HELP copy and 1 % under repack.
Where nothing helps: TRAINING (1,570 of 2,791 strings are fixed), GAME, HELP/DRAFT prose without duplicates.

### Headline: ratio at which each overlay starts to overflow (movable strings, `results/thresh_table.tsv`)

Largest English/JP byte ratio with zero overflowing movable string (bisection, step 0.005). `A` per-string, `B0` pool-local,
`B1` + cross-pool, `B2` + duplicate sharing. Suffix 0 = uniform ratio, 5 = mixed spread 0.5 (`B5`=pool-local, `B5x`=+cross,
`B5d`=+sharing). `slack` = pool slack %, `dup` = pool-local duplicate bytes as % of JP bytes.

| image | strings | pools | pool bytes | slack % | dup % | A0 | B0 | B1 | **B2** | A5 | B5 | B5x | **B5d** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MEETING | 7521 | 32 | 376541 | 0.04 | 24.2 | 1.001 | 1.001 | 1.005 | **1.330** | 0.669 | 0.820 | 1.001 | **1.333** |
| NEWS | 3693 | 93 | 303031 | 0.19 | 29.6 | 1.001 | 1.001 | 1.001 | **1.438** | 0.669 | 0.705 | 1.005 | **1.442** |
| DRAFT | 1555 | 29 | 120421 | 1.51 | 3.4 | 1.001 | 1.005 | 1.012 | **1.048** | 0.676 | 0.911 | 1.008 | **1.044** |
| ATFIRST/HELP and FLOW_PRG/HELP | 683 | 7 | 109794 | 0.02 | 0.8 | 1.001 | 1.001 | 1.001 | **1.005** | 0.669 | 0.762 | 0.983 | **0.994** |
| TRAINING | 1221 | 72 | 109725 | 0.22 | 0.3 | 1.001 | 1.001 | 1.001 | **1.001** | 0.669 | 0.705 | 0.994 | **0.994** |
| SCDRF | 835 | 29 | 72991 | 0.28 | 0.3 | 1.001 | 1.001 | 1.001 | **1.001** | 0.669 | 0.762 | 1.001 | **1.005** |
| EVENT | 2577 | 300 | 75722 | 5.45 | 0.0 | 1.001 | 1.008 | 1.041 | **1.041** | 0.672 | 0.683 | 1.052 | **1.052** |
| NEWS_ED | 2042 | 83 | 62419 | 3.98 | 10.9 | 1.001 | 1.001 | 1.041 | **1.171** | 0.669 | 0.737 | 1.026 | **1.164** |
| GAME | 861 | 146 | 53017 | 1.28 | 0.0 | 1.001 | 1.001 | 1.005 | **1.005** | 0.669 | 0.690 | 1.012 | **1.012** |
| ESTABLIS | 1798 | 40 | 39249 | 5.90 | 3.3 | 1.001 | 1.001 | 1.066 | **1.080** | 0.672 | 0.817 | 1.077 | **1.113** |
| SPONSOR / SPONSOR2 | 1756 | 58 | 31797 | 7.55 | 1.2 | 1.001 | 1.001 | 1.080 | **1.080** | 0.672 | 0.737 | 1.062 | **1.073** |
| SCHE0 / SCHE1 | 1810 | 82 | 30553 | 9.36 | 0.0 | 1.001 | 1.008 | 1.080 | **1.080** | 0.679 | 0.737 | 1.120 | **1.120** |
| LOCAL | 1752 | 35 | 28656 | 7.94 | 0.0 | 1.001 | 1.001 | 1.080 | **1.080** | 0.672 | 0.762 | 1.095 | **1.095** |
| YOUTH | 731 | 29 | 26266 | 0.71 | 26.5 | 1.001 | 1.005 | 1.008 | **1.380** | 0.676 | 0.809 | 0.965 | **1.341** |
| NEWS_OP | 314 | 58 | 25521 | 0.82 | 0.8 | 1.001 | 1.001 | 1.001 | **1.005** | 0.669 | 0.737 | 1.019 | **1.030** |
| SPF_READ | 1891 | 62 | 23679 | 10.83 | 0.0 | 1.001 | 1.001 | 1.088 | **1.088** | 0.669 | 0.734 | 1.102 | **1.102** |
| PL_EDIT | 1723 | 121 | 21399 | 16.40 | 0.6 | 1.005 | 1.005 | 1.135 | **1.164** | 0.669 | 0.799 | 1.171 | **1.182** |
| DRSLIST | 579 | 27 | 16187 | 1.19 | 24.2 | 1.008 | 1.008 | 1.012 | **1.337** | 0.676 | 0.697 | 0.958 | **1.319** |
| WEEKLY | 1612 | 83 | 16603 | 14.89 | 0.0 | 1.008 | 1.008 | 1.185 | **1.185** | 0.687 | 0.701 | 1.171 | **1.171** |
| TOWN | 1600 | 63 | 16129 | 15.07 | 0.0 | 1.008 | 1.008 | 1.185 | **1.185** | 0.687 | 0.705 | 1.171 | **1.174** |

Distribution over the 113 images with movable strings (JP-byte weighted mean in brackets): A0 min 1.001, median 1.005 (1.002);
B0 median 1.005 (1.003); B1 median 1.048 (1.039); **B2 median 1.080 (1.168), max 1.438**; no image has B2 <= 1.0.
Mixed spread 0.5: A5 median 0.687 (0.676; 107 of 113 images already overflow below mean ratio 1.0); B5d median 1.120 (1.167),
27 of 113 images below 1.0.

Game-wide sum bound (capacity / JP bytes, if English could move freely between all pools): 1.042 without sharing, 1.150 with
pool-local sharing, 1.160 with image-wide sharing.

Game-wide including fixed strings (`game_s*.json`, ratio grid step 0.05, first ratio at which overflowing English bytes
exceed X % of all English bytes): uniform: every mode first overflows between 1.00 and 1.05 (fixed strings, section 6); with
sharing > 50 % of English bytes overflow only from 1.35. Mixed 0.5: > 5 % at r=0.7 (a), 1.0 (b0/b1), 1.05 (b2); > 25 % at
0.85 / 1.1 / 1.25; > 50 % at 1.05 / 1.3 / 1.5.

## 6. Where the space is NOT

* Fixed strings: 37,960 strings (505,232 JP bytes in 680,927 bytes of slots; 37,885 orphans = 502,973 bytes of name records and
  packed prose). Uniform r=1.2: 2,443 (6.4 %) overflow, r=1.5: 30,835 (81.2 %). Repacking cannot touch them (UNKNOWN: how
  orphans are addressed).
* Dead space adjacent to pools: unreferenced ASCII-only runs (>= 6 chars) number 15,420 / 158,531 bytes, but samples
  (`b/Cn"c`, `$r,32a`, `Ccb,3cbca`) are code/data bytes that happen to be printable, and only 393 bytes of them touch a pool
  (341 after, 52 before; dead.py). Referenced ASCII (library debug/format text) is 17,066 runs / 333,956 bytes, ~2.9 KB per
  overlay, not reclaimable without proving the referencing code dead (UNKNOWN). Conclusion: no usable dead space.
* Pool slack is only 94,348 bytes (4.03 %): repacking makes it donatable, it does not create it.
* Duplicates: 210,694 bytes pool-local (228,481 image-wide). Suffix sharing +10,982 bytes. Orphans are not dead
  (index-addressed prose / name records), so they are not counted as reclaimable.

## 7. Integration notes for the synthesis agent

* Replace the FLOW_PRG/ATFIRST call of `textdb.insert_image` by
  `textrepack.repack(img.data, img.base, recs, source=src, share='dup', cross_pool=True)`. Report fields: `rep.overflow`
  (reverted to Japanese, with deficits), `rep.fixed_overflow`, `rep.skipped`, `rep.moved`, `rep.shared_saved`, `rep.pools`.
  `repack(extracted=...)` reuses `extract_image` output. Output size == input size.
* Remaining overflow still needs extra room (append / other memory, other agents); `repack` makes the existing 2.34 MB of pools
  one budget per pool and gives exact deficit numbers.
* `share='none'` gives the layout without any sharing assumption.

## 8. Risks and the dynamic tests that settle them

| risk | status | test |
|---|---|---|
| strings are only read, never written (needed to share identical strings) | UNKNOWN (dialogue text is compiled when a dialogue opens: INFERRED read-only) | build with `share='dup'` for MEETING/NEWS, play events/news; plus a Flycast memory-write watchpoint over the pool ranges (`report.pools`) during menus/events |
| hidden pointers (relative offsets, 16-bit literals, pointers from other images) | UNKNOWN. Scans: 0 words of `1ST_READ.BIN` equal any movable string address; 480 aligned words equal a string *offset* >= 0x10000 (206 are multiples of 0x1000, buffer-size style constants such as 0x40000, 0x70300; relscan.py), none shown to be an offset | **forced identity build**: `repack(..., force=True)` with no translation for CLUBEDIT/MEETING/NEWS/EVENT (every pool rewritten, text equivalent) and play through them; any garbled/missing text means a hidden pointer |
| `max_bytes` "full" padding absorbs real zero data | INFERRED harmless (safe mode loses only 0.04 % capacity) | same forced build with `pad_mode='safe'` if the full build misbehaves |
| moved untranslated strings change address | design choice (pool packed back-to-back) | covered by the forced identity build |

Reproduce: `python -I -X utf8 tools/re/capacity/pool/analyze.py` (pools.json), `sim.py grid|thresh` (env `SPREAD`, `PAD`, `SKIP_A2`),
`game.py`, `report_grid.py`, `report_thresh.py`, `dead.py`, `relscan.py`, `safepad.py`, `mdtables.py`.
