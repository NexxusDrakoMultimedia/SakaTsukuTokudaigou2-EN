# Test sheet: prop10g (the stage 9 fixes, the Roboto Condensed Medium font, subtitle speed)

Primary disc: `build/trial/prop10g.gdi` (flags of prop10e: `--repack on --share dup --append-safe --proportional-font on --strict`, defaults `--refit on --align-fix on --tag-fix on --scout-fix on`, plus `--crowd-fix on --bcast-speed 1.9 --lin-center on --open-font on`; log `build/trial/prop10g.log`, patch digest `c39635bbe75dfb93b30ea109043c81fb05cde84c`).
Control disc: `build/trial/prop10f_stdfont.gdi` (identical, but `--open-font off`: the original game font, so only the font and the 58-byte width table differ; patch digest `94b030aa5bf11fa4476186f766fa7cbc5fe0a695`).  **Boot the control only if the new font misbehaves or something looks wrong**, to separate font effects from the other fixes (section 9).
Both built and checked read-only: 396,819 strings applied, 0 failed, 0 skipped; `verify_disc` OK; `zsarc_crc_audit` 0 stale (2,482 members); `artcoverage` 0 NOT APPLIED (missing only the blank frames 02213 02214 03570 03571); 23 test suites passed.
Against prop10e (the stable baseline, played: no hang) 13 files differ: 1ST_READ (lin-center hook and cave, width table), FONT.BIN x2 (new glyphs), GAME, TRAINING, G_INCOME, ABROAD, FIRE, PLNUMSET, SELNAT, MON_INST.TBD (Ad Budget bar), BFGAME.ZAR and TRAINING.TBD (left plates).  EVENT, SCDRF and SEARCH are byte-identical to prop10e, so the Event message path and the scout panel code are unchanged.
**Nothing below has been seen on screen.**  Last disc played: `prop10e` (first Event message, Event screens, a match, lineup screen, Hometown, Office schedule and the Transfer list all reached, no hang).  Those items are dropped; the prop10e sheet (`docs/test-sheet-prop10e.md`) stays for the art, credits and BCAST lists that this build does not change.  Date: ____________  Tester: ____________

Launch only when the user says yes (window on DISPLAY9, no scripted input): `powershell -File tools/emu/launch.ps1 -Disc "build\trial\prop10g.gdi"`.

Result codes: **OK** / **clip** (cut at a box edge) / **over** (runs outside its box or over art) / **wrong** (Japanese, garbage, wrong number or unit) / **hang** (write the frame and the last button).
Ticks and hash marks around text are Flycast's texture filter: ignore them.  Words in `code style` are what the disc is supposed to show.  "Fallback" says which flag or constant to change when a check fails.

Order: the short hang check, the scout and Transfer panel, finances, lineup and plates, the in-match menu, then font, subtitle speed and the known-open list.  Items that decide something carry a **DECIDE** tag.
**Read this first (font spacing):** the skeptic found that a 7 px blank shifted padded numbers, so prop10g keeps the blank at the original 12 px (word gaps stay wide like prop10e; digits 12 px). Padded fields should line up as on prop10e. Items 2.9, 3.8, 6.4 and 6.5 confirm this; the earlier 7 px build is `prop10f`, kept on disk for comparison.

## 1. Hang check  (the changed shared code: 1ST_READ hook and FONT.BIN)

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 1.1 | New game, advance to **1 Yr 1 Mo Wk 1**: the first Event message (one look: only the font changed on this path) | the message appears, readable, advances with A | empty window, garbled glyphs, freeze (then boot `prop10f_stdfont`: if that works the font data is to blame, else the 1ST_READ hook) | |
| 1.2 | The secretary message `At last, they've accepted our offer.` (scout / transfer result confirm) | the full sentence types out to the end, then the next message or the screen closes | freeze mid-sentence (the old `accepted o` freeze) | |
| 1.3 | Reach the match and let the **match intro** draw (`Mythos Stadium`, weather, `KICK OFF`): the first user of the new lin-center hook | the intro text appears and the match starts | hang or garbage on the intro; blank intro (the hook in shared code is the suspect: control disc, then `--lin-center off`) | |
| 1.4 | Other linear-text screens that use the same writer: Ending, the data-management club-bar edit (DMCLBEDT) | text draws, nothing garbled | garbage or hang: write the screen | |

## 2. Transfer panel and scout screen   (stage 9a format fixes; the panel code is unchanged from prop10e)

