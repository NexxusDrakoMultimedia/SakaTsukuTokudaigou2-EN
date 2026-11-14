# Status report (integrator)

**Current state (2026-11-12, after the first playtest): NOT releasable.**  The first playtest of `build/trial/prop7` found a hang and a list of visible defects (section 0).
Sections 1 to 8 below are the end-of-stage-3 report of 2026-11-11 and describe prop7; where they say "ready" or "nothing known", section 0 overrides them.

Everything in this file was measured in this run unless it says "recorded".  Nothing was launched in an emulator, committed, published or uploaded.
"In game" below means "seen on screen in Flycast"; nothing after `trial_prop3` has been seen on screen except by the user's one prop7 session.

## 00. Stages 8a to 8d: complete BCAST commentary and the final trial disc prop10c (2026-11-12 evening)

**State: still not released; nothing of this section was seen on screen.**  The last disc played is `hsk_full1`; the disc to play next is `build/trial/prop10c.gdi` with the sheet `docs/test-sheet-prop10.md`.
Nothing was committed, tagged, published or launched in an emulator.  Stage 8a merged all 30,083 BCAST commentary records (four voices: announcer `yh` 7,498, colour commentators `kk` 3,518, `mt` 3,320, `mm` 3,267, plus 12,480 name callouts) into `translation/BCAST__BCAST.BIN.jsonl`; none is empty.
The earlier discs prop10a and prop10b were superseded and deleted.  Stage 8d (corrections after the user confirmed the staff reading via Sega Retro) produced prop10c: it differs from prop10b in `/GAME/STAFFLST.ZAR` (2 sectors: the credit texture `s_murayama` now reads `Sunao Murayama`, repainted with the same generator, font, size and colours as its 40 siblings, with a 1 px shadow offset because the 2 px shadow does not fit the 1,400-byte slot; ink 2..110 of 128 px) and `/BCAST/BCAST.BIN` (1 sector: `#1de96880` now reads `World Sports Festival Qualifiers`, the refit overlay line was removed); every other file, the directory records and the track geometry are byte-identical (`build/trial/prop10c_vs_b.log`, prop10b deleted).  The stage 8b integration notes below were measured on prop10a.

| What | Where | State |
|---|---|---|
| **prop10c**, built with `--repack on --share dup --append-safe --proportional-font on --strict` only (the defaults add `--refit on --align-fix on --tag-fix on`; the log `flags:` line shows refit, align-fix, tag-fix, money-format on) | `build/trial/prop10c.gdi` (+ `.cue`, five track files), log `build/trial/prop10c.log` | 396,819 strings applied (206,327 in place, 190,492 relocated), failed 0, skipped 0; the 1,785 untranslated records are not BCAST (all 30,083 BCAST records have English); texture rows failed 0; `verify_disc` OK; 334 files changed, 0 moved, end LBA 549150; patch digest `e7543242860a638a07c0945da573e34885828e5d`; 215 s; `zsarc_crc_audit` 0 stale, `artcoverage` MISSING only 02213 02214 03570 03571, 38,390 refit records modified |
| BCAST | build log `bcast /BCAST/BCAST.BIN applied=30083 in_place=30083 relocated=0 failed=0 skipped=0` | 30,083 of 30,083 segments English (prop10a: 20,914).  Read back from the built disc (`build/s8c_bcast_readback.py`, `build/trial/prop10c_bcast_readback.log`): all 30,083 equal the database English (stage 8d: the one refit-overlay exception was removed), 0 over the 75-byte budget, 0 non-ASCII bytes, longest line 74 characters; stratified sample of 357 in `build/trial/prop10c_bcast_sample.txt` |
| ZSARC audit | `tools/zsarc_crc_audit.py build/trial/prop10c.gdi` (`build/trial/prop10c_audit.log`) | 164 files, 2,482 members, **0 stale** (hsk_full1: 44 files, 521 members, 0 stale) |
| Art coverage | `tools/artcoverage.py --log build/trial/prop10c.log` (`build/trial/prop10c_artcov.log`) | NOT APPLIED 0; MISSING only the four blank frames 02213 02214 03570 03571; texture rows with failed>0: 0 |
| Duplicate copies | `build/s8i_dupcheck.py` | the 478 texture files written since 02:00 are all applied; 348 copy sets have exactly one file per copy (477 physical textures) |
| Read-back of the code patches (re-run on prop10b: `build/s8c_readback.py`, 0 problems) | `build/s8i_readback.py`, `tools/re/skp_discsim.py` | align cave = `align_bytes`; CAP_SLCT / ENDOPT / EVENT 20 `nop` + 8 `pw3` each; 11 short-name routines = `layoutpatch.tag_routine`; shirt-number digit x0 + 180 / 168 |
| Cheap suites (stage 8b run on prop10a; re-run in stage 8c on prop10b: `test_bcast` 9, `test_textdb`, `test_texinject` 427 checks, `test_alignfix` 19, `test_tagfix`, `test_layoutpatch`, `test_bldflags` 60 checks, `test_gap` 9, `test_l10n` 36, all exit 0, `build/s8c_suites/`; `test_pipeline` not re-run) | `build/s8i_suites/` | `test_sh4sim` 15, `test_patchengine` 26, `test_layoutpatch` ALL PASSED, `test_alignfix` 19, `test_texinject` 427 checks, `test_textdb` 0 failures, `test_moneypatch_tv` 16, `test_bcast` 9, `test_l10n` 36 (no `--full`), `test_gap` 9, `test_tagfix` 96 checks, `test_zsarc_crc_audit`, `test_bldflags` 55 checks, `fontcheck --quick`: all OK |

