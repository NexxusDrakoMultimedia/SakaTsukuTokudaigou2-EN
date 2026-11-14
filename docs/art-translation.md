# Art (image) translation: repainting Japanese baked into textures

> **Status note (docs, 2026-11-11).** Sections 3 and 8 were written before `tools/pvr.py`, `tools/texinject.py` and the art groups existed; the PVR codec and the injection are done, 235 repainted textures are installed (`translation/textures/`), and the seven art groups are listed in `build/art/groups.json` (docs/playtest-checklist.md section 5 has their ids). What is still open is seeing them in game.

Status legend as in `formats.md`: **PROVEN** = run and checked here, **INFERRED** = deduced, **UNKNOWN** = not investigated.

Many screens show Japanese that is part of a texture, not a string: menu tabs (the kanji list on Club Edit),
headings such as 秘書選択, `LEVEL UP` style labels, stat captions (血液型 / 誕生日), the Hometown labels, title logos.
String editing cannot reach these. They need: **decode texture -> repaint with English -> re-encode in the same format and size -> put back in the container.**
This document covers the repainting step, which is `tools/arttext.py`. Decode/encode (PVR) and injection are other tools
(`tools/pvr.py` did not exist when this was written; the sample below therefore uses a screenshot, see section 7).

## Index

1. What was built / 2. Fonts / 3. Workflow / 4. Spec reference / 5. English art strings / 6. Constraints / 7. Sample / 8. Open items.
9. Money-unit art pass (`Oku` / `Man` / `Yen`; the group 1 and 5 unit sprites).  Related: docs/art-group7.md (LOCAL / DRSSRANK graph header
   now `Amount (Oku Yen)  Year`, TOWNDATA population `10k`), docs/number-formats.md (the text the money formatter prints), docs/texture-injection.md,
   docs/pipeline.md 9.1 (texture policy).  Open for the TV station card: the capital is drawn left-aligned at x=440 and `32 Oku 5000 Man`
   (184 px) ends at x=624; no frame or label right of x=608 may exist in the TV_E*.TBD art (unverified, needs a screen).

## 1. What was built

| File | Role |
|---|---|
| `tools/arttext.py` | Library + CLI. Erase old art by inpainting, render English with outline/shadow/gradient/italic, auto-fit, optional pixel-format snap. |
| `tools/test_arttext.py` | Self-test (synthetic textures; every erase mode, every preset, fit, clipping, quantize, glossary check). `ALL OK` at time of writing (PROVEN). |
| `docs/art-sample/` | The sample's spec (`club_edit_menu.json`) and a preset gallery; the before / after / sheet pictures show the game's own art, are git-ignored and are regenerated locally with the command below. |
| `translation/art/<texture-id>.json` | Where real specs live (directory not created yet; this task only wrote under tools/ docs/ build/). |

Dependencies: Pillow 13.0.0 and numpy 2.5.4 are installed (PROVEN, `import PIL, numpy`). No scipy, no other library is used.
There are no pure-Python fall-backs because both libraries are present; if a different machine lacks them, `pip install pillow numpy` is the only requirement.

## 2. Fonts

Text is rendered at build time with Pillow `ImageFont` from fonts installed on the machine. **No font file is copied into the
repository, and PNGs rendered with them should stay under `build/`** (git-ignored). The patch is for private use; do not
distribute rendered textures or fonts. The spec names fonts by alias:

`python -I -X utf8 tools/arttext.py --list-fonts` lists them. On this machine (Windows 11) all 23 aliases resolve exactly (PROVEN):
`arial`, `arial-black` (ariblk), `arial-bold`, `arial-bold-italic`, `arial-narrow-bold`, `bahnschrift`, `calibri-bold`, `comic-sans-bold`,
`franklin-gothic` (framd), `franklin-gothic-condensed`, `georgia-bold`, `gothic-bold`, `impact`, `sans-bold`, `segoe-ui`, `segoe-ui-semibold`,
`segoe-ui-bold`, `segoe-ui-bold-italic`, `segoe-ui-black`, `tahoma-bold`, `trebuchet-bold`, `verdana-bold`, `verdana-bold-italic`.
Search path: `%WINDIR%\Fonts`, `%LOCALAPPDATA%\Microsoft\Windows\Fonts`, then the usual Linux/macOS directories. The machine also has many
Google-font families in `C:\Windows\Fonts` (Abel, Alata, ...); any of them can be used by file name (`"font": "Alata-Regular.ttf"`) or by absolute
path. A font may be a list (first one found wins). If nothing resolves the tool warns and uses Pillow's default font, so check the report.