Format changes in ABROAD, FIRE, PLNUMSET and SELNAT: age `Age %8d`, contract `%4d/%d yrs  `, apps `%4d apps   `, rating `%7d.%02d  `.  The same four rows appear in several panels, check the Transfer panel first and one other panel for each row.

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 2.1 | Transfer panel (the Transfer list, open a player): the **Age row** | `Age` then a number, e.g. `Age        25` (digits near the right edge of the row) | `Age ` with no number; `23 Yen` or any `Yen` in the age row (the old money mis-parse) | |
| 2.2 | Same panel: **no `Yen` anywhere** on the four rows except a real money row | `Yen` only on money | `Yen` after an age or years value | |
| 2.3 | Same panel: **no rows below the window**: `Gls` and `Avg Rating` visible | all rows inside the window: contract, apps, `Gls`, `Avg Rating` | the last two rows pushed under the window; blank rows between | |
| 2.4 | Contract row for a player on a 1-year deal | `   1/1 yrs  ` (shows `1/1 yrs`) | `1/1` with no `yrs`; `yrs` cut | |
| 2.5 | Apps row | `   0 apps   ` style: number then `apps`, not cut | `app` cut; number overlapping `apps` | |
| 2.6 | `Gls` row | number in place | missing or wrong | |
| 2.7 | `Avg Rating` row | `   0.00  ` style two decimals, e.g. `6.50` | `6` and `.50` split; number over the label | |
| 2.8 | The same four rows in **Study Abroad** (ABROAD), **Release / Fire** (FIRE), **Select Nation** (SELNAT) and the **shirt-number right panel** (PLNUMSET) | each panel reads like 2.1 to 2.7; the `Squad No.` panel is as on prop10e | a blank row, `Yen`, or a row below the window in any of them | |
| 2.9 | **DECIDE**: candidate card (SCDRF / SEARCH, scout list) row right edges: money `35 oku 8500m` / `7800 man`, `Wants  2 yrs`, `      Age 25`, region `Ehime` | the five rows end near the same x as on prop10e (about 10 px apart) | rows ragged by about 30 px (estimate for the 7 px blank: money -12 to -24, `Wants` -20, Age -37, region -36): note the spread; fallback: space 12 in the open table (2 bytes), or boot the control | |
| 2.10 | Candidate card contents unchanged | contract rows, club row, portrait as in prop10e (the panel code is byte-identical) | rows missing, garbage box `g6` | |

## 3. Ad Budget, income table, finances

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 3.1 | **Ad Budget** (Event / Office, the advert budget bar): the amount bar caption | unit sprites read `1 oku` and `8000 man` (lower case); **no `an` fragment** (the old `okan`) | `okan`, `oka`, `man` cut to `an`; kanji left | |
| 3.2 | Ad Budget: the Yen cell after the amount (user decision: blank) | the old yen cell is blank, nothing in its place | the yen kanji or `Yen` still there; a stray smear in the cell | |
| 3.3 | **Ticket Price** bar (same texture 03333) | same fixes as 3.1 and 3.2: `man` / `oku` clean, yen cell blank | `okan`, kanji, or the cell showing garbage | |
| 3.4 | Bar texture as a whole | digits, bar fill, other labels undisturbed after the repaint (draw order inferred, not decoded) | a repainted cell on the wrong place, bar graphics broken | |
| 3.5 | **Income table crowd line**, HOME match report | `1man 827ppl` style (`man ` then digits then `ppl`), right edge near the column edge | `1ma827pp` (the prop10e bug); letters over the digits | |
| 3.6 | Same line, AWAY match report | same format as 3.5 | clipped units | |
| 3.7 | Crowd of **zero** (match with no attendance, if one appears) | `0ppl` | `0pp`, `0` alone, garbage | |
| 3.8 | **DECIDE**: INVEST (investment) money rows `    1 oku 8500m`, `        1500 man` (deliberate blank alignment: the 7 px blank puts them about 20 to 50 px further left) | the `oku` rows and the `man` rows still line up within about 5 px, as on prop10e | the two row types 30 px apart; amounts running into labels | |
| 3.9 | **Earn / Cost tabs** (the income and cost panel tabs) | `Earn` and `Cost` fit inside the green tabs, with no overrun (`Income` ran past its tab) | text beyond the tab; `Ear`, `Cos` | |
| 3.10 | Win Bonus / Sponsor `0 Yen` and a second money screen (data room, monthly report) | read as before, red negatives; `oku` / `man` lower case | `Yen` fragments, misaligned digits (see 3.8) | |

