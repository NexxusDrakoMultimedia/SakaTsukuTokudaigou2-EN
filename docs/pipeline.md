# Patch pipeline (translation DB -> patched GD-ROM)

Files: `tools/build_patch.py` (pipeline + CLI), `tools/test_pipeline.py` (self-test), built on `tools/textdb.py`,
`tools/textfmt_*.py`, `tools/font.py`, `tools/bzlib.py`, `tools/discbuild.py`.  Pure python 3 stdlib, run with
`python -I -X utf8 <script>`.  Nothing is committed, `extracted/` and the original tracks are never written.

## 1. How to run

```
python -I -X utf8 tools/build_patch.py                    # translation/*.jsonl -> build/out/SakaTsuku2-EN.{cue,gdi} + 5 track files
python -I -X utf8 tools/build_patch.py --dry-run          # patch files + summary only (0.7 s with an empty DB)
python -I -X utf8 tools/build_patch.py --dump build/patched   # also write every changed file for inspection
python -I -X utf8 tools/build_patch.py --strict           # exit code 2 if any string failed / was skipped
python -I -X utf8 tools/build_patch.py --append-safe       # see section 5
python -I -X utf8 tools/build_patch.py --money-format off   # default ON: English money text / ASCII %D (tools/moneypatch.py, docs/number-formats.md);
                                                           # code patch in the 1ST_READ tail (0x8c299a00) + 12 bytes in 102 overlays; off = original code
python -I -X utf8 tools/build_patch.py --texture-policy exact|grow --prop-scale on|off --money-style jp|western --refit on|off --grow-overlays N
                                                           # all opt-in / defaults unchanged: section 9 (flag reference + proof)
python -I -X utf8 tools/test_pipeline.py                  # self-test, about 3 minutes, needs ~3.5 GB free in build/out
```
Other options: `--tdb DIR` `--out DIR` `--name NAME` `--strategy gap|append` `--only SUBSTR..` `--font-dir`
`--members-dir` `--files-dir` `--relocate-ptrblob`.  Boot the result with the **.gdi** (the .cue is also written).
API: `build_patches(...) -> Result` (`.patches = {iso path: bytes}` of changed files only, `.files`, `.totals()`),
then `discbuild.build_disc(result.patches, out, name, ROOT)`.

## 2. Data flow

```
translation/*.jsonl ──load_tdb──> records grouped by the SOURCE in the id ("FLOW_PRG/X.BIN#hex")
   │  (empty "en" = keep original; sources without any English are skipped entirely)
   ├─ FLOW_PRG/*.BIN, ATFIRST/{HELP,TITLE,FACEMDUL}.BIN ─ textdb.insert_image ──────────────┐
   ├─ 1ST_READ.BIN, 2_DP.BIN (base 0x8C010000) ─ textfmt_ptrblob.apply (in place only) ──────┤
   ├─ DPETC/MESSAGE.INI ─ textfmt_ini.apply (rebuilt line by line, any length) ──────────────┤  modified file bytes
   ├─ ETC_DATA/BPINFO.BIN ─ textfmt_bpinfo.apply, applied to ETC_DATA/ AND ATFIRST/ copies ──┤  (kept only if != original)
   ├─ BCAST/BCAST.BIN ─ build_patch.do_bcast (clip subtitle headers, sparse sector edits, never held in memory; docs/text-sources.md s6) ─┤
   ├─ gap strings ─ textfmt_gap (curated, in place; docs/uncovered-text.md s9), like hwptr / recarr ─────────────────────────────────────┤
   ├─ translation/font/edit_{full,half}.png ─ font.Font set_glyph/set_half/build, both FONT.BIN┤
   ├─ translation/members/<container>/<member> ─ patch_container (bzlib) ────────────────────┤
   ├─ translation/textures/<iso path>/<id>.pvr ─ texinject (same-size slot, docs/texture-injection.md) ┤
   └─ translation/files/<iso path> ─ whole-file replacement ──────────────────────────────────┘
                                                                                              ▼
                                          discbuild.build_disc(patches): in place if it fits the old extent,
                                          else first-fit into zero gaps, else appended past track 5; EDC/ECC regenerated
                                                                                              ▼
                                          build/out/<name>.cue, .gdi, "<name> (Track 1..5).bin" + summary
```
Before anything is applied each record is checked against the real file: the Japanese text at the id's offset must still equal `ja`
(stale DB entries are SKIPPED with a message, never written); English must be encodable in cp932 (ASCII); a record that
cannot fit (no room, or the field cannot be relocated) is FAILED and keeps its Japanese.  Failures never abort the run.
A file produced by two stages, or an unknown iso path, raises `PipelineError`.
An orphan record (no pointer) whose English is a placeholder (`-`, `Plot`, `Misc`, `Bow`, `?`, `----`) is binary data or code that was decoded as cp932; `do_overlay` refuses it
(FAILED, so `--strict` stops) and `tools/re/int_blankjunk.py` blanks them in the database (`docs/status-report.md` section 0.2; `tools/test_junk.py`).  `"skip": true` alone is only a merge hint; the build keeps the original bytes when `en` is empty.
`discbuild.build_disc` / `plan_patches` also take `sparse={iso path: {offset: bytes}}` (the BCAST edits) and `verify_disc` gets the streamed `sparse_sha1`.

## 3. Adding translations

1. `python -I -X utf8 tools/textdb.py extract` (and the `textfmt_*.py --write` tools) create/refresh the DB; both keep existing `en`
   (`textdb.preserve_en`: merged back by id when the `ja` is unchanged; translated records that no longer match are reported as
   ORPHANED and saved to `build/trans/orphaned_en/`).  The bulk translation workflow (shards, validator, merge) is in
   `docs/translation-workflow.md`; it is the only intended writer of `en`.