`tools/test_pipeline.py` was run once at the end (it writes its scratch disc to `build/out`, as it always did): tests A to F passed (99 checks); G (money) stopped on two expectations that predate the mn6 money work, not on a defect:
the changed-bytes check of ABROAD.BIN (the number-library stub and pool words of the `money.lib*` owners were not in the allowed set) and the "1ST_READ.BIN differs only in the cave" check (the two wrappers `money.lib` / `money.libn` in the tail were not
allowed).  Both were widened to the declared edits of those owners (`MPT.overlay_edits` owners `money.lib*`, spans of `lib_bytes()` / `libn_bytes()`), every other changed byte is still refused, and G + the repack tests were re-run: 261 checks, 0 failed.
`tools/test_release.py`: 206 checks OK.  Also widened (said here on purpose): `tools/test_bldflags.py` jp-versus-western bound 4 -> 64 patch bytes per overlay.

What changed in the tools: `--align-fix on|off` and `--tag-fix on|off` (both default ON), `--refit` default ON, `flags:` line, flag-combination errors, `--strict` exit 2 with a stderr reason (`docs/pipeline.md` 9, 9.10, 9.11);
`tools/release.toml` `[build] standard_flags` = `--repack on --share dup --append-safe --proportional-font on --refit on --align-fix on --strict`; `layoutpatch.tag_patches`; `tools/zsarc_crc_audit.py`.
Text: `OPTION.BIN` `Advance Schedule` / `Quit / Options`, `PLNUMSET#34b74` ` Squad No.%2d`, `G_INCOME#26490` `man`, `NENREP#24ef8` and four new gap records (`@R/%soku %sman@` ...).
Trial discs: everything older than prop10c except `hsk_full1` was deleted (prop10a in stage 8c, 1.2 GB; the 103 older entries, 43 GB, in stage 8b, `build/s8i_clean.log`); `bis_summary.txt` and `tvc_dump` were kept (not disc sets).

Open for the user: ordinal `th`; `Mid Defence` / `Midfield Defence`; `Rd` / `MD`; the five low-confidence staff readings; tag window width (limit 7, alternatives 5 / 6); `Grampus` vs `Grampus Eight`; `European XI` / `World XI` vs `EURO` / `WORLD` on plates.
Not done: the black name boxes and `CF` overlap of Player Placement, the black rectangle above `4-4-2`, the annual report attendance formats (`%s万%s人`), the `OPTION.BIN` cell width check, any release.

