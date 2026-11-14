# Repository audit before the first commit

Date: 2026-11-11.  Scope: what a first `git add -A` would contain, whether it is safe and sensible to publish, and what must be decided first.
Everything here was measured read-only (`git status`, `git ls-files --others --exclude-standard`, file reads).  Nothing was committed, tagged, pushed or downloaded.
The only file changed by the audit is `.gitignore` (section 3); this document is the other.

## 0. Status of 2026-11-15 (what is resolved since this audit was written)

The sections below are the audit as written on 2026-11-11 and are kept as the record; this block says what has been settled since.

* **Repainted textures (D2): decided.**  Deltas only ("Deltas, VQ as-is").  `l10n/textures/` holds 637 VCDIFF deltas + `MANIFEST.tsv` (about 3.2 MB, `tools/texdelta.py`, `docs/texture-delta.md`);
  `translation/textures/` (the full repainted PVRs, 637 files) is git-ignored; original art that is unchanged must not be in the repository.  The 236 VQ textures (not 14: that figure was
  counted on the earlier 237-texture set) carry a re-quantised codebook in their delta; accepted as is and documented as a known point (README.md, `docs/texture-delta.md` section 10).
* **Windows user-name paths (absolute paths under the Windows Users folder): resolved** (section 4, scrubbed 2026-11-14; a search of the files that would be committed finds none; `tools/release.py` refuses a bundle that contains one).
* **Original-art pictures (D3): decided.**  `docs/art-sample/club_edit_menu_before.png`, `_sheet.png` (original pixels on the left half) and `_after.png` (our lettering on the game's own background) and
  `tools/re/art6/plate_menu.png` (a strip of the original plate) are git-ignored and regenerated locally; `docs/art-sample/preset_gallery.png` (synthetic background, our own lettering) and
  `tools/re/art6/p37300a.png`, `p37300b.png` (flat colour stripes) stay.  Nothing was deleted from disk.
* **E-mail address: decided.**  `nexxus@nexxusdrako.au` is the project's public contact and is intended to appear as the git author; it stays in the files and in the git config (section 4).
* **Wording:** README and bundle text now say "no original Sega pixels; textures are shipped as binary deltas against the owner's own dump" instead of "no game data".
* **Still open:** D1 (the Japanese `ja` fields stay in the git-ignored working form; the committed form is `l10n/`), D4.

## 0.1 Summary (2026-11-11)

* **Git state**: branch `main`, no commits, remote `origin` = `https://github.com/NexxusDrakoMultimedia/SakaTsukuTokudaigou2-EN.git` (already configured, never pushed), `user.name` = `Pyra Drake`, `user.email` = `nexxus@nexxusdrako.au`.
* **Bug found and fixed in `.gitignore`**: the old rule `*.bin` is matched case-insensitively on this machine (`core.ignorecase=true`), so it silently ignored **7 folders (9 repainted textures)** named `translation/textures/FLOW_PRG/*.BIN/`.  A first commit would have lost them.  The rules are now anchored (`/*.bin`).
* **Certain game data is now ignored**: the five disc tracks (1.11 GiB), the `.cue`, `extracted/` (363 MiB), `build/` (41 GiB), `dist/` (13 MiB), caches, scratch, `.remember/`.
* **After the ignore rules, `git add -A` stages 1,475 files, 122,693,672 bytes (117 MiB)**: nothing over 4 MB, no file near GitHub's 100 MB limit.
* **Not certainly safe, so not decided here**: the Japanese source text in `translation/*.jsonl` (the whole game script, 3.07 million characters in 406,673 records) and the 235 repainted textures (`.pvr`, derived from original art).  See "DECISIONS NEEDED" (section 2).
* **No secrets** (no tokens, keys, passwords, credentials).  **Personal data**: 24 absolute paths containing the Windows user name (scrubbed, see section 4) and a few `D:\` paths; the author e-mail address is still in this file (decision pending).
* **Two statements in the public text are not accurate until the decision is made**: `README.md` says "No game data is in this repository" and `REUSE.toml` says the `.jsonl` files are CC-BY-SA-4.0 while they carry the original Japanese strings (see 2.4).

## 1. What a first `git add -A` contains now

Counts are after the `.gitignore` changes of section 3 (the repository root also has the new `CHANGELOG.md`, `LICENSES/` and `REUSE.toml`, written by other owners during the audit).

| Top-level path | Files | Bytes | What it is |
|---|---:|---:|---|
| `translation/*.jsonl` (+ `glossary.tsv`) | 119 | 67,165,226 | translation database: id, **ja**, en, max_bytes, refs, ctx, fmt, ... (2.1) |
| `translation/textures/` | 235 | 33,586,528 | repainted textures as PVR, one folder per source container (2.2) |
| `translation/refit/` | 78 | 5,923,132 | opt-in short forms; every record also carries **ja** (2.1) |
| `translation/art/` | 7 | 19,676 | repaint specs (JSON, a few Japanese labels) |
| `tools/` (top level, 91 files) | 91 | 1,514,552 | the pipeline: build, patch, disc, release, tests |
| `tools/re/` | 879 | 13,028,832 | research helpers (2.5) |
| `tools/emu/` | 10 | 57,219 | Flycast launch and Lua scripts |
| `docs/` (incl. `art-sample/`, `expansion/`) | 47 | 1,314,432 | documentation, 4 PNG screenshots (2.6) |
| `doc/`, `README.md`, `CHANGELOG.md`, `LICENSE`, `LICENSES/`, `REUSE.toml`, `.gitignore` | ~12 | ~130,000 | project files |
| **Total** | **1,475** | **122,693,672** | about 117 MiB; git compresses the JSONL well |

By extension: `.jsonl` 73.2 MB (194 files), `.pvr` 33.6 MB (235), `.txt` 4.8 MB (164), `.tsv` 4.7 MB (14), `.py` 2.7 MB (699), `.json` 2.2 MB (53), `.md` 0.9 MB, `.png` 0.5 MB (7), `.pkl` (now ignored).

### The 40 largest files that would be committed

| # | bytes | path |
|---|---:|---|
| 1 | 3,726,571 | `tools/re/capacity/verify_memory/scan_sizes_out.txt` |
| 2 | 3,565,051 | `translation/FLOW_PRG__SPF_READ.BIN.jsonl` |
| 3 | 3,257,593 | `translation/FLOW_PRG__DMCLBEDT.BIN.jsonl` |
| 4 | 3,254,603 | `translation/FLOW_PRG__BPMATCH.BIN.jsonl` |
| 5 | 3,246,974 | `translation/FLOW_PRG__AUTOSAVE.BIN.jsonl` |
| 6 | 3,234,836 | `translation/FLOW_PRG__EXTRADE.BIN.jsonl` |
| 7 | 3,225,084 | `translation/FLOW_PRG__ENDOPT.BIN.jsonl` |
| 8 | 3,215,335 | `translation/FLOW_PRG__CSAVE4.BIN.jsonl` |
| 9 | 3,212,816 | `translation/FLOW_PRG__EXFLAG.BIN.jsonl` |
| 10 | 3,195,353 | `translation/FLOW_PRG__CSAVE.BIN.jsonl` |
| 11 | 3,180,766 | `translation/FLOW_PRG__LOAD.BIN.jsonl` |
| 12 | 2,930,728 | `translation/FLOW_PRG__BACKUP.BIN.jsonl` |
| 13 | 2,787,899 | `translation/FLOW_PRG__CSAVE3.BIN.jsonl` |
| 14 | 2,534,704 | `tools/re/datatext/texinv.tsv` |
| 15 | 2,474,290 | `translation/FLOW_PRG__CHALMODE.BIN.jsonl` |
| 16 | 2,401,031 | `translation/FLOW_PRG__SONGSAVE.BIN.jsonl` |
| 17 | 2,399,299 | `translation/FLOW_PRG__FREELOAD.BIN.jsonl` |
| 18 | 2,387,008 | `translation/FLOW_PRG__VTRLOAD.BIN.jsonl` |
| 19 | 1,897,415 | `translation/FLOW_PRG__MEETING.BIN.jsonl` |
| 20 | 1,847,382 | `tools/re/datatext/survey3.tsv` |
| 21 | 1,178,467 | `translation/FLOW_PRG__NEWS.BIN.jsonl` |
| 22 | 1,001,669 | `translation/FLOW_PRG__PL_EDIT.BIN.jsonl` |
| 23 | 999,041 | `translation/FLOW_PRG__TRAINING.BIN.jsonl` |
| 24 | 933,193 | `translation/FLOW_PRG__PLNUMSET.BIN.jsonl` |
| 25 | 734,747 | `translation/ETC_DATA__BPINFO.BIN.jsonl` |
| 26 | 673,173 | `translation/FLOW_PRG__EVENT.BIN.jsonl` |
| 27 | 656,675 | `translation/FLOW_PRG__HOMETOWN.BIN.jsonl` |
| 28 | 524,320 | `translation/textures/TRAINING/TRAINING.TBD/#4.pvr` |
| 29 | 524,320 | `translation/textures/TRAINING/TRAINING.TBD/#0.pvr` |
| 30 | 524,320 | `translation/textures/GAME2/SS_EDIT.TBD/#0.pvr` |
| 31 | 524,320 | `translation/textures/FLOW_PRG/YOUTH.ZAR/youth.tbd#5.pvr` |
| 32 | 524,320 | `translation/textures/FLOW_PRG/YOUTH.BIN/@36114#0.pvr` |
| 33 | 524,320 | `translation/textures/FLOW_PRG/LOADBAR.BIN/@1ec#0.pvr` |
| 34 | 524,320 | `translation/textures/ETC_DATA/TOWNSEL.TBD/#0.pvr` |
| 35 | 524,320 | `translation/textures/ETC_DATA/TOWNDATA.TBD/#1.pvr` |
| 36 | 524,320 | `translation/textures/ETC_DATA/SUPPORT.ZAR/pvr.tbd#0.pvr` |
| 37 | 524,320 | `translation/textures/ETC_DATA/SS_TEX.ZAR/SS_TITLE.TBD#0.pvr` |
| 38 | 524,320 | `translation/textures/ETC_DATA/SELNAT.TBD/#0.pvr` |
| 39 | 524,320 | `translation/textures/ETC_DATA/PL_EDIT.ZAR/PL_PT4.TBD#0.pvr` |
| 40 | 524,320 | `translation/textures/ETC_DATA/PL_EDIT.ZAR/PL_PT3.TBD#0.pvr` |

Ranks 1-24 are JSONL / TSV text; ranks 25-40 are 512 x 512 PVR textures of 524,320 bytes (the largest possible texture, all repainted).  Nothing here approaches the 100 MB per-file limit, and the 235 textures plus 194 JSONL files total 107 MB, so the repository would be roughly 117 MiB in the working tree and far less compressed.

## 2. Inventory by category, and what to do

Typical practice for fan translation repositories: ship **patches as deltas** (xdelta / IPS / BPS) and keep the repository to tooling and the translator's own work.  A full dump of the source text or the extracted game files is usually avoided because it is the publisher's copyrighted work; translation tables that contain the source strings are common but are the part most likely to draw a takedown.

### 2.0 Certain game data: never commit (now ignored)

| Path pattern | Size | Contents | Typical in repos? | Recommendation |
|---|---:|---|---|---|
| `/Sakatsuku ... (Track 1..5).bin` | 1,193,447,136 B (1.11 GiB) | original disc tracks (the player's own dump) | never | **ignore** (`/*.bin`) |
| `/Sakatsuku ... (Japan).cue` | 832 B | cue sheet of the original dump; names the tracks, no game data in itself | no | **ignore** (`/*.cue`); the expected hashes live in `tools/release.toml` |
| `extracted/` | about 363 MiB (371,170 KiB) | every file read out of the disc: `1ST_READ.BIN`, `2_DP.BIN`, `FONT.BIN`, `.ZAR`, `.TBD`, `.PVR`, audio, models | never | **ignore** (`/extracted/`) |
| `build/` | about 41 GiB (43,247,493 KiB), 316 entries | trial discs (`build/trial`, `iso`, `iso_test`), decoded textures (`build/tex` 1.3 GB, `textures`, `texindex.*`), `skv_dump`, `hnm_dump_t4`, release scratch (`release`, `release_dev*`), emulator captures (`emu`), per-art work folders (`art*`), logs | never | **ignore** (`/build/`) |
| `dist/` | 13 MB | release bundle `SakaTsuku2-EN-0.1.0-dev/` (3 xdelta patches, hashes, bundled README) and its `.zip` + `.sha256` | patches are normally attached to a GitHub release, not committed | **ignore** (`/dist/`, `*.zip`, `*.xdelta`, `*.sha256`); upload on release day |
| any `.gdi` `.iso` `.img` `.cdi` `.chd` `.raw` at root; `*.zar` `*.tbd` `*.mlt` `*.afs` `*.adx` `*.wav` `*.ram` `*.dump` `*.sav` `*.vms` `*.vmu` anywhere outside `translation/textures/` | none today | copies of game assets or emulator dumps | never | **ignore** (rules added; verified none exist in the staged set) |
| `*.pvr` outside `translation/textures/` | none today | decoded or raw game textures | never | **ignore** (rule added; `translation/textures/` is explicitly re-included, see 2.2) |
| `tools/re/datatext/png/*.png` (14 files) | about 1.4 MB | rendered sheets and crops of **original** game textures (`sheet_UI1.png`, `sheet_FLOW_TWND1.png`, `TITLE_DAT_9.png`, ...) | no | **ignore** (rule added: `/tools/re/datatext/png/`); they are research renderings, not needed to build |
| `.remember/`, `tools/**/__pycache__/` (119 `.pyc`, 1.9 MB), `*.bak` (`tools/emu/scenario_title_walk.lua.bak`), `*.log`, `*.pkl` (`tools/re/verify_gt/anom.pkl`, a binary pickle) | small | assistant state, bytecode, backups, logs | never | **ignore** |
| FONT dumps, extracted audio, scratch dumps | none inside the staged set | live only under `extracted/` and `build/` | n/a | covered by the two rules above; no `FONT*`, `*.adx`, `*.wav` file is staged |

I checked the staged list for `.bin .gdi .iso .zar .tbd .cue .zip .xdelta .pyc .bak .log`: **none present**.  The hex found in tracked text is the project's own SH-4 patch code and hash tables (`tools/emu/fonttest.lua` `CAVE_HEX` / `TABLE_HEX`, `tools/release.toml` hashes), not original game bytes.  The decompiler listings under `tools/re/**/*.txt` (Ghidra output, for example `tools/re/font/h3.txt`) are pseudo-C of the game's program, see 2.5.

### 2.1 Translation databases carrying Japanese text (RISKY, decision needed)

| Path pattern | Size | Contents |
|---|---:|---|
| `translation/*.jsonl` (118 files: `FLOW_PRG__*.BIN.jsonl`, `ETC_DATA__BPINFO.BIN.jsonl`, `ROOT__1ST_READ.BIN.jsonl`, ...) | 67.2 MB | 368,492 records; keys `id` (file + hex offset), **`ja`** (original string), `en`, `max_bytes`, `refs`, `ctx`, `fmt`, `slot`, `why`, `cls`, `orphan`, `skip` |
| `translation/refit/*.jsonl` (76 files) | 5.9 MB | 38,188 records, every one with **`ja`** + `en` + `why` |
| `translation/glossary.tsv`, `translation/refit/forms.tsv`, `_report.txt` | small | ja / en glossary and forms (about 3,000 Japanese characters) |

Measured: 406,673 of 406,680 records have a non-empty `ja`, 3,073,541 Japanese characters in total (2,878,947 in the main files, 194,594 in refit), i.e. effectively **the complete script, menus, help pages, news, club/player/town names and data tables of the game**.  No raw hex / byte arrays of the original binaries are embedded (ids are offsets only).  405,177 records have English.

Fan-translation practice: tables of `ja -> en` pairs are common (translators need them) but the complete source script is the most visible copyrighted-text exposure in an otherwise clean repository.  Not decided here.

### 2.2 Repainted textures (decided 2026-11-15: committed as deltas only, see section 0)

`translation/textures/**/*.pvr`: 235 files, 33,586,528 B, six top-level folders (`ETC_DATA`, `FLOW_PRG`, `GAME2`, `TRAINING`, `EVENT`, `ATFIRST`) with one sub-folder per source container, each a PVR (GBIX + PVRT header, ARGB4444 and similar) that the build injects back into the disc.  They are the game's own pictures with the Japanese text painted over by new English art.  Only the repainted regions are new work; the rest is original art, so they are derivative of the publisher's artwork even where the new lettering is the translator's.  xdelta patches of the disc carry the same material but only as a difference against the player's own disc.

* The `.gitignore` fix matters here: 9 of the 235 live in folders named `*.BIN/` that the old `*.bin` rule hid.
* Repaint specs in `translation/art/*.json` (7 files, 19 KB) and the art scripts in `tools/re/art*/` are the translator's own recipe (text, positions, fonts) and contain no pixels: **commit**.

### 2.3 Documentation and screenshots of the game

| Path | Size | Contents | Recommendation |
|---|---:|---|---|
| `docs/art-sample/club_edit_menu_before.png`, `_after.png`, `_sheet.png`, `preset_gallery.png` | 477 KB, 4 PNG | before / after pictures of one menu texture and sheets of repainted variants; `_before` is original art | **ask user** (decision D3 below); one before/after for a README is commonly accepted as illustration, a full sheet less so |
| `docs/*.md` (36), `docs/expansion/*.md` | 0.8 MB | design notes, pipeline docs; text with short Japanese quotations (largest: `docs/style-guide.md` 1,665 Japanese characters, `docs/uncovered-text.md` 364, `docs/text-sources.md` 221) | **commit**; quotations are short glossary-style examples (no large dumps found) |
| `docs/playtest-log.md`, `docs/status-report.md` | small | text only, no screenshots | **commit** |
| `tools/re/art6/p37300*.png`, `plate_menu.png` | under 6 KB each | tiny test images | **commit** (or drop); not game-art sheets |

### 2.4 Licence consistency (found while auditing)

`REUSE.toml` (new) licenses `translation/*.jsonl` and `translation/textures/**` as CC-BY-SA-4.0 and states that the Japanese strings are not licensed by the project.  A single `.jsonl` file mixing a CC-BY-SA English field with an unlicensed Japanese field is awkward: one file cannot carry two licences, and CC-BY-SA does not fit text the project does not own.  Option B below removes the problem (the committed file would hold only the translator's own text, so the whole file is CC-BY-SA).  `README.md` line 5 ("No game data is in this repository or in a release") is only true under B or C.

### 2.5 `tools/re/` (research outputs)

962 files before ignore rules; 879 after.  About 700 are small `.py` helpers (commit: they are the project's own code).  Items that embed original data or large derived dumps:

| Path | Size | Contents | Recommendation |
|---|---:|---|---|
| `tools/re/capacity/ratio/sample.jsonl`, `sample_src.tsv` | 212 KB + 78 KB | samples of the game's Japanese text (about 14,900 Japanese characters each) used to measure ratios | **ask user** (D4); safe to drop, they are regenerable from `translation/` |
| `tools/re/**/*.txt` Ghidra listings (`font/h*.txt`, `capacity/memmap/d*.txt`, `capacity/verify_memory/*`, 159 files, 4.7 MB) | 4.7 MB | decompiled pseudo-C and cross-references of the game's program (`FUN_8c...`) | **ask user** (D4); decompiler output of the publisher's code is a grey area; the analysis notes in `docs/` already carry what is needed |
| `tools/re/capacity/verify_memory/scan_sizes_out.txt` | 3.7 MB | scan results (offsets and names only) | commit or drop; largest `tools/` file |
| `tools/re/datatext/texinv.tsv`, `survey3.tsv` | 2.5 MB + 1.8 MB | inventories of the disc's files and textures: names, offsets, sizes, 12-hex-digit hash prefixes | commit (metadata, no content) |
| `tools/re/capacity/pool/results/*.json` | about 2 MB | grid search results | commit (derived numbers) |
| `tools/re/verify_gt/anom.pkl` | 46 KB | binary pickle | now ignored; a pickle in a public repo is an execution risk for readers |
| `tools/re/**/*.ps1` (30), `*.java` (17) | small | Ghidra headless scripts | commit; absolute paths were replaced by `$PSScriptRoot`, `GHIDRA_HOME` and `GHIDRA_PROJECTS` (section 4) |

### DECISIONS NEEDED

Not decided here.  Until the owner chooses, `translation/`, `docs/` and `tools/` are **not** ignored (as instructed), so a careless `git add -A` would still stage the items below.

**D1. `translation/*.jsonl` and `translation/refit/*.jsonl` (73 MB, Japanese text)**
* **A**: commit everything as is, `ja` included (simplest, full workflow reproducible, but publishes the complete Japanese script of a commercial game).
* **B**: commit the translation as `en` only plus ids: a generated copy where `ja` is dropped (or replaced by a hash / length) and `max_bytes`, `refs`, `ctx`, `fmt`, `slot`, `cls`, `why` stay.  `ja` is then re-derived from the player's own disc at build time (`tools/extract.py` reads it).  Needs a small converter, a loader change (`textdb`, `build_patch`, `refit`) and a round-trip test; size drops to about 15-20 MB; the whole file can honestly be CC-BY-SA-4.0.
* **C**: keep `translation/` private, publish only tooling and docs, plus the xdelta release.

**D2. `translation/textures/**/*.pvr` (235 files, 33.6 MB, repainted game art)**  (RESOLVED 2026-11-15: deltas only, see section 0)
* **A**: commit the PVRs.
* **B**: do not commit PVRs; commit only a build recipe (`translation/art/*.json` specs + `tools/re/art*` scripts) that repaints from the player's own disc, so no original pixels are published; the xdelta patch remains the delivery.  Costs a reproducibility check (does every texture have a spec?  today only 7 `art/*.json` files exist, most textures were drawn by scripts in `tools/re/art*/`), so this is real work.
* **C**: keep private.

**D3. `docs/art-sample/*.png`** (RESOLVED 2026-11-15, section 0: `_before`, `_sheet` and `_after` ignored, `preset_gallery.png` kept) (4 PNG, original art in `_before`, `_sheet`): A commit all; B commit only `_after.png` and `preset_gallery.png` (new art) and ignore `_before` / `_sheet`; C drop.  Suggested B.

**D4. `tools/re/` listings of game text and code** (`capacity/ratio/sample*`, Ghidra `*.txt`): A commit; B drop the two sample files and keep the Ghidra listings; C ignore `tools/re/**.txt` listings.  The scripts themselves (`*.py`, `*.ps1`, `*.java`) are fine under all options.

My recommendation (not applied): D1 = B, D2 = B if the recipe check passes (otherwise C for the PVRs and commit the rest), D3 = B, D4 = B.  If the owner wants the history to be public later without rewriting it, decide **before the first commit**: removing files from a public history needs a rewrite.

## 3. `.gitignore` changes

* Replaced the old five rules (`extracted/`, `build/`, `*.bin`, `*.BIN.bak`, `!tools/**`, `dist/`) with anchored rules grouped by purpose (disc dump, extracted data, generated outputs, archives, raw assets, caches, editor/assistant state, secrets).
* **Why anchored**: on this Windows checkout `core.ignorecase=true`, so `*.bin` matched directories such as `translation/textures/FLOW_PRG/YOUTH.BIN/` (and `ESTABLIS`, `LOADBAR`, `NEWCON`, `RECON`, `SCDRF`, `SEARCH`).  `/*.bin` only matches the five tracks at the root.
* `*.pvr`, `*.zar`, `*.tbd` are ignored globally; at the time of this audit `/translation/textures/` was re-included, since 2026-11-15 it is ignored and `/l10n/textures/` (the deltas, folders named like the originals) is re-included instead, after the generic rules.  Verified with `git check-ignore -v`: texture folders and files, `translation/*.jsonl`, `tools/**`, `docs/**`, `README.md`, `LICENSE*` are **not** ignored; tracks, `.cue`, `extracted/`, `build/`, `dist/`, zips, `__pycache__`, `.remember/` and the datatext PNG sheets are.
* A comment block at the bottom lists the pending decisions (D1-D4) so nobody ignores or commits them by accident.
* Removed `!tools/**` (it would have re-included a future `tools/.../*.bin`).

Verification run: `git status --ignored --short` lists exactly `.remember/`, the five `.bin`, the `.cue`, `build/`, `dist/`, `extracted/`, the `__pycache__` folders, `tools/re/datatext/png/` and `tools/emu/scenario_title_walk.lua.bak` as ignored; `git ls-files --others --exclude-standard` returns 1,475 files (1,476 with this audit document), none of type `.bin .gdi .iso .zar .tbd .cue .zip .xdelta .pyc .log .bak`, and 235 `.pvr` (all under `translation/textures/`).

## 4. Secrets and personal data in files that would be committed

Searched all staged text files (excluding `.pvr`, `.png`) for tokens, keys, passwords, e-mail addresses, Windows paths and user names.

* **Tokens / keys / credentials: none.**  The only "password" hit is the game string `password: %s<br>Have...` inside a translation record.  No `.env`, no key files.  The only e-mail-like hits are `n_over@0.8` style column names in `tools/re/capacity/**` (not addresses).
* **E-mail address** (resolved 2026-11-15): `nexxus@nexxusdrako.au` is the project's public contact address and is intended to appear as the git author of every commit; it stays in the files and the git config.  No no-reply address is needed.
* **Organisation / author name** (`Nexxus Drako Multimedia`) in SPDX headers of `tools/release.py`, `vcdiff.py`, `apply_patch.py`, `verify_dist.py`, `release.toml`, `REUSE.toml`, `doc/TRANSLATORS_NOTES.md`: intended credit, keep.
* **Absolute paths with the Windows user name: scrubbed (2026-11-14).**  The audit found about 141 mentions of the name in 84 files, almost all inside 24 absolute paths.  None is left in the files that would be committed (a search for the Windows and MSYS home-directory forms over the tree, without `extracted/`, `build/` and `dist/`, finds only a made-up sample path in `tools/test_release.py`; `tools/release.py` also refuses to build a bundle that contains such a path).  What was done, and the placeholders that replace the paths:

| Where | Count | Was | Now |
|---|---:|---|---|
| `tools/emu/harness.lua`, `live.lua`, `dump_ram.lua`, `probe_api.lua` | 4 | a fixed repository path | `ROOT` is the environment variable `SAKATSUKU_ROOT` (set by `tools/emu/launch.ps1`), else derived from the path the script was loaded from (`debug.getinfo(1,"S").source`); behaviour is unchanged when started through `launch.ps1`.  Not run: Flycast was not started to check this. |
| `tools/emu/launch.ps1` | 2 | default `-Disc 'D:\Retro\SDC\...(Japan).cue'`, `-Lua` a path under the user profile | `-Disc` (or `SAKATSUKU_DISC`) is required; `-Lua` defaults to `harness.lua` next to the script and is passed to Flycast relative to its folder as before; the Flycast folder is `FLYCAST_DIR` (default `C:\Games\Emulators\Flycast`); run it from the repository root |
| `tools/re/**` Python scripts (about 45 files: `art5sk_*.py`, `capacity/ratio/*.py`, `font/*.py`, `s7t_*.py`, `rel_skeptic_edit*.py`, `verify_pipeline/vp_mkscen.py`, ...) | about 117 mentions | `os.chdir('C:/Users/<name>/SakaTsukuTokudaigou2-EN')`, `R = r'C:\Users\<name>\...'` | the repository root computed from `__file__` (`os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', ...))`); `import os` added where it was missing |
| `tools/re/yn_match*.py` (3) | 3 | the scratch folder of an assistant session | `SAKATSUKU_SCRATCH` (default `build/scratch/`, which is ignored) |
| `tools/re/**/*.ps1` (about 30) | about 60 | `$d='C:\Users\<name>\SakaTsukuTokudaigou2-EN\tools\re\...'`, the Ghidra install, the Ghidra project copies | `$PSScriptRoot`, or a path built from it; `$env:GHIDRA_HOME` (the Ghidra folder that holds `support\analyzeHeadless.bat`) and `$env:GHIDRA_PROJECTS` (the folder with the `ghproj_*` project copies) |
| `tools/re/texinject/README.txt`, `tools/re/capacity/verify_numbers/t_pipe.log` | 3 | the project copy path, two logged output paths | `$GHIDRA_PROJECTS\ghproj_texinject`; the log paths made repository-relative |
| `docs/expansion/overlay-memory.md`, `font-hook-notes.md`, `font-patch-design.md`, `font.md`, `memory-map.md`, `text-engine.md`, `trans-bank.md` | 7 | `C:\Users\<name>\tools\ghproj_memmap` (Ghidra project copies) | `<GHIDRA_PROJECTS>\ghproj_memmap` |
| `docs/playtest-checklist.md`, `docs/test-sheet-prop8.md`, `test-sheet-prop10.md`, `10e`, `10f`, `10g` | 7 | `-Disc "C:\Users\<name>\SakaTsukuTokudaigou2-EN\build\trial\...gdi"` | `-Disc "build\trial\...gdi"` (run from the repository root) |

Still personal, but not the user name: `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-25.0.5.8-hotspot'` in the Ghidra `.ps1` scripts, and the default Flycast folder in `launch.ps1`.  The author e-mail address is the project's public contact (resolved 2026-11-15, kept on purpose): it appears in this file (git-state bullets) and in the git config.

The scrub was cosmetic and low risk for the history; it is done **before** the first commit so that no rewrite is needed later.

## 5. Git state and a proposed first-commit structure

* `git branch --show-current` = `main`; `git log` fails with "does not have any commits yet"; `git remote -v` shows `origin` (fetch/push) `https://github.com/NexxusDrakoMultimedia/SakaTsukuTokudaigou2-EN.git`; the task text says "not yet pushed", which matches (no commit to push).  `user.name = Pyra Drake`, `user.email = nexxus@nexxusdrako.au` (global or local, read only here).
* Commit attribution trailer for commits made by the assistant is set by the session; the owner decides if it is wanted.
* Proposed structure (conventional commits, small and reviewable, tooling first so the history shows the pipeline, translation last because of the open decisions):

1. `chore: add repository metadata` : `.gitignore`, `LICENSE`, `LICENSES/`, `REUSE.toml`, `README.md`, `CHANGELOG.md`
2. `feat(tools): disc extraction, text database and build pipeline` : `tools/*.py` (top level, not `tools/re`, not tests), `tools/VERSION`, `tools/release.toml`, `tools/*.tsv` / `*.txt` data
3. `test(tools): self-tests for the pipeline` : `tools/test_*.py`
4. `feat(tools): xdelta release tooling` : `vcdiff.py`, `release.py`, `apply_patch.py`, `verify_dist.py` (may be folded into 2)
5. `docs: pipeline, formats, memory maps and style guide` : `docs/`, `doc/`
6. `chore(tools): research helpers and emulator scripts` : `tools/re/`, `tools/emu/` (after the path scrub and D4)
7. `feat(translation): glossary and art specs` : `translation/glossary.tsv`, `translation/art/`
8. `feat(translation): English text database` : per decision D1 (A: as is; B: ja-stripped generated files; C: skip)
9. `feat(art): repainted textures` : per decision D2

Then tag `v0.1.0` later, only on the owner's explicit go (this audit does neither).  Stage with named paths (`git add <paths>`) rather than `git add -A` so nothing from an undecided area slips in; check with `git diff --cached --stat` before each commit.

## 6. Checks to repeat before the first commit

```
git status --ignored --short
git ls-files --others --exclude-standard | grep -iE '\.(bin|gdi|iso|zar|tbd|cue|zip|xdelta|pyc|log|bak)$'   # must print nothing
git check-ignore -v translation/textures/FLOW_PRG/YOUTH.BIN/@36114#0.pvr                                   # must print only the "!" re-include rule
git ls-files --others --exclude-standard | wc -l                                                           # 1,476 today (including docs/repo-audit.md)
```

## 6. Second-pass check (skeptic)

Re-run independently, read-only: `git add -n -A` lists 1,476 paths, 122,719,858 B, largest 3.7 MB; no file with extension `.bin .gdi .iso .cue .zar .tbd .zip .xdelta .pyc .log .bak .pkl` is in the list (the `*.BIN.jsonl` names are text files), no `.pvr` outside `translation/textures/` (235 inside), and `git check-ignore` reports none of `tools/VERSION`, this document, `translation/glossary.tsv`, `translation/art/*` or the texture folders as ignored.  The five tracks, the `.cue`, `build/`, `dist/`, `extracted/`, `.remember/` and the caches are ignored.  The figures above hold.

Additional points found:

* Hex in tracked JSON: `tools/re/capacity/bank/hook_patches.json` carries the project's own patch bytes plus 4 bytes of one original pointer; no original game blocks.  No other tracked file has a 64-hex-digit run except the patch tables already named in 2.x.
* `tools/re/datatext/texinv.tsv` and `survey3.tsv` (2.5 MB and 1.8 MB) list `extracted/...` paths, sizes and short hashes of original textures: metadata only, no pixels; fine under any option, but the paths reveal the disc layout.
* The three PNGs in `tools/re/art6/` are tiny test plates (a 5 KB menu strip), not sheets of game art, yet `REUSE.toml` labels every `tools/re/**/*.png` as `LicenseRef-Game-Content`.  Either narrow that glob to `tools/re/datatext/**/*.png` or accept the label (harmless, only over-cautious).
* Licence wording elsewhere contradicts the decided split (GPL tooling, CC-BY-SA translated text and art): `README.md` line 7 says the GPL covers "the tooling and the documentation" and line 5 says no game data is in the repository (see D1/D2); `doc/TRANSLATORS_NOTES.md` section 10 offers the translation "for personal use" and names only GPL.  Both need rewording by their owners before the first commit.  The CC-BY-SA statement must stay limited to the translators' own contribution: the licence cannot cover the publisher's Japanese text or the original pixels inside a repainted texture.
