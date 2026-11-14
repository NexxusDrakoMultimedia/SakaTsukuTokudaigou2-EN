# Test sheet: prop10c (everything changed since hsk_full1)

Disc: `build/trial/prop10c.gdi` (built by `tools/build_patch.py --repack on --share dup --append-safe --proportional-font on --strict`; the command-line defaults added `--refit on --align-fix on --tag-fix on`;
digest `e7543242860a638a07c0945da573e34885828e5d`, log `build/trial/prop10c.log`).  prop10c is the previous trial disc prop10c (complete BCAST commentary) plus two corrections: the credit texture `s_murayama` now says `Sunao Murayama` and the clip `BCAST#1de96880` uses the full wording; it differs from prop10c in `/GAME/STAFFLST.ZAR` (2 sectors) and `/BCAST/BCAST.BIN` (1 sector) only.  The last disc played was `hsk_full1` (2026-11-12 01:47); **nothing below has been seen on screen**: every item is
proven only by static analysis, the SH-4 simulator and read-back of the disc bytes.  Date: ____________  Tester: ____________

Launch only when the user says yes (window on DISPLAY3, no scripted input): `powershell -File tools/emu/launch.ps1 -Disc "build\trial\prop10c.gdi"`.

Result codes: **OK** / **clip** (cut at a box edge) / **over** (runs outside its box or over art) / **wrong** (Japanese, garbage, wrong number or unit) / **hang** (write the frame and the last button).
Ticks and hash marks around text are Flycast's texture filter: ignore them.  Words in `code style` are what the disc is supposed to show.  "Fallback" says which build flag or constant to change when a check fails.

Order follows the game: title, credits, new game, Hometown, Office, schedule, squad screens, finances, match, system menus.  Items that decide something carry a **DECIDE** tag.

## 1. Title screen and credits  (art, package J / H / I)

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 1.1 | Title: the red 2x2 tile logo | `SA KA` over `TSU KU`, one syllable per tile, same red extruded look | kana left; a tile with clipped letters | |
| 1.2 | Title: the hexagon banner under the logo | `TOKU DAI GOU` (the pun title kept romanised) | `特大号`; letters touching the hexagon edge | |
| 1.3 | Title: wordmark with its shadow | `SakaTsuku` in the red italic, black silhouette shadow exactly behind it | shadow offset from the letters, or the old `サカつく` shadow shape | |
| 1.4 | Title: tagline strip | `J.LEAGUE Let's Make a Pro Soccer Club!` | cut at the strip ends; `Football` (the older art7 wording) | |
| 1.5 | The three face tiles (the 大 / 特 / 号 tiles of the title / news sequences) | three tiles with `DAI`, `TOKU`, `GOU` in white (tile colours not confirmed: `docs/title-logo.md` says red, the member names `kao_g` / `kao_r` / `kao_y` suggest green / red / yellow; write down what you see); a very faint ghost of the old kanji is KNOWN (VQ residue) | Japanese kanji at full strength; a tile of garbage colours | |
| 1.6 | Credits (ending or title menu): the 15 role titles | `Director`, `Technical Director`, `Planner`, `Programmer`, `Network Programmer`, `Designer`, `Sound Technical Director`, `Commentary`, `Play-by-play`, `Promotion`, `Publicity`, `Special Thanks`, `Assistant Producer`, `Producer`, `General Manager` | kanji role; a title clipped at 128 px | |
| 1.7 | Credits: the 41 staff names, Given Family order | e.g. `Koichi Sasaki`, `Masaru Setsumaru`, `Kazushi Kimura`, `Takashi Mizunuma` (commentators), `Sanae Tatsuo`; readable at the credits size | kanji names left; names overlapping a role title | |
| 1.8 | **DECIDE**: the two readings that are still unconfirmed (`docs/credits-names.tsv`) | `Hiroyasu Lee`, `Kansuke Saito` look plausible to a Japanese reader (`Sunao Murayama`, `Kenji Takano`, `Atsutoshi Takahashi` were confirmed via Sega Retro) | a reading that is wrong: give the right one (two constants per name in `tools/re/s7bi_run.py`; one rebuilt texture each) | |
| 1.9 | News splash `ONISTA` (the December 2000 return story, if it comes up) | `DECEMBER 2000` over `Onishige Returns!!`; the seam falls inside `DECEMBER` (KNOWN) | untranslated halves | |