## 0. After the first playtest of prop7 (integrator, 2026-11-12)

### 0.1 What the user saw (prop7, standard flags)

| # | Finding | Status in prop8 |
|---|---|---|
| a | attract demo / match overlay: commentary box Japanese (`なるほど。放送席、解説は水沼貴史さん ...`); HOME / AWAY label `静観` | commentary box: FIXED in the build (new source `/BCAST/BCAST.BIN`, 20,914 of 30,083 segments English, the rest Japanese); NOT seen on screen.  `静観`: **NOT fixed**, not text anywhere on the disc, so it is a sprite nobody has found yet |
| b | Name Entry tabs `ABC/123`, `Symbols`, `Confirm` clipped | repainted inside the old ink extents (03541); NOT seen on screen |
| c1 | Hometown header money `15億0000 Man` (億 sprite Japanese) | 億 cell repainted `Oku` in all five textures that hold it (BAR, LOADBAR, YOUTH, YOUTH.ZAR#5, TOWNSEL#0); NOT seen |
| c2 | Hometown data panel Japanese | the panel comes from TOWNSEL.TBD#0 (04077), not TOWNDATA#1 (04073); 04077 repainted; NOT seen |
| c3 | `O` of `Oku` reads like a zero (`1 0ku 8500 Man`) | **NOT fixed, needs a decision** (section 0.5) |
| d1 | Event panel `Oku 300 Man` with the leading `1 ` clipped | cause found: the info panel code right-aligns the money text in a 12-byte field and the English text is 13 bytes; fixed by a compact form (`1 Oku 300M`, 10 bytes); proven on the disc bytes and in the SH-4 simulator; NOT seen |
| d2 | `Centre P` truncated, `Left Side` lost a letter | the five style labels are right-aligned to the 12-cell window (`Centre Push`); NOT seen |
| d3 | black rectangle above `4-4-2` | **NOT found.**  No art change makes an opaque black or transparent area; most likely a label drawn from text or a control code on that panel.  Needs a screenshot of the same screen on prop8 |
| d4 | `Wants 2 yrs`, `Age`, `Chiba` | layout of the same panel; not examined separately, look at it again on prop8 |
| e | **hang** on the next Event screen (1 Yr 1 Mo Wk1st) | **cause not proven.**  Best lead found: 432 mis-decoded "orphan" records overwrote DATA and CODE (section 0.2).  Fixed in prop8, NOT booted |

### 0.2 The best lead for the hang: records written over machine code

`FLOW_PRG/EVENT.BIN#dbf2` (Japanese orphan, English `Bow`) was written into the code of EVENT: the original `extu.b r8,r8 ; mov r8,r3` became `mov.l @r4,r15 ; mul.l r7,r0`,
a load of the stack pointer from memory, at the target of a state-handler branch.  That is exactly what a screen with a secretary, an empty message window and no scout menu looks like.
The same class of record (`-`, `Plot`, `Misc`, `Bow`, `?`, `----` over binary data decoded as cp932) wrote over 16-bit data tables in 66 files; 432 records in all.
It is **not proven** to be the hang: prop4 contained the same overwrites and passed the same screen (`docs/hang-investigation.md` section 0).

What was done (integrator): the 432 records have `en = ""` and `skip: true` in `translation/*.jsonl` (`tools/re/int_blankjunk.py`, backups of the 66 changed files in `build/int/db_bak/`);
`build_patch.py` now refuses an orphan record with a placeholder English (`is_junk_orphan`, counted as failed, so `--strict` stops the build); `tools/test_junk.py` guards the database.
Written-over bytes in prop8: EVENT 0xdbf2 is the original code again (`tools/re/skh_orig_diff.py prop8 FLOW_PRG/EVENT.BIN 0xdb00 0xdd00`: 0 ranges), NENREP 0..0x400 unchanged (0 ranges).
About 2,600 other applied orphan records remain (`tools/re/skh_orphan_census.py`: 34,829 table-stride records = names and similar, 2,241 "other", 373 short kanji = place names); they were not audited one by one.

### 0.3 The second suspect (money panel overflow)

The scout info panel code in SCDRF and SEARCH wrote a 13-byte money text one byte before its 12-byte field (a 15-byte text would reach b[34..36], a flag and a geometry byte that the same function uses).
prop3 and prop4 (western money, at most 9 bytes) never did this; prop7 did for every salary with an Oku and a Man part.  The compact-form fix (4 bytes changed per overlay) is in prop8
and was read back from the disc (`tools/re/skm_panel.py`: 4 sites).  Also unproven as the hang.  Not audited: the size of the `$N` message buffers of EVENT (table 0x8c42a4c4, filled at run time); the jp money text (up to 20 characters) is the only behavioural difference of the money class.

### 0.4 Artefacts of this pass

| What | Where | State |
|---|---|---|
| **prop8**: standard flags + `--strict` | `build/trial/prop8/prop8.gdi` (+ `.cue`), log `build/trial/prop8.log` | 387,649 strings applied (388,081 of the stage minus the 432 blanked records), failed 0, skipped 0; `verify_disc` OK (0 errors, 0 warnings); 198 files changed, 0 moved, end LBA 549150; patch digest `b0e9515ba27831d1a89934aebdd691ebfdce9be2`; 169 s |
| bisect discs, rebuilt from the fixed tree | `build/trial/bis_a` .. `bis_e` (+ `.log`, `build/trial/bis_summary.txt`) | see section 0.6 for contents and digests; each 0 failed, 0 skipped, `verify_disc` OK |
| prop7, prop7r | `build/trial/prop7`, `prop7r` | unchanged, the discs of the first playtest (they have the junk overwrites and no panel fix) |

Deleted this pass (superseded by prop8, all contents are in prop8): `ar5a`, `tx5_p7`, `skx_gap`, `skh_fix1`, `bis_f` .. `bis_n` (the old bisect set, built before the junk fix).  Kept: prop6, prop6r, prop7, prop7r, hwr_on, skep_tv1.

What prop8 contains on top of prop7: the BCAST subtitle text (20,914 segments), the 23 missing overlay strings (`textfmt_gap`, year-end report and others), the five right-aligned style labels, 235 textures + the 04077 / 03541 / 03587 repaints (art coverage below),
the compact money form on the info panel, the permanent junk blanking.  The refit variant (`prop8r`) was not built.

### 0.5 Decisions the user has to make

1. **`O` versus `0`.**  In the game font the half-width `0` and `O` are the same oval (original FONT.BIN: pixel difference 338 of about 1,290 ink).  `1 Oku 8500 Man` reads `1 0ku 8500 Man`; `tools/re/skm_render.py` renders it into `build/skm/money_glyphs.png`.
   The glyph tile is 12 px wide, there is no room to draw a different capital.  Lower-case `oku` / `man` read fine in the same render.  The change would be: the two unit constants in the money cave (`s_oku`: ` Oku` = 0x756B4F20 -> ` oku`, ` Man` -> ` man`), `moneypatch.reference()`, the tests and the literal `Oku` / `Man` strings in the database, and the Oku / Man sprites (they say `Oku`, `Man` today).
   Not done because it is a house-style decision (project rule: keep the Japanese flavour of the units) and because it touches art and text together.
2. **Shrink `Oku` / `Man` to `O` / `M`** where space is tight (the user's idea).  Only `Man` -> `M` is done and only on the scout panel (`13 Oku 1500M`).  `1O 300M` was rejected by the money owner because `O` and `0` look the same.  A per-string selector `%M` exists in `moneypatch` (default OFF, no record uses it).
3. Honorifics / name order, licence, the commit and tag: unchanged from section 6.

### 0.6 Bisect discs (rebuilt from the fixed tree; use them only if prop8 still hangs)

Standard flags + `--strict`; the junk records are blanked in all of them, so a hang in one of them is not the junk overwrite.

| disc | what is switched off relative to prop8 |
|---|---|
| bis_e | everything optional: `--money-format off --club-guard off`, no textures.  Text, proportional font, town / club layout steps, BCAST and the gap strings remain |
| bis_a | `--money-format off` (original Japanese money code) |
| bis_b | `--club-guard off` |
| bis_c | no textures (empty textures directory) |
| bis_d | `--proportional-font off` |

Digests: see `docs/hang-investigation.md` section 8.  A bisect that needs more than these five (jp money alone, guard alone, texture subsets, western money, prop font off on top of bis_e) uses `tools/re/hng_build_bis2.sh` and `hng_build_bis3.sh` (about 3 minutes per disc; `docs/hang-investigation.md` section 5).

### 0.7 Coverage and test numbers of this pass

* Art (`tools/artcoverage.py --log build/trial/prop8.log`): 206 ids, 239 physical copies, 237 `.pvr` files present, **0 not applied**, texture rows with failed > 0: 0.
  **Missing (no `.pvr`): 7**: FACEMDUL 00056 / 00062 / 00065 (single red kanji tiles in a bind-style file the injector does not list), G_INCOME 02213 / 02214 (blank tables), PLATE 03570 / 03571 (blank plates).  Two `.pvr` files are not tied to a listed id (JSCEVENT#0, LOC_GAME#0).
  Not covered at all: the sprite behind `静観`, the black rectangle above `4-4-2`.
* Text: BCAST is now complete (30,083 of 30,083 segments English in prop10b, stage 8a; the figures 20,914 / 69.5 % elsewhere in this file describe the older prop7 / prop8 discs).  `NENREP#237fd` stays Japanese (tail pointer inside a character).
* Tests, all `python -I -X utf8`: `tools/re/fin_runtests.py` (23 test files, including the new `test_bcast`, `test_gap`, `test_junk`): **0 of 23 failed** (test_textdb 0 failures, test_transwork 789 checks, test_release 205 checks, test_layoutpatch ALL PASSED, test_moneypatch_tv OK, test_refit all passed, test_discbuild ALL PASSED, ...).
  `tools/moneycheck.py --quick`: 0 failures.  Club-name composer exhaustive on the real overlays of prop8 (`tools/re/fin_clubs.py build/trial/prop8 prop8`, `tools/re/skh_evclubs.py prop8` for EVENT): 142,670 runs per overlay, 0 problems, 0 odd shapes, longest 13 (BPMATCH, HOMETOWN, EVENT).
  (`skh_evclubs.py` also prints a HOMETOWN line with problems: that overlay uses a different calling convention that the script does not model; `fin_clubs.py` is the authoritative HOMETOWN check.)
  `tools/test_pipeline.py`: first run failed one check, `G: /FLOW_PRG/SCDRF.BIN differs outside the hook bytes` (the test did not know the 4 panel flag edits; fixed in the test, same fix as `moneycheck`); see section 0.8 for the second run.

### 0.8 test_pipeline.py second run

It ran three times, not once: run 1 and run 2 failed the same check `G: /FLOW_PRG/SCDRF.BIN differs outside the hook bytes / %D literal`.  The first fix (reading a `panel` key from `find_sites`) was wrong because only `overlay_edits` fills it; the second reads `MPT.panel_sites(old, r[1] + st['off'])` and passes.  Run 3: **351 checks passed, 0 failed**, 352 s (log `build/int/pipeline_test.log`; the failed runs are `pipeline_test_run1.log`, `pipeline_test_run2.log`).  The two "FAILED" lines inside that log are expected output of tests about failing strings.  After the doc edits `test_release` (205 checks), `test_junk` and `test_gap` were re-run: all pass.

### 0.9 What is still unverified (everything)

Nothing of prop8 has been seen on screen.  Specifically: whether the hang is gone; the commentary box (wrapping at column 37, how consecutive clips join, a word broken mid-word); the 12-cell panel alignment; the Hometown panel; Name Entry; the year-end report joins; the `$N` buffer sizes; 432 junk-orphan records is the number found by the placeholder heuristic (the hang owner's earlier count was 520 placeholder strings; the difference to 432 was not reconciled), other mis-decoded data may remain (about 2,600 other applied orphan records were not audited).

---

# Section 1 to 8: the end-of-stage-3 report (2026-11-11, prop7)

## 1. Final artefacts

| What | Where | State |
|---|---|---|
| Trial disc, standard flags + `--strict` | `build/trial/prop7/prop7.gdi` (+ `.cue`) | 366,989 strings applied, failed 0, skipped 0; `verify_disc` OK (0 errors, 0 warnings); patch digest `7c5bf437...`; 102 s |
| Trial disc, `--refit on` | `build/trial/prop7r/prop7r.gdi` (+ `.cue`) | same counts; refit 38,188 records, 0 skipped, 0 problems; `verify_disc` OK; digest `561355ac...`; 148 s |
| Stage-3 discs before the polish, kept for comparison | `build/trial/prop6`, `prop6r` | untouched |
| Dev release bundle (not a release) | `build/release_dev2/SakaTsuku2-EN-0.1.0-dev/` and `.zip` (23,294,686 bytes for the first build; the zip was rebuilt after the guide edit and has SHA-256 `9085c46c...`) | built from prop7 WITHOUT `--allow-placeholder`; contains `TRANSLATORS_NOTES.md` (byte-identical to `doc/TRANSLATORS_NOTES.md`) |
| Dev hashes | `tools/release.toml` `[dev.prop7]` (track 3 `64eec15d...`, track 5 `6e15e5e8...`, volume ISO `cc872a43...`) | recorded; `release.py` says "MATCH the built disc" |

Standard flags (both discs): `--repack on --share dup --append-safe --proportional-font on --strict`; prop7r adds `--refit on` (which forces `--hw-relocate on`).
Club-name guard, club dot, money text (jp style) and the layout patches are on by default.  The end LBA of the disc is unchanged (549150, 0 sectors of headroom to the GD-ROM ceiling, 6431 free sectors inside the data tracks).

Disk: the older trial discs `int1, trial_prop, trial_prop2, trial_prop3, trial_prop4, trial_plain, trial_plain2, trial_plain3, gunnew, gunbase, hnm_trial, tvc_card, skv_trial, skv_trial2` (disc files only) and the folders `prop5`, `prop5r` were deleted (about 18.6 GB freed).  Kept: `prop6`, `prop6r`, `prop7`, `prop7r`, `hwr_on`, `skep_tv1` (not in the delete list) and all logs.

## 2. Tests run in this pass (all with `python -I -X utf8`)

| Test | Result |
|---|---|
| `tools/test_pipeline.py` (once) | 351 checks passed, 0 failed |
| `tools/re/fin_runtests.py` (all 20 other `test_*.py`) | 0 of 20 failed: test_arttext ALL OK; test_bincue2iso all passed; test_bldflags 39/0; test_bzlib 95/0; test_discbuild ALL PASSED; test_discbuild_dsc ALL PASSED; test_hwreloc all passed; test_layoutpatch ALL PASSED; test_moneypatch_tv OK; test_patchengine OK; test_pvr 0 failures; test_refit all passed; test_release 175/0 (final, after the `[dev.prop7]` table was added); test_sh4sim OK; test_texinject 273/0; test_textdb 0 failures; test_textrepack 0 failures; test_transwork 668/0; test_uncovered all passed; test_vcdiff 135/0 |
| `release.py` dev bundle from prop7 | all patches re-applied with `vcdiff.py` AND xdelta3, both equal to the built file (track 3: 253 bytes, track 5: 18,898,420, volume ISO: 15,667,924); track 3 and 5 rebuildable from the patched ISO |
| bundle `verify_dist.py` (folder only) | all checks passed |
| bundle `verify_dist.py --source <repo cue> --built prop7.cue` (scratch deleted after) | 81 PASS, 0 FAIL.  Input forms: BIN/CUE (route A and route B), BIN/CUE `--to iso`, GDI (route A and `--method iso`), cooked volume ISO; every output has the promised hash and is byte-equal to the built disc; `--verify` says original / already patched; the source tracks are untouched |

`test_release` and the two doc counts changed from 174 to 175 only because `release.toml` gained a table.

## 3. Club-name exhaustive check on the real overlays (`tools/re/fin_clubs.py`)

`BPMATCH.BIN` and `HOMETOWN.BIN` were read out of the built discs themselves (not from a `--dump`) and run through the SH-4 simulator with the real patched composer
(`pol_shapes.py`, independent `skp_census.py`, `int_clubs.py` with the HOMETOWN popup join).

| | prop7 | prop7r |
|---|---|---|
| composer runs (every town + word pair, modes 0/1, every prefecture + word pair, modes 2/3) | 142,670 | 142,670 |
| problems | 0 | 0 |
| **odd shapes** (`. .`, `-.`, `..`, ` .`, `- `; independent census: any non-letter in the town part, doubled blank or dot, leading or trailing blank, hyphen, digit) | **0** | **0** |
| town forms that are not letters-only (optional trailing dot) | 0 of 1,248 | 0 of 1,248 |
| pairs cut | 32,343 of 68,640 (47.1 %) | 33,615 of 68,640 (49.0 %) |
| longest composed name | 13 characters | 13 characters |

HOMETOWN popup join: 0 problems on both.  The 916 odd cut results of the earlier stage (`N. . Topolino`, `Minami-. Arpe`) are gone (`docs/layout-issues.md` 9.9).

## 4. Conflicts resolved in this pass

* Odd club-name cuts: `docs/style-guide.md` 12.2, `docs/playtest-checklist.md` section 3, `docs/expansion/status.md`, `doc/TRANSLATORS_NOTES.md` section 8 now say "fixed" with the final numbers (47.1 % / 49.0 %, 0 odd shapes).
* Playtest checklist now names prop7 / prop7r instead of prop6 / prop6r; `docs/pipeline.md` section 9, `docs/RELEASING.md` and `docs/xdelta-release.md` name the `[dev.prop7]` record and the deleted prop5 discs.
* Dan ranks run 1 to 9 (style guide corrected; the guide already said 9).
* `docs/helper-scripts.md`: skp, fin rows added, skd count corrected.
* The shipped guide is the real text; `release.py` no longer needs `--allow-placeholder` (not used for the dev bundle).
* Honorifics and name order: NOT resolved, see section 6 item 1.

## 5. What is unverified in game (nothing from stage 3 has been seen on screen)

Booted and looked at in Flycast earlier (`docs/playtest-log.md`): the proportional-font trial discs up to `trial_prop3`.  Everything added after that has only simulator, byte-level and tool proof:

1. The money text (Oku / Man formatter, 102 overlays hooked) and the repainted art (235 textures, groups 1 to 7), including the TV station card and the header bar units.
2. The club-name guard: the real size of the destination buffers (the guard assumes 14 bytes), whether the popup clips a 13-character name, and that the neighbouring struct field at 0x1048 stays intact (`docs/layout-issues.md` 9.7).
3. The polished town short forms (107 forms, 32 files): the Hometown list still shows its own text for the same Japanese, NENREP keeps its own copy, AUTOSAVE `Hachin.` and EVENT `Okushi.` are slot-forced.  Several short forms are blunt prefixes (`Higashishi`, `Higashiyam` for two different towns, `Shimoag`).
4. Relocation of half-width pointer strings and the refit overlays (prop7r only, 38,188 records): no boot test of this combination.
5. `--prop-scale` (no disc has it), overlay growth and shared file extents (off by default, never booted).
6. The name-entry tab: the guide says the English letters are on the fourth of five tabs and are full-width; this rests on one early playtest note only.
7. Data-room screens that still use western sprintf money formats (`%s億%s万円` family, INVEST, GAME, `%d円`): a few may show plain yen (`docs/number-formats.md` sections 5 and 9).
8. Strings the guide names but the DB does not confirm as in-game text: `Emperor's Cup`, `Akan-gun`, `Oshima-cho`, `People (10k)`.
9. The hashes in `release.toml` (Redump 27370 as dumped) were not compared with Redump itself; the GDI route was only exercised on a synthetic GDI built from the repo tracks, not on a real GDI dump.

## 6. Decisions only the user can make

1. **Honorifics and name order.**  The user's decision is that these stay Japanese and are explained in the notes.  The build does the opposite: 0 occurrences of -san, -kun, -sama, senpai in any `en` field, and people are `Given Family` (`Katsuo Ozaka`, short forms `K. Ozaka`).  The guide (section 4) describes what the build does.  Switching to Family Given and re-adding honorifics is a translation-wide edit plus a width re-check of every name field (names have 14-byte slots); it was not attempted unattended.  `docs/style-guide.md` has an OPEN note.
2. **Licence of the translated text and the repainted art.**  The tooling is GPL-3.0-or-later; the guide says only that text and art ship inside xdelta deltas for use with the player's own disc.  Choose a licence (or none) before publishing.
3. Whether to bundle `doc/CHANGELOG.md` into the release (it needs `release.py` and `verify_dist.py` changes; the FAQ in the guide says it lives in the source tree).
4. The `Toshima` collision (village `Toshima` now equals the Tokyo ward form; `Toshimamura` would fit, 32 files) and whether to give the Hometown list the fused forms.  Cosmetic.
5. `--date` and `tools/VERSION` for a real release (`0.1.0-dev` now), and the `git commit` (the repo still has no commit; the manifest records `null`).

## 7. What to do next in Flycast (ordered)

Use only `tools/emu/launch.ps1` on DISPLAY3 as the playtest checklist says; hash marks around text are a texture-filter artefact, ignore them.  Walk `docs/playtest-checklist.md`.

1. Boot `build/trial/prop7/prop7.gdi`.  Title screen, new game, first week: does it boot and run without a freeze (proves the 3,424 changed town strings and the polished overlays did not break loading).
2. Money: header bar, a finance / data-room screen, a contract window, the TV station card (`13 Oku 1500 Man`, `6000 Man`, `0 Yen`; capital at x=440 to 624).  Report any plain-yen amount.
3. Club-name guard: create a club with a long town and a long word (for example Tsurugashima + Palentia, expect `Tsu. Palentia`), open the Hometown list and popup, the schedule, the save slots.  Report any name that is clipped, overlaps, or shows `. .` / `-.` / `..` (expected: none).
4. Name entry: confirm which tab holds the English letters and that typed names fit; check a player name on a card (`Given Family`) against the long-name rows.
5. Art groups 1 to 7: spot-check the ids listed in section 5 of the checklist (header bar, ranks `1st Dan` to `9th Dan`, tabs, the repainted texts).
6. Boot `build/trial/prop7r/prop7r.gdi`, repeat steps 1 to 5 and compare screen by screen with prop7 (section 8 of the checklist).  prop7r is the one that tests relocation and the refit overlays; a hang in a menu that is fine on prop7 is the main thing to look for.
7. If anything shows `?`, garbage or Japanese where English is expected, note the screen and the pair, then run `tools/re/fin_clubs.py` or `docs/uncovered-text.md` to see whether it is known.
8. Only after 1 to 6 are clean: decide section 6 (licence, honorifics and name order), set `tools/VERSION`, make the first commit, then `release.py` without `--allow-placeholder` and the standard flags, and `verify_dist.py --source ... --built ...` as `docs/RELEASING.md` section 4 says.
