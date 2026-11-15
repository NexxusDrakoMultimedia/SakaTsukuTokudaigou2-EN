# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).  For a translation patch the version means
(details in `docs/RELEASING.md`, section 1): **major** = something a player must redo, or that breaks old saves or the
supported dump forms; **minor** = a new feature or option, or a large translation change; **patch** = anything else that changes the
patch bytes (corrections, rebuilt art).  Pre-releases carry a suffix (`-beta.1`).  The single source of the version is `tools/VERSION`.

## [Unreleased]

### Fixed

- The match-time crash: the console reset to the BIOS when a goal was scored.  Record `FLOW_PRG/GAME.BIN#82138` is a script pointer, not text, and the build had written `---` over it.  It and 16 more records of the same kind (a pointer, a struct field or code that the text extraction had read as Shift-JIS) are blank again, so the build keeps the original bytes; `build_patch.py` now refuses such a record by looking at the original bytes (`docs/hang-investigation.md`, section 9).  Confirmed in play: five matches and more than a dozen goals with no reset.
- The in-match Attack/Defend instruction labels being clipped (`Attack/D` and `efend`): the `sakusen` HUD texture is now painted one English word per original sprite cell (`Attack` | `Defend`, `Hold` | `Atk` | `Def`, `All` | `Defend`, `All` | `Attack`); on the two `All` rows the word is right-aligned so the gap to the second word is a few pixels.  The split was checked in Flycast; the cell coordinates themselves are inferred from the original art, not read from the game code.

### Changed

- Correction to the beta.1 "Money and units" entry: the annual report is not covered by the money-format hook.  Read that entry as "in every text, on the TV station card, in the finance screens and the income table; the annual report has its own English formats".  The annual report (NENREP) money amounts are English because the report's own money formats were translated in place; they are not handled by `--money-format` and print glued (`13oku 1500man`).
- Annual report: the attendance (head-count) lines are now English too, written in place in `NENREP.BIN`.  They keep the Japanese counting, `man` = 10,000 and `ppl` for people, e.g. `  1man 2345ppl`, ` 345ppl`, and the red negative form `@R/ 345ppl@`.  Decoded and run in the SH-4 simulator, not yet seen on screen; the long form is wider than the Japanese (162 px against 132 px).
- Name Entry: the ABC/123 tab now opens on the half-width letter pages (narrow `1-0 A-L M-X Y-Z a-l`, then `m-z`), with the full-width pages after them.  The Japanese disc opens it on the wide full-width letters.  Done by swapping four pointer words in `FLOW_PRG/N_ENTRY.BIN` (8 bytes, same size).  New build flag `--name-entry-order half-first|original` (default `half-first`; `original` restores the disc order).  Read from the overlay code only; not seen in game yet, and typing on the half-width pages is untested.

### Known issues

- Annual report (year-end club report): money amounts use the report's own English formats instead of the money hook, so they are glued (`13oku 1500man`, `58 man`, `5000 Yen`), with the red form for negatives (`@R/` kept).  Not yet seen on screen.
- The same head-count formats in other overlays (`CHALMODE`, `DRSHRANK`, `DRSISEKI`, `DRSJAPAN`, `DRSLIST`, `DRSSRANK`, `GETREP`, `PL_EDIT`, `SELNAT`, `TV_EVENT`) are still Japanese and show kanji (万, 人).

## [0.1.0-beta.1] - 2026-11-14

Initial pass of the English translation of Sakatsuku Tokudaigou 2 - J.League Pro Soccer Club o Tsukurou! (Sega Dreamcast, Japan, HDR-0183; Redump disc 27370), released as a beta: it covers the whole game, was played in the Flycast emulator, and still has the known issues listed below.

### Added

