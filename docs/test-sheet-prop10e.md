# Test sheet: prop10e (hang checks, scout screen, everything else since hsk_full1)

Primary disc: `build/trial/prop10e.gdi` (standard flags: `--repack on --share dup --append-safe --proportional-font on --strict`, defaults `--refit on --align-fix on --tag-fix on`, plus `--scout-fix on`; log `build/trial/prop10e.log`, patch digest `a53fe0a7b9781556781bc2baa9c3d7fab854a5f5`).
Bisect discs, boot ONLY if prop10e hangs at the first Event message, in this order: `prop10e_snap`, then `prop10e_panel` (section 9).
Built and checked read-only: 396,819 strings applied, 0 failed; `verify_disc` OK; `zsarc_crc_audit` 0 stale (2,482 members); `artcoverage` 0 NOT APPLIED (missing only the blank frames 02213 02214 03570 03571); `test_pipeline` 351 checks passed.
**Nothing below has been seen on screen.**  Last discs played: `hsk_full1` (passed the Event screen), `s8e_nofix` (first message OK, scout screen wrong), `s8e_notag` (hung at the first message), `s8g_norefit` (scout screen working, Age blank).  Date: ____________  Tester: ____________

Launch only when the user says yes (window on DISPLAY3, no scripted input): `powershell -File tools/emu/launch.ps1 -Disc "build\trial\prop10e.gdi"`.

Result codes: **OK** / **clip** (cut at a box edge) / **over** (runs outside its box or over art) / **wrong** (Japanese, garbage, wrong number or unit) / **hang** (write the frame and the last button).
Ticks and hash marks around text are Flycast's texture filter: ignore them.  Words in `code style` are what the disc is supposed to show.  "Fallback" says which flag or constant to change when a check fails.

Order: hang checks first (stop and go to section 9 if one hangs), scout screen, then the game order: title, credits, new game, Hometown, Office, squad screens, finances, match, system menus.  Items that decide something carry a **DECIDE** tag.

## 1. Hang checks  (play these first)

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 1.1 | New game, advance to **1 Yr 1 Mo Wk 1**: the first Event screen (secretary) | the first message appears with its text (not an empty window) | empty message window, no text, no input response (the prop10c / `s8e_notag` hang) | |
| 1.2 | Press through the whole first Event message sequence | every message advances with A; the Event screen ends normally and the schedule screen comes up | freeze on any message: write the message text on screen and the frame | |
| 1.3 | The secretary message `At last, they've accepted our offer.` (scout / transfer result; the earlier freeze stopped at `At last, they've accepted o`) | the full sentence types out to the end, then the next message or the screen closes | freeze mid-sentence | |
| 1.4 | Other secretary / manager message chains (Office, Schedule, Meeting Room, a weekly report) | each completes; no empty window | hang or empty window: write which screen | |
| 1.5 | Reach a J.League match (hsk_full1 did) and play one minute | match runs, commentary appears | freeze before or in the match | |

## 2. Scout screen  (the Scout / Candidate list; fixes of stages 8f to 8h)

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 2.1 | Salary scale against club funds | salaries in the right order of magnitude: e.g. `7800 man`, with club funds of 8 oku (`s8g_norefit` showed this) | `35 oku 8500m` against 8 oku funds (value about x100: the relocated table base, the prop10c / s8e_nofix bug) | |
| 2.2 | Candidate list contents | Japanese and foreign candidates mixed, **including an Ehime player**; names romanised; many rows | only foreign candidates (Madrid, Kazakhstan); an empty list | |
| 2.3 | Candidate card: the Age row (SCDRF and SEARCH builders) | `Age 25` style, number shown, right aligned in 12 cells (`      Age 25`) | `Age ` with no number (the old blank; hsk_full1 and s8g_norefit showed it) | |
| 2.4 | Candidate card: the contract rows | `Wants  2 yrs` and the years row `   5/3 yrs  ` both present, rows 3 and 4 not missing | rows 3 and 4 vanish; `yrs` row absent or clipped | |
| 2.5 | Candidate card: the club row | the candidate's club name in English, inside its box | Japanese; club name running over the next row | |
| 2.6 | Candidate picture box | the player portrait / blank frame, no garbage | a box of garbage graphics labelled `g6` (the old bug) | |
| 2.7 | Scout positions, current-player rows (the other builder of the same panel) | rows draw with Age number; same format as 2.3 and 2.4 | rows 3 and 4 missing | |
| 2.8 | Open and close the scout list three times, change page | stable | hang or garbage appearing after the second open | |
| 2.9 | Backup / club-word lists (BACKUP): club words `Panther` and `Mythos` (these two records moved from in-place to relocated in this build) | read normally, e.g. `Kagos. Mythos` in a composed name | garbage; a name from the wrong entry; hang opening the screen | |