## 4. Lineup name tags, Practice, pre-match plates

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 4.1 | **Lineup / Formation name tags** (GAME): a family name of 6 or more letters | the tag shows 5 letters at most (`Nakat` style from `Nakata`): whole letters, none half-cut | last letter half drawn; the old 7-letter tag cut by the tag edge | |
| 4.2 | Lineup tags for short names (`Ito`, `Endo`) | full name, centred as before | blank or shifted tag | |
| 4.3 | **Practice > Player Placement** tags (TRAINING, same limit 5) | same as 4.1, 5 letters at most | clipped tag | |
| 4.4 | **DECIDE**: tag limit. Does 5 fit the tag window, with room? | 5 letters fit with a margin: keep 5 | `Nakat` still touches the edge: say limit 4; or the window has room: limit 6 (`layoutpatch.TAG_LIMIT_BY_OVERLAY` and rebuild) | |
| 4.5 | **Pre-match left plates**: `View Teamwork`, `Opponent Info`, `Start Match`, `Change Policy`, `Win Bonus` (repainted to 91 px) | each word inside the plate, same plate width on every row | a word over the plate edge; plates of different widths; Japanese left | |
| 4.6 | Practice left menu: `Practice Orders`, `Change Policy`, `Run Practice`, `View Teamwork`, `Team Check` | inside the plates (91 px) | a word cut | |
| 4.7 | Practice left strip (S37285) labels (KNOWN OPEN: three labels overshoot the Japanese width by 1 to 3 px) | note which labels touch the strip edge | something worse than 3 px | |

## 5. In-match OPTIONS and the match intro  (the linear text writer, i/l spacing)

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 5.1 | **In-match OPTIONS** (pause menu): the commentary row | `Subtitles` (was `Commentary Text`) fits the row | `Commentary Text`; `Subtitles` over the ON / OFF cells | |
| 5.2 | OPTIONS: the camera row | `Near/Mid/Far` aligned with the row above | shifted right, over the cells | |
| 5.3 | OPTIONS: ON / OFF highlight and moving the cursor | the selected cell highlights correctly; toggling `Subtitles` OFF hides the commentary box, ON brings it back | the highlight on the wrong cell | |
| 5.4 | **i and l spacing in OPTIONS** (`Player Names`, `Subtitles`, `Near/Mid/Far`) | `i`, `l`, `I`, `:` centred in their cell, no big gaps (the old `Cl oudy` look) | `S ubtitles`-style gaps | |
| 5.5 | **Match intro**: `Mythos Stadium`, `Cloudy`, `15:00 KICK OFF` | even letter spacing, `i` / `l` / `:` centred | uneven gaps as on prop10e | |
| 5.6 | Wider letters in the same text (`u s n h p q g`) | letters complete, none missing ink (KNOWN: up to 2 px extra gap on the right) | a letter with a column cut off | |
| 5.7 | **OPTIONS highlight windows** (`--options-fix on`, needs a build newer than prop10g: layout-issues s18): press left / right on each row and watch the bright part | exactly the selected word is bright and the other is dim: `ON` or `OFF` (three rows), `A` or `B`, `Near`, `Mid` or `Far` (in prop10h: `ON/O` bright, OFF never, only `ar` of `Far`) | a bright patch on other letters or nothing bright | |

## 6. The new font  (Roboto Condensed Medium; control = `prop10f_stdfont`)

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 6.1 | **Message windows** (Event, secretary, manager) legibility | smooth, readable, clearly less jagged than the old font; no touching letters | smeared glyphs; letters touching; unreadable at normal TV size | |
| 6.2 | **Name tags** in the lineup, Practice and the Event screens | readable at 5 to 7 letters, not too thin | broken glyphs, missing strokes | |
| 6.3 | **Tables** (data room, squad lists, standings) | digits and labels clear, rows straight | glyphs cut off, tight rows | |
| 6.4 | **DECIDE**: numbers and padded fields: shirt-number column, dates `M 5 D12 15:00`, `Yr 1 Mth 4`, `Squad No. 7`, YOUTH `%-13s  2y`, DRAFT lists, DRSHRANK, `No.  3` | columns still straight; numbers right-aligned as before | columns visibly ragged or touching their labels (the 7 px blank; estimated -7 to -35 px): write which screen and by how much | |
| 6.5 | **DECIDE**: word gaps in running text | words clearly separated; text reads fine at 12 px | words look too far apart (known: the blank is 12 px; space 9 is the compromise): note a screen | |
| 6.6 | Descenders and wide capitals (`g y p q j`, `M W Q`) | descenders complete, no clipped tails; wide capitals not squashed | tails cut by the row below; `M` / `W` unreadable | |
| 6.7 | Text that used to overflow its window | fits more often (6,450 down to 4,968 texts over, estimate, mostly dialogue) | a text now over a box that was fine on prop10e (nothing expected) | |
| 6.8 | Commentary box in the new font (longest line 74 characters) | within the box, two lines, readable | a line past the box edge (BCAST `Your next opponent is the strongest team,` is KNOWN 12 px over) | |
| 6.9 | Numerals and the unit sprites next to digits (`1 oku 8500 man`, `0 Yen`) | `oku` / `man` read well beside the digits | digits too thin or too wide beside the sprite | |
| 6.10 | **DECIDE**: overall, new font or original? (compare with the control if unsure) | new font clearly better: keep `--open-font on` in the release | the old font looks better, or the new font misaligns too much: `--open-font off` (release then ships the original font) | |

