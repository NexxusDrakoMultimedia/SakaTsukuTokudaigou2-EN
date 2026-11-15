# Translators' notes and player's guide

English patch for **Sakatsuku Tokudaigou 2 - J.League Pro Soccer Club o Tsukurou!** (Sega Dreamcast, Japan, HDR-0183).

This file ships in every release. It tells you how to apply the patch, and it explains the places where the English
deliberately stays close to the Japanese original (money in oku and man, kyu and dan ranks, place-name endings and so
on), so that nothing in the game has to stop and explain itself.

Contents: 1 What this is - 2 Applying the patch - 3 Money: oku and man - 4 Names - 5 Places and club names -
6 Ranks, counters, positions and other Japanese terms - 7 The name-entry screen - 8 Known rough spots - 9 Build options -
10 Credits and licence - 11 FAQ

---

## 1. What this is

This is a fan translation of the Japanese Dreamcast game. It changes the text and a number of repainted pictures and
patches a few small routines in the game program, so that the game can show English. You need **your own dump of the
Japanese disc**; the download contains no original Sega pixels, only small `xdelta` (VCDIFF) patch files that turn your dump into
the English version.

Project goals:

* **Make the whole game playable in English**: menus, dialogue, help pages, news, reports, names of places, clubs, players
  and staff, and the text baked into pictures.
* **Keep the game appropriately Japanese.** It is a Japanese football-club management game about the Japanese league
  of 1999-2000, and it should still feel like one. Where Japan counts or ranks things in its own way, the English
  keeps that structure in English letters instead of converting it to Western habits. Money is the clearest case
  (section 3). The few places where this means you need a little background are explained here, not in the game.
* **British English** for the running text (centre, colour, defence, football, match, pitch, kit, supporters).
  The product name keeps "Soccer" because that is its title.
* **Change as little as possible.** Nothing about the rules, the data or the balance of the game is altered. Only text,
  pictures, and the code needed to print the text (a variable-width letter routine, the money printer and a bounded
  club-name builder) are touched.

## 2. Applying the patch

### 2.1 What you need

* A dump of the Japanese disc (the dump this project was built against; its catalogue reference is Redump disc 27370)
  in one of these forms. The hashes in this guide are those of that dump; the tooling has not compared them with the
  Redump database:
  * **BIN/CUE**: one `.cue` and five `... (Track N).bin` files;
  * **GDI**: one `.gdi` with `track01.bin`, `track02.raw`, `track03.bin`, `track04.raw`, `track05.bin`;
  * **volume ISO**: one `.iso` (2048-byte sectors, starting at disc sector 45000 with `SEGA SEGAKATANA`).
  Other forms (a single `.bin` for all tracks, CHD, CSO, NRG, CDI, per-track 2048-byte `.iso`) are not supported:
  convert them to one of the above first.
* **Python 3.8 or newer.** `apply_patch.py` is a single file with no other requirements (the xdelta decoder is built in).
* About 1.2 GB of free space for the patched disc, plus about 2 GB of temporary space on the ISO route.

### 2.2 The easy way: `apply_patch.py`

Keep `apply_patch.py`, `MANIFEST.json` and the `.xdelta` files together in one folder, then run one of:

```
python apply_patch.py "C:\Games\Sakatsuku 2\Sakatsuku.cue"
python apply_patch.py "C:\Games\Sakatsuku 2\disc.gdi"
python apply_patch.py "C:\Games\Sakatsuku 2\Sakatsuku.iso"
python apply_patch.py disc.gdi --verify          # only report: original, already patched, or wrong dump
python apply_patch.py Sakatsuku.cue --to iso     # write the patched game as a volume ISO instead
```

It recognises the format from the file contents, checks your files against the hashes of the original dump, and writes the
patched copy **next to** your files in the same format (a new folder with a `.cue` or `.gdi`, or a new `.iso`). Your own
files are never modified. Other options: `--out` (output location), `--link` (hard-link the unchanged tracks instead of
copying them), `--overwrite`, `--method raw|iso`.