2. Fill `"en"` in `translation/<source>.jsonl` (schema: `id, ja, en, max_bytes, refs, ctx` [+ `orphan`]; one record per line).
   Keep inline markup exactly: `@Y/..@`, `#tk20#`, `%s %d %2d`, `\n` (= 0x0a).  Insert `\n` at word boundaries: the engine wraps per
   character (39 half-width chars per line in the default 20-cell window; docs/text-engine.md).  Player names (BPINFO): max 13 chars.
3. `python -I -X utf8 tools/build_patch.py`, read the summary (FAILED/SKIPPED lines name the id and the reason).
Only `id`, `ja`, `en` are read by the pipeline, so the textdb (`orphan`) and textfmt record variants are interchangeable (schema
conflict resolved: ids are `<source path>#<hex offset>` in both; the reader ignores extra keys).

Font: `python -I -X utf8 tools/font.py export translation/font` writes `edit_full.png` / `edit_half.png`; edit them (0 = ink, 255 = paper,
glyph i at col i%32, row i//32) and rebuild.  Only glyphs that differ from the original root FONT.BIN are applied, to both copies (the
copies differ in glyph 3580).  FONT.BIN > 679936 bytes raises an error (load slot, docs/font.md s6).
Container members: put the new plaintext at `translation/members/GAME/ACCESSRY.ZAR/xm02megs.bin`; the container must be a bare ZSARC
concatenation.  The member is re-encoded with its original method/name/mtime, new sizes, CRC16 and header CRC, 4-aligned, and the result is
re-parsed (all untouched members must stay byte-identical).

## 4. Conflicts between the agents' reports and how the pipeline resolves them

| Topic | Disagreement | Resolution in the pipeline |
|---|---|---|
| Appending to an overlay | overlaytext: `textdb --append` is available; textengine: unsafe (data lands on `_end`, where the heap header is written / on BSS) | Never appended by default (strings that do not fit FAIL). `--append-safe` is allowed only for FLOW_PRG overlays classed `no-bss(_end==file end)` in `tools/re/textengine/survey_overlays.tsv`, not GAME.BIN, only if the u32 at `end_var_off` equals `base+size` in the image, and then that `_end` word is raised to `base+new size`.  Eligibility is re-checked in the image at run time; BSS overlays are refused with a note.  INFERRED safe, never run on hardware/emulator. |
| 1ST_READ / 2_DP relocation | textfmt_ptrblob appends relocated strings to the image end | in place only unless `--relocate-ptrblob` (these executables have BSS right behind the image; untested) |
| Load addresses | overlay.py trusted a stub literal (GETREP 0x8c2f0000) | `textdb.load_image` is used for every overlay; it re-derives the base from string pointers (GETREP = 0x8c2d0000). The textengine survey table still says 0x8c2f0000 for GETREP/`end-var-not-found`, so GETREP is never append-eligible. |
| Which agent owns ATFIRST/HELP,TITLE and 1ST_READ | both textdb and textfmt_ptrblob can write them | Pipeline uses textdb for the ATFIRST overlays (the ids/ja agree: 669/669, 466/466) and textfmt_ptrblob (in place) for `1ST_READ.BIN`/`2_DP.BIN` when `translation/ROOT__*.jsonl` carries English.  Routing is by the source in the id, not by file name. |
| Texture bundle flag bits | docs/formats.md guessed 1=bz, 2=bzw | datatext (decode of all 7501 records): bit30 -> bzw, bit31 -> bz (confirmed from the disassembly of FUN_8c15a776; docs/formats.md is corrected).  Texture bundles are now written by `tools/texinject.py`. |
| Font used by the game | DPFONT (guess) vs FONT.BIN | FONT.BIN (textengine + font agree); DPFONT belongs to the 2_DP browser. |

## 5. What was verified (tools/test_pipeline.py, last run 2026-11-11 stage 3: 351 checks passed, 0 failed, about 180 s)

PROVEN by running it:
* A. Empty translation (the real DB: 126273 records, 0 with English; and an empty directory) -> 0 patches; disc tracks 1-5 are byte-identical
  to the originals (sha1 equal), no file moved, generated .cue == original .cue.
* B. Demo of 3 strings: `FLOW_PRG/CHALDANI.BIN#a80c` -> "Pick a rank.\nA: OK" (in place), `#bd9c` -> "Yuta Minami (Goalkeeper)" (relocated into the freed
  tail of the first; 1 pointer rewritten), `DPETC/MESSAGE.INI#22` -> "Connecting to host...".  Output disc re-read with `tools/gdrom.py`:
  1215 files, exactly 2 changed, 1213 byte-identical to the original disc; the pointers resolve to the English text, all 209 other
  strings and all other pointer words are unchanged, all 78 changed bytes lie in the two string regions / pointer words; INI: 1 line differs.
  Two runs give identical patches (digest).  71 sectors rewritten, no file moved.
* C. Failure handling: over-long orphan -> FAILED, stale `ja` -> SKIPPED, non-cp932 English -> SKIPPED, nothing written.
* D. Second disc: `--append-safe` on CHALDANI (+412 bytes, 4-aligned, `_end` word 0x8c4dd860 -> 0x8c4dd9fc); refused on MEETING.BIN (BSS);
  BPINFO name in both copies (22-char name rejected, only first name field bytes changed); half-width glyph 'E' edited in both FONT.BIN copies
  (only that glyph differs; unedited sheets = no change); GAME/ACCESSRY.ZAR member replaced (40 members, other 39 identical, CRCs valid);
  output disc: exactly those 6 files changed, 1209 identical.

## 6. Known limitations / still needs an emulator or hardware test