## 2. New game, Name Entry, Hometown  (text + art)

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 2.1 | Name Entry tabs | `ABC/123`, `Symbols`, `Confirm` not cut at the right edge (unchanged since prop8) | cut tab | |
| 2.2 | Hometown: header money | `.. oku .... man` with the unit sprites `oku` / `man` in lower case (the capital `O` read as `0`) | `Oku` capital; `15億` | |
| 2.3 | Hometown: data panel labels (TOWNSEL `04077`, TOWNDATA `04073`) | `Pop.`, `vs Prev`, `ppl`, `10k` (population corner unit, NOT `man`), `Land`, `Transit`, `Soccer Pop.`, `Annual Rainfall / Temp`, `vs Last Yr`, `Housing`, `Commerce`, `Sports`, `Nature`, `Other` | label runs to the plate edge or over a digit (the old `Population ppl / vs Last Month`); `Commerce` clipped | |
| 2.4 | Hometown / Office town menu plate (the 9-row list, yellow variant 08663 and white variant 08805) | two-line rows: `Advance Schedule`, `Office`, `Training Ground`, `Meeting Room`, `Youth` (white: `Sub Ground`), `Supporters' Club`, `Local Groups` (white: `Local Info`), `Quit / Options`, `National Ground`; each row inside the left 95 px | a row cut at the edge or Japanese left | |
| 2.5 | Town economy panel | tag `Economy`; levels `Boom` / `Good` / `Steady` / `Weak` / `Slump` | `景気` or a level in kanji | |
| 2.6 | Hometown lists (`Tohoku`, `Kansai` ...) and club names composed from town + word | unchanged since hsk_full1: `Tohoku` not `To ho ku`; club names at most 13 characters (`Kagos. Mythos`) | letter-pairs; a name running off its box | |
| 2.7 | **Club-name plates** (schedule cells, match preview, Stars / Legends teams, friendlies) | plates read like the logo art: `Antlers`, `Red Diamonds`, `JEF United`, `Reysol`, `Verdy`, `F Marinos` (no period), `Bellmare`, `S-Pulse`, `Júbilo`, `Grampus`, `Purple Sanga`, `Gamba`, `Cerezo`, `Vissel Kobe`, `Sanfrecce`, `Avispa`, `Consadole`, `Vegalta`, `Montedio`, `Ardija`, `F.C.TOKYO`, `Frontale`, `Ventforet`, `Albirex`, `Sagan Tosu`, `Trinita`, `Hollyhock`, `Yokohama FC` (the spellings of the plate table `tools/re/s7p_plates.py`, which follows the logo art; the text-side names in news / schedule strings may differ, e.g. `Reds`, `Sagan`, `FCTokyo`: that is KNOWN, `CHANGELOG.md` s7n); national teams without `代表`; the foreign clubs (`City + FC`) | katakana plates; a long name squashed unreadable; `F. Marinos` with a period | |
| 2.8 | Club words in made-up club names (second half: `Avalanche`, `Monolith`, `Topolino`, `Colmillo`, `Corriente`, `Herencia`, `Panthera`, `Cielo`, `Rosa`) | printed in FULL (`--refit on`), 13 characters at most in a composed club name | `Avalanc`, `Cie`, `Ros` (the slot-cut forms: then refit did not take); `Blau Wiese` / `Elf Schritt` cut to 8 in composed names (KNOWN) | |

