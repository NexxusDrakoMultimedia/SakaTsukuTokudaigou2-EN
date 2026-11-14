# Cutting a release (maintainer)

Players want `README.md` (generated into every release). Design, formats, hash tables and limits: `docs/xdelta-release.md`.
Everything below runs from the repo root with `python -I -X utf8`. Nothing here commits, pushes or launches an emulator for you.

## 0. Before you start

* The translation is merged into `translation/*.jsonl` and nobody is rewriting it (the build only reads it).
* The changelog `CHANGELOG.md` and the licence folder `LICENSES/` (`[bundle] changelog`, `licenses_dir` in `tools/release.toml`) are bundled; see section 1 and the checklist in section 6.
* The translators' notes `doc/TRANSLATORS_NOTES.md` (path: `[bundle] translators_notes` in `tools/release.toml`) are written by the docs stage. While the file
  still contains the word `PLACEHOLDER`, `release.py` refuses to build; `--allow-placeholder` is for development bundles only.
* The Redump-style source disc (the 5 track files and the `.cue` in the repo root) is untouched; `tools/release.toml` holds its hashes (Redump 27370 as dumped; Redump's database was not consulted).
  After a re-dump: `python -I -X utf8 tools/release.py --print-source-toml`.
* ~6 GB free under `build/` (disc 1.2 GB, two volume ISOs 2 GB, scratch) and Python 3.11+. xdelta3 on PATH (or `C:\ProgramData\chocolatey\bin\xdelta3.exe`) for the cross-check; `--no-xdelta3` skips it (do not release without it).
* Decide the build flags: they are passed through to `tools/build_patch.py` (`--proportional-font on|off|control`, `--repack`, `--share`, `--append-safe`, `--textures-dir ...`). Without any build option `release.py` uses the standard flags of `tools/release.toml` `[build] standard_flags` (below); build options given on its command line replace that list.
  The standard release flags are `--repack on --share dup --append-safe --proportional-font on --refit on --align-fix on --open-font on --small-prop on --strict` (docs/pipeline.md section 9; with the command-line defaults of `build_patch.py` they equal the flags of the trial disc prop10j that was checked on screen: `--tag-fix on --scout-fix on --crowd-fix on --options-fix on --lin-center on --cell-prop on --clip-lead-space on --bcast-speed 1.9 --money-format on --prop-scale off --texture-policy exact`; the `flags:` line and the `patch digest` at the end of a build or `--dry-run` record it, prop10j = `33be84fd97cab42d34645bb3c049978ba7a2ddce`; `--refit on` also forces `--hw-relocate on`; `--refit` and `--align-fix` are on by default since stage 8b, the others stay explicit).  `--align-fix on` needs `--proportional-font on`, variants A and the tail placement (a clear error otherwise); `--strict` makes `build_patch.py` exit 2 when any string failed or was skipped, which stops the release.  The club-name guard, the money text (`--money-format on`, jp style), the name-tag routine (`--tag-fix on`)
  and the layout patches are on by default.  Anything marked UNPROVEN in `docs/pipeline.md` (relocation, refit, `--prop-scale`, `--grow-overlays`, `--dedupe-files`) needs the Flycast test below with exactly those flags; `docs/playtest-checklist.md` is the list of screens. The flags are recorded in `MANIFEST.json` (`build.build_patch_args`).
* Decide whether to ship the raw track patches (BIN/CUE and GDI, 8 s apply) next to the volume-ISO patch, or only the ISO patch (`--no-raw-patches`: about 10 MB instead of 23 MB zipped, 21 s apply, `docs/xdelta-release.md` section 6).

## 1. Version (Semantic Versioning 2.0.0) and changelog (Keep a Changelog 1.1.0)

`tools/VERSION` is the single source of truth (one line, a semantic version; `0.1.0-beta.1` for the first public release, `0.1.0` stays free for the final one). `release.py` reads it (`--version` overrides it for a trial) and writes it into `MANIFEST.json`, the `VERSION` file of the bundle, the patch file names and the folder `dist/SakaTsuku2-EN-<version>/`; `apply_patch.py` and `verify_dist.py` read the version from the bundle's manifest, and `verify_dist.py` checks that `VERSION` equals it. Use `-beta.N` / `-rc.N` for pre-releases and `-dev` for trial bundles; a real release has no suffix (`SakaTsuku2-EN-0.1.0`).

What bumps which number for a patch of this kind (the "public API" is: the dump forms the patch supports, what a player has to do, and the save data):

| Bump | When | Examples |
|---|---|---|
| **MAJOR** (X.0.0) | a player must redo something or an older version no longer fits: an incompatible save or data format change, a different set of supported source dumps (new hashes required), a different way to apply it, a licence change that removes rights | the patch starts to rewrite save data; support for a dump form is dropped |
| **MINOR** (0.X.0) | a new, backwards-compatible feature or option, or a large addition of translated content | a new optional flag (honorifics, Japanese name order: 0.2.0), a new screen translated, a new art group |
| **PATCH** (0.0.X) | anything else that changes the patch bytes or hashes: translation corrections, polished short forms, rebuilt art, build fixes | a typo fix: the result hashes in `MANIFEST.json` change, so the version must change |

Rules: if the patch bytes (the result hashes) change, the version changes, at least a patch bump; never re-publish different bytes under the same version. A new optional feature that is off by default is a minor bump even if the default output is byte-identical. While the major number is 0, the project may still change; it moves to 1.0.0 when the translation is considered complete and tested on screen. Pre-release order follows SemVer (`0.2.0-beta.1` < `0.2.0`).

`CHANGELOG.md` (repo root) follows Keep a Changelog: `## [Unreleased]` on top collects changes as they are made (Added / Changed / Deprecated / Removed / Fixed / Security, plus this project's `Known issues`); when you cut a release, rename it to `## [X.Y.Z] - YYYY-MM-DD` (the same date as `--date`), add a fresh empty `[Unreleased]`, and update the links at the bottom (`[Unreleased]` compares `vX.Y.Z...HEAD`, `[X.Y.Z]` points to the tag or the compare against the previous tag). `release.py` refuses a non-trial build whose version has no `## [X.Y.Z]` section, and bundles the file as `CHANGELOG.md`. `doc/CHANGELOG.md` only points to the root file. Keep a Changelog defines no heading for planned work: a short plain note (`Planned for 0.2.0, not in this release: ...`, the optional honorifics and name order) sits at the end of the release section, and `[Unreleased]` stays empty until the first change after the release. The release section of a pre-release lists the work done in total, not a development diary; its `### Known issues` bullets are copied into the bundle `README.md` (section 8) by `release.py`, so keep them one bullet per issue and accurate.

## 2. Check the tree

```
python -I -X utf8 tools/build_patch.py --dry-run --strict      # translation failures, 0.7 s
python -I -X utf8 tools/test_vcdiff.py                          # 135 checks, 6 s (incl. move-aware encoder, xdelta3 cross-checks)
python -I -X utf8 tools/test_release.py                         # 213 checks, 16 s, tiny synthetic disc, every apply_patch route, version / changelog / licence checks (counts as of 2026-11-14)
python -I -X utf8 tools/test_bincue2iso.py                      # 15 s, real disc
python -I -X utf8 tools/test_pipeline.py                        # existing pipeline test, about 3 minutes, 3.5 GB
```
`--strict` exits 2 when a string failed or was skipped: read the list (a release with failures keeps those lines in Japanese).

## 3. Build

```
python -I -X utf8 tools/release.py --date 2026-11-10 [--version 0.1.0-beta.1] [--no-raw-patches] [build_patch flags]
```
`--date` is required and must be a real calendar date from 1980 on (the tool never reads the clock; the zip entries carry it too). About a minute: hash the source, build the disc (`build/release/disc`), export both volume ISOs, make the patches (move-aware: relocated files stay small),
re-apply each with `tools/vcdiff.py` and with xdelta3 and compare SHA-1/SHA-256, prove that the raw tracks can be rebuilt from the patched ISO (`raw_rebuild` in the manifest), write `dist/SakaTsuku2-EN-<version>/` and the zip.
The bundle holds: the `.xdelta` files, `MANIFEST.json`, `HASHES.txt`, `SHA256SUMS`, `README.md`, `TRANSLATORS_NOTES.md`, `CHANGELOG.md`, `apply_patch.py` (ONE stdlib-only file with the decoder and disc code embedded), `verify_dist.py`, `LICENSE`, `LICENSES/` (GPL-3.0-or-later, CC-BY-SA-4.0, LicenseRef-Game-Content; set by `[bundle] licenses_dir`), `NOTICE.txt`, `VERSION`, `BUILD-SUMMARY.txt`.
`--reuse-build` redoes the packaging with the disc already in `build/release/disc`. `--cleanup-work` deletes the two exported ISOs afterwards.

Development bundle from an existing trial disc (no `build_patch.py`, README banner, nothing to publish):
```
python -I -X utf8 tools/release.py --date 2026-11-11 --built-disc build/trial/prop7/prop7.gdi --dev-name prop7 --out build/release_dev --work build/rel_work_dev --cleanup-work
python -I -X utf8 tools/release.py --print-dev-toml build/trial/prop7/prop7.gdi --dev-name prop7   # the [dev.prop7] table of release.toml
```
`release.toml` holds the result hashes of three trial discs, `[dev.prop5]` (stage 2), `[dev.prop6]` (stage 3 with the club-name guard) and `[dev.prop7]` (final, with the polished town short forms; the dev bundle `build/release_dev2` was made from it without `--allow-placeholder`), as development records only; the build compares a `--built-disc` against the table named by `--dev-name` and says whether it still matches.  `--allow-placeholder` is only needed if `doc/TRANSLATORS_NOTES.md` contains the marker `PLACEHOLDER` again (the guide is real text now); a real release never uses the flag.

Any mismatch aborts with a message: source hash differs (which track, which value), a re-applied patch differs from the built file, `build_patch.py` fails (log `build/release/build.log`), notes missing or PLACEHOLDER.

## 4. Check the output

* `dist/<name>/BUILD-SUMMARY.txt`: failed / skipped strings, moved files, `disc: ... end LBA a -> b`. If the end LBA grew, the disc is larger than a real GD-R (emulator only; `README.md` says so automatically).
* The patch sizes the script printed (`docs/xdelta-release.md` section 6) and the `moved` figure per patch (`N sectors in M moved runs`). A raw patch close to the size of the track means something is wrong.
* `HASHES.txt` / `MANIFEST.json`: source hashes equal the table in `docs/xdelta-release.md`; "changed" tracks are the ones you expect; `raw_rebuild` has an entry for track 3 and 5 (else route B is off).
* The acceptance test, run from the bundle (or `tools/verify_dist.py --dist <bundle>`):
```
python -I -X utf8 dist/<name>/verify_dist.py --source "<repo root cue>" --built build/release/disc/SakaTsuku2-EN.cue --scratch build/verify_dist
```
  (2 minutes, 6 GB scratch, deleted at the end). Without arguments it only checks the folder (SHA256SUMS, manifest, patch magic, single-file/stdlib-only `apply_patch.py`, README hashes, notes not PLACEHOLDER). With `--source` it plays the player with the bundle's
  own `apply_patch.py`: BIN/CUE route A and route B, BIN/CUE `--to iso`, a synthetic GDI route A and B, the cooked ISO; every output must have the promised hash and, with `--built`, be byte-equal to the built disc.

## 5. Test in the emulator (manual)

Run `apply_patch.py` yourself on the source disc exactly as a player would (`python dist/<name>/apply_patch.py "<cue or gdi>"`), then boot the patched `.gdi`/`.cue` in Flycast (see the Flycast notes in the project memory: exe path and config) and walk through the title screen,
a menu with translated text and, if used, the proportional font. No release before this boot test has been done; the tooling can only prove the bytes, not that the game runs (`docs/disc-layout.md` UNKNOWN list).

## 6. Release checklist (nothing here is done by the tools: commit, tag, push and the GitHub release are manual and only on the maintainer's go)

Before the build
- [ ] `translation/` merged; `python -I -X utf8 tools/build_patch.py --dry-run --strict` clean (section 2).
- [ ] Tests green (section 2): `test_vcdiff`, `test_release` (also checks the version, the changelog and the licence files), `test_bincue2iso`, `test_pipeline`.
- [ ] `tools/VERSION` set to the release version; the bump follows the table in section 1.
- [ ] `CHANGELOG.md`: `[Unreleased]` turned into `## [X.Y.Z] - YYYY-MM-DD`, new empty `[Unreleased]`, links at the bottom updated; the notes of this release read correctly.
- [ ] `doc/TRANSLATORS_NOTES.md` has no `PLACEHOLDER`; its credits / licence section (section 10) is current; `README.md` licence table current.
- [ ] Licence files: `LICENSES/GPL-3.0-or-later.txt`, `LICENSES/CC-BY-SA-4.0.txt` and `LICENSES/LicenseRef-Game-Content.txt` present, `REUSE.toml` covers every new path (run `reuse lint` if the tool is installed). The CC-BY-SA text was copied from the author's Last-Combustion repository (REUSE/SPDX text, 18,545 bytes, sections 1 to 8); compare it once with https://creativecommons.org/licenses/by-sa/4.0/legalcode.txt when online.
- [ ] No game data in the tree that will be published: nothing from `extracted/`, `build/`, dumps or `*.bin`; the PNGs that show original game art (`docs/art-sample/club_edit_menu_*.png`, `tools/re/art6/plate_menu.png`, `tools/re/datatext/png/`) are git-ignored (regenerate them locally); `translation/textures/` is git-ignored too (the repaints are published as `l10n/textures/*.vcdiff` deltas only).
- [ ] Source-disc hashes in `tools/release.toml` still match (`--print-source-toml`).
- [ ] Flycast boot test of the exact build flags done (section 5).

Build and check
- [ ] `python -I -X utf8 tools/release.py --date YYYY-MM-DD --no-raw-patches|(default) <standard flags>` (section 3) without `--allow-placeholder` and without `--built-disc`; the `dist/SakaTsuku2-EN-X.Y.Z/` folder and the `.zip` + `.zip.sha256` exist.
- [ ] `BUILD-SUMMARY.txt`, `HASHES.txt` and the patch sizes look right (section 4); `MANIFEST.json` `git_commit` is the release commit without `+dirty`.
- [ ] `verify_dist.py --source ... --built ...` passes (section 4); the bundle holds `CHANGELOG.md`, `LICENSE`, `LICENSES/`, `NOTICE.txt`, `VERSION`.
- [ ] The zip's SHA-256 is recorded (`.zip.sha256`).

Publish (only on an explicit go)
- [ ] Commit the version, changelog, `translation/`, docs and the code the build used (so `MANIFEST.json` records a clean commit); rebuild if you committed after building.
- [ ] Tag: `git tag -a vX.Y.Z -m "SakaTsuku2-EN X.Y.Z"`, signed (`git tag -s ...`) when a signing key is configured; the tag name matches the changelog links.
- [ ] Push the commit and the tag.
- [ ] GitHub release for the tag: title `SakaTsuku2-EN X.Y.Z`; notes = the `## [X.Y.Z]` section of `CHANGELOG.md` plus `README.md` section 1 (which dumps work) and the SHA-1 of the Redump-style source; attach `dist/SakaTsuku2-EN-X.Y.Z.zip`, `dist/SakaTsuku2-EN-X.Y.Z.zip.sha256` and a `SHA256SUMS` file (the bundle's own `SHA256SUMS` covers the files inside the zip). Mark pre-releases (`-beta.N`) as pre-release. The release contains no original Sega pixels; never upload anything from `build/` or a dump.
- [ ] Download the published zip once and run `verify_dist.py` on it.
- [ ] After the release: open the next `## [Unreleased]` work; if a version bump is needed for the next development line, do it with its first change (not before).

## 7. Troubleshooting

| Symptom | Cause / action |
|---|---|
| `the source disc ... is not the dump the patches are built against` | a changed source track; the message names track, size or hash. Restore the Redump files |
| `tools/release.toml has no recorded hashes` | `--print-source-toml`, paste the tables |
| `... still contains the marker PLACEHOLDER` | the docs stage has not replaced `doc/TRANSLATORS_NOTES.md`; for a development bundle pass `--allow-placeholder` |
| `--no-raw-patches: track N cannot be rebuilt from the patched ISO` | the built track holds sectors that are not canonical Mode 1; ship the raw patches |
| patch for track 5 as large as the track | files relocated without matching user bytes, or the whole disc rewritten; see `BUILD-SUMMARY.txt` `moved` lines |
| `xdelta3 did not reproduce the built file` | a bug in `tools/vcdiff.py` or an old xdelta3; run `tools/test_vcdiff.py` |
| hashes of results change between two runs with the same DB | not expected: the build is deterministic (`patch digest` in the summary); compare the digests |
| player says their GDI differs | `README.md` section 5; a differing audio track or pregap alone no longer matters (apply_patch.py falls back to the ISO route when the game data matches) |
| player reports a half-written output folder | not expected any more: `apply_patch.py` checks every patch file (present, SHA-1) before writing, and removes the files of a failed run; a damaged download is reported as `damaged or not the patch of this release` |
| `verify_dist.py`: `no file outside SHA256SUMS` | something was dropped into the release folder (a `__pycache__` is ignored); remove it before uploading the folder, the zip never contains it |
