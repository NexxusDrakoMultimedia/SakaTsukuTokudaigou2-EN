# Contributing

Thank you for helping with the English patch for **Sakatsuku Tokudaigou 2: J.League Pro Soccer Club o Tsukurou!** (Sega Dreamcast, Japan).
Everyone taking part is expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).  Players should read `README.md` and `doc/TRANSLATORS_NOTES.md` first; this file is for people who want to change something.

## Legal note (please read)

* This project ships **patches only**.  You need your own legally obtained dump of the Japanese disc to build or test anything.  The repository and every release contain no game data and no original Sega pixels.
* Do **not** ask for, share, post or attach the game, a disc image, a patched disc, files extracted from the disc, or a save, save state or RAM dump made from a patched disc.  Issues and pull requests that contain them will be closed.
* The Japanese text read from your disc stays on your machine (`translation/*.jsonl` is git-ignored).  Do not commit it.  The public form `l10n/*.jsonl` holds English and hashes only.
* Unofficial fan translation, not affiliated with the owners of the game, clubs or competitions.

## Ways to help

| Help | How |
|---|---|
| **Test** | Play the patched game (so far only Flycast has been tested; real hardware and other emulators are explicitly wanted) and report what you see.  Reports of a full season (matches, training, news, save/load, ending) are the most useful.  Method: `docs/playtest-checklist.md`. |
| **Report a problem** | See "Reporting a bug" below. |
| **Fix or improve the English** | Wrong, clipped or awkward text; a better short form; a glossary term.  See "Translation workflow". |
| **Art** | Repaint lettering on textures (`docs/art-translation.md`, `docs/texture-delta.md`). |
| **Tools** | The build, patch and verification tools in `tools/` (Python, standard library only). |
| **Docs** | Corrections to `docs/` and `README.md`. |

Style choices (honorifics, Japanese name order, western money format and similar) are planned as **optional layers**, off by default (`ROADMAP.md`); the layer mechanism is not built yet, so please discuss such ideas in an issue before writing code.
Efficiency and space work belongs in the base build.  Open questions (for example `Grampus` vs `Grampus Eight`) are listed in `docs/style-guide.md` and the README known issues.

## Reporting a bug

Open an issue: https://github.com/NexxusDrakoMultimedia/SakaTsukuTokudaigou2-EN/issues .  Please include:

* the patch version (for example `0.1.0-beta.1`) and the form of dump you applied it to (BIN/CUE, GDI or volume ISO);
* the output of `python apply_patch.py <dump> --verify` (it says original, already patched or wrong dump);
* the emulator and its version, or the hardware (a real Dreamcast with GD-ROM or a burned disc);
* for a text or layout problem: the screen, how you reached it, the exact text you saw and a screenshot of the emulator window only;
* what kind of problem it is: clipped or overflowing text, wrong text (Japanese, garbage, a wrong number or unit), or a crash or hang (note the last button pressed and the frame it froze on).

Faint tick marks around letters in Flycast are a texture-filter artifact; set texture filtering to nearest-neighbour (`doc/TRANSLATORS_NOTES.md`).  Please do not attach saves or save states (they contain game data); describe the state instead.
For a security problem (for example a crafted patch file that crashes `apply_patch.py`), do not post exploit details publicly: open an issue saying only that you have a security report, and a maintainer will arrange a private channel.

## Development setup

Python 3.11+ (the player-side `apply_patch.py` runs on 3.8+).  Standard library only, except the art tools (`Pillow`, `numpy`) and a few research helpers (`capstone`).  Optional: xdelta3 on `PATH`, about 6 GB free under `build/` for a release build.
**Run every script as `python -I -X utf8 <script>` from the repository root.**

```
python -I -X utf8 tools/setup_from_disc.py "<your .cue>"     # verify your disc, extract, import, apply texture deltas (~2.5 min)
python -I -X utf8 tools/build_patch.py --dry-run --strict     # what would fail or be skipped (no disc is written; seconds to a couple of minutes)
python -I -X utf8 tools/build_patch.py --repack on --share dup --append-safe --proportional-font on --refit on --align-fix on --open-font on --small-prop on --strict --out build/trial/mine --name mine
python -I -X utf8 tools/test_X.py                             # each tool has a self-test; many take --quick
```

The pipeline is described in `docs/pipeline.md` (index in section 10).  Without the disc you can still read everything, run `tools/test_release.py` and similar synthetic tests, and edit `l10n/*.jsonl` (see below).
The release process is maintainer-only (`docs/RELEASING.md`).

## Translation workflow

1. Set up the working form from your own disc (above).  Edit only the `en` field of `translation/*.jsonl` records, by the tools: batches go through `tools/transcheck.py RESULT.json` (must exit 0) and `tools/transmerge.py merge RESULT.json`;
   layout-heavy text through the `tools/textfmt_*.py` helpers.  Never change `id`, `ja`, `max_bytes`, `refs` or `ctx`.