Which to use (INFERRED from comparing renders to `build/emu/live1..3.png`):

| Game look | Font that reads closest |
|---|---|
| Italic pale-cyan tab labels (漢字 ...) | `segoe-ui-bold` + shear 0.22 (preset `menu_label`) |
| Heading "Name Entry" (pale yellow, extruded purple shadow) | `bahnschrift` / `arial-narrow-bold` (preset `heading_yellow`) |
| Heading "Club Edit" (blue glass, deep-blue rim) | `arial-black` (preset `heading_blue`) |
| Small caption "Name" (lavender) | `arial-black` (preset `caption_lavender`) |
| Gold pop-ups (LEVEL UP, STEP UP) | `impact` + shear (preset `level_up`) |

The game's own English art (Club Edit, Name Entry, Name&Mascot Select, Avanzare / Estella / Stolz logos) is what the repaint should
match; look at it in `build/emu/live*.png` before choosing a style. Logos with custom lettering (AVANZARE etc.) are not to be repainted with a system font.

## 3. Workflow

1. **Find the texture.** Locate the container member and texture-table record that holds the art (UNKNOWN until the PVR/texture-table tooling
   exists; `formats.md` section 1 "Unparsed tails" and the corrected flag rule, bit30 -> bzw, bit31 -> bz, are the starting point).
   Match it to a screen by decoding candidates or by RAM/emulator capture.
2. **Decode** to RGBA PNG (`tools/pvr.py`, when it exists). Keep the texture's format, size, and mipmap/twiddle/VQ facts in the spec header.
3. **Write the spec** `translation/art/<texture-id>.json` (section 4). Start with one region per Japanese label. Texture id: the container path with `/`
   replaced by `__`, plus the member name or texture-table index, e.g. `DPTEX__MENU.ZAR__0012.json` (a proposal; match whatever the injector uses,
   as `translation/FLOW_PRG__CLUBEDIT.BIN.jsonl` does for text).
4. **Render:** `python -I -X utf8 tools/arttext.py translation/art/X.json build/art/X.in.png build/art/X.out.png --sheet build/art/X.sheet.png`
   The report prints chosen font, size and squash per region and warns on overflow / empty erase masks / glossary mismatches
   (`--strict` turns warnings into exit 1; `--debug-masks DIR` dumps each erase mask so you can tune ink conditions).
5. **Check** the before|after sheet at 3x. Iterate on `ink`, `dilate`, `fill`, region box, style.
6. **Encode** `X.out.png` with the same format and size as the original (`tools/pvr.py`). Set `"quantize": "argb4444"` (or `rgb565`/`argb1555`)
   in the spec so the PNG already shows what the hardware can display and the re-encode is lossless.
7. **Inject** the re-encoded texture into its container member (bzlib recompresses; `discbuild`/`build_patch` handle the disc).
8. **Look at it in the emulator** (not done in this task; no emulator was run).

## 4. Spec reference

The authoritative description is the docstring at the top of `tools/arttext.py`. In short:

```json
{
  "texture": "DPTEX__MENU.ZAR__0012", "size": [256, 64], "supersample": 4, "quantize": "argb4444",
  "styles":   { "my_label": { "font": "arial-black", "fill": "#fff", "outline": {"color": "#000", "width": 1} } },
  "defaults": { "style": "menu_label", "align": "left" },
  "regions": [
    { "id": "tab_kanji", "ja": "漢字", "text": "Kanji", "x": 64, "y": 8, "w": 148, "h": 50,
      "erase": { "mode": "mask", "ink": [ {"color": [180,240,240], "tol": 60}, {"luma_lt": 22} ],
                 "dilate": 3, "fill": "hfill" },
      "erase_grow": [0, 0, 7, 0] }
  ]
}
```

