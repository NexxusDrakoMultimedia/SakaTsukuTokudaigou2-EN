# AGENTS.md

Guidance for AI coding agents (and a quick orientation for humans) working in this repository.  Contributor-facing rules are in `CONTRIBUTING.md`; this file is the short, strict version.

## What this is

An English translation patch for **Sakatsuku Tokudaigou 2: J.League Pro Soccer Club o Tsukurou!** (Sega Dreamcast, Japan, HDR-0183).  The repository holds the reverse-engineered tooling, the English text and the repainted textures.
It ships **xdelta patches only**, applied by players to their own dump.  It contains **no game data**: no disc, no extracted files, no original Sega pixels.  Version: `tools/VERSION` (single source of truth).

## Hard rules (never break these)

* **Never commit, tag, push, bump `tools/VERSION`, build a release or publish anything unless the maintainer explicitly tells you to.**  Edit the working tree and report.  Release steps are in `docs/RELEASING.md` (maintainer only).
* **Do not edit `CHANGELOG.md`** unless asked; do not hand-edit generated files (`l10n/MANIFEST.json`, `l10n/textures/MANIFEST.tsv`, `l10n/disc-files.tsv`).
* **Never write to the player's dump** (the `.bin`/`.cue`/`.gdi`/`.iso` files, the repo root may hold the owner's own copy) or to `extracted/`.  Read only.  Build output goes under `build/`, scratch work under a temp directory.
* **Do not start an emulator** (Flycast, `tools/emu/`) unless the user asks.  Use `tools/sh4sim.py` and the disc verifiers instead, and say plainly what was and was not tested in play.
* **Never commit game data or Japanese source text**: discs, extracted files, saves, RAM dumps, `*.pvr`/`*.zar`/`*.tbd` etc., `translation/*.jsonl`, `translation/refit/*.jsonl`, `translation/textures/`, release bundles.  `.gitignore` covers them; do not work around it.  The public form `l10n/*.jsonl` must contain no Japanese (the exporter refuses).
* **No personal data in files**: no personal e-mail addresses, Windows user-name paths, tokens or keys.  Contact goes through GitHub issues and the Community Discord (https://discord.gg/7DNrGye9TZ).
* **No inline or heredoc Python.**  Write a script to a file, then run it.  Keep throwaway scripts out of the repo (scratch directory), or put one-shot research scripts in `tools/re/`.
* **Never write English over a pointer or binary record.**  A record whose original bytes are a pointer, struct or code must stay `en` = `""` with `skip: true`.  The beta.1 goal-crash came from `---` written over `GAME.BIN#82138` (`docs/hang-investigation.md` section 9; guard `build_patch.is_binary_record`; test `tools/test_junk.py`).
* Do not claim something works in game without a playtest.  The docs label claims PROVEN / INFERRED / UNKNOWN / UNPROVEN and date their counts; keep that habit.

## Setup and commands

Python 3.11+ for development (the player-side `apply_patch.py` runs on 3.8+).  The tools use only the standard library, except the art tools (`Pillow`, `numpy`) and a few research helpers (`capstone`).
**Run every script from the repo root as `python -I -X utf8 <script>`.**  Optional: xdelta3 on `PATH` (cross-check of patches), about 6 GB free under `build/` for a release build.

```
# set up the local working form from your own disc (extracts, imports to translation/, applies texture deltas; ~2.5 min)
python -I -X utf8 tools/setup_from_disc.py "<your .cue>"
python -I -X utf8 tools/l10n.py stats                 # live counts (doc counts are dated snapshots)
python -I -X utf8 tools/l10n.py export                # working form -> public form (l10n/), rewrites MANIFEST.json
python -I -X utf8 tools/l10n.py verify --full         # round-trip proof (~1 min)

# fast check of what the build would fail or skip (no disc written; seconds to a couple of minutes)
python -I -X utf8 tools/build_patch.py --dry-run --strict

# standard trial build (the release flags live in tools/release.toml [build] standard_flags)
python -I -X utf8 tools/build_patch.py --repack on --share dup --append-safe --proportional-font on --refit on --align-fix on --open-font on --small-prop on --strict --out build/trial/mine --name mine
```

Every opt-in build flag must leave the default output byte-identical when off (`tools/re/bld_cmp_default.py`).  `--prop-scale` is off in the standard build; `--money-style western` is not usable and must not be offered.

### Tests

`python -I -X utf8 tools/test_X.py` (40 scripts in `tools/`, each ends with a pass summary; many take `--quick`).  There is no CI and no test runner; run the ones that match what you touched.

| Changed | Run |
|---|---|
| any translation data or `l10n/` | `test_junk`, `test_l10n` (`--full` before export changes), `test_transwork --quick`, `test_gap` |
| build flags, layout, font, money | `test_bldflags`, `test_layoutpatch`, `test_nameentry`, `test_refit`, `test_hwguard`, `test_smallprop`, `test_open_font` |
| textures | `test_texdelta` (`--full` for the whole set), `test_texinject`, `test_pvr` |
| patching, releases, licences | `test_vcdiff`, `test_release` (fast, synthetic disc), `test_bincue2iso` |
| everything | `test_pipeline` (end to end, about 3 min, 3.5 GB scratch, needs the disc) |

Some tests need the owner's disc or the working form (`extracted/`, `translation/`) and cannot run in a fresh clone; say so in your report instead of skipping silently.

## Layout

| Path | What |
|---|---|
| `l10n/` | public translation: English `en`, record ids, `jah` hashes, `textures/` deltas, `MANIFEST.json` (committed) |
| `translation/` | working form with Japanese read from the player's disc (local, git-ignored); tracked: `glossary.tsv`, `art/`, `fonts/`, `refit/` docs and tables |
| `tools/` | pipeline and tests; `tools/re/` research one-shots (none imported by the build); `tools/emu/` Flycast scripts |
| `docs/`, `doc/` | documentation (index: `docs/pipeline.md` section 10); `doc/TRANSLATORS_NOTES.md` is the player guide shipped in releases |
| `build/`, `dist/`, `extracted/` | generated, git-ignored |

## The l10n round trip

Edit the **working form** (`translation/`) with the tools (`transcheck.py`, `transmerge.py`, `textfmt_*.py`), then run `tools/l10n.py export`.  Commit only `l10n/`; check that `git diff --stat` shows no `translation/` path.
Do not mass-rewrite `l10n/*.jsonl` by hand.  Bytes must be exact: `.gitattributes` is `* -text` because the files and deltas are hashed.  Keep each file's line endings (most files are LF; `CHANGELOG.md`, `docs/pipeline.md`
and `docs/art-translation.md` are CRLF; new Markdown is LF).  Textures are committed only as deltas (`tools/texdelta.py make`).  Many files are shared between concurrent workers, so touch only the files your task names.

