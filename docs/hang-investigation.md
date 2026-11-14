# Hang on the new-game Event screen (prop7): investigation and bisect procedure

Owner `hng`, 2026-11-11.  Static analysis, simulator runs and builds only; nothing was launched in an emulator.
Symptom (user, first playtest of `build/trial/prop7`): after the draft screen the next Event screen (1 Yr 1 Mo Wk1st, header `5 Oku 7400 Man`, secretary
visible, empty message window) never offers the scout choice.  `trial_prop3` / `trial_prop4` passed the same point.

**Integrator update (2026-11-12): read section 8 first.**  The junk records of section 0 are now blanked in the database and in prop8; the disc table in section 4 (bis_a .. bis_n) is
SUPERSEDED: bis_f .. bis_n were deleted and bis_a .. bis_e were rebuilt from the fixed tree (digests in section 8).  The decision tree of section 5 still applies, with the discs and rebuild commands named in section 8.

**Result (hang owner, before section 0): the cause is NOT found statically.  Every candidate class that could be checked by execution passed.  The shortest path is the disc bisect in section 5.**

## 0. Skeptic review (owner `skh`, 2026-11-11, later the same evening): a real code overwrite was found; test `skh_fix1` FIRST

**Finding.**  Section 2.6 treated the placeholder records (`Bow`, `Plot`, `Misc`, `-`, `?`) as "binary DATA decoded as cp932".  Some of them are **machine code**.
`tools/re/skh_orig_diff.py prop7 FLOW_PRG/EVENT.BIN 0 0x80000 --records` shows that `FLOW_PRG/EVENT.BIN#dbf2` (orphan `敬ツ` -> `Bow`, no pointer) is written into the
code of EVENT itself.  Original bytes `8c 68 83 63` = `extu.b r8,r8 ; mov r8,r3` (file 0xdbf2, load 0x8c2ddbf2) become `42 6f 77 00` = `mov.l @r4,r15 ; mul.l r7,r0`.
0xdbf2 is the branch target of `cmp/eq #6,r0 ; bf` at 0xdbce / 0xdbd0 (r0 = r11, a state variable of a UI state handler), so the corrupted pair runs whenever that
handler is entered with state != 6, and the first instruction **loads the stack pointer r15 from memory at r4**.  A wrong r15 is a crash or a freeze, and an
event screen that "shows the secretary, an empty message window and never offers the scout choice" is exactly what a broken menu handler looks like.  This has been
in every build since 2026-11-10 13:40 (`hng_hist.py`), including prop4, so it is NOT proven to be the regression; prop3 / prop4 may simply never have entered that
state (not known).  It is a definite defect whatever the hang turns out to be.

Code-zone overwrites found with `tools/re/skh_codezone.py` (records below the lowest pointer-referenced text of the file) and checked by disassembly:
`EVENT#dbf2 Bow`, `NENREP#162 Out R4` (the first instructions of NENREP, `mov.w @(..),r0 ; mov #52,r2 ...`), `NEWS_ED#b99 Home`, `YOUTH#4d9e -`, `ENDING#29fb9 Cma`,
`NEWMONTH#40290 Pact`, `NEWMONTH#84ad6 P/L` (the last three look like data).  The other 400 or so placeholders (`-` over `覧藍楓舶` and its five siblings in every overlay,
`?` over `促ぅ`, `チＡ` ... in OFFICE, `----` in CSAVE3, `Plot` / `Misc` in EVENT's player tables) overwrite 16-bit data tables.  432 records in 66 files in all
(`tools/re/skh_mkskip.py --dry`).

**Recommendation of 2.6 was wrong in one detail:** `"skip": true` is only a merge / extract hint (`tools/textdb.py` line 770 is the only reader; the build does not
look at it), so marking these records `skip` changes nothing.  The build keeps the original bytes only when `en` is EMPTY.  `skh_mkskip.py` therefore sets both.

**Consequence for the bisect of section 5: every `bis_*` disc contains the same overwrites (they come from the DB, not from an optional class).**  If the overwrite is the
cause, ALL fourteen discs hang and the bisect tells nothing.  Boot `build/trial/skh_fix1/skh_fix1.gdi` first:

* `skh_fix1` = standard flags (`--repack on --share dup --append-safe --proportional-font on --strict`), money jp, guard on, 235+ textures, and a copy of the DB
  (`build/skh/tdb`, made by `tools/re/skh_mkskip.py`) in which the 432 junk orphan records have `en = ""` and `skip: true`.  The real `translation/` is untouched.
  The DB is the repository state of about 22:25 (concurrent text-owner edits included; `BCAST__BCAST.BIN.jsonl` left out because it is a new source that is not
  on this path), so it is not byte-for-byte prop7 with the junk removed: against prop7 it also carries the money owner's newer cave (`1ST_READ.BIN` +274 bytes
  changed, a 2 byte edit in every hooked overlay) and the art owner's newer textures (N_ENTRY, SCHE1, SHINJIN, TOWNSEL).  Built 22:3x, 0 failed, 0 skipped,
  `verify_disc` OK (0 errors, 0 warnings), 85 texture files, 368,492 records of which 366,712 with English, patch digest `28dfb306641f08484c1b0f00c62d6f4581becc02`.
  From the disc bytes: `EVENT.BIN` 0xdbf2 is the original `extu.b r8,r8 ; mov r8,r3` again, no orphan record is applied in EVENT, NENREP, YOUTH (`skh_orig_diff.py`); the
  EVENT composer run, the CRC check and `hng_discprobe.py` pass on it.