## 3. Title screen and credits  (art)

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 3.1 | Title: the red 2x2 tile logo | `SA KA` over `TSU KU`, one syllable per tile | kana left; a tile with clipped letters | |
| 3.2 | Title: the hexagon banner under the logo | `TOKU DAI GOU` | `特大号`; letters touching the hexagon edge | |
| 3.3 | Title: wordmark with its shadow | `SakaTsuku` in the red italic, silhouette shadow exactly behind it | shadow offset, or the old `サカつく` shadow shape | |
| 3.4 | Title: tagline strip | `J.LEAGUE Let's Make a Pro Soccer Club!` | cut at the strip ends; `Football` | |
| 3.5 | The three face tiles (大 / 特 / 号) | tiles with `DAI`, `TOKU`, `GOU` in white (note the tile colours you see); a very faint ghost of the old kanji is KNOWN | Japanese kanji at full strength; garbage colours | |
| 3.6 | Credits: the 15 role titles | `Director`, `Technical Director`, `Planner`, `Programmer`, `Network Programmer`, `Designer`, `Sound Technical Director`, `Commentary`, `Play-by-play`, `Promotion`, `Publicity`, `Special Thanks`, `Assistant Producer`, `Producer`, `General Manager` | kanji role; a title clipped | |
| 3.7 | Credits: the 41 staff names, Given Family order, **including `Sunao Murayama`** | e.g. `Koichi Sasaki`, `Masaru Setsumaru`, `Sunao Murayama`, `Kenji Takano`, `Atsutoshi Takahashi`, `Takashi Mizunuma`; sponsors kept | `Nao Murayama` (the older texture); kanji names left; names overlapping a role title | |
| 3.8 | **DECIDE**: the two staff readings still unconfirmed (`docs/credits-names.tsv`) | `Hiroyasu Lee`, `Kansuke Saito` plausible to a Japanese reader | a wrong reading: give the right one | |
| 3.9 | News splash `ONISTA` (December 2000 return story, if it comes up) | `DECEMBER 2000` over `Onishige Returns!!`; the seam inside `DECEMBER` is KNOWN | untranslated halves | |

## 4. New game, Name Entry, Hometown  (text + art)

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 4.1 | Name Entry tabs | `ABC/123`, `Symbols`, `Confirm` not cut (seen OK in the last playtest) | cut tab | |
| 4.2 | Hometown: header money | `.. oku .... man`, unit sprites in lower case | `Oku` capital; `15億` | |
| 4.3 | Hometown data panel labels (TOWNSEL `04077`, TOWNDATA `04073`) | `Pop.`, `vs Prev`, `ppl`, `10k`, `Land`, `Transit`, `Soccer Pop.`, `Annual Rainfall / Temp`, `vs Last Yr`, `Housing`, `Commerce`, `Sports`, `Nature`, `Other` | label over a digit or plate edge; `Commerce` clipped | |
| 4.4 | Hometown / Office town menu plate (9 rows) | `Advance Schedule`, `Office`, `Training Ground`, `Meeting Room`, `Youth` (white: `Sub Ground`), `Supporters' Club`, `Local Groups` (white: `Local Info`), `Quit / Options`, `National Ground`, inside the left 95 px | a row cut or Japanese | |
| 4.5 | Town economy panel | tag `Economy`; `Boom` / `Good` / `Steady` / `Weak` / `Slump` | kanji | |
| 4.6 | Hometown lists and composed club names | `Tohoku` not `To ho ku`; club names at most 13 characters | letter-pairs; a name off its box | |
| 4.7 | **Club-name plates** (schedule cells, match preview, Stars / Legends teams, friendlies) | plates read like the logo art: `Antlers`, `Red Diamonds`, `JEF United`, `Reysol`, `Verdy`, `F Marinos` (no period), `Bellmare`, `S-Pulse`, `Júbilo`, `Grampus`, `Purple Sanga`, `Gamba`, `Cerezo`, `Vissel Kobe`, `Sanfrecce`, `Avispa`, `Consadole`, `Vegalta`, `Montedio`, `Ardija`, `F.C.TOKYO`, `Frontale`, `Ventforet`, `Albirex`, `Sagan Tosu`, `Trinita`, `Hollyhock`, `Yokohama FC`; text-side names in news may differ (KNOWN) | katakana plates; unreadable squash; `F. Marinos` | |
| 4.8 | Club words in made-up club names | second-half words in FULL (`Avalanche`, `Monolith`, `Topolino`, `Colmillo`, `Corriente`, `Herencia`, `Panthera`, `Cielo`, `Rosa`), 13 characters at most | `Avalanc`, `Cie`, `Ros` (refit did not take); `Blau Wiese` / `Elf Schritt` cut to 8 (KNOWN) | |