### 2.3 Checking your dump (hashes)

`HASHES.txt` and `MANIFEST.json` in this download list every hash (CRC-32, MD5, SHA-1, SHA-256); `README.md` has a
short table. The patch expects this original disc (SHA-1):

| File | SHA-1 of the original |
|---|---|
| Track 1 (`track01.bin`) | `ec178640c03ab98de4d07b76fd5555417137def1` |
| Track 2 (`track02.raw`) | `0ecd537e42946f3e74c80c9fcb8d0bccccfc96f1` |
| Track 3 (`track03.bin`) | `8a7c7484489d42896e3b73a8b2d4588720a3936d` |
| Track 4 (`track04.raw`) | `fbdd698c67ee95d4223f9c873bb3697ee8447132` |
| Track 5 (`track05.bin`) | `753b66f8a2a5553cce8abe804fa68145cf3522e4` |
| Volume ISO | `62a9ccfd3a965328861e5b46fa71e5686642e5e1` |

Tracks 3 and 5 hold the game and matter most. Tracks 1, 2 and 4 are not changed by the patch; different dumpers store
the audio track and the pregaps a little differently, and `apply_patch.py` only warns about that. If track 3 or 5
differs, do not patch: re-dump the disc, or see section 5 of `README.md`.

### 2.4 By hand

You can also apply each `.xdelta` to its track with xdelta UI, DeltaPatcher or `xdelta3 -d -s source patch output`; the
exact file names and command lines are in `README.md`. The output must get the same file name as the original, and
you must compare the result with the hashes in `HASHES.txt`.

### 2.5 Emulators and hardware

* **Flycast** is the emulator the patch was developed and played in. Boot the new `.gdi` or `.cue`.
* No other emulator has been tested by this project.

### 2.6 Flycast tip: faint tick marks around the text

If you see tiny ticks, hairlines or cell outlines around letters (line ends, under the baseline), that is **not** a
patch fault: it is texture filtering in the emulator. The game draws its letters as small textured squares taken
from one big picture, and smooth (bilinear) filtering lets a bit of the neighbouring square bleed in. The original
Japanese disc shows the same thing. In Flycast's graphics settings set the texture filtering to **nearest-neighbour**
("Force Nearest-Neighbor" in current versions) and the marks disappear.

## 3. Money: oku and man

Japan counts large numbers in steps of ten thousand, not a thousand. The game prints money in two units, and so does this
patch, in English letters:

* **man** = 10,000 yen (the Japanese character for ten thousand)
* **oku** = 100,000,000 yen = 10,000 man (the Japanese character for one hundred million)

An amount is written oku first, then man, with a space between them. A part that is zero is left out.
To turn it into yen: **yen = oku x 100,000,000 + man x 10,000.**
Both words are in lower case on purpose: a capital `O` looks like a zero in the game font (`1 Oku` read as `1 0ku`).

| In the game | Yen |
|---|---|
| `0 Yen` | 0 yen |
| `1 man` | 10,000 yen |
| `150 man` | 1,500,000 yen |
| `6000 man` | 60,000,000 yen |
| `1 oku` | 100,000,000 yen |
| `1 oku 300 man` | 103,000,000 yen |
| `13 oku` | 1,300,000,000 yen |
| `13 oku 1500 man` | 1,315,000,000 yen |
| `32 oku 5000 man` | 3,250,000,000 yen |
| `9999 oku 9999 man` | 999,999,990,000 yen |
| `3 oku 9000 man` | 390,000,000 yen |

Reading `13 oku 1500 man`: 13 oku is 1,300,000,000 yen, 1500 man is 15,000,000 yen, together 1,315,000,000 yen. A man part
can be at most 9999, because 10,000 man is already 1 oku.

Things to know:

* **There is no `Y` or yen sign in front of amounts and no decimal form** (no `Y1.3bn`). `Yen` appears for an
  amount of exactly zero (`0 Yen`), for a plain yen amount below one man (`5000 Yen`, a ticket price) and on the unit pictures.