## 3. Office, schedule

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 3.1 | Office main menu (07405) | `Schedule`, `Home Town`, `Staff`, `Facility` (rows 3 and 4 inside the original 51 px sprite), `Data Room`, `Quit / Options` | `Staff` / `Facility` cut at the right edge of the sprite (then 07405 needs a still shorter word) | |
| 3.2 | Office personnel plates and scout positions | `Sign Player`, `Transfer`, `Study Abroad`, `Change Manager`, `Change Scout`; scout positions `Goalkeeper` ... `Captain Candidate` `No Preference` | kanji; clipped plates | |
| 3.3 | Schedule calendar cells (word texture 10817) | `OFF`, `???`, `TBD` (for 未定), `Overseas Camp` | `未定` or `海外キャンプ` in a cell; `Overseas Camp` clipped | |
| 3.4 | Match preview line with the stadium | `Mythos Stadium` style: club name + ` Stadium` (`%s Stadium`) | `Mythos` followed by katakana `ｽﾀｼﾞｱﾑ` | |
| 3.5 | Schedule: `Wk 1` label under the `Today` arrow, `Pre-season Match` (KNOWN OPEN, finding 6 of `docs/layout-issues.md` s10.8) | note what you see: overlap or overflow, with a screenshot | | |
| 3.6 | Overseas camp banners (`04852` / `04853`) and event title banners | English banners, plate as wide as the text | | |

## 4. Squad screens  (alignment fix, `--align-fix on`)

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 4.1 | **Shirt numbers** (squad number screen, PLNUMSET): the list of 22 rows | the number column is straight: every number's digit starts at x0 + 180 (single digit) or x0 + 168 / 180 (two digits), whatever the name | numbers ragged (`3`, `4` at the right edge, `5` shifted left) as in hsk_full1; a number wrapped to the next line | |
| 4.2 | Shirt-number screen, right panel for a player WITH a number | row 1 ` Squad No.%2d` (12 cells, `Squad No. 7`), row 2 `DF 25yo` style (position + age), the two rows below present | rows 2-4 missing (the NUL cut the text), the number replaced by a line break | |
| 4.3 | Same panel for a player WITHOUT a number | ` Squad No.  ` and the rest of the panel intact | | |
| 4.4 | **Player-card panel** (Captain Select, Event info, Ending Options) right edges | `Tokyo`, `Season`, `Average`, `Age 25`, `1/2 yrs`, `3100 man`, `0 apps`, `0 goals`, `0.00 pts` end AT the panel edge, last letter not cut (hsk_full1 showed `Tokyc`, `Seasor`) | last letter cut by the panel edge (then the clip edge is not at the anchor: arithmetic says 2 to 5 px overflow was removed) | |
| 4.5 | **Name tags** (Practice > Player Placement; also Event, Office, GAME, G_RESULT, NEWCON, NEWS, TOWN, YOUTH, CAP_SLCT, ENDOPT name labels) | the FAMILY name, up to 7 letters: `Nakata`, `Yamada`, `Kawamoto`; one or two letters padded (` Ito `) | still `Taiy`, `Keij`, `H.` (patch not in the build: check the log line `tag fix: short_name() of 11 overlays replaced`); a tag cut to 4 cells | |
| 4.6 | **DECIDE (uncertainty)**: tag window width.  The label window may be clipped to 4 cells (`PlnameTask`, TRAINING `0x3391c`, not decoded) | up to 7 letters visible | `Nakat`, `Kawam` (clipped): set `layoutpatch.TAG_LIMIT` to 5 or 6 (proven for 4, 5, 6 in `tools/test_tagfix.py`) and rebuild; **LIMIT 5 / 6 / 7**: tell which count fits | |
| 4.7 | Name tags: the black empty name boxes and the `CF` position icon touching a name (KNOWN OPEN, code not located) | boxes filled; icon clear of the text | black empty boxes remain (they are sprites placed by the placement table; not fixed by the tag routine); `CF` overlaps a 7-letter name: then lower `TAG_LIMIT` to the icon-free width or move the name x | |
| 4.8 | Scout / player info fields (ABROAD, FIRE, PLNUMSET, SELNAT) | money in 12 characters, compact form `13 oku 1500m` | text past the field end | |
| 4.9 | Black rectangle above `4-4-2` (draft / manager panel) (KNOWN OPEN, still unlocated, `docs/s7t-proposals.md` s4) | note whether it is still there and what it sits above; screenshot | to test candidate (a) set `en = ""` for `SCDRF.BIN#32cd4` and `#32cdc` (the `Manager` / `Scout` labels) and rebuild: if the rectangle vanishes it is a text-width window | |

