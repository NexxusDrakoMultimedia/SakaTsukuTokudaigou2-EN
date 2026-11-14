# Art sweep v3: Japanese still baked into textures after the first inventory

Made 2026-11-12 by merging twelve sweepers that looked at all 547 contact sheets (`build/tex/sheets/`). The first inventory (`build/art/groups.json`, 7 groups, 211 ids) came from about 55 sheets. Machine-readable result: `build/art/groups_v3.json` (packages with per-texture items, copies, injectability, refit, done, skipped). Scratch: `build/art/v3/` (`sweep_1..12.json`, `m_build.py`, `m_pkgs.json`).

## 1. Totals

| | count |
|---|---|
| textures in `build/tex/index.tsv` | 37,302 on 547 sheets |
| sweeper entries / distinct ids found with Japanese | 272 / 271 (plus the 41 STAFFLST name textures, one id range) |
| DONE (installed already) | 108 ids: 107 event title banners / event pictures installed after groups.json was made (E005..E243, E024 / E025 graph pictures, E800) plus 1 id already in groups.json |
| TODO | 189 ids = 283 physical textures once same-payload copies are counted, in 10 packages |
| PARTIAL (installed, Japanese cells left) | 9 ids, listed inside package E / F |
| REFIT (installed but too wide or colliding) | 10 ids (section 4) |
| SKIPPED on purpose | 5 ids |

Sheets 0228-0455 and 0183-0227 (except 0183/0184) are `GAME/BINDUNIF.BIN` kit textures: no UI Japanese. Sheets 0137-0182 are `BINDFLAG` Latin pennants. Several sweepers judged some sheets from `index.tsv` member names rather than opening them (listed in their summaries); a stray UI texture on an unopened kit/flag sheet is unlikely but not excluded.

Conflicts resolved by looking at the textures: `docs/art-translation.md` section 10 says the club-word logos are English art. That is true of `ALLPNAME` / `BINDFLAG` (Latin). `ALLLOGOS` 10758-10823 and `BINDLOGO` 13825-13838 are katakana plates (viewed 10760, 10817, 13836): they are real Japanese textures. Sweeper 3 guessed that リュミエール / ミュートス in the schedule were strings; the katakana plate 13836 exists, so verify in game which is drawn.

## 2. Packages (ordered by priority)

Counts are ids / physical textures with copies. Wording, screens and tools per item are in groups_v3.json.

| # | Package | ids / phys | Priority | Technique |
|---|---|---|---|---|
| A | Office personnel and Hometown town menus: 07009 07012 07015 07018 07021 07023, 08663 (+09143 09623 10103), 08805 (+7 copies), 08688 (+11 copies) | 9 / 30 | high | arttext cell specs |
| B | Club-name plates 1: 10817 (schedule words), 10758-10766, 10818-10823, 13825-13838 | 30 / 46 | high | regeneration job |
| E | Practice, pre-match menu, post-match news: 37285 (left menu, partial), 37171 37172 37173 (=37286), 36912 36918 36921 36926 36927 36931 36932 36937 37302 | 14 / 16 | high | arttext, reuse art6 strings |
| F | End/Option plates 00803 00805, Step Up tags 00281 (+03865), OPTION values 03550, meter caps 03266, unit strips 00586 02281, 年目 00344, youth labels 10470 10474, 速報 04082 03342 03344 04104, event picture 02235 | 15 / 16 | high | new + fix-ups of installed specs |
| G | In-match tags 34703 34708 34716 34719 34723 (GAMEETC.ZAR) | 5 / 5 | high | BLOCKED: injector cannot reach them |
| C | Club-name plates 2: national teams 10767-10787, 14029 | 22 / 43 | medium | regeneration job |
| D | Club-name plates 3: foreign clubs 10788-10816 | 29 / 58 | medium | regeneration job |
| H | Credits role titles 35825.. (15) | 15 / 15 | low | regeneration job |
| I | Credits staff names 35825-35880 minus roles (41) | 41 / 41 | low | optional romanisation |
| J | Title logos / tagline 00101 00109 00108 00110, news tiles 00056 00062 00065, ONISTA 03546 03547 | 9 / 13 | low | decision; 00056/62/65 not injectable |

Package sizes: C and D are within 15-30; A (9 masters) reaches 30 with copies; G and J are small on purpose (blocked / decision).

## 3. Seeds from the brief

