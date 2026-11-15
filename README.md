# SakaTsuku Tokudaigou 2 - English patch

**Version 0.1.0-beta.1 (beta), 2026-11-14.**  An English translation of **Sakatsuku Tokudaigou 2: J.League Pro Soccer Club o Tsukurou!**
(Sega Dreamcast, Japan, HDR-0183), made by reverse engineering the game and rebuilding the disc.  The project ships **patches only**:
xdelta (VCDIFF) files that a player applies to their own dump of the Japanese disc.

**This project contains no original Sega pixels and no game files.**  A release contains only xdelta deltas; the repainted textures are shipped as binary deltas against your own dump.  You need your own legally obtained copy of the game; please do not ask for,
share or upload the game, a patched disc or an image made from it.

| | |
|---|---|
| Status | **Beta.**  The whole game has English and was played in the Flycast emulator, but not every screen has been tested; see [Known issues](#known-issues) |
| Version history | [`CHANGELOG.md`](CHANGELOG.md) (Keep a Changelog 1.1.0, Semantic Versioning 2.0.0; the version is in `tools/VERSION`) |
| Platform | Sega Dreamcast; tested only in the **Flycast** emulator (not on a real console, not in other emulators) |
| Needs | your own dump of the Japanese disc (see [What you need](#what-you-need)) and Python 3.8+ for `apply_patch.py` (or any xdelta tool) |
| Patch format | xdelta3 / VCDIFF (RFC 3284), uncompressed; one set for BIN/CUE and GDI, one for a volume ISO |
| Licences | tools GPL-3.0-or-later, English text and repainted art CC-BY-SA-4.0, font bitmaps OFL-1.1 ([Licence](#licence)) |

## What it changes

* **Text:** menus, dialogue, help pages, news and reports, data tables (places, clubs, nations, leagues, sponsors, players, staff) and all 30,083 lines of the
  match commentary subtitles are English (British English; 396,813 of the 398,604 text records of the game).
* **Pictures:** 637 repainted textures: title screen and logo tiles, town and office menus, club-name plates, practice and match menus, unit pictures, the credits role titles and staff names.
* **Engine patches:** an English proportional font, English money text in the Japanese style (`13 oku 1500 man`), a bounded club-name builder (13 characters), layout fixes so that
  the longer English fits its boxes.
* **Kept Japanese on purpose:** oku / man money, kyu / dan ranks, place endings (`-gun`, `-cho`, `-mura`), the franchise name `SakaTsuku`.  People are Given name, then Family name, without honorifics
  (honorifics and Japanese name order are planned as options for 0.2.0).  `doc/TRANSLATORS_NOTES.md` explains the choices.

## What you need

A dump of the Japanese disc in one of these forms.  The patches are made against the dump this project was built against (Redump disc 27370 is its catalogue reference,
as noted in `tools/release.toml`); the hashes below are those of that dump, and the tooling has not compared them with the
Redump database.

| Form | Files |
|---|---|
| **BIN/CUE** | `Sakatsuku Tokudaigou 2 - J.League Pro Soccer Club o Tsukurou! (Japan).cue` and `... (Japan) (Track 1).bin` to `(Track 5).bin`, raw 2352-byte sectors |
| **GDI** | one `.gdi` with `track01.bin`, `track02.raw`, `track03.bin`, `track04.raw`, `track05.bin`, raw 2352-byte sectors (the same track data as the BIN/CUE) |
| **Volume ISO** | one `.iso` of 2048-byte sectors in which sector 0 is disc LBA 45000 (`SEGA SEGAKATANA` first, ISO9660 descriptor at sector 16) |

Source tracks (BIN/CUE names `... (Japan) (Track N).bin`; the same data as the GDI tracks):

| Track | Size (bytes) | CRC-32 | MD5 | SHA-1 |
|---|---|---|---|---|
| 1 | 5,597,760 | `1703a248` | `9cc52765bbbdce41e4c4f32dcc46f692` | `ec178640c03ab98de4d07b76fd5555417137def1` |
| 2 | 2,088,576 | `1859ea65` | `652a31166a58b8f933e8a924e7c88780` | `0ecd537e42946f3e74c80c9fcb8d0bccccfc96f1` |
| 3 | 14,916,384 | `33ea62d0` | `1d6a02990ebbb522851c6a2e3ca4f973` | `8a7c7484489d42896e3b73a8b2d4588720a3936d` |
| 4 | 12,519,696 | `d3caaa47` | `716b732bb8861b012ab5f157fa6aba88` | `fbdd698c67ee95d4223f9c873bb3697ee8447132` |
| 5 | 1,158,324,720 | `e5bc326c` | `f364436ea0f054ea3a6558ab4aec69ff` | `753b66f8a2a5553cce8abe804fa68145cf3522e4` |
| Volume ISO | 1,032,499,200 | `395d0590` | `1b836a438f963af1bba2cf41551bc0ef` | `62a9ccfd3a965328861e5b46fa71e5686642e5e1` |

Only tracks 3 and 5 are changed by the patch (track 1-2 are the low-density area, track 4 is audio).  A dump whose audio tracks or pregaps differ but whose game data
matches is still accepted by `apply_patch.py` (it converts through the volume ISO).  CHD, CSO, NRG, CDI, a single merged `.bin`, per-track 2048-byte `.iso` tracks and an ISO
that starts at LBA 0 are **not** supported: convert them to BIN/CUE, GDI or the volume ISO first.

## How to apply the patch

Download the release zip (`SakaTsuku2-EN-<version>.zip`) and unpack it.  Its own `README.md` has the exact hashes of that version.

**Easiest: `apply_patch.py`** (one file, Python 3.8 or newer, nothing to install; it contains the xdelta decoder):

```
python apply_patch.py "C:\Games\Sakatsuku\Sakatsuku.cue"
python apply_patch.py "C:\Games\Sakatsuku\disc.gdi"
python apply_patch.py "C:\Games\Sakatsuku\Sakatsuku.iso"
python apply_patch.py disc.gdi --verify        # only report: original, already patched, or wrong dump
```

It recognises the dump by content, checks every file against the recorded hashes and writes the patched copy next to your files, in the same format, in a new folder
(or `<name> (SakaTsuku2-EN).iso`).  Your files are never modified.  Boot the new `.gdi` or `.cue` in Flycast.

**By hand with an xdelta tool** (xdelta UI, Delta Patcher, `xdelta3`): the patches apply to the **raw tracks** (BIN/CUE and GDI: the patch files for track 3 and track 5) or to the
**volume ISO**, never to a CUE or GDI sheet.  Source = your track (or the ISO), Patch = the `.xdelta`, Output = a new file with the **same name as the original** in a new folder; then copy the
`.cue` / `.gdi` and the unchanged tracks next to it.

```
xdelta3 -d -s "<name> (Track 3).bin" "SakaTsuku2-EN-<version>-track03.xdelta" "patched\<name> (Track 3).bin"
```

Floating IPS and other IPS / BPS tools cannot apply xdelta patches.  Compare every output with the SHA-1 list in the release `README.md` or `HASHES.txt`.  If a result hash is wrong, delete the
output; do not use it.

## Emulators and hardware

* **Flycast** is the emulator this patch was developed and played in.  If you see faint tick marks around the letters, set the texture filtering to nearest-neighbour; the original disc shows them too
  (`doc/TRANSLATORS_NOTES.md` section 2.6).
* Other emulators were **not tested**.  A real Dreamcast was **not tested** either.

## Known issues

The list below is for 0.1.0-beta.1; the complete, current list is in [`CHANGELOG.md`](CHANGELOG.md).

* Tested in the Flycast emulator only.
* Flycast cannot load the volume-ISO form of the patched disc; load the `.cue` or `.gdi` instead.
* Practice screen, left strip: three labels overshoot the strip by 1 to 3 px.
* In-match team-instruction label (HOME / AWAY): the repaint is incomplete and a remnant of the old picture (`efend`) can show.
* Name tags: the tag icon can overlap the name; in-match player tags (above the players) show initials only.
* Player List: the `Age 31` field pokes past the edge of its panel.
* About 5 % of the commentary lines are longer than their clip; 13 px glyphs in the subtitles are drawn in a 12 px cell.
* Ordinals on the in-match rank tag read `1th`, `2th`, `3th`.
* `Grampus` vs `Grampus Eight` is an open naming question; some staff-name readings in the credits are best guesses.
* The standalone OPTION screen label still reads `Commentary Text` (the in-match options say `Subtitles`); the `Screen Saver` label indentation is off.
* Three refit forms exceed their field and fall back to the short form (`CHALMODE#3d804`, `EVENT#e06a8`, `NEWCON#2e11c`).
* Composed club names have an abbreviated town (13-character limit); two people with the same romanised name may look identical.
* Texture deltas: 236 of the 637 repainted textures are VQ-compressed; their delta carries a re-quantised codebook (new codebook data derived from the whole picture, not only our lettering).  This does not affect how the game runs; it is a known point of the delta route (`docs/texture-delta.md`).

## Reporting problems

Open an issue at https://github.com/NexxusDrakoMultimedia/SakaTsukuTokudaigou2-EN/issues .  Please give: the patch version, the dump form you applied it to, the output of
`python apply_patch.py <dump> --verify`, the emulator and its version, and for a text or layout problem the screen and how you reached it (a screenshot helps).
Do not attach the game, a disc image or a save made from a patched disc.

## Credits

* Translation, reverse engineering, tooling and repainted graphics: the SakaTsuku2-EN project, Nexxus Drako Multimedia.
* Thanks to Nexxus Drako and to the **Community Discord** (https://discord.gg/7DNrGye9TZ).
* English half-width glyphs: rendered from Roboto Condensed Medium, Copyright 2011 The Roboto Project Authors (https://github.com/googlefonts/roboto-classic), SIL Open Font License 1.1
  (`LICENSES/OFL-1.1.txt`, notice in `doc/NOTICE-fonts.md`).
* The VCDIFF code in `apply_patch.py` is adapted from the LMAST-Reverse project (same author); xdelta3 (Joshua MacDonald and contributors) cross-checks every patch.
* Staff names in the credits were romanised with the help of public credit databases (Sega Retro, MobyGames).
* The original game, its club and competition names belong to their owners; this is an unofficial fan translation and is not affiliated with them.

## Licence

| What | Licence |
|---|---|
| The tooling: everything in `tools/` (build scripts, `apply_patch.py`, `verify_dist.py`, `release.py`, the tests) | **GPL-3.0-or-later** (`LICENSES/GPL-3.0-or-later.txt`, `LICENSE`) |
| The translators' own work: the English text (the `l10n/` files, the glossary), the repainted textures and art specs, the documents (`README.md`, `CHANGELOG.md`, `doc/`, `docs/`) | **CC-BY-SA-4.0** (`LICENSES/CC-BY-SA-4.0.txt`) |
| The half-width Latin glyphs of the `--open-font on` build: `translation/fonts/` (bitmaps rendered from Roboto Condensed Medium) | **OFL-1.1** (`LICENSES/OFL-1.1.txt`) |
| The original game: its Japanese text, pictures, music and code | **Not licensed by this project.**  It belongs to its owners.  The repainted textures are new artwork painted over the game's own pictures: CC-BY-SA-4.0 covers only the new contribution, never the art underneath |

A release and this repository contain no original Sega pixels: the xdelta files contain only differences, and the repainted textures are stored as binary deltas against the owner's own dump (`l10n/textures/`, `docs/texture-delta.md`).  The public form of the translation (`l10n/`) holds English text, record ids and a SHA-256 prefix of each original Japanese string,
not the Japanese itself; the Japanese is read locally from the player's own disc (`tools/setup_from_disc.py`).  `REUSE.toml` is the machine-readable licence map (REUSE 3.x).
Credit line for CC-BY-SA reuse: "SakaTsuku2-EN project, Nexxus Drako Multimedia, CC BY-SA 4.0".  In plain words: you may share and adapt the translated text and art if you credit the project and
release your changes under the same licence; you may use and change the tools under the GPL; you need your own copy of the game to use any of it.

## For contributors

> Players: the release zip has its own `README.md` and the translators' notes (`doc/TRANSLATORS_NOTES.md`).  The rest of this file is for people working on the project.

* Python 3.11+ (the player-side `apply_patch.py` runs on 3.8+).  Run every script as `python -I -X utf8 <script>`.  The tools use only the standard library, except the art tools (`Pillow`, `numpy`) and a few
  research helpers (`capstone`).
* About 6 GB free under `build/` for a release build (a disc is 1.2 GB).  Optional: xdelta3 on `PATH` (cross-check of every release patch), Flycast for boot tests (`tools/emu/`).
* The translation is kept in two forms (`docs/l10n-format.md`): the **public form** `l10n/*.jsonl` (English, ids, hashes; committed) and the **working form** `translation/*.jsonl` (with the Japanese source
  text read from your own disc; local and git-ignored).  Set up the working form from your disc: `python -I -X utf8 tools/setup_from_disc.py "<your .cue>"`.  After editing the working form run
  `python -I -X utf8 tools/l10n.py export` so that only the public form is committed.

Build a trial disc (standard flags, `docs/pipeline.md` section 9):

```
python -I -X utf8 tools/build_patch.py --repack on --share dup --append-safe --proportional-font on --refit on --align-fix on --open-font on --small-prop on --strict --out build/trial/mine --name mine
```

A dry run (`--dry-run --strict`) lists every failed or skipped string without writing a disc.  Cut a release: `docs/RELEASING.md` (maintainer checklist), design and formats: `docs/xdelta-release.md`.

```
python -I -X utf8 tools/release.py --date YYYY-MM-DD [--version 0.1.0-beta.1] [--no-raw-patches] [build_patch flags]
python -I -X utf8 dist/<name>/verify_dist.py --source "<repo cue>" --built build/release/disc/SakaTsuku2-EN.cue --scratch build/verify_dist
```

Each tool has a self-test next to it (`python -I -X utf8 tools/test_X.py`; each ends with a pass summary); `tools/test_pipeline.py` runs everything end to end (about 3 minutes, 3.5 GB scratch).

| Path | Contents |
|---|---|
| `l10n/` | the public form of the translation: English, record ids, SHA-256 prefixes of the original strings, and `textures/` (the repainted textures as binary deltas against the original ones; `docs/l10n-format.md`, `docs/texture-delta.md`) |
| `translation/` | the working form (local, git-ignored `*.jsonl`) plus `glossary.tsv`, `art/` (repaint specs), `fonts/` (open font bitmaps), `textures/` (the repainted art as PVR: local, git-ignored, rebuilt from `l10n/textures/` and your own disc by `tools/setup_from_disc.py`) |
| `tools/` | the pipeline and its tests: `build_patch.py`, `textdb.py`, `font*.py`, `moneypatch.py`, `layoutpatch.py`, `refit.py`, `texinject.py`, `discbuild*.py`, `vcdiff.py`, `release.py`, `apply_patch.py`, `l10n.py`, `sh4sim.py` |
| `tools/re/` | research and helper scripts (`docs/helper-scripts.md`) |
| `tools/emu/` | Flycast launch and Lua scripts; only ever started by hand |
| `docs/` | the documentation; start at the index in `docs/pipeline.md` section 10 |
| `doc/` | `TRANSLATORS_NOTES.md`, the player guide shipped with every release |
| `build/`, `dist/`, `extracted/` | generated, git-ignored: trial discs, work files, release bundles, files read from the disc |
| `CHANGELOG.md`, `tools/VERSION` | the changelog and the version (single source of truth) |
| `LICENSE`, `LICENSES/`, `REUSE.toml`, `.gitignore` | GPL text, licence texts, licence map, ignore rules |