2. Check the build: `python -I -X utf8 tools/build_patch.py --dry-run --strict`, then the tests that match your change (`test_junk`, `test_l10n`, `test_transwork --quick`, ...).
3. Export: `python -I -X utf8 tools/l10n.py export`.  This rewrites `l10n/` and `l10n/MANIFEST.json`; it refuses to write Japanese.  Commit **only** `l10n/` (and `translation/glossary.tsv` / `translation/art/` when you changed them), never `translation/*.jsonl`.
4. Without a disc: you may edit the `en` of a record in `l10n/*.jsonl` directly (records are matched by `id` and the `jah` hash on import), but you cannot run the checks above, so a maintainer will re-check it.  A list of "record id, new English" in an issue also works.
5. Never write English over a record that is not text (pointer, struct, code).  Leave it `en` empty with `skip`.  `docs/hang-investigation.md` section 9 explains the beta.1 goal-crash; `tools/test_junk.py` guards it.

Rules in short (full text: `docs/style-guide.md`; the glossary `translation/glossary.tsv` wins over local taste):

* British/Australian English (colour, centre, defence); "match", "pitch", "kit", "supporters"; Manager vs Coach; club (organisation) vs team (squad).
* ASCII only in game text; no `\`, `~`, and no `@`, `=`, `#`, `%` outside control tokens, which must stay unchanged and in order.  Byte budget `len(en)+1 <= max_bytes`; dialogue is 39 cells x 3 lines with manual line breaks.
* Names are Given Family in Hepburn without macrons and without honorifics.  The Japanese flavour stays (money `13 oku 1500 man`, kyu/dan ranks, `-gun`/`-cho`/`-mura`).
* Consistency over elegance: the same Japanese gets the same English.  Put new terms in the glossary in the same change.

Textures are committed only as deltas against the original: `tools/texdelta.py make`, never the `.pvr` files (`docs/texture-delta.md`).  Every opt-in build flag must leave default output byte-identical when off.

## Pull requests

`main` is the only branch.  Fork, make a branch, open a pull request against `main`; keep one logical change per request.

- [ ] No game data, Japanese text, saves, RAM dumps, `translation/*.jsonl`, `translation/textures/`, `build/`, `dist/` or `extracted/` in the diff (`git status` and `git diff --stat`).
- [ ] No personal data (e-mail addresses, user-name paths, tokens).
- [ ] The relevant `tools/test_*.py` pass and `build_patch.py --dry-run --strict` reports 0 failed; say which you ran and which you could not.
- [ ] `l10n/` was produced by `tools/l10n.py export`, not by hand (or you say so); `MANIFEST.json` is consistent.
- [ ] Line endings of each file unchanged (`.gitattributes` is `* -text`; most files LF, `CHANGELOG.md` and a few docs CRLF).
- [ ] Python run as `python -I -X utf8`; no new third-party dependency in `tools/` without discussion.
- [ ] Licence: new files fit the map in `REUSE.toml` (add an entry if not); code files carry the SPDX header used by their neighbours.
- [ ] `CHANGELOG.md` has a line under `## [Unreleased]` (Added, Changed, Fixed, Known issues; [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/)), or say that a maintainer should write it.  Versions follow [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html) (rules: `docs/RELEASING.md` section 1); do not change `tools/VERSION`.
- [ ] Claims about the game are labelled as tested in an emulator, tested in a simulator, or untested.

Commit messages: imperative, capitalised subject without prefix or full stop (about 70-80 characters), a blank line, then a wrapped body saying what changed, why and how you checked it.  No sign-off line is required.

## Licensing of contributions

By contributing you agree that your contribution is licensed under the licence that already applies to that part of the repository (`REUSE.toml`; "inbound = outbound"):

| Contribution | Licence |
|---|---|
| Code, tooling, tests | GPL-3.0-or-later |
| English text, glossary, art specs, repainted lettering and texture deltas, documents | CC-BY-SA-4.0 |
| Font bitmaps (`translation/fonts/`) | OFL-1.1 |

You keep the copyright in your work; the licence is what lets the project ship it.  Only submit work you made yourself or that you may license this way.  The original game is not licensed by this project and nothing of it may be contributed.
Credit line for reuse of the text and art: "SakaTsuku2-EN project, Nexxus Drako Multimedia, CC BY-SA 4.0".  To be named in `CONTRIBUTORS.md`, see that file.

## Questions and discussion

GitHub issues: https://github.com/NexxusDrakoMultimedia/SakaTsukuTokudaigou2-EN/issues .  Community Discord: https://discord.gg/7DNrGye9TZ .
AI coding agents: read `AGENTS.md` first.
