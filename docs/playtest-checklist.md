# Playtest checklist (Flycast, screen by screen)

For the user's next hands-on session.  Everything listed here is **proven offline only** (static analysis, the SH-4 interpreter, byte read-back of the built disc);
none of it has been seen on screen yet.  The first two playtests (`docs/playtest-log.md`) predate the Oku / Man money text, the repainted art groups,
the club-name guard, the half-width relocation and the refit forms.

**Sections 1 to 10 below were written for prop7 / prop7r; use prop8 (and the bis discs of section 0) instead, the screens are the same.  Section 0 is the plan for the next session.**

**Rules for the session**

* Flycast is started only with `tools/emu/launch.ps1` (it places the window on DISPLAY3, the vertical monitor), and only after the user has said yes: an agent asks first and never launches it unattended.
  `powershell -File tools/emu/launch.ps1 -Disc "build\trial\prop7\prop7.gdi"` (default Lua is the harness; pass `-Lua tools\emu\live.lua` for the live bridge; run it from the repository root).
* Discs: `build/trial/prop7` (standard flags: `--repack on --share dup --append-safe --proportional-font on`, club-name guard on) and `build/trial/prop7r` (the same plus `--refit on`, which also forces
  half-width relocation).  Compare the two on the screens of section 8.  A prop-scale disc has to be built first (section 9).  Trial discs are 1.2 GB; delete the ones you no longer need.
* Faint tick marks around text are Flycast's bilinear texture filter, not a patch bug (project memory); switch the texture filter to nearest-neighbour if they distract, and do not report them.
* Screenshots: the Flycast window only (`tools/emu/shot.ps1`, PrintWindow); never the whole desktop.
* Saves made on a patched disc stay on the patched disc; do not mix them with a Japanese-disc save you care about.
* A screen is **OK** when the "good" column holds; anything else goes into the report with the exact text seen.

**What to report for any screen:** the disc name, the screen and how you reached it, a window screenshot, the exact text you see (copy the glyphs, including gaps), and one of
*clipped* (text cut at the box edge), *overflow* (text runs outside its box or over art), *wrong text* (Japanese, garbage, wrong number or unit), *crash / hang* (note the frame the screen froze on).
For a crash or hang also say what you pressed last; a RAM dump (`tools/emu/dump_ram.lua`) helps but is optional.

## 0. Next session (after the first playtest of prop7): prop8 first, then the bisect discs only if it still hangs

The first playtest of prop7 found a hang on the second Event screen and the defects listed in `docs/status-report.md` section 0.1.  The discs of this session are
`build/trial/prop8` (everything, standard flags) and `build/trial/bis_a` .. `bis_e` (prop8 with classes switched off, section 0.3).  prop7 / prop7r are kept for comparison only.
Launch exactly as in the rules above, with `-Disc ...\build\trial\prop8\prop8.gdi`.  Do the same new-game path every time: new game, name entry, hometown, draft, then the first and second Event screen.

### 0.1 Boot prop8 and walk this path (about 15 minutes)

| Step | Look at | Good looks like | If not |
|---|---|---|---|
| 1 | Title, new game | boots | note the frame |
| 2 | **Name Entry** (tabs, symbol page) | tabs read `ABC/123`, `Symbols`, `Confirm` and are not cut at the right edge | which tab is cut (id 03541) |
| 3 | **Hometown screen** (header money, data panel, tabs) | header money reads `.. Oku .... Man` with a readable `Oku`; the panel shows `Annual Rainfall`, `Temp`, `Population` + `10k ppl`, `Land Price`, `Transport`, `Soccer Pop.`; `By Region` / `By Kana Order`; the confirm message `you will need 1 Oku 8500 Man.` | any Japanese left in the panel (ids 04077, 04073); **does the `O` of `Oku` still look like a zero?** (known, decision pending) |
| 4 | **Draft / Event panel** (right info panel) | `Wants 2 yrs`, `Age`, club, formation `4-4-2`, tactics `Centre Push` (not `Centre P`), salary right-aligned and fully visible, for example `1 Oku 300M` | a clipped salary; the black rectangle above `4-4-2` (screenshot it, say what is above and below it); a truncated style label |
| 5 | **The second Event screen** (1 Yr 1 Mo Wk1st, header `5 Oku 7400 Man`, secretary, message window) | the January message appears (`It's January. Player contracts are renewed every January.`) and the scout choice can be selected | **hang**: go to 0.2 at once.  Note the last button pressed and the frame it froze on |
| 6 | Attract demo (leave the title screen idle) and a first match | the commentary box is English; `HOME` / `AWAY` label (known to be still the old Japanese label); how consecutive commentary lines join; whether a word is broken at the end of a line; the left over Japanese lines (about 30 % of the clips) | screenshot of every box that still shows Japanese |
| 7 | Year-end report (NENREP) if reachable | sentences read as one (head + tail joined) | the cut sentence |