* The man part is not padded with zeros: `1 oku 1 man` is 100,010,000 yen.
* A negative amount has a minus sign in front: `-1 man` (in a few tables red text is used instead).
* In a narrow field the word `man` after an oku part is shortened to `m`: `13 oku 1500m` is `13 oku 1500 man`
  (the scout panel, the TV station card capital, the 12-character player-info fields).
* Amounts that the game keeps in plain yen (the income / costs table) are shown rounded down to whole man:
  `3 oku 9000 man` stands for 390,000,000 yen up to 9,999 yen.
* **Population is the exception.** Next to a head-count the Japanese "man" character is written `10k` (ten thousand people), not
  `man`: the graph header reads `People (10k)`.
* Graph headers and the small unit pictures beside digits are repainted to `oku`, `man` and `Yen` to match.
* The data-room tables, the monthly report, the income / costs table and the investment screen use older game routines;
  they were converted with small code patches (`tools/moneypatch.py`) and print the same words. A table of figures of the
  `debug` kind (the lists `%3d %-13s Y%d %d yr` in HELP / TITLE / LOCAL) may still show a plain `Y` figure; see section 8.

## 4. Names

* **People** (players, managers, coaches, you the Owner) are shown **Given name, then Family name**, as English-language
  football writing does (`Katsuo Ozaka`, not Ozaka Katsuo). The game stores Japanese names the other way round, so
  nothing is lost: the family name is always the last word.
* Names are romanised in plain Hepburn, **without macrons** (`Ono`, `Kyosuke`, `Shinbashi`), long vowels are not marked.
* Real footballers use the usual English spelling of the person (`Zidane`, `Ronaldo`, `Maradona`), names as they were
  known around 1999-2000. Invented foreign players are spelt as they sound.
* **Short forms.** Many name slots hold only 14 characters and the lists show about 12. A name that does not fit is
  shortened in this order: `Given Family`, then `G. Family`, then `Family`. So the same person may appear as
  `Katsuo Ozaka` in one list and `K. Ozaka` in another. A name is never cut in the middle of a word.
* **Honorifics.** Japanese attaches -san, -kun, -sama or -senshu to a name. This patch does not show them: the secretary
  simply says your name, and there is no "Mr." because the game knows neither your gender nor your family name. When the
  Japanese is very polite or very rough, the English keeps the tone in its wording instead.
* Player voices keep their character (a gruff one, a nervous one), without copying Japanese grammar.

## 5. Places and club names

### 5.1 Prefectures, cities, counties, towns and villages

Japanese place names carry an ending that tells you the kind of place. The patch drops the ones that are obvious and keeps
the ones that are needed to tell places apart:

| Kind | Japanese ending | In English | Example |
|---|---|---|---|
| Prefecture | ken / fu / to / do | name only | Aomori, Tokyo, Kyoto, Hokkaido |
| City | shi | name only | Sapporo, Yokohama |
| Tokyo ward | ku | name only | Shinjuku |
| District (county) | gun | name + `-gun` | Akan-gun, Oshima-gun |
| Town | cho (machi) | name + `-cho` | Oshima-cho |
| Village | mura | name + `-mura` | Toshima-mura |

* **-gun, -cho and -mura are kept** because a district, a town and a city can share one name (Oshima-gun, Oshima-cho;
  Shimizu city is `Shimizu`, Shimizu town is `Shimizu-cho`). The ending goes on the less common place. A gun is a rural
  district made of several towns and villages; it is not a place you can visit in itself.
* The list is the **pre-merger map of about 1999**, which is the map the game was made with. Many towns and villages
  listed no longer exist under that name.
* Regions: Tohoku, Kanto, Chubu, Tokai, Kansai (not "Kinki"), Shikoku, Kyushu, Okinawa. Old provinces are romanised
  (Mutsu, Hitachi). Foreign places use their English names (North Korea, Hong Kong).