## 7. Commentary subtitle speed  (`--bcast-speed 1.9`, about 1.94x faster typing)

Watch a match with subtitles on; half-time and full-time lines are the longest.  Original speed was about 2.23 ticks per character; at 1.9 it is about 1.15.  About 5% of lines are still expected to outlast their clip at 1.9.

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 7.1 | **Half-time** commentary lines | the whole line typed before the clip ends or the picture fades | a line cut mid-word when the cutscene ends | |
| 7.2 | **Full-time** lines (`They drew with ...`, trophy lines) | complete before the fade to black | cut off | |
| 7.3 | Ordinary lines (shots, fouls, chatter) | text keeps up with the speech; not instant, readable | text far behind the speech, or flashing by too fast to read | |
| 7.4 | Typing order and completeness | every character appears in order, none skipped, no stuck line | a skipped or doubled character; the box stuck half-typed | |
| 7.5 | **DECIDE**: speed. Is 1.9 right? | 1.9 reads well and mostly finishes: keep | still cut often: 2.2 (`--bcast-speed 2.2`, no gate); too fast to read: 1.7 (`--bcast-speed 1.7`): write **1.7 / 1.9 / 2.2** | |
| 7.6 | Other GAME text and match flow unaffected (menus, the tactics screen, replays) | normal | menu text speed changed, a stuck screen | |

## 8. Known still-open items  (not defects of this build; note anything that differs)

| # | Screen | Expected | Result |
|---|---|---|---|
| 8.1 | KNOWN OPEN: in-match player tags (the names above players on the pitch) | show initials only (stage 9a S3, not investigated): note what you see | |
| 8.2 | KNOWN OPEN: HOME / AWAY label (the sakusen texture) | still reads `efend` or part of it (repaint blocked: no injector for that texture) | |
| 8.3 | KNOWN OPEN: the tag icon (`CF` and others) touching or overlapping names longer than 5 letters | possible overlap; at 5 letters clear | |
| 8.4 | KNOWN OPEN: Practice left strip overshoot (4.7), 1 to 3 px on three labels | as in 4.7 | |
| 8.5 | KNOWN OPEN: about 5% of commentary lines outlast their clip at 1.9x | occasional cut line | |
| 8.6 | KNOWN OPEN: crowd line right edge on `man ` rows about 4 px left of plain rows (3.5) | cosmetic | |
| 8.7 | KNOWN OPEN: the three old byte-cap texts (CHALMODE, EVENT, NEWCON, one each) over by one byte | possibly a clipped last letter on those three | |
| 8.8 | EXPECTED to stay Japanese: sponsor logos and advert signage; annual-report attendance lines | Japanese | |

## 9. Control disc and fallbacks

Boot `prop10f_stdfont` ONLY if the new font misbehaves or something looks wrong in sections 2 to 6 and you cannot tell the font from the other fixes.  It has every fix of prop10g except the font: the original glyphs, space 12 px, original table.

| Disc | What it contains | Boot when |
|---|---|---|
| `prop10f_stdfont` | all prop10g fixes with the original font and the original width table | the hang check 1.1 to 1.4 fails; ragged numbers (2.9, 3.8, 6.4); garbled glyphs; any layout problem you suspect is the font |

Reading the results:

| prop10g | `_stdfont` | Meaning |
|---|---|---|
| wrong | same wrong | not the font: a stage 9 fix (crowd, Age rows, tags, speed, centring, bar texture); use the fallback flag |
| wrong | OK | the font: `--open-font off`, or change the space width (7 to 9 or 12; 2 bytes in the 1ST_READ table at 0x289900 and 0x289920 and the open widths file) and rebuild |
| hang | hang | shared code: boot-test with `--lin-center off` first |

Fallbacks without rebuilding everything: `--open-font off`, `--lin-center off`, `--bcast-speed off|1.7|2.2`, `--crowd-fix off`, `--tag-fix off`, `--scout-fix off` (each switches one piece, `docs/pipeline.md` s9).