### 0.2 If prop8 still hangs at step 5: bisect with the discs that exist (3 to 5 boots)

All five are prop8 with something switched off.  The junk overwrites are blanked in all of them, so none of them tests that class again.

1. Boot **bis_e** (everything optional off: jp money, club guard and textures; the proportional font, town / club layout steps, BCAST and gap text stay).
   * bis_e hangs -> the cause is in the text, the proportional font or the layout steps: boot **bis_d** (prop8 with the proportional font off).  bis_d fine -> the proportional font on the new text; bis_d hangs -> text.  For text, build `bis_n` (`tools/re/hng_build_bis3.sh build/int/empty_tex`, all off and prop font off) and then bisect the text with `--only` per source (ask for it; the first suspects are EVENT, DRAFT, RECON, BCAST is not loaded on that screen).
   * bis_e fine -> a class that is off in bis_e is the cause.  Boot **bis_a** (prop8 minus jp money), **bis_b** (minus club guard), **bis_c** (minus textures).  The one that is fine where prop8 hangs is the guilty class.
     If none of the three is fine, the cause needs two classes: build `bis_f` (money on only), `bis_g` (guard only), `bis_h` (textures only) with `tools/re/hng_build_bis2.sh build/int/empty_tex` (about 3 minutes each; the scripts name the subsets).
2. Guilty class = jp money: the next suspect is the length of the text (up to 20 characters) in a buffer sized for the Japanese one.  Build the western variant (`bis_i`, `--money-style western`); if that is fine the fix is shorter text or the compact `M` form on more sites.
3. Guilty class = textures: `bis_j` .. `bis_m` split the 235 files by directory (needs the `t1`..`t4` subsets of `docs/hang-investigation.md` section 4); halve again with `--textures-dir`.
4. Guilty class = guard: it only touches EVENT's `$N` club case among the screens of the hang; restrict it to the other 19 overlays and report.
5. A RAM dump at the hang (`tools/emu/dump_ram.lua`) plus the program counter would settle it in one boot: attach it to the report if you can.

### 0.3 Discs of this session

| disc | contents |
|---|---|
| prop8 | standard flags; junk blanked; BCAST; gap strings; panel compact money; 04077 / 03541 / 03587 repaints |
| bis_e | prop8 with `--money-format off --club-guard off` and no textures |
| bis_a | prop8 with `--money-format off` |
| bis_b | prop8 with `--club-guard off` |
| bis_c | prop8 with no textures |
| bis_d | prop8 with `--proportional-font off` |

### 0.4 New items to add to the ID lists below