### 5.2 How your club's name is built

A new club's name is made from **your hometown plus a word** from a list of 55 short words (Mythos, Tempest, Palentia,
Topolino and so on), either `Town Word` or `Word Town`. They are club-style tags, like the second half of real clubs'
names. Each word is spelt exactly as the club logo shows it (`Blues`, `Ape`, `Vullcan`, `Estella`); the logo is shown next to the text.
In the default build a few long words are shortened to fit their slot (`Avalanc`, `Panther`); a build with the refit option prints them in full.
The refit option moves a string only when it is plain text and room is left for it (4-byte aligned): where an overlay has no room, or the string is the start of a data table, the short in-place form stays (foreign player names, some cities and nations); the club words always print in full.

The name box holds **13 characters at most**. So the game builds the name like this:

1. In a composed name the town ending is dropped and the **short form** of the town is used (`Aogashima`, not
   Aogashima-mura).
2. If `town + space + word` is 13 characters or fewer, it is used as it is.
3. If it is longer, **the town is cut first** and the cut is marked with a full stop. The word is never cut. The town keeps
   at least 4 characters.

Examples: `Akabira` + `Tempest` becomes `Akab. Tempest`; `Tsurugashima` + `Palentia` becomes `Tsu. Palentia`;
`Kagoshima` + `Mythos` becomes `Kagos. Mythos`; with the word first it is `Mythos Kagos.`.

About half of all possible town and word pairs need a cut (the longer the word, the more often), but you only ever
choose from a handful of candidates. Real J.League clubs keep their normal English names (`Kashima Antlers`,
`F. Marinos`); where a field is too short the city is dropped, never the club name (`Reysol`).

## 6. Ranks, counters, positions and other Japanese terms

These are kept in a Japanese form on purpose.

| Term | What it means |
|---|---|
| **kyu** and **dan** | The Japanese ranking of Go and martial arts, borrowed by the game for the strength of clubs in challenge mode. `10-kyu` is the beginner's rank; the number counts **down** towards `1-kyu`, then the dan ranks start (`1-dan`, ..., `9-dan`) and count **up**. A higher rank means stronger opponents: "the higher the rank, the stronger the clubs you face." You start at 10-kyu. |
| **oku**, **man** | Money units, section 3. |
| **-gun / -cho / -mura** | District, town and village endings, section 5. |
| **Ginga** | A feint from the Brazilian martial art capoeira; the game's own help page explains it. |
| **Owner** | You. The game calls the player the club's owner; staff report to you. |
| **Manager** and **Coach** | Two different jobs. The Manager (kantoku) runs the team on match day; Coaches (koochi) train the players. |
| **Secretary** | Your assistant, who reports and asks you things. |
| **Wk** | Week, in tight columns and calendars. |

Other conventions:

* **Counters.** Japanese counts people, years, companies and so on with different counter words. The English uses plain
  numbers or short words: `3` or `3 players`, `1 yr`, `10 sponsors`.
* **Positions** are `GK`, `DF`, `MF`, `FW` (Goalkeeper, Defender, Midfielder, Forward); also `AM` (attacking midfielder),
  `DM` (defensive midfielder), `FB` (full-back), `CB` (centre-back), `WB` (wing-back). The Japanese "volante"
  (boranchi, from the Portuguese) is **Holding Midfielder**.
* **Formations** are written with hyphens, `3-5-2`, `4-4-2`. The game's own word for them is "formation", never "system".
* **Skills and tactics** use English football words: Through Ball, Cross (the Japanese "centring"), Overlap, Zonal Marking,
  Offside Trap, Counter-Attack.
* **Competitions**: J.League with its full stop, J1 / J2, the Emperor's Cup, the J.League Cup (the sponsor's name is not used),
  World Cup, Olympics, Asian Cup.
* Dates and amounts use English punctuation and a comma as thousands separator; "football", "match" and "pitch" are used
  instead of "soccer", "game" and "field", except in the title of the game.