## 5. Finances and money  (text + art; `docs/number-formats.md` s11, s12)

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 5.1 | **TV station card capital** | compact `32 oku 5000m` from x = 456: clear of the `Capital` capsule, inside the plate | text over the capsule or past the plate | |
| 5.2 | Finances screens: data room, monthly report, income / costs table (G_INCOME), investment (INVEST) | `3 oku 9000 man`, `2 oku 4300 man`, `58 man`, `0 Yen`, red negatives; right-aligned rows end at the same place | `Y 390000000` (western amounts), `0k`, kanji `万円` | |
| 5.3 | Income table, crowd column | after the number the unit reads `man` (was `0k`), then `ppl`: e.g. `1man 2345ppl`; note exactly what you see (the `man` is the 万 of a head count, 10,000 people) | `0k` or `万` | |
| 5.4 | Annual report (NENREP): money lines, red negative form | `13oku 1500man` (compact, glued: the 12 / 20 byte slots), red `@R/` kept for negatives; `58 man`; `5000 Yen` | kanji `億` / `万円` (the data block was not patched), or text cut at the slot | |
| 5.5 | Annual report: attendance lines `%s万%s人` | NOT TRANSLATED (left Japanese, format of a head count): note whether it shows kanji | | |
| 5.6 | Unit sprites everywhere (header bar, plates, strips, SPT_CLUB, INVEST, graph headers) | lower case `oku` / `man`, `Yen` capital; population units `10k` / `ppl` | capital `Oku` / `Man` left in one sprite: list the screen | |
| 5.7 | **DECIDE**: does `oku` / `man` read well next to digits in the game font?  (`1 oku 8500 man`) | | | |