* **Status note (stage 3, 2026-11-11): this section is the stage-1 text; the corrections follow each bullet.**  A no-op build is bit-identical so it boots iff the original does.  Since stage 1 the plain and
  proportional trial discs (up to `trial_prop3`) were booted and played in Flycast (docs/playtest-log.md, `docs/proportional-font-review.md`).  Everything added after that (money cave, club-name guard,
  half-width relocation, refit forms, repainted art groups 1-7, prop-scale) is proven only offline; the screen-by-screen list for the next session is `docs/playtest-checklist.md`.
* Whether a larger overlay (`--append-safe`) loads correctly, and whether the loader/allocator accept the raised `_end`, is INFERRED from decompilation only.
* Overlays other than the 33 no-BSS ones have no growth path: overflow strings fail.  The text packs with <1 % slack (docs/overlay-text.md), so a
  full prose translation will need either many strings shortened, `--append-safe` on the no-BSS overlays, or a new memory area (engine work).
  MEETING/NEWS/TRAINING/DRAFT (BSS) are the problem cases.
* Disc growth: a file that grows is moved (zero gaps 12.8 MB, then past track 5, beyond the real GD-R end 549150 -> emulator only).
  Files cannot be added/removed.  Not tested: reading by absolute LBA by the game outside ISO9660.
* Proportional spacing, wrap, `%D`/`%m` money text, window widths need overlay code patches (docs/text-engine.md).  **Implemented since** (stage 2-3): proportional font (`--proportional-font on`,
  docs/proportional-font.md), money text (`--money-format on`, docs/number-formats.md), Hometown label and window layout (`tools/layoutpatch.py`, docs/layout-issues.md), club-name guard (9.9).  Raw-flag
  windows (where `@ = % #` print literally) are unknown per call site.
* FONT: glyph editing only; FONT.BIN recompression of changed glyphs uses bzlib.compress_bz (game decoder assumed identical).  No extra glyph slots
  beyond blank cells, EXTRA_TABLE not extended.
* Textures with baked-in Japanese (title logo, club/staff name plates, menu atlases): the INJECTION side exists now
  (`translation/textures/<iso path>/<texture id>.pvr`, `tools/texinject.py`, stage `apply_textures`, `docs/texture-injection.md`);
  the pixel encoders (twiddle / VQ / 4444) exist since stage 2 (`tools/pvr.py`) and 235 repainted textures are installed (docs/art-translation.md); they are not yet seen in game.
  BPINFO names are limited to 13 bytes; BPINFO header/checksum not analysed.
* Container members: only bare ZSARC concatenations (nested `@<offset>` archives and offset-table bundles such as TBD/DAT are refused/unsupported).
* Duplicate Japanese texts (29122 distinct of 126273 records): `tools/transmerge.py merge` writes one translation to every record
  with the same `ja` (translation-memory propagation, see `docs/translation-workflow.md`).
* (fixed) `textdb.py extract` used to overwrite its jsonl files with empty `en`; it now preserves `en` by id (see section 3).

## 7. Shipping the result

The built disc is shipped as xdelta (VCDIFF) patches against the player's own dump (BIN/CUE, GDI or volume ISO): `tools/release.py`,
`tools/apply_patch.py`; see `docs/xdelta-release.md` (design, formats, hashes) and `docs/RELEASING.md` (how to cut a release).

## 8. Table records (`fmt` = `hwptr` / `recarr`)

`tools/textdb.py extract` also writes records the pointer / orphan scan cannot see (docs/uncovered-text.md): half-width-katakana strings
(`tools/textfmt_hwkana.py`: pointer-referenced and index-addressed pools) and Japanese fields of fixed-stride record arrays behind a
stat byte (`tools/textfmt_recarray.py`: municipalities, staff / player records).  They sit in the same `translation/<source>.jsonl`, carry an
extra key `"fmt"`, never overlap a textdb string, and are written **in place after the pool repacking** by `build_patch.do_extra`
(stale `ja` -> SKIPPED, `len(en)+1 > max_bytes` -> FAILED, nothing moves).  Without English they change nothing (the dry-run digest is
identical).  `translation/ROOT__1ST_READ.BIN.jsonl` (204 labels, ptrblob handler, in place) was added in the same change.
`textdb extract --no-extra` reproduces the old overlay-only files; `preserve_en` now also keeps `skip` on records without English.

## 9. Build flags (the standard command and every option)

The standard build used for trial discs and releases:

```
python -I -X utf8 tools/build_patch.py --repack on --share dup --append-safe --proportional-font on --refit on --align-fix on --open-font on --small-prop on --strict [--hw-relocate on] [--texture-policy grow]
```
Since stage 8b `--refit on`, `--align-fix on` and `--tag-fix on` are the DEFAULTS of the command line (a plain `build_patch.py --repack on --share dup --append-safe --proportional-font on --strict` builds exactly the standard disc; `tools/release.toml` `[build] standard_flags` records the release flags).  The library function `build_patches()` keeps its old keyword defaults (`refit=False`, `align_fix=False`, `tag_fix=False`).  The line `flags: ...` printed at the end of every run lists the effective flags.  With `--strict` the exit code is 2 when any string failed or was skipped (3 = disc verification failed, 1 = an error).
(State of stage 2: `--texture-policy exact` also builds now, `tools/re/bld_texgrow.py` reports 235 textures, 0 over their slot; `grow` is only needed if the art grows again.)
Every flag below except `--refit`, `--align-fix` and `--tag-fix` (default on since stage 8b) is opt-in and **leaves the default output byte-identical** when it is off / 0 (proof: `tools/re/bld_cmp_default.py`, section 9.7, which predates the three new defaults).
A bad combination or an impossible input stops the run with `ERROR: ...` and exit code 1 (a `PipelineError`, no traceback).