* **Numbers in the Japanese-style units** (people in 10,000s, `10k`) are explained in section 3.

## 7. The name-entry screen

When you create your club and your Owner you type names on a picker screen with several **tabs** for the different
scripts: kanji, hiragana, katakana, alphanumerics, symbols, then a confirm button.

* **The picker grids are Japanese by design.** The grids of kana and letters are rigid data tables in the game: each cell
  is two bytes wide, and translating them to ordinary letters broke the cursor, so they are left as the game made them.
* **To type an English name use the alphanumeric tab** (the fourth of the five tabs, "eisuuji" in Japanese, "ABC/123" if it
  has been repainted). It opens on the **half-width** letters: the game's ordinary narrow Latin letters, the same as the rest
  of the English text (digits, A-L, M-X, Y-Z and a-l on the first page, m-z on the second). The same letters in the game's
  **full-width** (wide) form come after them. The original Japanese disc shows the wide letters first; the patch puts the
  narrow ones first because they take one byte each (the owner name takes 13 of them) and show like normal English. If you
  prefer the original order, build the patch with `--name-entry-order original`.
* The tab names and the confirm button are pictures; some of them may still be Japanese in your build. Which tab is which
  does not change with the patch.
* Names are cut for display: the lists show about 12 characters of a person's name.

## 8. Known rough spots and limits

The English had to fit the game's own space, and a few things could not be fully solved:

* **Abbreviations are forced by slot size.** Many labels and table cells have room for 8 to 16 characters, so you will see
  `Att.`, `Wk`, `Comm:` and shortened names. The aim was a consistent short form (the same Japanese gets the
  same English everywhere), but a few are terse.
* **Variable-width letters.** The patched game draws the English letters at their natural width, so narrow letters are not
  spaced out like wide ones. A few centred or right-aligned spots, which the game positions by counting characters, may be
  slightly off.
* **Money in debug lists** (`%3d %-13s Y%d %d yr`: HELP, TITLE, LOCAL, SCDRF, SPF_READ) is still a plain `Y` figure; the
  lists are not part of normal play as far as we know. Wide amounts (`13 oku 1500 man`, 15 characters) can be wider than the
  Japanese column on a few tables; the patch then uses the short form `13 oku 1500m`.
* **Pictures not repainted.** 637 pictures with Japanese text were repainted, but not every one. Some captions, headings
  or tab labels may still be in Japanese; the repaint was done with tools, not by hand, so a few have rougher edges
  than the original (for example one ball icon and the small "Sponsorship" line).
* **Cut club names.** Because of the 13-character limit (section 5.2) many composed club names have an abbreviated
  town (for example `Kit. Topolino`). Every town form the cut works on is one plain word, so a cut never ends on a stray
  full stop or hyphen; checked on all 68,640 town and word pairs.
* **Name collisions.** Several places and people share a name once romanised; the endings `-gun`, `-cho` and `-mura` tell
  places apart, but two people with the same romanised name may look identical.
* **Texture marks** in the emulator: section 2.6.
* **Tested only in Flycast** (this is a beta, 0.1.0-beta.1), never on a real Dreamcast. Some of the code the patch adds could not be proven beyond the
  emulator.
* No game rule or data is changed, but this is a large hack; keep your original disc and your own saves safe.

The open issues of this beta are listed in `CHANGELOG.md` (section "Known issues" of 0.1.0-beta.1) and in `README.md`.

If you find a screen with Japanese left, text that runs out of its box, or a wrong word, note the screen and what you did to
reach it; that is the most useful report.

### 8.1 Judgement calls

These are decisions the translators made where the Japanese does not map one to one.  They can be changed (each is a table entry, a build flag or one repainted picture) and a few are open questions.

* **Round and match day: `Rd` or `MD`.**  The post-match tables abbreviate a round as `Rd` (`GF This Rd`, `(Rd 12 End)`); the in-match fixture tag uses `MD` for the match-day counter because the game's own text writes `MD %d` for a league match day.
  Cup rounds read `Round` (`5 Round`), `Final`, `Semi-final`.  Where there is room the full word `Matchday` is used in text.  Open: whether the plates should use one abbreviation everywhere.