## 5. Office, schedule

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 5.1 | Office main menu (07405) | `Schedule`, `Home Town`, `Staff`, `Facility`, `Data Room`, `Quit / Options` | `Staff` / `Facility` cut | |
| 5.2 | Office personnel plates and scout positions | `Sign Player`, `Transfer`, `Study Abroad`, `Change Manager`, `Change Scout`; positions `Goalkeeper` ... `Captain Candidate`, `No Preference` | kanji; clipped plates | |
| 5.3 | Schedule calendar cells (10817) | `OFF`, `???`, `TBD`, `Overseas Camp` | `未定` / `海外キャンプ`; clipped | |
| 5.4 | Match preview line with the stadium | `Mythos Stadium` style | club name then katakana `ｽﾀｼﾞｱﾑ` | |
| 5.5 | Schedule: `Wk 1` under the `Today` arrow, `Pre-season Match` (KNOWN OPEN, `docs/layout-issues.md` s10.8) | note overlap or overflow with a screenshot | | |
| 5.6 | Overseas camp banners (`04852` / `04853`) and event title banners | English, plate as wide as the text | | |

## 6. Squad screens  (alignment fix; the part that differs between prop10e, `_snap` and `_panel`)

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 6.1 | **Shirt numbers** (PLNUMSET): the 22 rows | number column straight, whatever the name | ragged numbers as in hsk_full1; a number on the next line | |
| 6.2 | Shirt-number right panel, player WITH a number | ` Squad No.%2d` (`Squad No. 7`), `DF 25yo` style row, the two rows below present | rows 2 to 4 missing; number replaced by a line break | |
| 6.3 | Same panel, player WITHOUT a number | ` Squad No.  ` and the rest intact | | |
| 6.4 | **Player-card panel** (Captain Select, Event info, Ending Options) right edges | `Tokyo`, `Season`, `Average`, `Age 25`, `1/2 yrs`, `3100 man`, `0 apps`, `0 goals`, `0.00 pts` end AT the panel edge (hsk_full1 showed `Tokyc`, `Seasor`) | last letter cut by the edge | |
| 6.5 | **Name tags** (Practice > Player Placement; Event, Office, GAME, G_RESULT, NEWCON, NEWS, TOWN, YOUTH, CAP_SLCT, ENDOPT labels) | the FAMILY name up to 7 letters: `Nakata`, `Yamada`, `Kawamoto` | `Taiy`, `Keij`, `H.` (log line `tag fix: short_name() of 11 overlays replaced` missing); a tag cut to 4 cells | |
| 6.6 | **DECIDE**: tag window width (`PlnameTask`, TRAINING `0x3391c`, not decoded) | up to 7 letters visible | `Nakat`, `Kawam`: set `layoutpatch.TAG_LIMIT` to 5 or 6 and rebuild; tell which count fits (**LIMIT 5 / 6 / 7**) | |
| 6.7 | Name tags: empty black name boxes, `CF` icon touching a name (KNOWN OPEN) | boxes filled; icon clear | black boxes remain; `CF` over a 7-letter name | |
| 6.8 | Player info fields (ABROAD, FIRE, PLNUMSET, SELNAT) | money in 12 characters `13 oku 1500m` | text past the field end | |
| 6.9 | Black rectangle above `4-4-2` (draft / manager panel) (KNOWN OPEN, `docs/s7t-proposals.md` s4) | note whether present and what it sits above; to test set `en = ""` for `SCDRF.BIN#32cd4` and `#32cdc` | | |

