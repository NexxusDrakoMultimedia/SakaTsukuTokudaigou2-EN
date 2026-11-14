# Art pass, group 7: Hometown, supporters, data room and system menus

Status legend as in `formats.md`: **PROVEN** = run and checked here, **INFERRED** = deduced.

This is the record of the group-7 repaint (87 texture ids, 92 physical copies once identical copies are included). The input is the decoded PNG of
each texture (`build/tex/`), the output is `translation/textures/<iso path>/<texture id>.pvr` exactly as `build_patch.py --textures-dir` expects, one
file per identical copy (the dups rule of `docs/texture-injection.md`). Nothing here is committed to git and no emulator was run (INFERRED:
the repaints look right as PNGs, not yet seen in the game).

## Tools (all under `tools/re/`, prefix `art7_`)

| Script | Role |
|---|---|
| `art7_lib.py` | Resolve a 5-digit sheet id to (iso file, texinject id), decode, find ink boxes, sample the old colours (`autostyle`), repaint through `tools/arttext.py`, encode with `tools/pvr.py` into the same format, write every copy, fit check against the container slot (`texinject.inject(..., 'exact')`). |
| `art7_match.py` | Alpha-mask matching (FFT correlation, IoU >= 0.9). One translated label repaints every texture that carries the same sprite, so the 40-odd Data Room labels were defined once. |
| `art7_specs_a.py` .. `_f.py` | The specs: A Hometown/Local/Support menus/Option/Help/VM, B Data Room vocabulary (matched), C manual Data Room pieces, D Challenge Mode and team banners, E result ribbons, F supporter screen. |
| `art7_run.py` | `python -I -X utf8 tools/re/art7_run.py [--write] [--scale N] ID ...|all`; writes `build/art7/out/ID.png`, a before|after crop `build/art7/v/ID_ba.png`, and with `--write` the `.pvr` files. If the encoded stream does not fit its slot it re-renders with simpler art (level 1: three flat colour bands instead of a gradient, 2: flat colour, 3: 1-bit alpha) and reports the level. |
| `art7_view.py`, `art7_grid.py`, `art7_boxes.py`, `art7_words.py` | Montage, pixel-grid crop, ink boxes, word splitter: used to read coordinates off the decoded art. |

## Rules applied

* Format, size and palette semantics unchanged (the encoder is given the original PVR as `original=`). 4444 textures keep partial alpha; the two
  1555 textures (LOCAL `pvr.tbd`, DRSSRANK #2, DRSUBC2 #2) are rendered with 1-bit alpha; RGB565 plates (menu bars, rank plates) have no alpha.
* The new text is rendered with an installed font (`arial-bold`, `arial-black`, `arial-narrow-bold`) in the colours sampled from the old ink
  (vertical gradient, outline or offset shadow). Wording is the group wording plus `translation/*.jsonl` for team names, so art and string pools agree.
* Erase: transparent backgrounds are cleared; text on plates is removed by an ink mask (white/black, a colour range or both) and filled along the
  rows (`hfill`) so that stripes survive; marble plates use harmonic inpainting. The ribbons with chrome glyphs on striped plates use a row-wise modal
  background (`art7_lib.rowfill`).
* (Superseded by docs/art-translation.md s9: the LOCAL/DRSSRANK graph header now reads `Amount (Oku Yen)  Year` and the 万 beside the TOWNDATA population is `10k`.)  Units that are a single kanji inside number strings (億, 万 in the LOCAL/DRSSRANK graph headers) were left as drawn: the money and population
  formats are produced by code and the art cannot know which part is printed. 人 after a population number became `ppl`; 位 on the ranking ribbon became `Pos.`.

## Judgement calls

* 級 / 段 / 初 / numerals one to ten (CHALDANI sprites) became `Kyu`, `Dan`, `1st`, `1` .. `10`; the rank plates read `10th Kyu` .. `1st Kyu`,
  `1st Dan` .. `9th Dan`, `Master`, `Special Match` (the string pools write `10-kyu` / `7-dan`; art uses ordinals because the group wording says `1st Dan`).
* `Unavailable` (公式戦出場不可能 / 試合出場不可), `Poor Club Finances` (クラブ経営悪化), `Poor Results` (成績悪化), `Bankrupt` (破産) are new terms
  of the DRSUB* player-status legend; add them to the glossary if the string pools ever need them.
* Tournament banners (CPNAMEB) were all Japanese; names are my own (`World Winners Cup`, `Platinum League`, ...), consistent with the team names of
  the string pools.

## Skeptic pass

* 00341: `Rankings by Position` was clipped by the neighbouring italic label; the box was narrowed (262 px) and repainted.
* 00344 and its copy 00628: leftover kanji removed (the rank suffix after the numbers became `th`, the year suffix on the orange bar became `Yr`).
* CORRECTION (2026-11-12 playtest): 04073 (TOWNDATA#1) is NOT the panel of the Hometown selection screen.  That screen draws TOWNSEL.TBD#0 (04077), repainted in `docs/art-translation.md` section 10.
* Known residue: the single kanji 万 beside the population numbers on 04073 (`Population 万 ppl`) and in the LOCAL/DRSSRANK graph headers is left as drawn.
* Trial disc `art7sk_g7_trial` (build/out/art7sk_g7): every texture record failed=0; `tools/test_texinject.py --quick`: 264 checks, 0 failed.