* **`Mid Defence`.**  The tactics label for midfield defence is `Mid Defence` on the narrow plates and `Midfield Defence` in the text (the plate has about 100 px).
* **Result words of the post-match / season tables:** `Champions`, `First Advance` (first time into the later rounds), `Advanced`, `Leaders`, `First Title`, and `Last Match` in the manager's record.  They are short labels for narrow plates, not game terms.
* **Ordinals.**  The rank number in the match has one suffix cell (the Japanese rank counter), so every rank reads `th`: `1th`, `2th`, `3th`, then `4th` and up are correct.  Fixing it needs a different texture layout (a code change), so it is left.
* **Title screen.**  The franchise name stays romanised: the four red tiles read `SA KA / TSU KU`, the banner `TOKU DAI GOU` ("toku dai gou", a pun on a "special extra-large issue"; no game text spells it), the wordmark `SakaTsuku`;
  the tagline is translated, `J.LEAGUE` is the licence mark and is not touched.  The three face tiles read `DAI`, `TOKU`, `GOU` to match.
* **Credits.**  The 15 role titles are translated and the 41 staff names are romanised in Given Family order (`docs/credits-names.tsv` lists kanji, reading, member file and how sure the reading is).  Most readings are the common ones;
  where the game's own file name or a public credits database (Sega Retro, MobyGames) gave the reading it is `high`.  **Not yet confirmed** (the given name has several readings): `Hiroyasu Lee` (a Korean family name with a Japanese reading of the given name) and `Kansuke Saito`; `Sunao Murayama`, `Kenji Takano` and `Atsutoshi Takahashi` were confirmed through Sega Retro.
  `Takahashi` / `Saito` / `Ohashi` follow the common romanisation without macrons or `h`.
* **Name tags** show the family name, up to seven letters, because the game's code takes one word of the name and the English order is Given Family.
* **Compact money** where a slot is tight: `13 oku 1500m` (the `man` shrinks to `m`), `32 oku 5000m` on the TV card, and glued forms `13oku 1500man` in the 12 and 20 byte formats of the annual report.

## 9. Build options (only if you build the patch from source)

Players can ignore this. The release is built with `tools/build_patch.py` and `tools/release.py` (see `docs/RELEASING.md`
and `docs/pipeline.md` in the source tree). The standard build is
`--repack on --share dup --append-safe --proportional-font on --refit on --align-fix on --open-font on --small-prop on --strict` (the fixes `--tag-fix`, `--scout-fix`, `--crowd-fix`, `--options-fix`, `--lin-center`, `--cell-prop`, `--clip-lead-space` and `--bcast-speed 1.9` are on by default). The flags used for your download are recorded in
`MANIFEST.json`. Optional flags:

| Flag | Default | What it does |
|---|---|---|
| `--money-style jp\|western` | `jp` | `jp` prints oku / man (`13 oku 1500 man`). `western` is the old decimal style (`Y1.315bn`) and is not the shipped style. |
| `--refit on\|off` | `on` | Applies the name "refit" overlays (`translation/refit/`): fuller forms in place of slot-forced abbreviations (club words of nine or more letters print in full). Turns `--hw-relocate on` on as well. `off` gives the slot-cut forms. |
| `--align-fix on\|off` | `on` | With `--proportional-font on`: the shirt-number column and the right edge of the player-card panel follow the pixel widths of the proportional font. |
| `--tag-fix on\|off` | `on` | The small name tags of the practice and event screens show the family name (up to 7 letters) instead of the first four letters of the given name. |
| `--prop-scale on\|off` | `off` | With `--proportional-font on`: windows with a letter spacing other than 24 scale the width table instead of halving it. |
| `--hw-relocate on\|off\|force` | `off` | Lets half-width text strings (club-name words, nations, leagues, name parts) that do not fit their slot move into spare room in the same file (4-byte aligned). Strings that are the start of a data table never move. |
| `--club-guard on\|off` | `on` | The bounded club-name builder of section 5.2 (13 characters). `off` restores the original unbounded join. |
| `--club-dot on\|off` | `on` | `off` leaves the cut town without its closing full stop. |