## 6. Match, practice and system menus

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 6.1 | **In-match tags** (GAMEETC): fixture heading, ranks | `No.5 MD` style (第N節 composed as prefix + number + suffix: `No.` + `5` + `MD`), cup rounds `5 Round`, `Final`, `Semi-final`; ranks `1th`, `2th`, `3th`, `4th` ... (**DECIDE**: the atlas has one suffix cell, so `1th / 2th / 3th`; 4 and up are right) | composition reads wrongly (`MD No.5`, `5 No.`); a missing cell | |
| 6.2 | In-match: tactics change heading and penalty buttons | `Change Tactics`; `Auto Select` (teal) / `Confirm` (orange); GK DF MF FW tabs unchanged | Japanese; letters cut | |
| 6.3 | In-match team-instruction sprite (attract demo or match: the HOME / AWAY label `静観`) | `Attack/Defend`, `Hold`, `All Defend`, `All Attack` (this texture IS the old `静観` label) | `静観` left (then the injector did not reach it: `34716`) | |
| 6.4 | Match / attract demo: the commentary box | All commentary is English: `/BCAST/BCAST.BIN` is fully merged (build log `bcast ... applied=30083 ... failed=0 skipped=0`, 30,083 of 30,083 subtitle segments, none empty), four commentary voices (`yh` play-by-play announcer 7,498 segments, `kk` 3,518, `mt` 3,320, `mm` 3,267 for the three colour commentators) plus 12,480 name callouts.  **No Japanese line is expected in the commentary box any more**; a Japanese line there is a defect.  Read three minutes of a match and the full list in section 6.4a: English lines read naturally, none runs past the box (75 byte clips, longest built line 74 characters), each voice keeps its own tone (announcer excited and brisk, colour commentators analytical and chatty), name callouts are full names | a Japanese line; an English line cut off or past the box; a stray glyph or box character in a line; wrong speaker tone; a name callout reading `Atsu` where a full name belongs; clips that run together without a space | |
| 6.5 | Practice screen, left menu and chips (37285 and friends) | `Practice Orders`, `Change Policy`, `Run Practice`, `View Teamwork`, `Team Check`; `Team Practice` / `Individual Practice` / `Extra Rest`; week labels `Wk 1`..`Wk 4`; `1st Half` / `2nd Half`; `Leave to Manager`; `Special Prep` | Japanese below y 170 (the old partial repaint); a chip wider than its plate | |
| 6.6 | Pre-match menu (BFGAME) and post-match news plates | `Opponent Info`, `Start Match`, `Change Policy`, `Win Bonus`, `Formation`, `Change Tactics`, `Mid Defence` (**DECIDE**: `Mid Defence` vs `Midfield Defence`), `DF Type`, `Set Takers`; news words `Today's Results`, `Standings`, `Goal Ranking`, `Scorers`, `Injured`, `Champions`, `Leaders` | Japanese plate; `Mid Defence` too wide for its plate | |
| 6.7 | Result words on the schedule / news: `First Advance`, `Advanced`, `Leaders`, `First Title`, `Last Match` (`docs/TRANSLATORS_NOTES.md`) | read naturally in context | | |
| 6.8 | Plates `Rd` vs `MD`: **DECIDE** which abbreviation reads right for a round / matchday (`Rd`, `MD`, `Matchday`) | | | |
| 6.9 | Meeting screen: the meter caption and end caps | `Complain.` (the 62 px box shortened `Complaint`), `Weak` / `Strong` end caps | clipped caps | |
| 6.10 | **End / Option menu** (ENDOPT plates 00803, 00805) | `Save and Quit` / `Create Data` / `Options` / `Backup` / `EXIT`; `Free Players` / `Opponent Clubs` / `Legend Clubs` / `EXIT` | gold text clipped | |
| 6.11 | OPTION screen: value plates and the list of sounds | `Near` / `Mid` / `Far`, `1 min` / `3 min` / `5 min`; OPTION.BIN labels now agree with the town menu plates: `Advance Schedule` (was `Next Day`), `Quit / Options` (was `End/Setup`) | a label wider than its cell (16 and 14 characters now; the OPTION.BIN cell width is NOT known: if cut, shorten both strings and the plate together) | |
| 6.12 | Facility Step Up tags and others | `Can Expand`, `To Be Removed`, `Can Rebuild`; unit strips `oku` / `man` / `ppl`; `Yr` plate; youth labels; `FLASH` (速報) | Japanese tag | |
| 6.13 | Hometown event picture (JSCEVENT, id 02235: the blue banner over the crowd) | `Local Soccer Tournament` in white on the blue banner, inside it; the small sideline advert board is left as it was (advert signage) | the Japanese banner `地元サッカー大会`; the English wider than the banner | |
| 6.14 | **EXPECTED to stay Japanese** (not defects; do not log them as failures, list what you see) | sponsor logos and advert signage (user rule: sponsor logos stay Japanese); the annual-report attendance lines `%s万%s人` (item 5.5) | | |

### 6.4a BCAST commentary playtest list (all of it new in prop10c, nothing seen on screen)

Play or watch a match with the commentary on and tick each situation once; for every one note the speaker (announcer `yh`, or a colour commentator `kk` / `mm` / `mt`), the line, and a result code.
Pass = English, fits the box, no stray glyph, tone suits the voice.  Clips are shown one behind the other, so two lines in a row must read as a sentence with a space between them.

