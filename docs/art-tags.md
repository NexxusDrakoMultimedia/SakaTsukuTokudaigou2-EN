# In-match tag textures (GAME/GAMEETC.ZAR, package G, prefix s7g)

The five tag textures live as PVR members of a ZSARC run inside `GAME/GAMEETC.ZAR` (offset `0x110`).  They were not reachable until
`tools/texinject.py` learned run members (`@<hexoffset>/<name>` ids, docs/texture-injection.md section 11).  Files:
`translation/textures/GAME/GAMEETC.ZAR/@110/<member>.pvr.pvr`.

| id | member | size, format | Japanese | English art | slot (packed/available) |
|---|---|---|---|---|---|
| 34703 | `ktss03` | 128x128 ARGB4444 VQ | 作戦変更 | `Change Tactics` (white, black outline, hard edges) | 2619 / 2656 |
| 34708 | `pk_parts1` | 128x128 RGB565 VQ | 自動選択 / 決定 | `Auto Select` (teal button) / `Confirm` (orange button); the GK DF MF FW tabs were already English | 4615 / 4724 |
| 34716 | `sakusen` | 128x128 ARGB4444 VQ | 攻めろ守れ / 静観攻守 / 全員守備 / 全員攻撃 | one English word per original sprite cell: `Attack` (x 0..75) + `Defend` (x 78..127) / `Hold` + `Atk` + `Def` (x 0..53, 56..80, 96..120) / `All` (right-aligned, x 20..47 of its 0..49 cell) + `Defend` / `All` + `Attack` (second word left-aligned from x 51, ink x 52..100 of 51..101, so the gap to `All` is 4 px; the owner saw 18 px in Flycast with the centred words) (per-line colour gradients kept; beta.1 painted `Attack/Defend` as one string, which the game's two-cell split showed as `Attack/D` + `efend`; cell split inferred, UVs not read from the code) | 4044 / 4340 |
| 34719 | `sk_parts2` | 128x128 ARGB4444 twiddled | 位 (after 9 0) | `th` (gold digits style) | 9075 / 9192 |
| 34723 | `taisenhyoji` | 256x256 ARGB4444 VQ | 第 / 節 / 回戦 / 決勝 / 準決勝 / 位 | `No.` / `MD` / `Round` / `Final` / `Semi-final` / `th` (HOME / AWAY were English) | 7190 / 7740 |

Notes and limits

* Every word is drawn inside the old glyph cell (the game addresses the cells by fixed UVs; no code was changed), so the English is as short
  as the cell allows: `MD` (matchday, as the game text "MD %d") for 節, `No.` for 第.  If the game composes `第N節` as prefix + number + suffix it now reads `No.5 MD`;
  if it composes cup rounds as `N回戦` it reads `5 Round`.  This composition was NOT checked in game.
* `th` for 位 gives `1th / 2th / 3th`: the atlas has one suffix cell, there is no room for st / nd / rd.  Ranks 4 and up read correctly.
* Run members cannot grow: the VQ stream must fit the old compressed slot.  `34703` and `34719` needed hard-edged text (no anti-aliasing) or a
  slightly smaller size for that; see `tools/re/s7g_run.py` (reserve/seed search) and `s7g_specs.py` (the specs).
* No copies: each of the five textures occurs once on the disc.
* FACEMDUL 00056 / 00062 / 00065 (the 大 / 特 / 号 face tiles, run `@cb7e0` of `ATFIRST/FACEMDUL.DAT`) were repainted and installed by
  package J (docs/title-logo.md: `DAI` / `TOKU` / `GOU`) with the same tool; package G did not write them.
* The embedded TBD tables of `GAME/GAMEETC.ZAR` (sheet ids 34625 ... with source `@<offset>`) are a different family (`TBD-embedded`, not run
  members) and are still not in the texture index.

Tools: `tools/re/s7g_dump.py` (extract originals), `s7g_specs.py` + `s7g_run.py NAME [--write]` (repaint, fit check, install),
`s7g_cmp.py` (before | after on a blue backdrop), `s7g_verify.py` (apply to extracted/ as the build does, stale-member and loader checks),
`s7g_equiv.py` (old-tool / new-tool equivalence over translation/textures and every listing), `s7g_covcheck.py` (artcoverage resolve
before / after).  `tools/artcoverage.py` now resolves run members by their `@off/name` and GAME/ bind files by order
(`_by_order`: the sheet rows of one file in id order equal the texindex rows of that file when the counts and sizes agree).