* **Region** = paint rectangle (drawing is clipped to it, so include room for outline and shadow). `erase_rect` / `erase_grow` widen the erased
  area beyond it. A region without `text` only erases; `"erase": null` only draws.
* **Fit:** `size: "auto"` picks the largest size whose block (ink + outline + shadow) fits, first squashing horizontally down to `min_sx` (default 0.8),
  then shrinking. A fixed `size` squashes only if it overflows. Overflow beyond that is clipped and reported. `wrap`, `line_spacing`, `align`,
  `valign`, `pad`, `dx`, `dy` as expected.
* **Style:** `fill` or `gradient` (stops `[t, colour]`, equal t = hard split), `outline`, `shadow` (`steps` > 1 = solid extrusion like the heading shadows),
  `highlight`, `shear` (italics), `bold`, `letter_spacing`, `opacity`, `aa: false` (1-bit alpha for cut-out textures). Presets:
  `menu_label`, `heading_yellow`, `heading_blue`, `caption_lavender`, `caption_white`, `level_up`, `plain_white` (colours sampled from the live screenshots;
  see `docs/art-sample/preset_gallery.png`). Add or override presets under `styles`.
* **Erase modes:** pick by what is behind the text.

| Background behind the old text | Mode |
|---|---|
| One flat colour | `flat` (sampled from a ring around the rect) or `auto` |
| Smooth gradient plate (button, window) | `coons` (all four edges) or `hgrad` / `vgrad` (when only two opposite edges are clean) |
| Horizontally banded art (tabs, bars, stripes) | `mask` + `fill: "hfill"` (interpolates along each row; keeps horizontal structure) |
| Textured / photographic | `mask` + `fill: "diffuse"` (harmonic inpainting; smooth, loses texture), or `copy` a clean patch from elsewhere |
| Hand-made clean plate available | `plate` (paste a PNG) |
| Atlas cell that must become transparent | `clear` |

  Ink masks: a dict of conditions is AND, a list is OR (`luma_gt/lt`, `alpha_gt/lt`, `sat_gt/lt`, `color`+`tol`, `bg_dist_gt`, `rects`, `mask_png`).
  `dilate` grows the mask over antialiased fringes (2-3 px for scaled screenshots, 1 px for decoded textures). `exclude` rects protect things you must keep.

## 5. English art strings: glossary and style guide

Art text is a *different medium* from the string pools, so only some rules of `style-guide.md` carry over:

| Topic | Rule for art |
|---|---|
| Terms | **RULE** Use the glossary: `translation/glossary.tsv` (`ja`, `en`, `short`). Art labels are space-starved, so use the `short` column when there is one (GK, DF, ...). If a term is new, add it to the glossary in the same change; the string pools and the art must agree (the glossary wins). Put the Japanese in each region's `"ja"` field: `arttext.py` then warns when the art text differs from the glossary `en`/`short`, and notes terms missing from it. (PROVEN on 決定 -> Confirm, which the glossary lists as `決定 / キャンセル` = `Confirm / Cancel`.) |
| Voice, variant | **RULE** British spelling, `football`/`match`/`kit` vocabulary (`style-guide.md` section 1). Art headings use Title Case ("Secretary Select"), like the game's existing English art. |
| ASCII-only, `\`/`~`/`@`/`=`/`#` bans (`style-guide.md` section 2.1-2.3) | Do **not** apply: pixels, not engine strings. Still prefer plain ASCII; do not introduce accented glyphs unless the string pools need them too. |
| Byte budgets, control tokens | Do **not** apply to art. Applies instead: the texture's pixel size and the region box. |
| Length | **DEFAULT** Target <= the Japanese width in pixels; the tool squashes to 0.8 by default and shrinks beyond that. Prefer a shorter term (Symbols, not Special Characters) over a tiny font. Numbers and units (`LV`, `HP`, `%`) stay as drawn when already Latin: leave them out of the erase mask. |
| Names | Logos and club names stay as they are; name plates that are real lettering (AVANZARE) are not repainted. |