## 10. Credits and licence

* **Translation, reverse engineering, tooling and graphics:** the SakaTsuku2-EN project, copyright (C) 2026 Nexxus Drako
  Multimedia.
* **Thanks:** Nexxus Drako, and the **Community Discord** (https://discord.gg/7DNrGye9TZ).
* The built-in VCDIFF (xdelta3) decoder in `apply_patch.py` is adapted from the author's LMAST-Reverse project; xdelta3 is used
  to cross-check every patch. The patched game was run in the Flycast emulator.
* **Licence of the tools:** the patch tooling (`apply_patch.py`, `verify_dist.py`, the build scripts) is free software under
  the **GNU General Public License, version 3 or (at your option) any later version (GPL-3.0-or-later)**. The full text is in
  `LICENSE` and `LICENSES/GPL-3.0-or-later.txt`.
* **Licence of the translation:** the translated text, the repainted pictures and the documents of this project (this guide,
  `README.md`, `CHANGELOG.md`) are licensed under **Creative Commons Attribution-ShareAlike 4.0 International (CC-BY-SA-4.0)**;
  the full text is in `LICENSES/CC-BY-SA-4.0.txt`. In plain words: you may share and adapt them if you credit the project
  ("SakaTsuku2-EN project, Nexxus Drako Multimedia, CC BY-SA 4.0"), say what you changed and release your version under the same licence.
  The repainted pictures are new artwork painted over the game's own pictures: the licence covers only that new contribution,
  never the art underneath.
* **This download contains no original Sega pixels.** It consists of `.xdelta` delta files that only describe the differences between
  the original disc and the English one, plus the programs and documents listed in `SHA256SUMS`. A patch is useless without
  your own copy of the original disc, and applying it happens on your computer, to your dump. The game, its Japanese text,
  art, music and code belong to their rights holders and are **not licensed by this project**; this project claims nothing
  over them. The translated text and repainted pictures exist in this download only inside the deltas.
* Football clubs and competitions are named as in 1999-2000; they belong to their owners.

## 11. FAQ

**Why does it say `13 oku 1500 man` and not `1.3 billion yen`?**
Because the game is Japanese and counts that way. It is a small habit to learn: 1 man is 10,000 yen, 1 oku is 10,000 man.
Section 3 has a table.

**Why does `-gun` appear in some lists but not in club names?**
A list has room, and the ending tells you what kind of place it is. A club name has only 13 characters, so the ending is
dropped and the short form of the town is used.

**Why are the picker grids in Japanese?**
They are fixed tables inside the game that were not safe to change. Use the alphanumeric tab to type English letters
(section 7).

**Why do I see faint marks around the letters?**
Emulator texture filtering; set Flycast to nearest-neighbour (section 2.6).

**Does it work on a real Dreamcast, or from a burned disc?**
Untested: Flycast is the only emulator this patch has been tested in.

**The patcher says my dump does not match.**
Compare the hashes of tracks 3 and 5 with section 2.3. Differences in the audio track or the pregaps alone are harmless.
A different size or hash in track 3 or 5 means a different dump; see `README.md`, section 5.

**Are my VMU saves safe?**
This patch does not change the save format on purpose, but it has not been tested against every save. Keep a copy of
your Japanese saves.

**A name is cut or an item looks wrong. Is that a bug?**
It may be a space limit (section 8) or a real mistake. Reports are welcome.

**Which version is this?**
See `VERSION` in this download, and `CHANGELOG.md` (also in this download) for what each version adds. Honorifics and Japanese
name order are planned as options for the next version (0.2.0); this version always shows people Given name first, without honorifics.