| Flag | Default | Meaning |
|---|---|---|
| `--texture-policy exact\|grow` | `exact` | see 9.1 |
| `--prop-scale on\|off` | `off` | 9.2 |
| `--money-style jp\|western` | `jp` | 9.3 |
| `--refit on\|off` | `on` | 9.4 |
| `--align-fix on\|off` | `on` | 9.10 |
| `--tag-fix on\|off` | `on` | 9.11 |
| `--crowd-fix on\|off` | `on` | 9.12 |
| `--bcast-speed off\|1.7\|1.9\|2.2` | `1.9` | 9.13 |
| `--lin-center on\|off` | `on` (with `--proportional-font on`, tail placement) | 9.14 |
| `--cell-prop on\|off` | `on` (with `--proportional-font on`, tail placement) | 9.17 |
| `--clip-lead-space on\|off` | follows `--cell-prop` (`on` with it) | 9.18 |
| `--small-prop on\|off` | `off` (opt-in, unproven in game) | 9.15 |
| `--options-fix on\|off` | `on` | 9.16 |
| `--grow-overlays N` | `0` | 9.5 |
| `--club-guard on\|off` | `on` | 9.9 |
| `--club-dot on\|off` | `on` | 9.9 |
| `--dedupe-files`, `--allow-overflow`, `--add-file`, `--verify-disc` | see 9.8 | disc options |

### 9.1 Texture policy: `exact` stays the default, and why
`exact` keeps every container length: a repainted texture must pack into the slot of the original.  `grow` re-lays-out containers
(a bare ZSARC member, a whole-file TBD or a TBD tail; offsets shifted by exactly the growth) and the file then grows, which `discbuild`
handles by moving it.  That is **INFERRED safe only, never run in the game** (docs/texture-injection.md s7: the loader of the container
and the room behind boot-loaded files are not proven), so it is not made the default.  What the build does instead of a traceback: it
collects every texture that does not fit and stops with ONE message naming each file, texture id and the number of bytes over the slot:

```
ERROR: 11 texture(s) cannot be injected under --texture-policy exact:
  ETC_DATA/PLATE.ZAR texture P0.TBD#0: record #0: repainted data packs to 1064 bytes ... (200 bytes over the slot)
  -> simplify the repainted art so it packs into the original slot ..., or pass --texture-policy grow ... (INFERRED safe only ...)
```
`tools/re/bld_texgrow.py` lists the same offenders (and whether their container may grow) without building anything.  State when this was
written: the TRAINING/TRAINING.TBD record #7 texture fits its slot, and after the art owner's stage 2 pass the 11 ETC_DATA/PLATE.ZAR plates fit
too (`bld_texgrow.py`: 235 textures, 0 over), so a plain `exact` build succeeds.  The ERROR text above is what an over-slot texture gives.

### 9.2 `--prop-scale on|off` (needs `--proportional-font on`, tail placement)
Passes `prop_scale` to `fontpatch.make_patches`: windows whose advance byte is not 24 (16 / 32 / 48 / 10 px: rank lists, size class 2 prose)
scale the advance table by A/24 instead of using the fixed `A >> 1` (docs/patch-engine.md s4).  Only 1ST_READ.BIN 0x8c299800..0x8c299900
changes (a 144 byte cave instead of 104); every hook byte of every overlay is identical.  Refused without the proportional font or with
`--prop-font-place gap1`.  Not proven in the game.

### 9.3 `--money-style jp|western`
Passed to `moneypatch.make_patches(style=...)` (`moneypatch.STYLES`).  `jp` (default, binding user decision): the Japanese oku / man
structure in English words, `13 Oku 1500 Man`, `6000 Man`, `1 Oku`, `0 Yen` (Oku = 100 million yen, Man = 10 thousand yen; a translator's
guide explains it, nothing in game).  `western` = the old decimal output (`Y1.315bn`).  Ignored with `--money-format off`.  The summary
names the style used.  See docs/number-formats.md.

### 9.4 `--refit on|off`
Applies the names owner's refit overlays (`translation/refit/<source with / as __>.jsonl`, `tools/refit.py`) on top of the DB English **in
memory** before any patching, through the real API `refit.load_overlays(db_by_source, overlay_dir, relocate, report)` (en of existing
records only; `translation/*.jsonl` is never written; stale / unknown / untranslated / over-cap overlay records are skipped by refit and
listed in the build notes, a malformed overlay file stops the build with a `PipelineError`).  The overlay directory is `<--tdb>/refit`.
`--refit on` forces `--hw-relocate on` (an explicit `force` is kept), because refit forms are longer than the old slot-forced
abbreviations and rely on the relocation of the half-width pointer strings.  State when written: `translation/refit/` held no overlay
file yet (`forms.tsv` only), so `--refit on` changed nothing but the forced relocation.  **Now (stage 3) it holds 75 overlay files** (`tools/re/rfit_gen.py`, `translation/refit/README.md`) and the
trial disc `build/trial/prop6r` is built with them (0 failed, 0 skipped).

(Stage 8b: the default is now `on`; `--refit off` gives the slot-cut forms `Avalanc`, `Cie`, `Ros` again and does not force `--hw-relocate`.)

**Stage s8gf (table-base fix).**  The forced relocation moved strings that are the base of a table (`Damui` = record 0 of the 56 byte player
table, `Nuchitos`, company arrays) and caused the Event-screen hang and the wrong scout data of prop10c.  Now `tools/hwguard.py` classifies every
pointer site, `translation/hw_inplace.tsv` lists the 417 records that never move (and never lend their slot), `apply_relocate(guard=True)`
re-checks at build time (fail safe: unknown stays in place), and relocated strings are 4-byte aligned (`build_patch.HW_ALIGN`).  Because
aligned strings need more room, `hw_relocate_fit` gives refit forms back to the in-place short form, lowest class first (person, other,
sponsor, town, city, nation, jclub; club words never; HOMETOWN.BIN falls back to 2-byte alignment); the build notes list the counts per
overlay (`refit forms back to the in-place short form ...`).  `prop10d`: 23,792 of 38,386 refit forms given back, 0 failed.  Details and the
bytes proof: `docs/hw-relocation.md` section 6.