04077 (Hometown selection panel and the `Oku` cell, TOWNSEL.TBD#0), 03587 (`Mo`, the month strip in SCHE1.TBD and SHINJIN.TBD), 03541 tab widths (Name Entry), 07592 (SCDRF / SEARCH style tiles).  The Hometown panel is TOWNSEL#0, not 04073 (`docs/art-translation.md` section 10).

## 1. Header bar and money units (art group 1, money text)

| Screen | What to do | What good looks like | What to report |
|---|---|---|---|
| Any Office screen with the top bar (BAR.TBD tex 00002) | start a new game or load, open the Office | the amount sprites next to the digits read `Man`, `Oku`, `Yen`; digits and units line up; nothing Japanese left in the bar | the unit sprite that is still Japanese or sits on the digits; ids to name: 00002, 00091, 03634 |
| Loading bar, Youth screen, Training top bar | open Youth (YOUTH), start any scene change that shows the loading bar (LOADBAR), open Training | `Man` / `Oku` sprites match the Office bar (ids 07332, 10469, 10470, 10474, 10475, 37285) | any unit still `x10k Y` / `x100M Y` or Japanese |
| Contract and money strips (mon.tbd 00088, 03642; ESTABLIS strip 07308; SPT_CLUB 03822 / 03823; JSCEVENT 02232 / 02233) | open a contract screen and the facility / sponsor cost screens | `Oku` / `Man` boxes beside the amounts; 02233 (JSCEVENT) has a rough ball patch and a rough small `Sponsorship` line: known, report only if it is worse than that | the id and what looks wrong |
| Yes / No box (yesno.tbd in SHTEX0..8, 64x64 variant in SHTEX.ZAR) | any confirm dialog (for example Save) | `Yes` / `No` readable inside the box | which dialog |

## 2. Money text in windows (the patched money function)

| Screen | What to do | What good looks like | What to report |
|---|---|---|---|
| TV station card (TV_EVENT) | open the TV station / broadcast card | the capital line starts at x = 440 (where the Japanese capital started) and reads like `32 Oku 5000 Man` (widest text, 184 px, ends at x = 624); it must not touch a frame or label at the right edge; the other cards read `65 Oku`, `227 Oku`, `441 Oku`, `834 Oku`, `945 Oku` | text cut at the right edge, text over a frame or label, any `Y` or decimal form.  Open question from `docs/number-formats.md` 4.4: is there art right of x = 608? |
| Finances / funds (G_INCOME income and costs table, GETREP monthly report, MON_INST, data-room tables, INVEST) | open the finance screens | amounts as `3 oku 9000 man`, `2 oku 4300 man`, `1 oku 4642 man`, `58 man`, `5000 Yen`, `0 Yen` (lower case, no `Y` prefix, never `Y 390000000`); right-aligned columns `  3 man`, ` 10 man`; negative amounts in red | a number printed with a `Y` or as plain digits, or text overlapping the next column or the table edge (note the screen: the x of the library text objects is unknown, `docs/number-formats.md` s11.5); the debug lists `%3d %-13s Y%d %d yr` may still show `Y` |
| GETREP (reports with money) | trigger or read a weekly / monthly report with money lines | `%m` amounts in the Oku / Man form, text wrapped inside the bubble | clipped line, amount beyond the window |
| MEETING | open a meeting with a bonus or fee | `1000 Man bonus`, `2 Oku`, `9 Oku 9000 Man` style amounts; no `Y10M` | the text that still shows a western amount |
| INVEST | open the investment screen | the sprintf-formatted columns show the documented form (`%6d00 Man`); the wider formats may still be western: note them | the exact line and column |
| ESTABLIS dialogs (facility cost texts) | open the facility build / upgrade dialogs | each of the 15 cost texts is three rows of at most 39 cells with the amount in it; no fourth row, nothing over the frame | which facility, how many rows, the cut text |
| Sponsor and supporters windows (SPONSOR, SPONSOR2, SPT_CLUB) | open the sponsor list and a sponsor offer | names fit their column (`Aogashi Shipping`, suffixes of at most 9 characters: Shipping, Society, Fishery, Farming); fee lines use `Man` / `Oku` | name over the next column, text over the heading texture |
| Draft and contract windows (DRAFT, NEWCON, RECON, SCDRF) | open the draft, a new contract and a renewal | the deal text with `%m` fits its three rows; the shortened texts read naturally (`Deal:` in DRAFT; `deducted from funds` in GETREP; `Let's not lose any more trust.` in SPONSOR / SPONSOR2; `is suitable` in SPT_CLUB) | any clipped line |

## 3. Hometown and the club-name guard

| Screen | What to do | What good looks like | What to report |
|---|---|---|---|
| Hometown lists (HOMETOWN) | choose region, prefecture, kana tab, town in a new game | `Tohoku`, `Kansai`, `Kyushu`, `Nara` print as plain words (no `To ho ku`, no 24 px gap); towns read in full (the 35-byte record names) | a spaced word; a town still Japanese or cut |
| Hometown candidate popup | pick a town so the club-name candidates appear | the four previews equal the final names (the popup uses the same cut rule), for example `Kagos. Mythos`; nothing clipped at the 13th letter | preview differing from the name chosen; a clipped last letter |
| Create-club / club-name entry (CLUBEDIT, N_ENTRY) | give the club a name, then read it back on the confirm screen | the composed `<town> <word>` is at most 13 characters; longer pairs show a cut town with a dot (`Akab. Tempest`, `Abashi. Sting`); the word is never cut | a name over 13 characters, a cut word, **any corruption of the field after it** (the next field, e.g. the owner name, changing) |
| Schedule and results (SCHE0, SCHE1) and Event list (EVENT) | open the schedule, the standings, the Event list | rival and own club names complete and not overlapping neighbours; Event list names at most 12 characters | the screen, the name, the clipping |
| Save / load slots (AUTOSAVE, LOAD, CSAVE, FREELOAD) | save a game, open the load screen | the club name in each slot is complete (13 characters at most) and the slot rows align | clipped or overlapping name |
| Known cosmetic oddities | look for towns that end in `.`, `-` or a space | `N. . Topolino` and `Minami-. Arpe` were the known ugly cuts; they are fixed (the simulator census of the real prop7 / prop7r composers finds 0 odd shapes, `docs/layout-issues.md` 9.9), so any `. .`, `-.`, `..` or a trailing blank you see in game is a new finding | the pair of town and word, and the screen |

## 4. Name entry

| Screen | What to do | What good looks like | What to report |
|---|---|---|---|
| Name Entry, tab labels and buttons (N_ENTRY atlas 03541, 03553; Password 07594; SEARCH labels; Player Edit 03578, 03583-03585) | open the screen for the owner name, club name and a player edit | tabs read Kanji / Hiragana / Katakana / ABC/123 / Symbols, buttons Delete / Space / Confirm; the English `Name Entry` and `Club Edit` headings are unchanged | a tab still Japanese, text over the plate |
| The letters page (the page you call page 3) | switch tabs until the English letter grid shows and type a name | **each grid cell takes one letter** (the first playtest took two per cell; the five picker records were restored to Japanese on purpose, `docs/playtest-log.md`); English names are typed on the alphanumeric (eisuuji) tab, which since `--name-entry-order half-first` opens on the **half-width** letters | two letters per cell, wrong letter, the cursor stepping by two; also say which page number the grid was on |
| ABC/123 tab page order (`--name-entry-order half-first`, `docs/layout-issues.md` s20; not booted, the expectations are INFERRED from the code) | open the ABC/123 tab for the owner name, then move the cursor down past the last row of each page until it stops; leave the tab and come back; type `Ab 9` | the tab opens on narrow `1 2 3 ... 0 / A B ... L / M ... X / Y Z / a ... l`; the next page is narrow `m ... x / y z`, then the same two pages in wide full-width letters, then the cursor stops; the letters sit in the cells (32 px pitch, no bunching, no overlap with the cursor box); the typed text shows as normal English; cells beyond the letters are not selectable; a blank page cell cannot be selected; coming back to the tab keeps the last page | which page the tab opens on; a page that is out of order, missing or empty; letters off their cells (the proportional font hook skips these windows because their advance is 32, not 24: this is the thing to confirm); a half-width letter that types two bytes; a cursor that cannot reach the next page |
| Typing a long name | type 13 characters | the field takes 13 and the confirm screen shows them without clipping | the length at which it stops or clips |

## 5. Repainted art, groups 1 to 7 (ids to spot-check)

`build/art/groups.json` holds the full id lists (written by `tools/re/inv_groups.py`); 235 texture files are installed in `translation/textures/`.  For every id: look at the screen in game, compare it with the PNG in
`build/art/` if you have it, and report ids by their five-digit number.  What good looks like for all of them: English readable, the original colours, no leftover Japanese, no kanji fragments, nothing cut at the plate edge.

| Group | Screens | Ids to spot-check (first the ones most likely to be wrong) | Known rough spots |
|---|---|---|---|
| 1 Header bar, Yes/No, money strips | Office bar, Youth, Training bar, loading bar | 00002, 00091, 03634, 07332, 10469, 10475, 37285, 04112, 00088, 03642, 07308, 10470, 10474 | none |
| 2 TV station card | TV_EVENT card for each of the six networks | 04080, 04081, 04082, 04084, 04085, 04087, 04089, 04091, 04093 | the six English logos are kept on purpose |
| 3 Name Entry / edit labels | Name Entry, Password menu, SEARCH, Player Edit | 03541, 03553, 07594, 03578, 03583, 03584, 03585 | kana table and English headings are kept |
| 4 Secretary, staff, recruiting | Secretary select and profile plates, Office icons, draft / contract menus, national team select, scout report, youth menus | 03833-03842 (profile plates; names must match the string-pool names), 03798, 03801, 03804, 03807, 03810, 07589, 07592, 07304-07306, 07334, 03620, 04148, 10471, 10472, 03629 | secretary names on the plates versus the same names in text |
| 5 Schedule, finance, facilities | Office menu, schedule controls, finance and income, facility captions, sponsor cost screens, money plates | 07405, 03587, 03589, 03590, 03323, 03333, 02227, 02228, 02213, 02214, 02219, 02208, 07309, 02003, 02006, 02009, 02187, 02190, 02193, 02196, 02199, 02202, 02205, 03530, 03533, 03536, 03816, 03822, 03823, 02233, 03555-03562 (`Yen` plates, except 03561 which is `Man`), 03563-03569 (`Man` / `Oku` plates; 03570 and 03571 are blank on purpose and are in the group too) | 02233 ball patch and `Sponsorship` line are rough (known) |
| 6 Training, match setup, cheer editor | Training menus, Match Regulations, Cheer Song editor, GOAL sheet, Meeting-room icons, face tiles | 37289, 37292, 37293, 37277, 37281, 37300, 00165, 00167, 00169, 00170, 36802, 36805, 36800, 03266, 00056, 00062, 00065 | the English `MATCH REGULATIONS` / `ENTRY CLUB` art is kept |
| 7 Hometown, supporters, data room, system | Hometown data and selector, Local Info, Supporters, Option / Help / Memory, Dream Club and Data Room score books, Challenge Mode, result ribbons | 04073 (population reads `10k`, not `Man`), 04077 (corner unit `Man`), 02281 and 00586 (graph header `Amount (Oku Yen)  Year`), 02270, 02273, 02276, 02279, 03869, 03879, 03882, 03885, 00340-00345, 00347, 00362, 00587, 00596, 00603, 00616, 00621, 00628, 00637, 00332, 00337, 04096, 04097, 06483-06490, 00208-00222, 00227-00229, 00235, 00238-00258 (Data Room vocabulary; the ids between are not in the group), 00290-00295, 00067, 03550 | 00344 / 00628 rank-suffix `th` and year `Yr`; any leftover man character beside a population (should be `10k`); Challenge kanji numerals are optional, late-game screens |

| What to report for art | |
|---|---|
| the id (five digits) and the screen | and one of: Japanese left, kanji fragment, wrong colour or alpha (a black box where it should be see-through), clipped, blurry beyond the original, wrong word (compare with `translation/glossary.tsv`) |

## 6. Dialogue and layout (proportional font on both trial discs)

| Screen | What to do | What good looks like | What to report |
|---|---|---|---|
| Speech bubbles and message windows | read any conversation (secretary, Local Info, news) | words wrap at word boundaries; lines stay inside the box (about 468 px per line at 24 px advance); no mid-word wrap such as `com/e` | the line and what broke |
| Lists in columns (rank lists, player cards, Event list) | open the player card, the Event list | no clipped leading digits; `Isao Nakagak`-style clipping gone; 12 character names complete | the exact clipped text |
| Number and unit cells (FIRE, ABROAD player-card block) | open the player card with `This Season` | `%8d Gls` and `%7d.%02d` fit the block; `This Season` may still overlap a neighbour (open item: next step `Season`) | whether `This Season` overlaps |

## 7. Half-width pointer strings (relocation, `--hw-relocate`, on prop7r only)

| Screen | What to do | What good looks like | What to report |
|---|---|---|---|
| Club words, nations, leagues, foreign player-name parts | open the club-name word list, the overseas camp list, a league table, a match with foreign players | complete English words (refit forms, for example `Arg.` replaced by a longer form where the pool had room); no garbage, no Japanese, no crash on entering the screen | text that is Japanese, garbled, cut mid-word, or a crash when a screen with moved strings opens (name the overlay if you know it) |
| Boot and a long play-through | play a few in-game weeks | no hang, no freeze in a menu that was fine on prop7 | the first screen that differs between prop7 and prop7r |

## 8. prop7 versus prop7r (refit forms)

Run the same five screens on both discs and put the results side by side: club-name word list, overseas camp country list, a league / cup table, Event list staff names, a match with foreign players.
prop7r (`--refit on`) should show **longer, better short forms** of the same names (for example `Casab.` becoming a fuller form) at the cost of more cut club names (49.0 % of town + word pairs on prop7r against 47.1 % on prop7).
Report: which disc looks better on each screen, any screen where prop7r is worse (clipped, overlapping), and any crash that only one of the discs shows.

## 9. Prop-scale (`--prop-scale on`)

Not in any trial disc yet.  Build one first (`python -I -X utf8 tools/build_patch.py --repack on --share dup --append-safe --proportional-font on --prop-scale on --out build/trial/ps --name ps`, then delete it afterwards).
Only 1ST_READ's cave changes (144 bytes instead of 104): windows whose advance is not 24 (rank lists with 16 / 32 / 48 / 10 px, size-class 2 prose) scale their advance table by A/24 instead of A >> 1.

| Screen | What good looks like | What to report |
|---|---|---|
| Rank lists and size-class 2 windows (Data Room score books, CHALDANI ranks, small-print help) | text spacing proportional and even, not squeezed or gappy; no overlap | spacing that is worse than on prop7, and the screen |
| Everything that was fine on prop7 | unchanged | any screen that changed |

## 10. Things this session cannot judge

Overlay growth (`--grow-overlays`) and shared file extents (`--dedupe-files`) are off in every trial disc and need their own builds and boot checks (`docs/pipeline.md` 9.5, 9.8; `docs/expansion/overlay-memory.md` T4 / T5).
The real size of the club-name buffers is still unknown (`docs/layout-issues.md` 9.7): the first item of that list can be settled with one RAM dump while a rival club is shown.
