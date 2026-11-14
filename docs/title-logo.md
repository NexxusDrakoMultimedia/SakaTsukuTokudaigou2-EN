# Title logo, tagline and the 特大号 tiles (package J, prefix s7bj)

## Decision

| Element | Japanese | English art | Reason |
|---|---|---|---|
| Four red kana tiles (title screen, 00101) | サ カ / つ く | `SA KA / TSU KU` (one syllable per tile, same red extruded look) | The franchise name is a brand and stays romanised (`SakaTsuku`, as in the README, docs and disc label). One syllable per tile keeps the logo's 2x2 layout and reads in the same order. |
| Hexagon banner (00101) | 特 大 号 | `TOKU DAI GOU` | 特大号 is a pun title (a newspaper's "special extra-large issue"). The project name is already `SakaTsuku Tokudaigou 2`, so the romanised title is used everywhere the title shows. A gloss ("Special Edition") belongs in the translator's notes, not in the art. |
| Wordmark `サカつく` (TITLEM 00108 + black silhouette 00110) | サカつく | `SakaTsuku` (heavy italic, red gradient, silver + black outline; silhouette repainted in step) | Same brand rule. 00110 is the drop-shadow mask of 00108 and must match it. |
| Tagline strip (00101, TITLEM 00109) | J.LEAGUE プロサッカークラブをつくろう! | `J.LEAGUE Let's Make a Pro Soccer Club!` | Translated; the wording is the one already on the English disc label. `J.LEAGUE` is the licence mark and is kept unchanged. |
| Face tiles (FACEMDUL 00056 / 00062 / 00065 + copies) | 大 / 特 / 号 | `DAI` / `TOKU` / `GOU` | Same romanised title as the banner; red tile, white letters. |
| News splash (ONISTA 03546 + 03547, one picture in two halves) | 2000年12月 / 鬼茂復活!! | `DECEMBER 2000` / `Onishige Returns!!` | Plain translation; the name follows the style guide (given name Onishige, 河本 鬼茂 = Onishige Kawamoto). |
| `(C) SEGA CORPORATION`, `Smilebit`, `TM`, `J.LEAGUE`, `PRESENTED BY SEGA` | (already Latin) | untouched | Proper marks. |

Style guide open decision 1 ("subtitle Special Edition 2") is superseded for the title art: the banner is `TOKU DAI GOU`.
No game string spells 特大号 (checked in `translation/*.jsonl` and the glossary), so nothing else needs to change.
If a later release wants `SPECIAL EDITION` instead, it is two constants in `tools/re/s7bj_title.py` / `s7bj_faces.py`
(`TOKU DAI GOU` hex text and the tile words); the tiles are single-word, so the three-tile pun would need rethinking.

## Textures written (every identical copy has its own file under translation/textures)

| id | file / texture id | size, format |
|---|---|---|
| 00101 (03909) | ATFIRST/TITLE.DAT #9, ETC_DATA/TITLE.DAT #9 | 512x256 ARGB4444 rect-twiddled |
| 00108 (04060) | ATFIRST/TITLEM.DAT #6, ETC_DATA/TITLEM.DAT #6 | 512x256 ARGB4444 |
| 00109 (04061) | TITLEM.DAT #7 (both dirs) | 512x32 ARGB4444 (earlier art7 version, `Football`, replaced) |
| 00110 (04062) | TITLEM.DAT #8 (both dirs) | 512x128 ARGB4444 |
| 00056 | ATFIRST/FACEMDUL.DAT `@cb7e0/kao_g_dai.pvr`, TITLEM.DAT #11 (both dirs), GAME/KSPAPET.ZAR `kao_g_dai.pvr` | 128x128 RGB565 VQ |
| 00062 | `@cb7e0/kao_r_toku.pvr`, TITLEM.DAT #14, KSPAPET `kao_r_toku.pvr` | same |
| 00065 | `@cb7e0/kao_y_gou.pvr`, TITLEM.DAT #16, KSPAPET `kao_y_gou.pvr` | same |
| 03546 / 03547 | ETC_DATA/ONISTA.TBD #0 / ONISTA2.TBD #0 | 256x256 RGB565 twiddled |

FACEMDUL is now reachable: `tools/texinject.py` lists the run members (`@cb7e0/...`) and the build applies them
(trial disc log: `textures replaced: @cb7e0/kao_g_dai.pvr, ...`). Each `@cb7e0/x.pvr` file is stored as
`translation/textures/ATFIRST/FACEMDUL.DAT/@cb7e0/x.pvr.pvr`.

## Known small points

* The tiles show a very faint ghost of the old kanji (VQ codebook residue); flat white lettering was used because
  the gradient version of GOU did not fit the 3856-byte slot.
* ONISTA is drawn as one 512x256 picture and cut into its two textures; the seam falls inside `DECEMBER` (the original
  seam also cut `2000|年`).
* In-game look is not checked (no emulator was started).

## Tools

`tools/re/s7bj_lib.py` (text/inpaint helpers), `s7bj_title.py`, `s7bj_faces.py` (PNG makers, `build/s7/titles/new/`),
`s7bj_install.py [--write] ID...` (encode, slot check, install every copy; backups in `build/s7/bak/s7bj/`),
`s7bj_loadchk.py`. Before/after PNGs: `build/s7/titles/ba_*.png`. Trial disc: `build/trial/s7bj_title.gdi`.