## 7. Finances and money  (`docs/number-formats.md` s11, s12)

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 7.1 | **TV station card capital** | `32 oku 5000m` from x = 456, clear of the `Capital` capsule | text over the capsule or past the plate | |
| 7.2 | Finances: data room, monthly report, G_INCOME, INVEST | `3 oku 9000 man`, `2 oku 4300 man`, `58 man`, `0 Yen`, red negatives, right-aligned rows | `Y 390000000`, `0k`, `万円` | |
| 7.3 | Income table crowd column | `1man 2345ppl` style; note exactly what you see | `0k` or `万` | |
| 7.4 | Annual report (NENREP) money lines | `13oku 1500man`, red `@R/` negatives, `58 man`, `5000 Yen` | kanji `億` / `万円`; text cut at the slot | |
| 7.5 | Annual report attendance lines `%s万%s人` | NOT TRANSLATED (KNOWN): note whether it shows kanji | | |
| 7.6 | Unit sprites everywhere | lower case `oku` / `man`, `Yen`; `10k` / `ppl` | capital `Oku` / `Man`: list the screen | |
| 7.7 | **DECIDE**: does `oku` / `man` read well next to digits? (`1 oku 8500 man`) | | | |

## 8. Match, practice and system menus

| # | Screen | Good looks like | Failure looks like | Result |
|---|---|---|---|---|
| 8.1 | **In-match tags** (GAMEETC) | `No.5 MD`, `5 Round`, `Final`, `Semi-final`; ranks `1th`, `2th`, `3th`, `4th` (**DECIDE**: one suffix cell, so `1th / 2th / 3th`) | `MD No.5`, `5 No.`; missing cell | |
| 8.2 | Tactics change heading and penalty buttons | `Change Tactics`; `Auto Select` / `Confirm`; GK DF MF FW tabs | Japanese; cut letters | |
| 8.3 | Team-instruction sprite (the old `静観` label) | `Attack/Defend`, `Hold`, `All Defend`, `All Attack` | `静観` left | |
| 8.4 | Match / attract demo: the commentary box | all commentary English (`/BCAST/BCAST.BIN` fully merged, 30,083 of 30,083 segments, four voices `yh` `kk` `mt` `mm` plus 12,480 name callouts); read three minutes and the list in 8.4a; none past the box (longest line 74 characters), each voice keeps its tone | a Japanese line; a cut or overlong line; a stray glyph; wrong tone; `Atsu` where a full name belongs; clips run together | |
| 8.5 | Practice screen, left menu and chips (37285) | `Practice Orders`, `Change Policy`, `Run Practice`, `View Teamwork`, `Team Check`; `Team Practice` / `Individual Practice` / `Extra Rest`; `Wk 1`..`Wk 4`; `1st Half` / `2nd Half`; `Leave to Manager`; `Special Prep` | Japanese below y 170; chip wider than plate | |
| 8.6 | Pre-match menu (BFGAME) and post-match news plates | `Opponent Info`, `Start Match`, `Change Policy`, `Win Bonus`, `Formation`, `Mid Defence` (**DECIDE**: vs `Midfield Defence`), `DF Type`, `Set Takers`; `Today's Results`, `Standings`, `Goal Ranking`, `Scorers`, `Injured`, `Champions`, `Leaders` | Japanese plate; `Mid Defence` too wide | |
| 8.7 | Result words: `First Advance`, `Advanced`, `Leaders`, `First Title`, `Last Match` | read naturally | | |
| 8.8 | **DECIDE**: `Rd` vs `MD` vs `Matchday` for a round / matchday plate | | | |
| 8.9 | Meeting screen meter caption and end caps | `Complain.`, `Weak` / `Strong` | clipped caps | |
| 8.10 | **End / Option menu** (ENDOPT 00803, 00805) | `Save and Quit` / `Create Data` / `Options` / `Backup` / `EXIT`; `Free Players` / `Opponent Clubs` / `Legend Clubs` / `EXIT` | gold text clipped | |
| 8.11 | OPTION screen (seen OK once) and sound list | `Near` / `Mid` / `Far`, `1 min` / `3 min` / `5 min`; `Advance Schedule`, `Quit / Options` agree with the town menu | label wider than its cell (width unknown: shorten both string and plate) | |
| 8.12 | Facility Step Up tags and others | `Can Expand`, `To Be Removed`, `Can Rebuild`; `oku` / `man` / `ppl`; `Yr`; youth labels; `FLASH` | Japanese tag | |
| 8.13 | Hometown event picture (JSCEVENT 02235) | `Local Soccer Tournament` in white inside the blue banner | `地元サッカー大会`; English wider than the banner | |
| 8.14 | **EXPECTED to stay Japanese** (not defects) | sponsor logos and advert signage; annual-report attendance lines (7.5) | | |

### 8.4a BCAST commentary playtest list

Watch a match with commentary on and tick each situation once; for every one note speaker (`yh` announcer, `kk` / `mm` / `mt` colour), the line and a result code.  Pass = English, fits the box, no stray glyph, tone suits the voice, two clips in a row read as one sentence.