## Translation rules (normative: `docs/style-guide.md`; glossary `translation/glossary.tsv` wins)

* British/Australian English; ASCII only in game text (0x20-0x7E; no curly quotes).  Never type `\`, `~`, or `@`, `=`, `#`, lone `%` outside control tokens.  Keep control tokens (`@Y/ ... @`, `=K/ ... =`, `%s %d`, `#sname#`, `<XX>`) in the same multiset and order.
* Byte budget `len(en)+1 <= max_bytes`; dialogue window 39 cells x 3 lines, break per character, insert `\n` yourself.  Edit only `en`, never `id`, `ja`, `max_bytes`, `refs`, `ctx`.
* Names: Given Family, Hepburn without macrons, no honorifics in the default build.  Keep the Japanese flavour on purpose (money `13 oku 1500 man`, kyu/dan, `-gun`/`-cho`/`-mura`).
  Style preferences are optional layers, off by default (`ROADMAP.md`); do not change the default for taste.  New terms go into the glossary in the same change.

## Verify before you report

1. `build_patch.py --dry-run --strict` (0 failed), the tests for what you touched (table above), `tools/transcheck.py` for text batches.
2. For build changes: a scratch build under `build/`, `tools/verify_disc.py`, and the patch digest line compared with a release build (every flag off must stay byte-identical).
3. State what was run, what was not, and that nothing was tried in an emulator.

## Licences (`REUSE.toml` is the map)

Code and tooling: **GPL-3.0-or-later**.  English text, glossary, art specs, texture deltas and documents: **CC-BY-SA-4.0**.  Font bitmaps (`translation/fonts/`): **OFL-1.1**.  `CODE_OF_CONDUCT.md`: **CC-BY-4.0** (Contributor Covenant 2.1).
The original game is **not licensed** by this project.  Credit line: "SakaTsuku2-EN project, Nexxus Drako Multimedia, CC BY-SA 4.0".  A new path needs a `REUSE.toml` entry if the default does not fit.

## Commits (only when the maintainer asks)

Imperative, capitalised subject without prefix or full stop (about 70-80 characters), a blank line, a wrapped body saying what, why and how it was verified (name the paths and tests).  `main` is the only branch.
End with the attribution trailer the session gives you (the existing history carries `Co-Authored-By: Claude ... <noreply@anthropic.com>`).  Do not add `Signed-off-by` lines; the project does not use them.