- **Text.**  English for 396,813 of the 398,604 text records of the game (the rest is mostly debug and binary text, left alone on purpose; 850 records are marked skip) and 38,390 "refit" forms, fuller spellings that the build uses where a field has room for them.  The build applies 396,819 strings with none failed and none skipped.  British English.  Covered: menus and option screens, dialogue, help pages, news and reports, data tables (places, clubs, nations, leagues, sponsors, players, staff), the name-entry screen and the pre-match, in-match and post-match texts.
- **Match commentary.**  All 30,083 commentary subtitle records (`/BCAST/BCAST.BIN`) are English: the announcer (7,498), three colour commentators (3,518, 3,320 and 3,267) and 12,480 name callouts.  Clips are joined with a leading blank so that names and team names read correctly (`Seoul FC vs Grampus`), and the subtitles are revealed 1.9 times faster so that the longer English text keeps up with the clip.
- **Names.**  People are shown Given name, then Family name (`Katsuo Ozaka`) in plain Hepburn romanisation without macrons and without honorifics; place endings (`-gun`, `-cho`, `-mura`) are kept.  Club words, J.League clubs, special teams and competitions follow the spelling of the game's own logo and banner art (`Red Diamonds`, `JEF United`, `Yokohama F Marinos`, `Asia Winners Cup`).  A bounded club-name builder keeps a composed club name within 13 characters.
- **Money and units.**  Amounts are shown the Japanese way, in oku and man (`13 oku 1500 man`, `6000 man`, `1 oku`, `0 Yen`), in every text, on the TV station card, in the finance screens, the annual report and the income table; the crowd line of the income table reads `1man 827ppl`.
- **Art.**  637 repainted textures in 221 game files: the title screen and logo tiles (`SA KA TSU KU`, `TOKU DAI GOU`, `SakaTsuku`, the tagline), the town and office menus, club-name plates, practice and pre-match menus, post-match tables, option values, in-match tag textures, unit pictures (oku, man, yen) and graph headers, the 15 credits role titles and the 41 staff names (romanised).  The textures are delivered as binary deltas against the player's own dump (`l10n/textures/`), not as pictures.
- **Fonts and layout.**  A proportional half-width English font (mean advance 10.65 px) instead of the fixed-width one, with its own glyphs: Roboto Condensed Medium bitmaps (SIL Open Font License 1.1), plus a narrower variant for the 16 px windows of the option and training screens.  Layout fixes so that the English fits: cell-count alignment of the shirt-number column and the player-card panel, name tags that show the family name, scout `Age` rows, centred narrow glyphs in the match intro, proportional commentary subtitles, the selected-option highlight of the in-match options, and window and field limits.  Half-width strings that do not fit their slot are moved into spare room (guarded so that data tables never move), which lets nine long club words print in full (`Avalanche`, `Monolith`, `Topolino`, `Colmillo`, `Corriente`, `Herencia`, `Panthera`, `Cielo`, `Rosa`).
- **Patch delivery.**  The release is a set of xdelta (VCDIFF) patches that a player applies to their own dump: for BIN/CUE, for GDI (the same raw track patches) and for a volume ISO.  `apply_patch.py` (one stdlib-only Python file, Python 3.8 or newer) recognises the dump by content, checks it against the recorded hashes and writes a patched copy next to it; `verify_dist.py` checks a download.  Every patch is re-applied with our own decoder and with xdelta3 when the bundle is built.  The bundle contains no original Sega pixels.
- **Build from source.**  The disc is rebuilt from the translation by `tools/build_patch.py` (flags documented in `docs/pipeline.md`); `tools/release.py` makes the bundle; `tools/l10n.py` and `tools/setup_from_disc.py` move the translation between its public form (`l10n/`: English, record ids and hashes of the original strings) and the local working form read from the player's own disc; 39 self-tests (`tools/test_*.py`).
- **Documentation.**  `README.md`, a player's guide and translators' notes (`doc/TRANSLATORS_NOTES.md`), the style guide and glossary, the release and maintenance guides (`docs/`).
- **Licences.**  Tooling GPL-3.0-or-later; English text, repainted art and documents CC-BY-SA-4.0; the font bitmaps OFL-1.1 (`LICENSES/`, `REUSE.toml`).  The original game's text, art, music and code belong to their owners and are not licensed by this project.

### Known issues

- Tested in the Flycast emulator only; not tested on real hardware or in other emulators.
- Practice screen, left strip: three labels overshoot the strip by 1 to 3 px.
- In-match team-instruction label (HOME / AWAY): the repaint is incomplete and a remnant of the old picture (`efend`) can show.
- Name tags: the tag icon can overlap the name.
- In-match player tags (the names above the players on the pitch) show initials only.
- Player List: the `Age 31` field pokes past the edge of its panel.
- About 5 % of the commentary lines are still longer than their clip and are cut off when the clip ends.
- Commentary subtitles draw 13 px glyphs in a 12 px cell (clamped to 12).
- Ordinals on the in-match rank tag read `1th`, `2th`, `3th` (4th and up are right).
- `Grampus` is used for Nagoya Grampus Eight in the places where the logo art says `Grampus`; whether to use `Grampus Eight` everywhere is open.
- Some staff-name readings in the credits are best guesses (`docs/credits-names.tsv`: one reading is low confidence, 29 medium).
- The label of the standalone OPTION screen still reads `Commentary Text` (the in-match options say `Subtitles`).
- The indentation of the `Screen Saver` label is off.
- Three refit forms are longer than their field and fall back to the short form: `FLOW_PRG/CHALMODE.BIN#3d804` (9 bytes, cap 8), `FLOW_PRG/EVENT.BIN#e06a8` (13 bytes, cap 12), `FLOW_PRG/NEWCON.BIN#2e11c` (9 bytes, cap 8).
- Many composed club names have an abbreviated town because of the 13-character limit; two people with the same romanised name may look identical.
- 236 of the 637 repainted textures are VQ-compressed; their delta carries a re-quantised codebook (harmless to how the game runs).
- The source-disc hashes were taken from the dump used here and were not compared with the Redump database.

Planned for 0.2.0, not in this release: Japanese honorifics (`-san`, `-kun`, `-sama`, `-senshu`) and Japanese name order (Family name, then Given name) as optional build and patch features, off by default; a width re-check of the name fields for both.

[Unreleased]: https://github.com/NexxusDrakoMultimedia/SakaTsukuTokudaigou2-EN/compare/v0.1.0-beta.1...HEAD
[0.1.0-beta.1]: https://github.com/NexxusDrakoMultimedia/SakaTsukuTokudaigou2-EN/releases/tag/v0.1.0-beta.1