### 9.5 `--grow-overlays N` (opt-in, INFERRED, never booted; requires `--append-safe`)
`--append-safe` alone only ever extends the 33 `no-bss` overlays.  With `N > 0` an overlay that HAS a BSS area (class `bss` in
`tools/re/textengine/survey_overlays.tsv`, 76 overlays) may also take appended text, but only in the fallback, i.e. only when the pool repack
left strings Japanese and the appended strings (all of them or nothing) need at most N bytes.  This is "option 1" of
docs/expansion/overlay-memory.md s8, the safest of its options: no stub patch, no slot-count edit, no new file.
1. The image is zero-padded from its end up to the old `_end` (rounded up to 4), so every BSS address keeps its meaning;
2. the strings are appended behind the pad (`textdb.insert_image(append=True)`, pointers rewritten);
3. the `_end` word (survey `end_var_off`, which must still hold the survey `_end`) is set to `base + new size`: the heap start
   (`round32(_end)+0x20`) moves up by pad + growth, so the heap loses only that.
Never grown: GAME (its stub zeroes up to `_end`), ESTABLIS / MOVIE / MOVIE_BG / LOADBAR (stubs ignore `_end`), COMM CON_REP NF_CON PASS_PL
J1_REP PL_CON (no slot-aligned base, budget 0), anything outside FLOW_PRG.  Caps: N <= 262144 (`GROW_MAX`; the table of
overlay-memory.md gives 20 KiB to 220 KiB of "safe growth" per overlay), HELP 20480 (`GROW_CAPS`; slot 11 is resident behind it).  A need
above the cap leaves the repack result and says so in a note.  The file grows by pad + growth (disc cost: the BSS pad dominates, up to
310 KB for AUTOSAVE); `discbuild` moves a file that outgrows its extent.  **Not checked by the build**: the real free memory of the moment
the overlay runs (docs/expansion/overlay-memory.md T4 / T5 need an emulator boot) and the slot-count / next-slot state.  Tests:
`tools/test_bldflags.py` (eligibility, pad all zero, `_end` word, every pointer resolves, cap, default size unchanged).

### 9.6 Tools fixed alongside
* `tools/test_transwork.py` 'every real jsonl file re-serialises byte-identically': `translation/ROOT__1ST_READ.BIN.jsonl` had 2 lines in
  the compact separator style inside a spaced file (a writer that re-wrote single records; textdb.write_jsonl is compact,
  textfmt_common.write_jsonl is spaced).  Fix in the writer, not the data: `translib.normalise_styles` re-serialises odd lines, and
  `transmerge` applies it whenever it rewrites a file, so a mixed file heals itself on the next merge (unit-tested);
  `tools/re/bld_normalise_jsonl.py [--write]` reports / heals any file the same way (it healed this one; records unchanged).
* `tools/test_textrepack.py`: the identity / forced cases load `translation/*.jsonl` through `R.load_entries`; the DB now carries English, so
  the test blanks `en` (and `skip`) itself.

### 9.7 Proof that the default output did not change
`tools/re/bld_cmp_default.py SNAPSHOT_DIR --disc PREFIX`: the standard build (money format on, grow policy) on one input snapshot with
the current `build_patch.py` and with an in-memory old-equivalent copy (the pass-through of `prop_scale`, `style` and the grow plan
removed): the `{iso path: bytes}` dicts are compared and so are the 5 track files of the two discs written from them.

### 9.8 Disc options (stage 3, disc owner): capacity guard, `--dedupe-files`, `--add-file`, `--verify-disc`
Details and proofs: docs/disc-layout.md (sections "Stage 3 additions"). All new options leave the default output byte-identical
(`tools/re/dsc_cmp_default.py`: standard build patch set, with and without growing files, 5 tracks + cue + gdi `cmp`-identical).

| Flag | Default | Meaning |
|---|---|---|
| (capacity guard, always on) | - | a build whose content would pass LBA 549150 (the end of track 5 / the GD-ROM ceiling) stops with `ERROR: disc full ...` (exit 1) naming the shortfall, the free holes left and the remedies. Before stage 3 such a build silently appended past the end (emulator-only) |
| `--allow-overflow` | off | restore the old behaviour for experiments: append past 549150, print a loud `WARNING: OVERFLOW` line |
| `--dedupe-files on\|off` | `off` | byte-identical files (final bytes, after patching; 15 groups, 20 extents, 3726 sectors on this disc) share one extent: the lowest-LBA member keeps it, the other directory records point to it, their old extents join the free list (10157 free sectors instead of 6431). INFERRED safe (the game opens by name and takes size from the record), never booted; a patch that changes only one member of a group un-shares it automatically |
| `--add-file /ISO/PATH=LOCAL` | none | ship an extra file inside the image (README, text pack); repeatable; missing directories are created; the game never opens it. In git-bash write `MSYS_NO_PATHCONV=1` before the command or the leading `/` is rewritten |
| `--verify-disc off\|fast\|full` | `fast` | run `tools/verify_disc.py` on the written image and print its report at the end of the summary (about 10 s fast, 25 s full); an error exits with code 3. `fast` = geometry, gdi/cue, PVD/IP.BIN, both ISO readers, extents, every patched file read back, tracks 1 and 3 fully, every changed sector, diff against the original; `full` = every sector of every data track and every file read through its record |

### 9.9 Club-name guard (stage 3, overflow owner; default ON)