## 6. Constraints to keep in mind (what the codec must handle)

* **Same format, same size.** The game and the texture table expect the original dimensions and pixel format (INFERRED; the loader never gets told
  otherwise). Never resize a texture. Atlases: edit cells in place.
* **Palette / VQ / twiddled textures** (INFERRED to exist on Dreamcast; the game's formats are UNKNOWN here): VQ and paletted images share a codebook/palette,
  so the encoder must re-quantise; use `quantize` plus a limited fill/outline colour count to keep the result close. If a codebook is shared with other
  textures, changing it affects them (UNKNOWN whether this game shares).
* **Mipmaps:** a mipmapped texture needs every level regenerated or the small levels will still show Japanese when the art is far away (INFERRED).
* **Alpha:** cut-out textures (ARGB1555, or 4444 with 0/F alpha) want `aa: false`, or the semi-transparent antialiasing is dropped by the encoder anyway.
* **Source of truth is the decoded texture, not a screenshot.** The game scales textures and filters them; spec coordinates always refer to texture pixels.

## 7. Sample (made with this tool)

`docs/art-sample/club_edit_menu_before.png` -> `club_edit_menu_after.png` (side by side, 3x: `club_edit_menu_sheet.png`), spec `club_edit_menu.json`:
the five input-mode tabs and the confirm button of the Club Edit name-entry screen (漢字, ひらがな, カタカナ, 英数字, 記号, 決定) become
Kanji / Hiragana / Katakana / ABC/123 / Symbols / Confirm, in the italic pale-cyan menu look with black outline and block shadow
(erase: mask of pale-cyan and black ink + `hfill`; render: `menu_label` preset, auto-fit with squash <= 0.7, 4444 snap).

Honest caveats (PROVEN by looking at the result):

* The input is a 240x420 crop of the **emulator screenshot** `build/emu/live1.png` (the game scaled ~1.56x with bilinear filtering), because no PVR
  decoder existed yet. It is not a game texture, so the fringe-width settings (`dilate: 3`) are larger than a decoded texture would need and the
  inpaint leaves faint banding, a few stray light pixels above the second tab, and a dark band behind the third one that comes from the screenshot's own dark stripe.
* The new labels sit a little tighter to the right edge of the plate than the Japanese did.
* The text is rendered, not hand-drawn: strokes are cleaner/heavier than the game's rounded gothic. It matches the colour scheme and shadow structure.

Regenerate: `python -I -X utf8 tools/arttext.py docs/art-sample/club_edit_menu.json docs/art-sample/club_edit_menu_before.png docs/art-sample/club_edit_menu_after.png --sheet docs/art-sample/club_edit_menu_sheet.png`
and the preset contact sheet: `python -I -X utf8 tools/test_arttext.py --gallery docs/art-sample/preset_gallery.png`.

## 8. Open items

* `tools/pvr.py` (decode/encode, VQ/palette/mipmap) and the texture-table parser: not done (UNKNOWN formats, see `formats.md` section 1 tails).
* An inventory of which textures carry Japanese (a screen-by-screen list plus texture ids) does not exist; start with the Club Edit set, secretary
  select, status/profile captions, Hometown menu, LEVEL UP / Step Up pop-ups, title logo.
* Hand-tuned outline/shadow offsets per texture are expected; the presets are starting points sampled from screenshots.
* No in-game verification yet (emulator not run for this task).

## 9. Money-unit art pass (am2): Oku / Man

Decision (user): money keeps the Japanese oku/man structure in English words, so the unit sprites that sit beside the digit sprites read
`Oku` (億) and `Man` (万, 万円), no longer `x100M Y` / `x10k Y`. A plain 円 is `Yen`. Nothing is explained in game; the translator's guide does that.

| Texture | Change |
|---|---|
| BAR.TBD 00002 (ATFIRST + ETC_DATA), LOADBAR 07332, YOUTH.BIN 10469, YOUTH.ZAR 10475, mon.tbd 00088 / 03642, ESTABLIS strip 07308 | `Man`, `Oku` repainted (tools/re/art1_spec/*.json, rendered by `art1_run.py`, installed by `art1_install.py --final`). 10470, 10474, 37285, 04112 carry no unit. |
| PLATE.ZAR money plates 03555-03562 | `Yen` (digits kept). 03563-03568 `Man`; 03561 `Man`; 03569 `Oku` (`tools/re/art5_plates.py`). 03570 / 03571 are blank plates. |
| SPT_CLUB 03823 / 03822, JSCEVENT 02233 / 02232 | `Oku` / `Man` boxes (`art5_pairs.py`) |
| INVEST 02227 / 02228, MON_INST 03333 | `Oku` / `Man` (`art5_invest.py`, `art5_monin.py`) |
| TOWNSEL 04077 | corner unit `Man` (was `10k Yen`) |
| LOCAL 02281, DRSSRANK 00586 | graph header `Amount (Oku Yen)  Year` |
| TOWNDATA 04073 | **population is the exception**: 万 beside the population figure became `10k`, not `Man` (Man reads wrong for people). `People (10k)` on LOCAL / DRSSRANK stays. |

**Update (stage 6, 2026-11-12): lower-case sprites.**  The user decided on lower-case `oku` / `man` (the capital `O` of `Oku` reads as a zero in the half-width font, `docs/number-formats.md` s11).  Every unit sprite above, the PLATE.ZAR money plates, the
SPT_CLUB / JSCEVENT / INVEST / MON_INST boxes, the header cells of BAR / LOADBAR / YOUTH, the graph strips and the Hometown corner unit were repainted `oku` / `man` (`Yen` keeps its capital; population stays `10k` / `ppl`); the table above names the textures, the words in it are the
pre-stage-6 spelling.  `PLATE.ZAR` `PW.TBD#0` / `TW.TBD#0` and `G_INCOME.DAT#0/#1` are blank frames.  Checked on `prop10a`: all of these textures are applied (`artcoverage`), none seen on screen.

Helpers added: `art1_run.py` gained `prefill` (row-fill a rectangle from a clean column before rendering), `polyfill` (rebuild a slanted bevelled plate edge, 07308) and `post` (alpha repairs);
`tools/re/am2_*.py` are viewing / dump scripts. The two orphan text records `FLOW_PRG/LOADBAR.BIN#7330` and `FLOW_PRG/YOUTH.BIN#422ee` (bytes inside the compressed texture stream) now have a blank `en`, which released the
held group-1 textures 07332 and 10469; they are installed in `translation/textures/FLOW_PRG/LOADBAR.BIN` and `YOUTH.BIN`.
All 235 repainted textures still pack into their slots (`tools/re/bld_texgrow.py`: 0 over); the `Yen` plates only fit as 1-bit alpha without a shadow (variants 2-3 of `art5_plates.py`).
Known leftover (not touched here): the soccer-ball inpaint on JSCEVENT 02233 and the small `Sponsorship` line are rough.

## 10. First playtest of prop7: art findings and fixes (ar5)

Coverage tool: `python -I -X utf8 tools/artcoverage.py [--log build/trial/ar5a.log] [-v]` lists, for every id of `build/art/groups.json` and `docs/art-group*.md` and every identical copy (the `texinject dups` rule), whether `translation/textures` has the `.pvr` and whether the build log lists it under `textures replaced:`.  Result after this pass (standard build `build/trial/ar5a`, texture rows failed=0): 206 ids, 239 copies, 0 NOT APPLIED; MISSING only the intentional or impossible ones: G_INCOME 02213 / 02214 (blank table textures, no text), PLATE 03570 / 03571 (blank plates), (FACEMDUL 00056 / 00062 / 00065, the three 大 / 特 / 号 face tiles, were listed here as impossible; they are injectable as `ATFIRST/FACEMDUL.DAT @cb7e0/kao_*.pvr` and are installed and applied, see section 12.)  The "copies" column of `groups.json` counts ZSARC members stored inside overlays (`@2ff38/scda.tbd`) that are the same bytes as the embedded table next to them, not extra copies.

* **The Hometown data panel was never missing a file.** `TOWNDATA.TBD#1` (04073) is installed and applied; the Hometown *selection* screen simply does not use it.  It draws its pill labels, the 億 digit-column sprite and the corner unit from **`TOWNSEL.TBD#0` (04077)**, which only had the tabs and the corner `Man`.  04077 now also has `Annual Rainfall / Temp`, `Population` + `10k ppl` (the game prints the figure between them), `Land Price`, `Transport`, `Soccer Pop.` and the 億 cell as `Oku` (same style and rect as BAR.TBD).  The new ink stays inside the columns of the old ink because the code prints values in the gaps.  Spec: `tools/re/art7_specs_a.py` (end of file); regenerate with `art7_run.py --write 04077`.
* **億 sprite search** (`tools/re/ar5_find.py`, alpha mask, every directory except GAME and FACE): the sprite exists only in BAR.TBD (+ ETC_DATA copy), LOADBAR, YOUTH.BIN, YOUTH.ZAR#5 and TOWNSEL#0; all five now read `Oku`.  Same for the 万円 corner sprite (BAR, YOUTH.ZAR#5, TOWNSEL).  The `Hometown` header money `15 Oku 0000 Man` is these sprites.
* **Name Entry tabs (03541):** the quads of the tab row only show the old ink columns.  `Confirm`, `Symbols` and `ABC/123` now sit inside the old extents (x 4..55, 70..121, 6..76), narrow bold, 13 to 15 px; `translation/art/03541.json`, `art3_run.py N_ENTRY`.
* **03587 month strip** (SCHE1.TBD / SHINJIN.TBD): the lone kanji 月 in front of the 1..12 numerals had been missed; it is `Mo` now (`tools/re/art7_specs_g.py`).
* **Black rectangle above `4-4-2` (manager panel, SCDRF / SEARCH):** NOT found in the art.  `tools/re/ar5_blackscan.py` finds no new opaque black or fully transparent rectangle in any of the repainted textures, and the SCDRF 128x128 sheet (07592) is unchanged outside the label boxes.  The label is not in a texture that carries Japanese; look at the string side (a `ctx` row of SCDRF / SEARCH whose English is empty or whose control codes draw a black box).  `Centre P` is the string `FLOW_PRG/SCDRF.BIN#32d58` (`" Centre Push"`, 16 byte slot) and its SEARCH twin: the box shows 8 characters, so the text owner needs a shorter form (`Centre`).
* Helpers added (`tools/re/`, prefix `ar5_`): `find` (sprite search over every texture), `dump`, `view` (before | after, magenta = transparent), `boxes`, `diff`, `blackscan`, `dupcmp`.

**Club-word logos are English art: do not repaint them.**  `GAME/ALLPNAME.BIN` (texture ids 10824-10877, one logo per club word, pool order) and the gold flags `GAME/BINDFLAG.BIN`
(13522-13575) carry the spelling the text must follow (`docs/style-guide.md` 12.2, `translation/clubwords_art.tsv`).

## 11. Second pass (ar6, 2026-11-12)

* `build/art/groups_v2.json` (written by `tools/re/ar6_groups.py`) lists what the second inventory added: EVENT title banners (`tools/re/ar6_banner.py`, plate rebuilt to the text width),
  the schedule cell words texture (`GAME/ALLLOGOS.BIN [59]` + copy `GAME/BINDLOGO.BIN [73]`, sweep id 10817: OFF / ??? / `TBD` / Overseas Camp; `tools/re/ar6_sched.py`),
  TV station headings and card, header unit cells, lower-case money units and the ALLJINI / TWND / STAFFLST / NEWS PARTS sets. SCHE1.TBD itself has no 未定.
* Header digits: the unit cells `Yr` / `Mo` / `Wk` carry 5 px of left padding and a narrow face so a wide code-placed digit sprite no longer overlaps them (`tools/re/ar6_hdrspec.py`, simulation `ar6_hdrsim.py`).
* Money units are `oku` and `man` (lower case) in every sprite and plate; `PLATE.ZAR/PW.TBD#0`, `TW.TBD#0` and `G_INCOME.DAT#0/#1` are blank frames (nothing to repaint).
* `tools/texinject.py` `_member_key` now also matches members whose name holds backslashes (`.\TMP\name050.tbd`) from a file path with `/` (`.../E050.DAT/TMP/name050.tbd#0.pvr`).
* The club-name plates `ALLLOGOS` / `BINDLOGO` / `BINDNAME` written by the club-words workflow did not fit under `exact` at the time of the art6 trial (art6 was built from a snapshot without them); they fit now, see section 12.

## 12. Skeptic pass over section 11 (sk6, 2026-11-12)

* Re-run: `tools/test_texinject.py` 427 checks 0 failed, `tools/test_arttext.py` ALL OK.  Fresh standard trial `build/trial/sk6a` from the LIVE `translation/textures`
  (club-name plates included): 216 texture rows, failed=0; `artcoverage` 206 ids, 0 NOT APPLIED, MISSING only 02213 / 02214 / 03570 / 03571, all four decoded and checked: blank table / plate frames, no text.
  (The only non-zero exit was one string, `BCAST/BCAST.BIN#1c755080`, 75 bytes for a 75-byte budget including the NUL; text side, not art.)
  `tools/re/sk6_fit.py` / `sk6_fit2.py` show ALLLOGOS 66, BINDLOGO 80, BINDNAME 1 textures inject under `exact`, one by one and as a set: the "86 club-name textures do not fit" note in section 11 was stale.
* `artcoverage` does resolve 00056 / 00062 / 00065: FACEMDUL.DAT `@cb7e0/kao_{g_dai,r_toku,y_gou}.pvr`, TITLEM.DAT #11 / #14 / #16 and KSPAPET.ZAR, all applied.
* Defect found and fixed: **LOADBAR.BIN `@1ec#0` (07332) and YOUTH.BIN `@36114#0` (10469)** kept fragments of the old 年 / 月 / 週 top strokes (a dot and dashes at y 31..33 above `Yr` / `Mo` / `Wk`, outside the erase rectangle that started at y 34), and the English sat 3 px below the kanji centre.
  `tools/re/sk6_hdrfix.py` widens the three erase rectangles to y 28..70 and moves the text up 2 px in `tools/re/art1_spec/07332.json` and `10469.json`; `art1_run.py 07332 10469`, then the two `.pvr` copied into `translation/textures` (only the two files; changed pixels x 202..324, y 31..57).  The BAR, YOUTH.ZAR and TRAINING sheets were clean.
* Header overlap: `ar6_hdrsim.py` prints the same 9 px "overlap" for the old kanji, the previous and the new sheet, so its number is not a usable metric; the composed picture `build/ar6/hdrsim.png` (digits right-aligned against the old kanji's left edge, month 12, week 4) is, and shows no digit/unit contact for the installed sheets.  Ink columns in the BAR sheet (`sk6_cells.py`): `Mo` x 268..277, `Wk` x 304..320 (old 月 264..274, 週 300..313); the next sprite starts at x 328.  The code's real digit x is not known, so this is a model, not an emulator check.
* Heuristic overflow scan (`sk6_bbox.py`: new ink outside the old ink's row band, 426 changed textures): the EVENT banner plates grow to the left (whole 256-wide texture), money plates PLATE.ZAR end at x 123 of 128 (+1 px against the pre-ar6 sheet), TV_E1#2 `Decided` x 11..83 inside the old 決定 x 0..86, `Wk n` in SCHE1#3 matches the old footprint.  Needs a screen to settle.
* Not part of art6 and being installed by another run while this pass ran: `TRAINING/BFGAME.ZAR bfgame.tbd#0..#2` (the pre-match tactics menu, ids 37171-37173, fully Japanese in the extracted disc).