* `skh_fix1` fine -> the code overwrite was (at least part of) the hang; the text owner makes the same blanking permanent (empty `en` for the 432 records, or better
  a build rule: refuse to write an orphan record whose original bytes are not text).  `skh_fix1` hangs -> go back to section 5 but build the bis discs from
  `build/skh/tdb` (`--tdb build/skh/tdb`) so that they do not carry the overwrite.

**What the skeptic re-checked and agrees with:** `hng_texdec.py` (LOADBAR sample re-run: the real bz decoder in `sh4sim` reproduces the data, 10 s); the diff of `prop7`
against `bis_e` (`tools/re/skh_discdiff.py prop7 bis_e --quiet`, 183 files): `1ST_READ.BIN` differs only in the money cave (0x289a00..0x289b6d), every overlay only in the
12 byte money hook (+ 3 bytes of `%D` literal), EVENT additionally in the composer (214 bytes at 0x29440), HOMETOWN / CSAVE3 composer only; every other differing file is a
texture container; nothing unintended.  Every changed ZSARC member has the right payload CRC16 and header CRC (`tools/re/skh_crc.py prop7`: 36 files, 219 members, 0
regressions).  The EVENT copy of the club-name composer, which `fin_clubs.py` never ran (it runs BPMATCH and HOMETOWN), passes the same exhaustive run on the real
bytes of the disc (`tools/re/skh_evclubs.py prop7`: 142,670 runs, 0 problems, robustness 0, longest name 13).  The `$N` buffer size is still unknown.

New helper scripts (prefix `skh`, read-only on the project): `skh_discdiff.py`, `skh_orig_diff.py`, `skh_codezone.py`, `skh_orphans.py`, `skh_orphan_census.py`, `skh_mkskip.py`
(writes only below `build/skh`), `skh_crc.py`, `skh_evclubs.py`, `skh_texpng.py`, `skh_findlit.py`, `skh_litrange.py`.

## 1. What differs between prop4 and prop7 (reconstructed from `build/trial_prop4.log`, `build/trial/prop7.log`, `tools/re/hng_logdiff.py`, the DB snapshots `build/hnm_bak` and `tools/re/hng_dbdiff.py`)

| class | prop4 (12:40) | prop7 (20:34) |
|---|---|---|
| proportional font (98 overlays, cave 0x8c299800) | on | on, identical |
| money cave + 102 hooks + `%D` ASCII + TV card routine | **western** style, 428 B | **jp** style (Oku / Man), 368 B; TV card text starts at x=440, 32 byte buffer |
| layout patches in 20 overlays (town_short no cut, pref_short, `%s %s`) | yes | yes |
| club-name guard (composer body replaced in place, 20 overlays; HOMETOWN popup join) | **no** | yes |
| textures | **none** | 235 textures in 85 files (ETC_DATA 195, EVENT 9, FLOW_PRG 22 incl. 7 inside overlays, GAME2/TRAINING) |
| pool repack | `--repack on --share dup --append-safe` | same flags; only the text changed |
| text | DB of about 12:21 | 11,901 en changes: 359 town short forms per overlay (3,424 strings), HOMETOWN 657, ESTABLIS 387 (rewrap), INVEST 368, 57 money re-wraps (DRAFT 8, RECON 3, NEWCON 1, GETREP 8, MON_INST 5 ...), SEARCH 5 label pads, `Oku` literals (EVENT 2, JSCEVENT 1) |
| disc dedupe, prop-scale, refit, hw-relocate, grow-overlays | off | off |
| files changed / sectors rewritten | 119 / 22,185 | 197 / 31,381 (0 files moved, end LBA unchanged) |

