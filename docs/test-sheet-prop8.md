# Test sheet: prop8 hang test

Disc: `build/trial/prop8/prop8.gdi` (standard flags, junk-record fix). Date: ____________  Tester: ____________

Launch (only when you say yes; window goes to DISPLAY3, no scripted input):

```
powershell -File tools/emu/launch.ps1 -Disc "build\trial\prop8\prop8.gdi"
```

Result codes: **OK** / **clip** (cut at box edge) / **over** (runs outside box or over art) / **wrong** (Japanese, garbage, wrong number/unit) / **hang** (note the frame and the last button). Ticks around text are Flycast filtering, ignore them.

## A. The hang (do this first)

| # | Step | Good looks like | Result | Notes |
|---|---|---|---|---|
| A1 | Title screen, New Game | boots to name entry | | |
| A2 | Name Entry | tabs read `ABC/123`, `Symbols`, `Confirm`, not cut | | |
| A3 | Hometown: pick Aogashima (or any) | header `.. Oku .... Man`; panel in English; message `you will need 1 Oku 8500 Man.` | | |
| A4 | Draft / first Event: right info panel | `Wants 2 yrs`, `Age`, `4-4-2`, `Centre Push`, salary fully visible | | |
| A5 | **Second Event screen** (1 Yr 1 Mo Wk1st) | message appears and the scout choice can be selected | | |

If A5 hangs: write the last button pressed and what was on screen: ______________________________

Then boot, in this order, and repeat A1 to A5 (stop at the first one that gets past A5):

| Disc | What is off | Past A5? |
|---|---|---|
| bis_e | money, club guard, textures | |
| bis_d | proportional font | |
| bis_a | jp money | |
| bis_b | club guard | |
| bis_c | textures | |

## B. Known open items (just confirm what you see)

| # | Screen | Question | Answer |
|---|---|---|---|
| B1 | Message `1 Oku 8500 Man` | Does the `O` still look like a zero? (lower-case `oku` is the planned fix) | |
| B2 | Draft panel, above `4-4-2` | Is there still a black rectangle? What label should be there? | |
| B3 | Match screen | `HOME` / `AWAY` still the old Japanese label? | |
| B4 | Match commentary box | English lines? Any Japanese left (expected about 30%)? | |
| B5 | Attract demo (idle on title) | English subtitles? | |

## C. Other things worth a look if you get that far

| # | Screen | Good looks like | Result | Notes |
|---|---|---|---|---|
| C1 | Created club name | at most 13 chars, e.g. `Tsu. Palentia`; owner name next to it not corrupted | | |
| C2 | Hometown popup previews | match the final club names | | |
| C3 | TV station card | `32 Oku 5000 Man`, not touching the right edge | | |
| C4 | Facility cost dialogs | three rows, amount visible | | |
| C5 | Save, then load slot | club name complete | | |

Send back: this sheet (photo or text), plus a window screenshot of any row not OK. A RAM dump at a hang (`tools/emu/dump_ram.lua`) is optional but settles the cause in one boot.