| Flag | Default | Meaning |
|---|---|---|
| `--club-guard on\|off` | `on` | `tools/layoutpatch.py` replaces the club-name composer of the 20 overlays by a bounded one (13 characters + NUL, 224 bytes in place of 232): a `town + ' ' + word` over 13 characters gets the TOWN cut to `max(12 - len(word), 4)` characters ending in `.`; the word is kept.  HOMETOWN's candidate popup join uses the same rule.  `off` = the original unbounded composer (the stage-2 default output; the patch digest differs between on and off). |
| `--club-dot on\|off` | `on` | `off` = the cut town has no trailing dot. |

Proof on the real prop7 / prop7r overlays (47.1 % / 49.0 % of the 68,640 pairs cut after the stage-3 polish, never more than 13 characters, 0 problems and 0 odd shapes in 142,670 runs per overlay type; `tools/re/fin_clubs.py` reads the overlays from the built disc itself): `tools/re/int_clubs.py <dump>`
and docs/layout-issues.md 9.8.  The guard is part of the standard build and therefore of the patch digest (prop6 `04e77bcf...`, prop6r `6bde8892...`; after the town-short-form polish prop7 `7c5bf437...`, prop7r `561355ac...`).
Final trial discs: `build/trial/prop7` (standard flags + `--strict`) and `build/trial/prop7r` (`--refit on`), both 0 failed / 0 skipped, `verify_disc` OK (prop6 / prop6r are the stage-3 discs before the polish and are kept for comparison).

### 9.10 `--align-fix on|off` (stage 8b, default ON)
**Stage 8h change (docs/layout-issues.md 10.9): `--align-fix on` now means the ISOLATED wiring.**  The font cave is no longer modified; the blank-run snap is entered only by the overlays in `fontpatch.ALIGN_SNAP_FILES` (PLNUMSET), every other overlay has the
align-off hook bytes, and the player-card panel edits stay in CAP_SLCT / ENDOPT / EVENT.  `SAKA_ALIGN_MODE` (`default`, `snap-only`, `panel-only`, `snap-all`) bisects it without touching the command line; the `flags:` line still reads `--align-fix on`.
Read-back of a disc: `1ST_READ.BIN` differs from an align-off disc only in `0x8c299700..0x8c2997ff`, `PLNUMSET.BIN` in one byte, the three panel overlays in 64 bytes each, nothing else (`tools/test_align_isolation.py` proves it on the build output).

Passes `align_fix=True` to `fontpatch.make_patches` (docs/layout-issues.md s10, docs/patch-engine.md s2): the cave `font.align` (blank-run columns such as the shirt-number column snap
to the fixed-cell grid) and the player-card panel edits (`pw3` replaces strlen, 18 `shll2` become `nop`; the 2 salary idioms keep their `shll2` because their setter returns a character count, `docs/layout-issues.md` s10.3a) in CAP_SLCT, ENDOPT and EVENT.  Default ON whenever the build supports it, OFF otherwise (a bare `build_patch.py --dry-run` works).  An EXPLICIT `--align-fix on` is refused with a clear error (exit 1, no build)
without `--proportional-font on` (including `control`), with `--prop-font-variants` other than `A` and with `--prop-font-place gap1`; pass `--align-fix off` for such builds.  A panel overlay whose bytes are
not the known panel (already patched, another build) stops the build (`FontPatchError`).  Not seen in the game yet (`docs/test-sheet-prop10.md`).

### 9.11 `--tag-fix on|off` (stage 8b, default ON)
`layoutpatch.tag_patches`: the shared `short_name(dest, name)` routine of 11 overlays (CAP_SLCT, ENDOPT, EVENT, GAME, G_RESULT, NEWCON, NEWS, OFFICE, TOWN, TRAINING, YOUTH; the Practice > Player
Placement tags and ten more name labels) is replaced in place (152 bytes, same entry, same pool words) by a routine that shows the LAST blank-separated word of the name, up to
`TAG_LIMIT` = 7 letters (the local buffer holds 8; since stage 10 `TAG_LIMIT_BY_OVERLAY = {'GAME': 5, 'TRAINING': 5}`: the lineup tags of the match screen and of Practice > Player Placement are cut to 5 letters because the next sprite starts there, `Kasam t` / `Hisan` / `Kanaw` were clipped; the other nine overlays keep 7), with the original ` %s ` padding for 1 or 2 letters: `Yamada` instead of `Taiy`, `Nakata` instead of `H.`.  The routine is found by exact signature in the
CURRENT bytes (text repacking is kept); a foreign or already patched image stops the build.  Proven in the SH-4 simulator on the real bytes of all 11 overlays (`tools/test_tagfix.py`); the tag
WINDOW width (the label may be clipped to 4 cells) and the `CF` icon overlap are unknown until a Flycast look: the alternative limits are one table (`layoutpatch.TAG_LIMIT_BY_OVERLAY` and `TAG_LIMIT`, tested in `tools/test_tagfix.py`, `layoutpatch.tag_limit_for(name)`).  `docs/s7t-proposals.md` s2.

### 9.12 `--crowd-fix on|off` (stage 10, default ON)
`layoutpatch.crowd_patches` / `patch_crowd`: the crowd-row function of `FLOW_PRG/G_INCOME.BIN` (file 0x2d0, used by the HOME MATCH and AWAY MATCH tables of the Event income screen) copies its unit strings
with the libc `strncpy` and counts of 2 bytes (right for the Japanese 万 and 人), so `man` / `ppl` printed as `1ma827pp`.  The patch changes 6 halfwords (copy count and pointer step 2 -> 4 for `man `,
2 -> 3 for `ppl`, 3 -> 4 for the zero case), repoints two pool words and writes the strings `man ` and `0ppl` into zero padding of the overlay (0x264a0, 0x264a8): the line reads `1man 827ppl`, `5000ppl`, `0ppl`, all
ending at the same right edge (x = 593 on the 600 px column).  Same size; found by a 232 byte code signature at 0x2d0 plus the old halfwords, the zero area and the English `ppl` / `0` records; a foreign or already patched
image stops the build; an image whose unit text is still Japanese (a partial translation database) is skipped with a note (`CrowdUntranslated`).  Proven in the SH-4 simulator on the real bytes
(`tools/test_crowdfix.py`); not seen on screen yet.  Details: `docs/layout-issues.md` s13.