EVENT.BIN text changed only in 2 money strings and the 360 town forms; DRAFT changed only in 8 re-wrapped money messages.  Token check of all 366,989 English
records (`hng_tokens.py`, `hng_markers.py`): no printf token reordered, no lost `=w/` frame, `$N`, `@X/` span (only 16 `#tkNN#` reorders, which are legal).

## 2. Evidence gathered

1. **Textures, real game decoders.**  `tools/re/hng_texdec.py` runs the game's own LZ decoders (1ST_READ `FUN_8c15a9f4` bz, `FUN_8c15aae4` bzw) in `sh4sim` on every
   compressed stream of all 235 installed textures (member level and record level): **229 streams, 229 identical to the intended data and to the Python port, 0 bad**
   (`build/hng_texdec.log`; the other 6 records are stored raw).  So a bad stream, wrong length or missing end token is ruled out.  Not ruled out: VRAM / texture slot budget,
   a texture the screen loads in a way the table walk does not show.
2. **Money cave in real contexts.**  Calling convention is the one of prop4's western cave (same hook, same registers, r8-r13 and PR saved, r14 untouched, no NUL written, same
   as the original).  `int_disc_money.py` on `bis_b`: 14 sample values correct from disc bytes.  EVENT has 3 direct callers (`hng_moneycallers.py`): the `$N` argument case at
   0x1aaa (dst = `table[0x8c42a4c4][idx]`, length stored, NUL written by the caller), a right-aligned panel text at 0xbb5e (dst = static 32 byte buffer 0x8c348cd4, **the length
   is used to position the text** = cause of the clipped `1 Oku 300 Man` on the draft panel, a layout problem, not a hang) and a helper at 0x27f20 (stack buffer sp+8, 20 bytes).
   **Residual risk: output length.**  jp text is 15 chars for 2-digit Oku (16 for 3-digit Oku, 20 worst) against at most 8-9 for western and 14 bytes for the Japanese original;
   a caller buffer sized for the Japanese maximum (16 or less) overflows at 16+ chars (not reached at funds of 5 Oku).  The size of the `$N` buffers was not found (the table is
   filled at run time).  This is the only way the jp cave differs from the western one.
3. **Club guard.**  Composer is a leaf-compatible replacement: pushes r8-r14 and PR, balanced frame (76 + 32), returns the length in r0, 5th argument read from `@(108,r15)`,
   exhaustively run before on real overlays (142,670 runs, 0 problems, `docs/layout-issues.md` 9.5).  EVENT's single call site (the `$N` club case, 0x1936) writes into the same
   `$N` buffers; the guard only ever writes 13 chars + NUL, fewer than the original.  Nothing wrong found.