| Seed | Result |
|---|---|
| 未定 schedule cell text | FOUND 10817 (`ALLLOGOS` [59], copy `BINDLOGO` [73]): OFF / ??? / 未定 / 海外キャンプ. SCHE1.TBD (03587-03596) has no 未定. Package B. |
| 海外キャンプ出発 / 帰国 | FOUND and DONE: 04852 (E242) and 04853 (E243) banners are installed (written by another process during the sweep; not yet in a build log). The schedule cell word 海外キャンプ is 10817 (todo). |
| Office personnel plates 選手獲得 移籍 留学 監督変更 スカウト変更 | FOUND 07009 07012 07015 07018 07021 (+ scout positions 07023), `ALLJINI.ZAR`. Package A. |
| Town menu plates 日程進行 ... 終了・設定 | FOUND 08663 (+3 copies), 08805 (+7 copies). Package A. |
| 景気 好況 | FOUND 08688 (+11 copies): 景気 tag and five levels. The E024 / E025 pictures 好況 / 不況 (04361 / 04378) are DONE. |
| Perso / Facili too wide | REFIT 07405 (+07469 07539): the original 人事 / 施設 rows are only 51 px wide, repaint is 95 px. Section 4. |
| 増設可能 red tags | FOUND 00281 (+03865): 増設可能 / 撤去予定 / 改築可能. Package F. |
| Practice left menu | FOUND 37285 (installed only above y=170); also 37171-37173 / 37286. Package E. |
| Meeting meter 弱 / 強 | FOUND 03266, installed but the two end caps are still Japanese. Package F. |
| Club-name plates (パープルサンガ, アルビレックス, リュミエール, 横浜FC, ヴァンフォーレ, サガン, ベガルタ, アルディージャ, ミュートス) | FOUND: 10760 (Purple Sanga), 10763 (Ventforet, Albirex), 10764 (Sagan), 10762 (Vegalta, Ardija), 10766 (Yokohama FC), 13836 (Lumiere, Mythos). Packages B-D. STAFFLST is the credits, not clubs. |
| END/OPTION plates | FOUND 00803, 00805 (headings 00802/00804 already English). Package F. |
| OPTION values 中景, 3 分 | FOUND in 03550 (installed, but the value columns at x330-512 y0-140 were not repainted). Package F. |
| TOWNDATA / TOWNSEL overlap | FOUND, REFIT 04073 and 04077 (section 4). |
| スタジアム suffix | NOT FOUND as a texture: it is a string (match preview stadium line); report to the text owner. |

## 4. Refit list (installed, too wide or colliding)

| id (+copies) | Problem | Suggested fix |
|---|---|---|
| 07405 (+07469, 07539) | Office menu: rows 3 and 4 must fit 51 px (sprite UV clips there: Perso / Facili) | 51 px labels e.g. Staff / Sites, or squeeze horizontally |
| 04073 | TOWNDATA: Population ppl / vs Last Month fill the plate edge to edge; Land Price, Transport, Commerce % run to the edge, digits overlap | Pop. / vs Last Mo. / Land / Transit / Soccer Pop. |
| 04077 | TOWNSEL: Population 10k ppl and Soccer Pop. too tight | same short forms |
| 07589 (+07591) | RECON: Do Not Renew and Finish Renewals touch | No Renewal / Finish |
| 10471 | YOUTH words on one row touch (MF Defence / Pick Coach, DF Type / Coach Check) | shorter forms |
| 03836 (also 03838, 03840) | SS_PR1 hobby line clipped | Snowboard, Marathon |
| 03869 | SUPPORT trait plates: Coaching Talent clipped, Good Connections tiny | Coaching / Connections |
| 03590 | SCHE1 calendar buttons tiny two-line text | verify in game |
| 37292 | Manager Team Check auto-shrunk | Team Check |
| 37293 | Midfield Defence fills the plate | Mid Defence |

## 5. Families needing a different technique

* Club-name plates (B, C, D, 132 physical textures with BINDLOGO copies): a regeneration job. Four 32 px lines per 128x128 VQ texture, same style for all, text from a table. Build one generator, not 66 hand specs.
* `tools/artcoverage.py` cannot resolve `GAME/` bind ids (`[k]` in texindex) or GAMEETC members; add an order-based resolver (as in `build/art/v3/m_res.py`) before listing these ids in groups.
* G (GAMEETC `@110/*.pvr`): texindex lacks these members (61 of 164 listed): injector work needed first. FACEMDUL 00056 / 00062 / 00065 have the same problem.
* Credits (H, I): optional, regeneration job.

## 6. Strings and not-texture items for the text owner

* Match preview stadium line suffix スタジアム (string).
* Whether the schedule/match preview draws club names from ALLLOGOS/BINDLOGO textures or from strings: confirm in game before spending effort on D.
* Skipped on purpose: 07566, 07572 (prop decor), 02717 (illegible legend), 03898 (ticket print), 00098 (already English). In-world signs and sponsor boards were also skipped.