### 9.13 `--bcast-speed off|1.7|1.9|2.2` (stage 10, default 1.9)
`layoutpatch.bcast_patches` / `patch_bcast_speed`: the commentary subtitle (BCAST) typewriter of `FLOW_PRG/GAME.BIN` (box update function 0x8c31eee8) reveals one character per about 2.23 ticks and nothing waits for it, so the
longer English text was still typing (or cut by a fade) when the clip ended.  Two sites (signatures `a6f33df35a038823018ba0a00900` +4 and `04e005e067a0e18003e064a0e180` +10, each unique over `extracted/`):
the gate `sts fpul,r3 ; tst r8,r3` becomes `sts fpul,r0 ; tst #7,r0` (1.9 = 1.94x; `#3` = 1.7 = 1.67x; 2.2 = the gate's `bra` becomes a nop, one character per tick = 2.23x) and the return after reading a character
becomes a branch back to the dispatch behind the prologue (`64 a0` -> `18 ae`, `bra 0x8c31eefa`), so the normal state 3 code draws it in the same tick.  **Not `11 a0`** (a branch straight to the draw call): that first version crashed the emulator on the first message of every box (prop10g, the tactics explainer) because the slot pick (state 1) leaves r13 = 0x8c159000, a table of function pointers, and falls into the read in the same tick; the draw call is `jsr @r13` (layout-issues s14).  `off` leaves GAME.BIN alone.  The Event / scout message typewriter is another function and is untouched.  Proven in the simulator with the real box routine, started from the slot pick like a real message
(`tools/test_bcastspeed.py`: 2.233 / 1.333 / 1.150 / 1.000 ticks per character, characters identical, only the draw routine is called, the crashing first version is kept as a negative control; never booted).  About 5% of the commentary lines remain longer than their clip at 1.9.  Details: `docs/layout-issues.md` s14.

### 9.14 `--lin-center on|off` (stage 10, default ON with the proportional font)
`fontpatch.LIN_SRC` / `patch_1st_read(lin=True)` / `make_patches(lin_center=True)`: the linear text writer `FUN_8c15e9c6` of `1ST_READ.BIN` (match intro, in-match OPTIONS rows, ENDING ...) centres narrow half-width glyphs (`i l I ! ' ,` ...) in
their 12 px tile instead of leaving a 7 px gap behind them.  A 42 byte hook at file 0x14ea22 (signature located, refuses foreign / patched / moved images) jumps to the cave `font.lin` (0x8c299600, 192 bytes, a full 0xC0 registry claim) that
reads the advance table at run time and shifts the glyph row right by `k = (14 - adv) >> 1` (`adv <= 9`) / `(13 - adv) >> 1`; works with the default table and with `--open-font on`.  Only `1ST_READ.BIN` changes (42 + 192 bytes).
`--lin-center on` is refused without `--proportional-font on` and with `--prop-font-place gap1`; the default is off where the build cannot take it (bare dry runs).  Proof and the Roboto check: `tools/test_lincenter.py`, `docs/layout-issues.md` s16.

### 9.15 `--small-prop on|off` (stage 10 follow-up, OPT-IN, default OFF, not booted)
`fontpatch.SMALL_SRC` / `patch_1st_read(small=True)` / `make_patches(small_prop=True, small_files=None)`.  The 16 px text windows of `OPTION.BIN` (option / sound-test lists) and `TRAINING.BIN` (Practice player-info panel) kept the fixed
8 px advance of the font cave's `A != 24` path, so `i l r t` were followed by a gap (`Trai ni ng`, `H i roshi`).  With the flag the advance hook of those two overlays enters `sm_adv` (unused tail of the font cave reserve): A == 16 gives the table scaled by
2/3 (`(2 t + 1) / 3`, digits and blanks stay 8), every other A is a tail jump into the unchanged font cave.  Nothing else changes (EVENT, SCDRF, SEARCH, GAME ... byte-identical; `1ST_READ.BIN` only in the zero tail of the font cave).  Refused without
`--proportional-font on`, with `--prop-font-place gap1` and with `--prop-font-variants` other than A.  Unlike `--prop-scale` it never touches A = 1 / 5 / 10 / 24 / 32 / 48 windows.  Proof: `tools/test_smallprop.py`; diagnosis: `docs/layout-issues.md` s17.

### 9.16 `--options-fix on|off` (stage 10 follow-up, default ON, not booted)
`layoutpatch.patch_options` / `options_patches` / `build_patch.apply_options_fix`: the selected option of the in-match OPTIONS panel (`FLOW_PRG/GAME.BIN` and the identical copy in `ENDING.BIN`) is brightened by a sprite that re-draws a fixed window of 12 px character cells that fitted the Japanese full-width
values (`ＯＮ・ＯＦＦ`, `Ａ・Ｂ`, `近・中・遠`); with the English values it lit `ON/O` / nothing, `A/` / nothing and `ar` / `id` / `ar`.  The 11 sprite records (data, same size, 33 changed bytes per overlay) are recomputed from the cells of the option words in the CURRENT value strings, so the highlight covers exactly
ON or OFF, A or B, Near, Mid or Far.  Located by the 220 byte record block, refuses foreign / already patched bytes; a Japanese value image is left alone.  Proof: `tools/test_optionsfix.py`; diagnosis and numbers: `docs/layout-issues.md` s18.

### 9.17 `--cell-prop on|off` (stage 11, default ON with the proportional font, not booted)
`fontpatch.CELL_SRC` / `patch_1st_read(cell=True)` / `make_patches(cell_prop=True)` + `layoutpatch.patch_cell_prop` / `cell_patches` / `build_patch.apply_prop_font(cell_prop=True)`: the commentary subtitle (BCAST) line engine of `FLOW_PRG/GAME.BIN` (`0x8c3202b0`) gave every half-width character a constant 12 px advance and never read the advance table, so `i l t f` were
followed by a gap (`Fi r st hal f`), and the blank that a wrap leaves at the start of the next line was drawn.  The routine `cell_adv` (28 bytes, registry claim `font.cell`, `0x8c2996c0`, the spare 64 bytes behind the 192 byte `font.lin` cave) returns `table[code]` clamped to 12 (0 -> 12); the half-width block of the engine (22 bytes) calls it through a literal in a free zero word
(`0x8c32053c`), the blank block (30 bytes) writes the table's blank advance and skips a blank at column 0.  The overlay edit runs inside `apply_prop_font` (after the font stage, on the CURRENT bytes of `GAME.BIN`, because the blank advance is read from the built table).  Only `1ST_READ.BIN` (28 bytes) and `GAME.BIN` (22 + 30 + 4 bytes) change.  Refused without `--proportional-font on`
(also with `control`) and with `--prop-font-place gap1`; the default is off where the build cannot take it.  Proof: `tools/test_cellprop.py`; diagnosis and numbers: `docs/layout-issues.md` s19.

### 9.18 `--clip-lead-space on|off` (commentary clip separator, default follows `--cell-prop`, not booted)
`build_patch.bcast_clip_text` / `do_bcast(..., lead_space)`: the blank between two consecutive commentary (BCAST) clips is written IN FRONT of the clip (one blank before every clip that starts with a letter, digit or opening mark, none before `, . ; : ! ? ) ] } '`, nothing appended) instead of AFTER it (old rule: one trailing blank after every clip but the name callouts, which gave `SuzukiCut out` and `Grampus ,`).  Needs `--cell-prop on`: only that engine skips a blank at column 0 (first clip of an utterance, line start after a wrap); an explicit `on` without it is refused in `check_flag_combos` and `build_patches`.  Names and team names are not special (they follow `The one to watch,` / `Seoul FC vs` and need the blank in front like any clip).  Details, counts and the shortened 15-letter epithets: `docs/text-sources.md` s6.1.  Proof: `tools/test_bcast.py` (`ClipSeparator`), `tools/test_bldflags.py`, read back with `tools/re/tx5_verify_bcast.py ... --blank lead`.

## 10. Documentation index (docs owner, 2026-11-11)

Top level: `README.md` (project overview, build, test, repo layout), `doc/TRANSLATORS_NOTES.md` (the guide shipped with every release), `LICENSE` (GPL-3.0-or-later).
Status words: **current** = describes the code as it is; **study** = read-only analysis, see `docs/expansion/status.md` for what was built from it; **history** = kept for the derivation, the status note at its top says what replaced it.

| Area | Document | Status |
|---|---|---|
| Overview | `docs/pipeline.md` (this file: build, flags, index), `docs/helper-scripts.md` (every `tools/re/` prefix family), `docs/status-report.md` (end of stage 3: final discs, tests, what is unverified, next steps), `docs/playtest-checklist.md` (screen list for the next Flycast session), `docs/playtest-log.md` (what the user saw so far) | current |
| Translating | `docs/style-guide.md`, `docs/translation-workflow.md`, `docs/number-formats.md` (Oku / Man money), `translation/glossary.tsv` (includes Oku, Man, Yen), `docs/uncovered-text.md` (table records), `docs/hw-relocation.md` | current |
| Text engine and font | `docs/text-engine.md`, `docs/font.md`, `docs/font-hook-notes.md`, `docs/font-widths.md`, `docs/window-widths.md`, `docs/pixel-widths.md`, `docs/proportional-font.md`, `docs/proportional-font-review.md`, `docs/patch-engine.md` | current (each has the facts; `text-engine.md`, `font-widths.md`, `pixel-widths.md` carry a status note) |
| Layout | `docs/layout-issues.md` (lists, panels, club-name guard in section 9) | current |
| Formats and RAM | `docs/formats.md`, `docs/overlay-text.md`, `docs/text-sources.md`, `docs/string-pools.md`, `docs/memory-map.md`, `docs/textures.md` | current |
| Art | `docs/art-translation.md`, `docs/art-group7.md`, `docs/texture-injection.md`, `docs/art-sample/` | current |
| Disc and shipping | `docs/disc-layout.md`, `docs/xdelta-release.md`, `docs/RELEASING.md` | current |
| Capacity | `docs/capacity-ratio.md`, `docs/capacity-design.md` | history (the plan was carried out as repack / `--append-safe` / relocation) |
| Capacity | `docs/trans-bank.md` | history (design only, never built) |
| Font design | `docs/font-patch-design.md` | history (superseded by `docs/proportional-font.md` and `tools/fontpatch.py`) |
| Expansion studies | `docs/expansion/disc-layout.md`, `overlay-memory.md`, `field-widths.md`, `patch-toolkit.md`, `save-format.md`; table of results: `docs/expansion/status.md` | study |

Where the numbers come from: record and translation counts from `python -I -X utf8 tools/transmerge.py status`; patch and test figures are quoted with the date they were measured, so re-run the tool before relying on one.