4. **TV card routine** lives only in `TV_EVENT.BIN`; the hang screen is not a TV card.  Not involved by evidence of the screen description (not excluded as an overlay load).
5. **Proportional font wrap** is identical to prop4 and has no word wrap (no loop possible); unchanged since prop4.
6. **Pre-existing hazard (NOT a regression, present in every build since 2026-11-10 13:40, see `tools/re/hng_hist.py`)**: 520 DB records are placeholder English (`-`, `Plot`,
   `Misc`, `Bow`) for "orphan" Japanese that is really **binary data decoded as cp932** (`覧藍楓舶`, `錘緒訣鵠刻瑞錘誌`, `麹倹月`, `克試緒`, `荘荘`, `賄謀`, `趨慧` ...): 6 of them in every one of
   about 100 overlays (the statically linked library's data), plus EVENT 0x124113 and 0x13b5fb (player stat tables: bytes `9f 62 68 6d ..`, `8c 8d 90 ..`).  The build writes `-` + NUL over
   9 to 17 bytes of that data.  Prop4 booted past the same screen with them, so they are not the regression, but they are data corruption and should be `skip: true`
   (`tools/re/hng_junk.py` lists them; `hng_orphans.py EVENT.BIN orphan` shows EVENT's 27 orphans).  Recommend to the text owner; to be tested as a separate disc after the bisect.
7. Build hygiene: other owners edited `tools/moneypatch.py` (a "compact" `M` form, cave now 388 B), `build_patch.py` and `SCDRF` / `SEARCH` text while the bisect discs were built.  The discs
   built before 21:35 hold the prop7 jp cave (368 B); `bis_i` onward were built after the SCDRF / SEARCH text edit at 21:32 (label pads only).  Digests per disc: `hng_bisreport.py`.

## 3. Hypotheses, ranked (before the bisect)

| # | hypothesis | for | against / check |
|---|---|---|---|
| H1 | jp money text longer than a fixed destination or window (`$N` buffers, panel code that positions by returned length, DRAFT / NEWCON confirm messages that were re-wrapped) | it is the only difference of the money class, funds / contracts are exactly what changed on screen before the hang | cave and callers pass; buffer size unproven; bis_f / bis_i discriminate |
| H2 | club guard in EVENT (`$N` club case) | EVENT is the overlay of this screen | exhaustive simulation clean; writes less than the original; bis_g |
| H3 | a texture the Event screen loads (BAR.TBD header, TV_EVENT.ZAR, SHTEX*, EVENT/E003, overlay-embedded SEARCH / LOADBAR) breaks loading or VRAM | 85 files are new vs prop4, the empty message window could be a failed load | decoders verified, sizes exact; bis_h then j, k, l, m |
| H4 | text change in a script-visible record (town forms in EVENT's tables, re-wrapped DRAFT messages) | EVENT is a bytecode VM fed by these tables | only town names and 2 money strings changed in EVENT; cannot be toggled, only seen if bis_e / bis_n hang |
| H5 | something not in this list (disc layout, junk-record corruption of binary data) | - | bis_n and the junk skip test |

## 4. Discs (all `build/trial/bis_*/`, each 0 failed, 0 skipped, `verify_disc` OK; logs `build/trial/bis_*.log`; contents proven from disc bytes by `tools/re/hng_discprobe.py`)

Standard flags `--repack on --share dup --append-safe --proportional-font on --strict` unless noted.  Build scripts: `tools/re/hng_build_bis.sh`, `hng_build_bis2.sh`, `hng_build_bis3.sh`.

| disc | contents | digest |
|---|---|---|
| bis_e | everything optional OFF: `--money-format off --club-guard off`, empty textures dir (text, prop font, town/club layout steps remain) | 375910d112 |
| bis_a | prop7 with `--money-format off` | 45899acbcd |
| bis_b | prop7 with `--club-guard off` | 91353a1177 |
| bis_c | prop7 with an empty textures dir | d3ba792bb3 |
| bis_d | prop7 with `--proportional-font off` | 4984b0f0eb |
| bis_f | bis_e + jp money ON | 3ea41f362b |
| bis_g | bis_e + club guard ON | 6ae52e1401 |
| bis_h | bis_e + all 235 textures | f2c6557927 |
| bis_i | bis_e + `--money-style western` (the money code of prop4) | 0aca6b9360 |
| bis_j | bis_e + 7 overlay-embedded textures (ESTABLIS LOADBAR NEWCON RECON SCDRF SEARCH YOUTH) | 25dbb70928 |
| bis_k | bis_e + EVENT/ textures (E003.DAT, REPORT.DAT) | ded49d3b5a |
| bis_l | bis_e + ETC_DATA/ and ATFIRST/ textures (195: BAR, SHTEX*, TV_EVENT, PLATE ...) | 0b5abc8c1a |
| bis_m | bis_e + GAME2/, TRAINING/, FLOW_PRG/*.ZAR textures (22, incl. DRAFT.ZAR) | 604ccb1ed8 |
| bis_n | bis_e + `--proportional-font off` (text + town/club-format layout only) | f3ff390c6f |

Texture subsets were copied from `translation/textures` into the session scratch dir (`t1`..`t4`; 9 + 9 + 195 + 22 = 235 files).

## 5. Test procedure (each test: new game, name, hometown, draft, reach the next Event screen, does the scout choice appear?)

1. **bis_e.**  Hang here -> the cause is text, prop font or the town/club layout steps (all present in prop4 except text): go to 2.  No hang -> go to 3.
2. (bis_e hangs) **bis_n.**  No hang -> proportional font on the new text.  Hang -> text itself or the junk records: build a disc with the 520 junk records skipped (section 2.6) and, if still hanging, bisect the text by `--only`.
3. (bis_e fine) add one class: **bis_f** (jp money), **bis_g** (guard), **bis_h** (textures).  Whichever hangs is the class; if none hangs alone, test **prop7 leave-one-out** bis_a, bis_b, bis_c (an interaction).
4. bis_f hangs -> run **bis_i** (western money, prop4's code).  bis_i fine confirms output length (H1); fix = shorter text / compact `M` form / larger buffers (money owner).
5. bis_h hangs -> bis_j, bis_k, bis_l, bis_m (each one subset); then halve the guilty subset (move files between `translation/textures` copies and pass `--textures-dir`).
6. bis_g hangs -> the guard in EVENT: report to the integrator; the guard can be restricted to the other 19 overlays.

Expected cost: 3 to 5 boots.

## 6. For the other owners

* money: a destination-size audit of the `$N` buffers (table 0x8c42a4c4 in EVENT, filled at run time; dump it once in an emulator) and the right-aligned panel at EVENT 0xbb5e (positions by returned length).  The 15+ character jp text is the one behavioural change of the money class.
* text: skip the junk placeholders (`hng_junk.py`); they overwrite binary tables.
* integrator: do not publish until bis results exist; concurrent edits of `moneypatch.py` / `build_patch.py` mean any new disc needs a fresh digest.

## 7. Helper scripts (prefix `hng`, all read-only on the project)

`hng_build_bis*.sh` (discs), `hng_bisreport.py` (table from logs), `hng_discprobe.py` (what a disc really contains), `hng_texdec.py` (game decoders on every texture), `hng_logdiff.py`
(two build logs), `hng_dbdiff.py` / `hng_hist.py` / `hng_rec.py` (DB snapshots), `hng_tokens.py` / `hng_markers.py` (token checks), `hng_junk.py` / `hng_orphans.py` (placeholder
records), `hng_moneycallers.py`, `hng_dis.py`, `hng_peek.py`, `hng_lit.py`, `hng_litrange.py`, `hng_find.py`, `hng_grep_m.py`, `hng_cavecmp.py`.

## 8. Integrator, 2026-11-12: what changed after the first playtest

* The first playtest (prop7) hung on the second Event screen (1 Yr 1 Mo Wk1st).  prop8 is the new candidate; whether it still hangs is **unknown** (nothing was booted).
* **Junk records.**  The 432 orphan records of section 0 have `en = ""` and `skip: true` in `translation/*.jsonl` (`tools/re/int_blankjunk.py`; the 66 changed files were copied to `build/int/db_bak/` first).
  `build_patch.do_overlay` now FAILS (so `--strict` stops) any orphan record with a placeholder English (`is_junk_orphan`); `tools/test_junk.py` checks the database.
  Read back from the discs: `EVENT.BIN` 0xdbf2 is the original code in prop8 and in bis_e (`tools/re/skh_orig_diff.py DISC FLOW_PRG/EVENT.BIN 0xdb00 0xdd00 --records`: 0 ranges); `NENREP.BIN` 0..0x400 is unchanged in prop8.
* **Panel overflow (H1b of the money owner).**  In prop8 and bis_b / c / d the 4 call sites in SCDRF / SEARCH pass the compact flag (`mov #77,r6`, `tools/re/skm_panel.py build/trial/prop8 prop8`); bis_a and bis_e have no money patch at all.
* No definite bug was found in `tools/moneypatch.py` or `tools/layoutpatch.py` by the hang owner or the skeptic, so no change was made there.  Checks re-run on the fixed tree: `moneycheck --quick` 0 failures, `test_moneypatch_tv` OK, `test_layoutpatch` ALL PASSED,
  club-name composer exhaustive on the real overlays of prop8 (BPMATCH, EVENT; HOMETOWN through `fin_clubs.py`): 142,670 runs each, 0 problems.
* The old discs bis_f .. bis_n were deleted (built before the junk fix; they carried the overwrites).  The scripts `hng_build_bis2.sh` / `hng_build_bis3.sh` rebuild them from the current tree if the decision tree of section 5 needs them
  (`sh tools/re/hng_build_bis2.sh build/int/empty_tex` builds f .. i; the subsets `t1`..`t4` of j .. m must be recreated, section 4).  `build/int/empty_tex` is the empty textures directory.

Discs of this pass (standard flags + `--strict`, all 387,649 applied, failed 0, skipped 0, `verify_disc` OK 0 errors 0 warnings; logs `build/trial/<name>.log`):

| disc | contents | files changed | digest |
|---|---|---|---|
| prop8 | standard: jp money (cave 388 B, panel compact), guard, 235+ textures, prop font, BCAST, gap strings, junk blanked | 198 | b0e9515ba2 |
| bis_e | `--money-format off --club-guard off`, empty textures dir | 119 | fa31474634 |
| bis_a | prop8 with `--money-format off` | 198 | 733af1b481 |
| bis_b | prop8 with `--club-guard off` | 198 | 4fcb9a2f03 |
| bis_c | prop8 with an empty textures dir | 119 | 354a1db9c8 |
| bis_d | prop8 with `--proportional-font off` | 196 | 4d7301018e |

Boot order and the exact steps: `docs/playtest-checklist.md` section 0.  If bis_e hangs and prop8 hangs, the junk overwrite was not the (only) cause and the cause is in text, BCAST-independent layout steps or the proportional font:
the next discs to build are `bis_n` (`hng_build_bis3.sh`) and a per-source `--only` bisect of the text.