| # | Situation | What to look for | Result |
|---|---|---|---|
| a | Attract demo and match opening: introductions, who is commentating, stadium and weather | `yh` announcer opens; colour commentator greeting; stadium and club names are the same English as on the plates | |
| b | Kick-off and the first replay intros (`replay`, `rplay` clips) | `Let's go to the replay right away.` style lines; the replay intro does not run over the box | |
| c | Half-time (`hftm`, `halfend`): score summary and the commentators' analysis | long colour-commentator lines (up to 74 characters) stay inside two lines; score wording agrees with the scoreboard | |
| d | Full-time (`end`, `win`, `siai`): result of the match, `They drew with El Salvador.` style lines, titles and trophies (`Super Youth Cup champions`) | club / nation / tournament names are the English of the plates; no Japanese | |
| e | Set pieces: free kicks (`fk`), corners (`ck`), penalties (`pk`, `pkm`), penalty shoot-out (`pks`), throw-ins (`hkick`, `furi`) | short punchy lines; the shoot-out lines suit the kicker / keeper outcome | |
| f | Shots, saves and goals (`shoot`, `sht`, `gk`, `goal`) | goal calls read as excitement, not stilted; `A little lob!` | |
| g | Fouls, cards, injuries (`foul`, `jiko`), substitutions and tactical changes (`chg`, `chan`) | the card colour and the player agree with the line; `The trump card is brought on here.` | |
| h | Zatsu chatter (`zatu`: the idle talk between the colour commentators, about 900 clips per voice) | natural conversation, no repeated robotic line, no Japanese; check three clips from each of `kk` `mm` `mt` | |
| i | Name callouts (`name`, `call`, `num`, `tm`): a player is named, a team is named | full romanised names or club names, the same spelling as the squad screens; `Yatsuka` / `Yatsuka?` as in the call clips | |
| j | Announcer results (`yh` results block after a match, league tables, tournament progress: `tour`, `win`, `new`, `time`) | rank and round words (`Quarter-final`) agree with the plates; no cut-off | |
| k | Mid-match situation talk (`siama`, `plan`, `play`, `pass`, `dri`, `surp`, `bgm`) | tone: analytical for `kk` / `mm` / `mt`, brisk for `yh` | |
| l | Count any Japanese line, any line cut at the box edge and any stray symbol; write the clip's first words and the minute | **expected: none** | |

The clip `BCAST/BCAST.BIN#1de96880` (`yh_gm_name_0036`, Japanese `世界ｽﾎﾟｰﾂ大会予選`) now shows the full database English `World Sports Festival Qualifiers` (the refit overlay that shortened it to `Sports Fest. Qual.` was removed in stage 8d; the slot has room).  Check that it fits the banner and reads well.

## 7. If the disc hangs or looks broken

* The hang of 1 Yr 1 Mo Wk 1 (second Event screen) is still the first thing to test (`docs/test-sheet-prop8.md` section A, `docs/hang-investigation.md`).
* Checks already made on the disc bytes (read-only, 2026-11-12 evening): `verify_disc` OK, `tools/zsarc_crc_audit.py build/trial/prop10c.gdi` 164 files / 2,482 members, 0 stale; `tools/artcoverage.py --log build/trial/prop10c.log`: 0 NOT APPLIED, MISSING only the four blank frames 02213 02214 03570 03571.
* BCAST read back from the built disc (2026-11-12 stage 8d, `build/s8c_bcast_readback.py`, `build/trial/prop10c_bcast_readback.log`): all 30,083 records compared with the database English, 30,083 equal, 0 over the 75-byte budget, 0 non-ASCII bytes; sample of 357 in `build/trial/prop10c_bcast_sample.txt`.
* Fallbacks without a rebuild of everything: `--tag-fix off`, `--align-fix off`, `--refit off` each switch one piece off (`docs/pipeline.md` s9).