| # | Situation | What to look for | Result |
|---|---|---|---|
| a | Attract demo and opening: who is commentating, stadium, weather | `yh` opens; names match the plates | |
| b | Kick-off and first replay intros (`replay`, `rplay`) | `Let's go to the replay right away.` style; no overrun | |
| c | Half-time (`hftm`, `halfend`) | long colour lines (up to 74 chars) stay inside two lines; score agrees with scoreboard | |
| d | Full-time (`end`, `win`, `siai`) | `They drew with El Salvador.` style; trophies (`Super Youth Cup champions`); no Japanese | |
| e | Set pieces (`fk`, `ck`, `pk`, `pkm`, `pks`, `hkick`, `furi`) | short punchy lines | |
| f | Shots, saves, goals (`shoot`, `sht`, `gk`, `goal`) | excitement, not stilted; `A little lob!` | |
| g | Fouls, cards, injuries, substitutions (`foul`, `jiko`, `chg`, `chan`) | card colour and player agree; `The trump card is brought on here.` | |
| h | Chatter (`zatu`): three clips from each of `kk` `mm` `mt` | natural, no robotic repeats, no Japanese | |
| i | Name callouts (`name`, `call`, `num`, `tm`) | full romanised names, same spelling as the squad screens | |
| j | Announcer results (`tour`, `win`, `new`, `time`) | round words (`Quarter-final`) agree with plates | |
| k | Mid-match talk (`siama`, `plan`, `play`, `pass`, `dri`, `surp`, `bgm`) | analytical for `kk` / `mm` / `mt`, brisk for `yh` | |
| l | Count Japanese lines, cut lines, stray symbols (first words and minute) | **expected: none** | |
| m | Clip `BCAST#1de96880` (`世界ｽﾎﾟｰﾂ大会予選`) | full `World Sports Festival Qualifiers`, fits the banner | |

## 9. If prop10e hangs: boot the bisect discs, in this order

Known so far: `s8e_nofix` (align off, tag off) passed the first message; `s8e_notag` (global align hook plus panel edits, tag off) hung.  prop10e removed the global hook (the snap is now only in PLNUMSET) but still has the panel edits (20 `shll2` to `nop`, 8 `strlen` to `pw3` literals in CAP_SLCT, ENDOPT, EVENT), the tag fix and the hw-guard changes.  Static checks show the first-message layout path is bit-for-bit the align-off one, so the cause is not found by simulation; booting decides it.

| Disc | What it contains | Boot when |
|---|---|---|
| `prop10e_snap` (`SAKA_ALIGN_MODE=snap-only`) | shirt-number snap in PLNUMSET only; NO panel edits (the three overlays CAP_SLCT / ENDOPT / EVENT are as on the align-off disc) | first, if prop10e hangs |
| `prop10e_panel` (`SAKA_ALIGN_MODE=panel-only`) | panel edits only; NO snap (PLNUMSET unchanged) | second, only if `prop10e_snap` also hangs, or to confirm |

Reading the results (1.1 to 1.3 on each disc):

| prop10e | `_snap` | `_panel` | Meaning |
|---|---|---|---|
| OK | not needed | not needed | fixed; run sections 2 to 8 on prop10e |
| hang | OK | (boot to confirm: expected hang) | the **panel edits** in EVENT / CAP_SLCT / ENDOPT are the culprit; ship the snap only (shirt numbers straight, player-card edges as hsk_full1: items 6.4 clip is expected) |
| hang | hang | OK | the **snap** is the culprit (PLNUMSET hook); ship the panel edits only (6.1 ragged numbers expected) |
| hang | hang | hang | align-fix is exonerated: the cause is the tag fix (EVENT routine 0x4ba14) or the hw-guard / relocation changes.  `s8e_noalign` (tag on, align off) was built and never booted: boot it next; if it hangs the tag fix is to blame (fallback `--tag-fix off`) |

On any disc: `snap` shows items 6.1 to 6.3 straight but 6.4 with last letters cut; `panel` shows 6.4 correct but 6.1 ragged.  That is expected, not a failure.
Fallbacks without rebuilding everything: `--align-fix off`, `--tag-fix off`, `--refit off` switch one piece off each (`docs/pipeline.md` s9); `--scout-fix off` removes the Age patch.
Note on BACKUP: prop10e differs from prop10d in `FLOW_PRG/BACKUP.BIN` (two club-word records moved to relocated; array heads kept in place 3 to 1); item 2.9 checks it.