## 7. Package status after stages 7 and 7b (integrator, stage 8b, 2026-11-12)

Installed means: the `.pvr` files are under `translation/textures/` (every identical copy has its own file) and the build log of `build/trial/prop10a` lists each of them under `textures replaced:`.
Measured on that disc: `tools/artcoverage.py --log build/trial/prop10a.log` 206 ids, 251 physical copies, 637 texture files, **0 NOT APPLIED**, MISSING only the four blank frames `02213` `02214` `03570` `03571`
(`G_INCOME.DAT` #0 / #1, `PLATE.ZAR` `PW.TBD#0` / `TW.TBD#0`: empty table / plate frames, nothing to repaint); 0 texture rows with `failed > 0`; the 478 texture files written since 2026-11-12 02:00 are all applied and each
copy set has exactly one file per copy (`texinject.find_copies`, 348 sets = 477 physical textures; the 478th, `EVENT/E050.DAT` `TMP/name050.tbd#0`, is not in the index); `tools/zsarc_crc_audit.py`: 0 stale members.
**Nothing was seen on screen**; "verified" below means the tools above and the owners' own checks, not a Flycast look.

| # | Package | State | Owner scripts | Skeptics' notes / limits |
|---|---|---|---|---|
| A | Office personnel, Hometown / Office town menus, economy | INSTALLED, verified by tools | `s7m_jini.py`, `s7m_selb.py` (`Advance Schedule` ... `Quit / Options`, two-line rows), `s7m_glv.py` (`Economy`, `Boom` ... `Slump`) | the plates now say `Advance Schedule` / `Quit / Options`; `OPTION.BIN` was made to agree (cell width unknown); the Office menu rows 3 and 4 are `Staff` / `Facility` inside the 51 px sprite (`s7r_office.py`, was `Perso` / `Facili`) |
| B | Club-name plates 1 (schedule words, J.League clubs, select teams, 54 club words) | INSTALLED, verified | `s7p_plates.py` (one table, ALLLOGOS 66 + BINDLOGO copies + the club words) | `F Marinos` without a period (the Japanese plate abbreviates too); `TBD`, `Overseas Camp`; whether the schedule draws names from these plates or from strings is still to be seen |
| C | Club-name plates 2 (national teams, `14029` Sakatsuku Stars) | INSTALLED, verified | `s7p_plates.py`, `s7p_logo.py` | `代表` dropped from the names |
| D | Club-name plates 3 (foreign clubs) | INSTALLED, verified | `s7p_plates.py` | condensed face for the long cities; squashed names need an eye |
| E | Practice, pre-match menu, post-match news | INSTALLED, verified | `s7x_run.py`, `s7x_specs.py`; the `7r` refits (`Team Check`, `Mid Defence`) | 37285 now repainted below y 170 too; `Rd` on the news tables vs `MD` on the in-match tag is a judgement call (`doc/TRANSLATORS_NOTES.md`) |
| F | End / Option plates, Step Up tags, OPTION values, meter caps, strips, `FLASH`, picture 02235 | INSTALLED, verified | `s7e_run.py`, `s7e_specs.py` | `Complain.` is 03266's 62 px box (shortened `Complaint`); the OPTION value columns need an eye |
| G | In-match tags (`GAME/GAMEETC.ZAR` run members) | INSTALLED (needed the injector change, `docs/texture-injection.md` s11) | `s7g_run.py`, `s7g_specs.py`, `docs/art-tags.md` | `th` gives `1th` / `2th` / `3th`; `No.` + number + `MD` composition not checked; 34716 is also the old `静観` HOME / AWAY line (`Hold`) |
| H | Credits role titles | INSTALLED, verified | `s7c_run.py` | 128 px boxes, regenerated in one style |
| I | Credits staff names | INSTALLED (romanised, Given Family) | `s7bi_run.py`, `docs/credits-names.tsv` | two readings still unconfirmed: Hiroyasu Lee, Kansuke Saito (Sunao Murayama, Kenji Takano and Atsutoshi Takahashi confirmed via Sega Retro; s_murayama repainted in stage 8d) |
| J | Title logos, tagline, face tiles, ONISTA | INSTALLED, verified (`00056` `00062` `00065` through the `@cb7e0` run) | `s7bj_title.py`, `s7bj_faces.py`, `s7bj_install.py`, `docs/title-logo.md` | faint kanji ghost on the tiles (VQ residue), the ONISTA seam falls inside `DECEMBER`; the title wording `TOKU DAI GOU` is a house decision |
