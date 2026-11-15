# Money and number formats: what the engine prints, why English showed `130015000,00`, and the fix (oku / man style)

Author: agent `money` (task B of the playtest round, restyled in stage 2 after the user decision below).  Everything below was
obtained by static reverse engineering of `1ST_READ.BIN` and the overlays plus **execution of the original and the patched code in
`tools/sh4sim.py`** (`tools/moneycheck.py`).  Nothing was run in an emulator or on hardware.  Status words: **PROVEN** = reproduced
in the interpreter on the real bytes, **INFERRED** = follows from code but not executed, **UNKNOWN** = not determined.

**USER DECISION (binding, stage 2): the game stays appropriately Japanese.  Second playtest (mn6): the words are LOWER CASE, `oku` and `man` (a capital `O` reads as a zero in the half-width
font: `1 Oku` looked like `1 0ku`); `Yen` keeps its capital.  Sections 4.1 - 4.8 were written with capitals and were converted mechanically; section 11 is the new work.**  Money keeps the Japanese oku / man structure,
translated into English words: `13 oku 1500 man`, `6000 man`, `1 oku`, `0 Yen`.  *oku* = 100 million yen, *man* = 10 thousand yen.
It is NOT converted to decimal western style (`Y1.315bn`).  Nothing is explained in game; the translator's notes / guide (written
later) explains oku and man.  The old decimal output stays available as `--money-style western` (section 4.2).

Files: `tools/moneypatch.py` (the patch, a pure bytes-in / bytes-out module like `fontpatch.py`), `tools/moneycheck.py` (static
self-check + interpreter run, both styles), `tools/test_moneypatch_tv.py` (unit checks), `tools/re/money_audit.py` (writes
`build/trans/money_records.tsv`), `tools/re/mny_*.py` (stage 2 helpers, section 8), build flags `tools/build_patch.py
--money-format on|money-only|off` (default **on**) and `--money-style jp|western` (default **jp**; `build_patches(money_fmt=False)`
stays off so the no-op tests keep their meaning).

## 1. Summary

* `%m` (and every `%s` the game fills with a money text) is printed by one **money function** that every overlay carries a
  copy of (102 live copies + 6 dead ones).  It takes an amount in **units of 10,000 yen** (man, 万円) and glues together
  `[hi][億][lo][万円]` from the Japanese number text plus **four unit strings that are copied with `strncpy` at fixed lengths
  of 2, 4, 2 and 3 bytes**.  A hi part below 10 is written in **full-width digits**.
* The first English translation replaced those four unit strings by `00M`, `0,000 Y`, `Y`, `Y0`.  They are not strings that get
  printed: they are byte pieces of fixed length, so `13億1500万円` became `13` + `00` + `1500` + `0,00` = **`130015000,00`**
  (the `M` and the rest of `0,000 Y` are cut off), `6000万円` became **`60000,00`**, `81億5000万円` became **`810050000,00`**, and
  `１億300万円` became **`１003000,00`** (the first `１` is a full-width digit: the odd glyph).  The pieces `Y` / `Y0` are shorter
  than their copy length, so `strncpy` NUL-pads them and the **text is cut off after the amount** (`１億円` -> `１00Y`, then end of
  string).
* No English string can fix this (the number and the unit pieces cannot be reordered, `lo` is not zero padded, a unit piece cannot
  carry a space or a variable length).  The fix is **code**: the first 12 bytes of every money function jump to a routine in the
  `1ST_READ.BIN` tail (`0x8c299a00`) that writes ASCII money text.  **jp style (default, 388 bytes since the compact form of 4.7.2): `0 Yen`, `15 man`, `6000 man`,
  `1 oku`, `1 oku 300 man`, `13 oku 1500 man`.**  western style (428 bytes): `Y0`, `Y150k`, `Y60M`, `Y103M`, `Y1.315bn`.  The expander's
  `%D` branch is pointed at a second routine in the same cave that prints ASCII digits instead of full-width ones.
* The four Japanese unit strings are dead data with the patch.  Their 405 translation records were cleared (`en = ""`,
  `skip`), so a build **without** the patch shows correct Japanese amounts instead of garbage.
* The TV station card prints its capital through a private function, not `%m`; it is replaced by a 64 byte routine that calls the
  same money function (section 4.4): `32 oku 5000 man`.
* A few **sprintf format tables** (`INVEST`, the shared 億/万 number library of 9 overlays) were re-translated in the first round
  so that the digits they print are exact (section 5); they still use the old western pieces (`Y%s%s0000`), see section 5 for what
  is converted and what is left open.

## 2. What each token prints (PROVEN: the real expander of MEETING executed, `moneycheck.py`)

The text of a tsString window goes through the **expander** (`FUN_8c2df128` in MEETING, a copy in every overlay;
docs/text-engine.md s4.2).  It knows exactly four conversions; arguments are consecutive 4-byte words (SH-4 va_list rule).

| token | prints | examples (original bytes) |
|---|---|---|
| `%s` | the string at the pointer, verbatim (`strlen` + `strncpy`) | `[%s]` with "STR" -> `[STR]` |
| `%d` | signed decimal, ASCII, no padding (`FUN_8c2dd844(dst, V, 0, ' ')`) | 7 -> `7`, -7 -> `-7`, 123456 -> `123456` |
| `%D` | signed decimal in **full-width** digits, 2 bytes per digit (`FUN_8c2dd964`, digit strings in a table of the overlay) | 7 -> `７`, -12 -> `－１２` |
| `%m` | the money function (below) | 0 -> `0円`, 1 -> `1万円`, 10000 -> `１億円`, 131500 -> `13億1500万円`, -50 -> `-50万円` |
| `%%` | `%` | |
| `%` + any other character | **that character** (the `%` is dropped, no argument is consumed) | `%2d` -> `2d`, `%04d` -> `04d`, `%-13s` -> `-13s`, `%f` -> `f`, `%x` -> `x` |
| `#sname#` `#YOU#` `#tkNN#` | name substitution (docs/text-engine.md) | |

So **width formats (`%2d`, `%04d`, `%-13s`, `%f`) do not work in a tsString window**: they print their letters and the following
tokens read the wrong arguments.  They only occur in strings that the game gives to the libc `sprintf` first (the result then
goes into a window as `%s`); the JA records that contain them are all of that kind (families SPRINTF_* / NUM in the audit).
With `--money-format on`, `%D` prints the same as `%d` (7 -> `7`).  The libc side (`sprintf` in `1ST_READ.BIN`) is a normal printf.

**Budget of a money text in a window** (`tools/transcheck.py` / `translib._fmt_cells` still charge `%m` as 8 cells, a number made for the
western style): jp style needs **15 cells for the usual amounts ("13 oku 1500 man"), 16 below 1000 oku, 17 at the cap** (section 4.6).

## 3. The money function (PROVEN)

`FUN_xxxx(char *dst, int V, int flag) -> int length` (MEETING: `0x8c2dda68`, 206 bytes; file offset = address - base).
Callers: the `%m` branch of the expander (`flag = 0`) and game code that builds `%s` strings (`flag = 0`; seven direct call sites
pass `flag = 1` (DRSLIST `0x446e`, G_INCOME `0x202 / 0x254 / 0x466 / 0x4b0`, NEWCON `0xa990 / 0xa9aa`: `mov #1,r6` right before the `jsr`; found by `build/mn5/callers.txt` + the skeptic scan `tools/re/skm_flags.py`;
the earlier "false positive" remark was wrong).  The original prints `lo` zero padded (`%04d`) for them; the jp cave ignores the flag (`1 oku 300 man`), the western cave prints exact yen.  It does **not** write a NUL.

```
hi = V / 10000   (1ST_READ div helper 0x8c012bf8: r0 = r1 / r0)       lo = V % 10000   (0x8c013460)
hi > 0:   hi < 10 ? full-width digits : "%d" ;   strncpy(dst, [億], 2)
lo == 0 and flag == 0:   hi > 0 ? strncpy([円], 2) : strncpy([0円], 3)
otherwise:   lo printed "%d" (flag != 0 and hi > 0: "%04d")  ;  strncpy([万円], 4)
```
So **V is in units of 10,000 yen (man)**, `hi` is the oku count (V / 10^4 = yen / 10^8) and `lo` the man remainder.  A value below 10,000 yen
cannot be passed (V = 0 is the only amount below one man); the plain-yen form exists only as `0 Yen` and as the `%d円` sprintf strings of
section 5.  [億] [万円] [円] [0円] are four strings in the overlay's data pool, loaded by `mov.l @(d,pc),r5` (MEETING: `0x8c374948`,
`0x8c37494c`, `0x8c374954`, `0x8c374958`, i.e. translation records `FLOW_PRG/MEETING.BIN#a4948 / a494c / a4954 / a4958`).
`strncpy` is `0x8c013294` (copies up to n bytes, stops at the NUL and **pads with NULs up to n**).

Interpreter results for the original bytes (`moneycheck.py --before`):

| V | amount | Japanese (original pieces) | first English pieces `00M` `0,000 Y` `Y` `Y0` | jp patch | western patch |
|---|---|---|---|---|---|
| 0 | 0 | `0円` | `Y0` + NUL (text ends here) | `0 Yen` | `Y0` |
| 1 | 10,000 | `1万円` | `10,00` | `1 man` | `Y10k` |
| 150 | 1,500,000 | `150万円` | `1500,00` | `150 man` | `Y1.5M` |
| 6000 | 60,000,000 | `6000万円` | **`60000,00`** | `6000 man` | `Y60M` |
| 10000 | 100,000,000 | `１億円` | `１00Y` + NUL | `1 oku` | `Y100M` |
| 10300 | 103,000,000 | `１億300万円` | **`１003000,00`** | `1 oku 300 man` | `Y103M` |
| 131500 | 1,315,000,000 | `13億1500万円` | **`130015000,00`** | `13 oku 1500 man` | `Y1.315bn` |
| 815000 | 8,150,000,000 | `81億5000万円` | **`810050000,00`** | `81 oku 5000 man` | `Y8.15bn` |

(bold = the playtest reports).  The B variant (6 overlays COMM, CON_REP, NF_CON, PASS_PL, J1_REP, PL_CON linked against another
`1ST_READ.BIN` build, INFERRED dead: docs/font-hook-notes.md) calls helper addresses that do not exist in this `1ST_READ.BIN`;
they are found and counted but not patched (`variants='AB'` would hook them too).

## 4. The patch (`tools/moneypatch.py`)

### 4.1 jp style (default): the oku / man text (PROVEN against a Python reference, 100,332 calls per style)

`V` = signed 32-bit amount in units of 10,000 yen; `|V|` is printed, a negative `V` gets a leading `-`.  Let `L` be the number of
decimal digits of `|V|`: **oku = the digits above the last four, man = the last four digits without leading zeros** (so `oku = |V| / 10^4`,
`man = |V| % 10^4`; no division is executed, the digits come from the power table).

| `|V|` | text | note |
|---|---|---|
| 0 | `0 Yen` | the only amount without oku or man part |
| `man` only (`|V|` < 10,000) | `[man] man` | `15 man`, `6000 man`, `9999 man` |
| `oku` only (`man` = 0) | `[oku] oku` | `1 oku`, `13 oku`, `99 oku` |
| both | `[oku] oku [man] man` | one space between; the man part has NO zero padding: `1 oku 1 man`, `13 oku 1500 man` |

The `flag` argument is ignored (the game never passes one).  The text denotes **exactly** `V * 10,000` yen (checked by parsing it back
for every sample).  Longest texts: `15` glyphs for `13 oku 1500 man` (every 2-digit oku with a 4-digit man), `16` for `999 oku 9999 man`,
`17` for `9999 oku 9999 man` (V = 99,999,999 = 10^8 - 1, the cap literal found next to the money code of several overlays), `20` for any int32
(`-214748 oku 3648 man`, V = INT_MIN).  Code: 168 instruction words, **388 bytes including `m_dec` and the power table** (368 before the compact form of 4.7.2), fits the 0x200 reserve
(124 bytes to spare), no new cave needed.  Worst case 661 executed instructions (V = 2^31 - 1).

### 4.2 western style (`--money-style western`, kept byte-compatible)

The old decimal output, byte for byte identical to the first round (PROVEN: `tools/re/mny_baseline_cmp.py` re-runs the 49 sha256 entries of
`tools/re/pe_baseline.py` recorded before the jp style existed, with the style forced to western: identical).  428 bytes.

| `|V|` | rule | examples |
|---|---|---|
| 0 | `Y0` | |
| 1..99 (< 1M yen) | digits + `0k` | 15 -> `Y150k`, 99 -> `Y990k` |
| 100..99999 (1M .. < 1bn) | millions, up to 2 decimals, trailing zeros dropped | 100 -> `Y1M`, 150 -> `Y1.5M`, 1234 -> `Y12.34M`, 6000 -> `Y60M`, 99999 -> `Y999.99M` |
| >= 100000 and a multiple of 100 (>= 1bn, whole millions) | billions, up to 3 decimals, trailing zeros dropped | 100000 -> `Y1bn`, 131500 -> `Y1.315bn`, 1315000 -> `Y13.15bn` |
| >= 100000, not a multiple of 100 | millions with 2 decimals (no precision lost) | 100050 -> `Y1000.5M` |
| `flag != 0` | exact yen, no separators | `Y1315000000` |

### 4.3 Hook and cave (the design follows `fontpatch.py`)

* `1ST_READ.BIN` tail, file offset `address - 0x8c010000`: **`0x8c299a00 ..`** (jp 388 bytes to `0x8c299b83`, western 428 bytes; 512 reserved:
  `0x8c299a00..0x8c299bff` must be zero, otherwise the build refuses; the cave registry claim `money.cave` is unchanged).  The font patch owns
  `0x8c299800..0x8c2999ff` (untouched).  Entries (jp): `money` `0x8c299a00`, `m_dec` `0x8c299af8` (the `%D` routine), power table `0x8c299b48`;
  (western: `m_dec` `0x8c299b36`, table `0x8c299b84`).  Both styles share the `m_dec` + power table tail (`_TAIL_SRC`).  Calling convention as the
  original (r4 dst, r5 V, r6 flag, r0 = length, r8-r15 and PR preserved, 16 byte digit buffer on the stack, r0-r3 / r7 scratch).
* jp algorithm: sign; ten decimal digits by repeated subtraction of powers of ten into a stack buffer (no leading zeros); `0 Yen` for none;
  if `L > 4` copy digits `[0, L-4)` and the four bytes ` oku`; skip leading zeros of digits `[max(0, L-4), L)`; if any is left,
  a space (only when an oku part was written), the digits and ` man`.  The unit words are three 4-byte constants (` oku`, ` man`, ` Yen`), copied by one helper.
* Every money function copy: its first 12 bytes become `mov.l @(1,pc),r0 / jmp @r0 / nop / nop / .long 0x8c299a00` (the function
  is 4-aligned in all 108 copies).  The rest of the old body is dead code.  Sites are found by an exact masked byte signature
  (2 known variants); a look-alike with another signature raises instead of being patched.
* `%D`: the literal-pool word of the expander that holds the address of the full-width digit function is replaced by `m_dec` (the m_dec of the
  chosen style).  It is located through the pool (`strlen`, `strncpy` literals) and cross-checked against the `bsr` of the money function (`hi < 10`
  uses the same function): 98 overlays; LOGO, OFFICE, TITLE and ATFIRST/TITLE have the money function but no expander.
* No file grows, no `_end` change, nothing else is touched.  Composes with the text stages (signature scan on the current bytes) and
  with the proportional font (other cave, other function).
* API (the contract of the build owner): `moneypatch.make_patches(read, current=None, addr=CAVE_ADDR, paths=None, expect=None, variants='A',
  decimal_d=True, tv_card=True, style='jp', compact_token=False, panel_compact=True)` (4.7), module constants `STYLES = ('jp', 'western')`, `DEFAULT_STYLE = 'jp'`; the same `style` keyword on
  `cave_bytes`, `cave_assembly`, `cave_symbols`, `patch_overlay`, `overlay_edits`, `patch_1st_read`, `tv_card_bytes`, `patch_tv_card`, `reference(v, flag, style)`.
  The report dict carries `style`.  An unknown style raises `MoneyPatchError`.
* Build: `python -I -X utf8 tools/build_patch.py --money-format on|money-only|off [--money-style jp|western]` (default on, jp); report line per file
  `money ... hooked`.  `money-only` leaves `%D` full-width (the original).

### 4.4 The TV station card capital (`FLOW_PRG/TV_EVENT.BIN`, PROVEN by execution)

The "capital" line of the TV station card is NOT drawn through `%m` but by a private function `draw_money(V, x, y)` at `0x8c2d0ed0` (single caller `0x8c2d109a`; V = table
`0x8c2d9a54[level]` in 10,000-yen units: 325000 650000 2270000 4410000 8340000 9450000).  The original splits V and draws two text objects, `%s億` at `x-72` and `%s万円` (4 zero padded
digits) at `x` (x = 512), i.e. the Japanese capital occupies x = 440..608 of 640.  The first English pieces printed `3200M50000000`.  The function is replaced (by signature, same size, the literal
pool is not touched) by a 64 byte routine that formats V with the (hooked) money function of the same overlay into a stack buffer and draws ONE text object (format = the `%s` record) at (x', y):

| | western style | jp style |
|---|---|---|
| x' | x (512) | **456** (mn6; round 1 used x - 72 = 440) |
| flag | 0 | **77 = compact form** (mn6; round 1 used 0) |
| stack buffer | 16 bytes | **32 bytes** (an int32 needs up to 20 + NUL) |
| texts | `Y3.25bn` ... `Y94.5bn` | `32 oku 5000m`, `65 oku`, `227 oku`, `441 oku`, `834 oku`, `945 oku` |

**Second playtest (finding 3b):** the capital started at x = 440, on top of the end of the `Capital` capsule, and `32 oku 5000 man` (183 px, proportional font) ran past the end of the plate
(about x = 616).  The plate window is about x = 448..616 = 168 px.  The full form does not fit (183 px); the compact form `32 oku 5000m` is **147 px** (456 .. 603, 13 px inside the plate end), the
single part capitals are 75..87 px (`pixelwidth.py`).  Left aligned at x = 456 (8 px behind the capsule).  `moneycheck.py` section 7 executes the routine with 19 values for both styles (the text
== `reference(V, 77)` in jp style, one text object, object x/y = (456 or 512, 148), text + NUL inside the buffer, callee-saved registers / sp / PR preserved, no write into the overlay image) and checks
`x + width <= 616` for the six capitals; `test_moneypatch_tv.test_capital_fits_the_plate`.  **UNKNOWN until seen:** the exact plate edges (448 / 616 come from the align owner's measurement of the screenshot).

### 4.5 What was verified, and how (`tools/moneycheck.py`; `--quick` 13 s is part of `test_pipeline.py` section G; full about 10 min with both styles and --e2e)

`moneycheck.py [--quick] [--e2e] [--before] [--style jp|western|both]` runs sections 1, 2, 4-7 for each style (default both):

1. every word of the cave decoded by **capstone** equals the assembler's text; delay slots legal; the power table;
2. the hook of all 102 copies: capstone decodes `mov.l / jmp @r0 / nop / nop`, the literal is the cave address, nothing else in the file
   changed, same size; `1ST_READ.BIN` changed only in the cave which was zero; a second patch is refused;
3. (once) the **original** function executed in `sh4sim` (with the 1ST_READ helpers as Python hooks) on 3 overlays reproduces the Japanese
   text and the playtest bug strings;
4. the cave executed on **100,332 (V, flag) pairs per style**: every V of 0..20000 (all man parts of 0, 1 and 2 oku), the oku grid (k * 10000 and
   its neighbours, k up to 215,000), every digit count, 10^k +- 1, random and INT_MIN, negatives: bytes == Python `reference()`, length in r0,
   r8-r15 and PR preserved, **no write outside dst and the stack below sp**, the text parses back to EXACTLY V * 10,000 yen (jp: canonical form,
   no leading zeros, separator rules, <= 20 bytes); the `%D` routine on the same values == `str(V)`;
5. patched overlay + patched `1ST_READ.BIN` in one memory image, entered at the ORIGINAL function address (all 102);
6. the real **expander** of all 98 overlays with `%s %d %D %m %%` before and after;
7. the TV card routine (section 4.4);
8. the scout info panel field of SCDRF / SEARCH (4 call sites executed on the real bytes, with and without `panel_compact`, section 4.7.1); and in sections 4 / 5 / 6 the compact flag 77 and the `%M` token
   (4.7.2 / 4.7.3); with `--e2e`: `build_patches(money_fmt=True, money_style=...)` with the release flags and the real translations, then every English
   text with `%m` / `%D` (111 texts, 31 overlays) expanded by the real expander of the BUILT overlay == model.

Unit tests without interpreter: `tools/test_moneypatch_tv.py` (12 tests: styles, reference examples, exactness, western unchanged, caves, `make_patches(style=)`, TV routine
differences, TV widths).  UNKNOWN / not done: running it in an emulator (not allowed in this task); instruction-cache coherence of the freshly loaded tail (the same
assumption as the font cave); whether other game code calls the money function with `flag != 0` through a path the scan missed (jp then prints the same as flag 0).

### 4.6 Examples and the width budget of every `%m` text

| V (10k yen) | jp text | yen | glyphs / px | western text |
|---|---|---|---|---|
| 0 | `0 Yen` | 0 | 5 / 61 | `Y0` |
| 1 | `1 man` | 10,000 | 5 / 61 | `Y10k` |
| 15 | `15 man` | 150,000 | 6 / 73 | `Y150k` |
| 150 | `150 man` | 1,500,000 | 7 / 85 | `Y1.5M` |
| 6000 | `6000 man` | 60,000,000 | 8 / 97 | `Y60M` |
| 9999 | `9999 man` | 99,990,000 | 8 / 97 | `Y99.99M` |
| 10000 | `1 oku` | 100,000,000 | 5 / 63 | `Y100M` |
| 10300 | `1 oku 300 man` | 103,000,000 | 13 / 160 | `Y103M` |
| 100050 | `10 oku 50 man` | 1,000,500,000 | 13 / 160 | `Y1000.5M` |
| 131500 | `13 oku 1500 man` | 1,315,000,000 | 15 / 184 | `Y1.315bn` |
| 325000 | `32 oku 5000 man` | 3,250,000,000 | 15 / 184 | `Y3.25bn` |
| 990000 | `99 oku` | 9,900,000,000 | 6 / 75 | `Y9.9bn` |
| 9450000 | `945 oku` | 94,500,000,000 | 7 / 87 | `Y94.5bn` |
| 99999999 | `9999 oku 9999 man` | 999,999,990,000 | 17 / 208 | `Y999999.99M` |
| -131500 | `-13 oku 1500 man` | -1,315,000,000 | 16 / 194 | `-Y1.315bn` |
| 2147483647 | `214748 oku 3647 man` | 21,474,836,470,000 | 19 / 232 | `Y21474836.47M` |

(`tools/re/mny_examples.py` prints this table.)  **Real value ranges** (what the game can pass): the TV capitals are 325,000 .. 9,450,000 (PROVEN, table
in the overlay; 15 glyphs at most).  Every other amount comes from game state: contracts, salaries, transfer fees, facility costs, sponsor fees, funds.  No
table bounds them; several overlays carry the literal 99,999,999 (10^8 - 1, `tools/re/mny_caps.py`) next to the money code, so **17 glyphs
(`9999 oku 9999 man`) is the design maximum, 20 the arithmetic maximum of an int32**.  For the budget the validator should charge: **15** (one amount below 100 oku, the
case of every contract / fee / facility text), **16** (below 1000 oku) or 17 for texts that can show club funds.

**Budget check of every `%m` text** (`tools/re/mny_budget.py`, 100 records, window limits from `tools/winwidth.py`, cells and proportional-font pixels):
with the OLD 8 cell budget every record fitted; with 15 glyphs **56 records did not** (lines up to 6 cells too long, three-row windows already
full); with the line breaks fixed (below) **all 100 fit 15 and 16 glyphs; 25 records (the funds warning of 11 DRS* overlays and LOCAL, 4 ESTABLIS, ...) are 1-8 cells over
only for the 17 glyph cap** (`build/mny/budget.tsv`).  The 20 glyph int32 case is not reachable in the game and is not budgeted.

**Edits made (stage 2, translation database, only records whose English contains `%m` or a literal western amount; words are kept, only line breaks change unless
listed):** `tools/re/mny_rewrap.py` re-wrapped 57 records (DRAFT, ESTABLIS, INVEST, MEETING, MON_INST, NEWCON, RECON, SCDRF, SPT_CLUB, GETREP, SPONSOR/2) so that every line fits
its window with `%m` = `999 oku 9999 man`; lines that fit were kept, an overflowing line pushes its last words to the next line.  Seven records had no room (three full rows)
and were shortened: `DRAFT#3db6c` "The deal is" -> "Deal:", `DRAFT#3dbc9` "contract, including the transfer fee, costs" -> "deal with the transfer fee costs",
`DRAFT#3dc7d` rephrased ("From July on, half a year is added. / A %d-year deal with the transfer fee / comes to ... Is that OK?"), `GETREP#2568c` "deducted from your funds" -> "deducted from funds",
`SPONSOR#2c7e1` / `SPONSOR2#2c825` "Let's be careful not to lose any more trust." -> "Let's not lose any more trust.", `SPT_CLUB#bf87` "seems appropriate" -> "is suitable".
`tools/re/mny_literals.py` converted 28 records with a literal western amount: `Y200M` -> `2 oku`, `300 million yen` -> `3 oku`, `Y990M` -> `9 oku 9000 man`, `Y9,999M` -> `99 oku 9900 man`,
`Y100M` -> `1 oku`, `Y10M bonus` -> `1000 man bonus` (13 MEETING copies), and the 7-cell right-aligned columns `Y30K` / `Y50K` / `Y100K` / `Y0` of GETREP and MON_INST -> `  3 man` / `  5 man` / ` 10 man` / `  0 Yen`.
Both scripts are idempotent, check the exact old text before writing and write each `translation/*.jsonl` atomically.

### 4.7 Playtest round 2 (prop7): the info panel, the compact form, the `%M` token, `O` versus `0`, the header sprites  (agent mn5)

Everything here was obtained by static analysis and by executing the real bytes in `tools/sh4sim.py` (`tools/moneycheck.py` sections 4, 5, 6 and 8; `tools/test_moneypatch_tv.py`).  Nothing was run in an emulator.

**4.7.1 The cost line `oku 300 man` with the `1 ` lost (PROVEN by execution; the screen is the scout panel of SCDRF.BIN and SEARCH.BIN).**
The right-hand info panel of the scout draft / search screens ("Wants 2 yrs", "Age", club, formation, tactics, the salary) is NOT a tsString `%m` window.  A function of
each overlay (SCDRF `0x8c2d7598..` and `0x8c2d76d8..`, SEARCH the same code at `0x...88d8` / `0x...8a04`; 2 call sites per overlay, 4 in all) builds the text of the panel
in a buffer `b` (the money row is the window string that starts at `b + 37`, rows separated by `\n`, NUL at `b + 88`) with libc calls:

```
len = money(buf, V, 0)                 ; V = word(player + 16) * 100  (units of 10,000 yen), the salary / asking amount
strncpy(b + 37 + (12 - len), buf, len)  ; right-aligned in a FIXED 12 BYTE FIELD b[37..48]  (b[37..88] was space-filled first)
sprintf-like(b + 50, "%4d/%d yrs" | "Wants %2d yrs", ..); (b + 71, "Age %2d", ..); (b + 76, club / prefecture name)
```

The Japanese text of a salary is at most 12 bytes (`13億1500万円` = 2 + 2 + 4 + 4 = 12), so the field was exactly big enough.  `1 oku 300 man` is 13 bytes: `12 - len = -1`, the
copy starts at `b[36]` and the window string starts at `b[37]`, so the first character (`1`) lands in front of the string and the window shows ` oku 300 man`
(the playtest: `oku 300 man`).  Any longer text eats more characters (`13 oku 1500 man`, 15 bytes, shows `oku 1500 man` and writes its first three bytes into `b[34..36]`, in front of the displayed string).
`moneycheck.py` section 8 executes the 4 call sites on the real bytes, with and without the fix, and reproduces exactly this (field `' oku 300 man'`, byte before the field `'1'`).

Other fixed-width idioms around the money function were looked for in all 38 direct (non-expander) call sites of the 102 copies (`tools/re/mn5_callers.py`, `mn5_padsites.py`): only these 4 write into a
buffer by byte count.  G_INCOME (field 8) and SPONSOR / SPONSOR2 (field 14) compute `(N - len) * 12` as an x offset of a text object: a longer text moves left, nothing is overwritten.  The remaining
callers format into a stack buffer that is then used as a `%s` argument (windows, i.e. tsString lines, section 4.6).

**Fix: the compact form (below), selected at the four sites by the flag the caller passes** (`mov #0,r6` becomes `mov #77,r6`, the same two bytes, found by the 10-instruction tail of the idiom, `moneypatch.panel_sites`,
checked against the money function address).  `13 oku 1500m` = 12 bytes: every salary below 100 oku (the word is multiplied by 100 man, so only multiples of 100 man, `1 oku 300m` ... `99 oku 9900m`) fits;
`make_patches(panel_compact=True)` is the default, jp style only.

**4.7.2 The compact form (flag `COMPACT_FLAG` = 77 = `M`, jp style only).**  Design question: `1O 300M` (the user's idea) versus the longer forms.  Decision after measuring (section 4.7.4: the font draws `O` and `0` almost identically):
only the unit `man` shrinks, to `M`, and only when an oku part is present; `oku` stays.  So

| full | compact | note |
|---|---|---|
| `0 Yen`, `15 man`, `6000 man`, `1 oku`, `99 oku` | identical | one part: unchanged, already short |
| `1 oku 300 man` (13) | `1 oku 300m` (10) | |
| `13 oku 1500 man` (15) | `13 oku 1500m` (12) | still unambiguous: the `M` follows digits that follow `oku` |
| `999 oku 9999 man` (16) | `999 oku 9999m` (13) | |
| `9999 oku 9999 man` (17, the cap) | `9999 oku 9999m` (14) | |

`1O 300M` was rejected: with these glyphs `1O` reads as `10` (the amount is then off by a factor of ten).  `1 O 300 M` (9) has the same problem.  Pixel widths (proportional font on):
`1 oku 300 man` 160 px, `1 oku 300m` 124 px, `13 oku 1500 man` 184 px, `13 oku 1500m` 148 px.  Implementation: `flag == 77` in r6 of the cave (`_JP_SRC`, +20 bytes: the cave is now **388 bytes**, reserve 512, nothing else moved); `reference(v, 77)` is the model;
the old flags 0 and 1 still print the full form.  Western style does not know the flag (any non-zero flag there means "exact yen").

**4.7.3 The per format string selector `%M` (tsString expander, jp style, `make_patches(compact_token=True)`, default OFF).**  `%M` is `%m` with flag 77, e.g. `@Y/%M@`.  The expander (all 98 copies are byte-identical, `tools/re/mn5_expcmp.py`) tested
`s d D m` in a chain ending in `bra default`; there is no spare word, so the 10-halfword chain is rewritten (same size): `D`, `d` first (an upper case `D` must not be folded into `d`), then `mov r0,r6` (r6 = the character, 109 or 77),
`or #32,r0` (fold), `m`, then `s` last so that its fall-through is the `%s` code, `bf default`; the `mov #0,r6` of the `m` branch becomes a `nop` (r6 keeps the character, the cave only reacts to 77).  Side effect: `%S`
prints a string like `%s` (no record contains `%S`: checked).  Every word is checked against the original bytes (EditSet `expect`), a second application is refused.  `moneycheck.py` section 6 runs the REAL expander of all 98 overlays with
`%D %d %s %m` and `%M %M %m`, `%x`, `%2d`, `%%`: original (before), patched without the token (`%M` prints a literal `M` and takes no argument: unchanged behaviour), patched with the token: byte-identical to the model.
**No translation record uses `%M`**: with the realistic cap (`999 oku 9999 man`, 16 bytes) every one of the 100 `%m` records fits its window in cells and in proportional pixels (`mny_budget.py`: 0 records over at 8, 15 and 16).  Only at the arithmetic cap
`9999 oku 9999 man` (17, `V = 99,999,999`) do 21 records overrun by 1 or 2 cells (the funds warning of 11 DRS* overlays and DATAROOM, 6 ESTABLIS, 4 LOCAL; `python -I -X utf8 tools/re/mn5_slack.py`); the compact form (14 bytes) would fit all of them.
Switching them to `%M` is a text-owner edit PLUS `compact_token=True` in the build (a `--money-compact-token` flag of `build_patch.py`, not added: not mine); it is not needed for any reachable amount, so it was left off.
Validators: `translib.GAME_TOKEN_RE` / `PRINTF_RE` know `%M` (game text only), `_fmt_cells('%M')` = 12 (compact of the typical amount; `%m` stays 15), `translib.canon_tokens` makes `%M` equal to `%m` in the Japanese-vs-English token
comparison of `transcheck.py` (a `%M` can only stand for a `%m`), `pixelwidth` charges 12 cells x 12 px, `transwork.NUMRE` counts it as a number; `mny_budget.py` measures a `%M` with the compact sample.

**4.7.4 `O` versus `0` (PROVEN, `tools/re/mn5_glyphs.py`, `mn5_oh.py`; no bitmap changed).**  In the ORIGINAL `FONT.BIN` half-width block the digit zero and the capital O are the same shape: both 11 columns x 19 rows (rows 3..21), the same oval; `0` has ink in columns 0..10,
`O` in columns 1..11, so `O` is `0` moved one pixel to the right with a slightly rounder top and bottom (sum of absolute nibble differences 338 of about 1290 ink = 26 %, almost all of it that one column shift).  `fontpatch.proportional_font` does not touch glyph
bitmaps and gives `0` advance 12 (digits are fixed) and `O` advance 13, so the patch does not cause the look; the playtest `1 0ku` is the original design of the font (the Japanese 24 px glyph set has no such problem, the English text is the first user of this half-width `O`).
Not changed: a safe fix needs a redrawn `O` (e.g. 2 px wider and taller than the zero) or lower-case unit words (`oku`, `man`: the lower case `o` is 14 rows, x-height only, clearly not a zero) - both change art or the guide wording, so it is the user's call; the second one is a three-constant change of `_JP_SRC`
(`s_oku`) plus the unit sprites `oku` / `man` of docs/art-translation.md section 9.  The compact form avoids a lone `O` next to digits for that reason.

**4.7.5 The header money (digit sprites; INFERRED, the drawing code was NOT found).**  The header bar draws `15 [億] 0000 [万円]` as sprites; the units are cells of texture `BAR.TBD` 00002 (`ATFIRST/BAR.TBD#0` = `ETC_DATA/BAR.TBD#0`, 512 x 512 ARGB4444, resident: loaded at boot by the code at `0x8c160276` into
`0x8ce2c000`).  The cells from the art spec (`tools/re/art1_spec/00002.json`): `man` **49 x 24 px** at (66,141) [the old 万円], `oku` **30 x 32 px** at (462,266) [the old 億, a single 24 px kanji plus margin; the repaint `oku` is condensed to fit 30 px];
the digit sheets are 15 px pitch (a white row `1234567890` at about y 430..455, teal pairs at about x 466..510).  A `man` cell (49 px) holds `man` easily; `oku` in 30 px needs a condensed face (the art owner did that: it reads `oku`, small).
Why the Hometown header still shows a Japanese 億: BAR.TBD 00002 contains exactly ONE `oku` cell, in the teal digit style of the Event header.  The white digit row (Hometown header: `15 [億] 0000 man`, the `man` is from BAR.TBD) has no unit cell next to it, so its 億 must be a cell of a
different texture or a text glyph; group 7 (TOWNDATA, `build/art/groups.json`) lists `億 = x100M Y` for that screen.  Needed from the art owner: the cell size of that 億 (probably the same 30 x 32 / 24 x 24) and a repaint `oku`; and the digit count / gaps: the Japanese layout prints `hi` + unit + `lo` as 4 zero padded digits + unit (`15億0000万円`:
the header always shows the 4 man digits), which is the same structure as the English `15 oku 0000 man`; the unit cell is the only element whose width changed (`oku` is 3 letters in 30 px).  The layout code that places the cells (a resident library, not a field of the overlays: no overlay holds the UV pairs, searched as u16 and float,
`tools/re/mn5_uvfind*.py`) was not located; whether the gap after the unit cell tolerates a wider glyph is therefore UNKNOWN: look at the repainted Hometown header first.

### 4.8 Skeptic review of 4.7 (agent skm, playtest round 2; executed, nothing run in an emulator)

Re-run: `test_moneypatch_tv` 16 OK, `test_sh4sim` OK, `test_patchengine` OK, `moneycheck --quick` 0 failures, `moneycheck --style jp` (full) see the final report.  A trial disc was built with the standard flags under a scratch name and deleted:
`int_disc_money.py` OK (cave 388 bytes in the disc, 102 hooks, 14 sample values), and `tools/re/skm_panel.py` reads SCDRF and SEARCH back from the disc: the four panel `mov #0,r6` halfwords are `mov #77,r6` (`4d e6`) on the disc and nowhere else changed.

* **The 4.7.1 diagnosis is confirmed by the symptom** (field `' oku 300 man'`, the `1` lands in front of the string).  Evidence that the underflow is more than a clipped digit: `b` is the object that the constructor at SCDRF `0x7500` fills; **`b[36]` is initialised to 22 (`0x754a`) and used for geometry at `0x756a`, and `b[34]` is a flag that the SAME function reads at `0x7620`** (0 = money path, else another text path).  A 13 byte text overwrites `b[36]`, a 15 byte text (`13 oku 1500 man`) overwrites `b[34..36]`.  The western style of prop3 / prop4 never wrote more than 9 bytes, so it never touched these bytes; prop7 (jp) does for every salary with an oku and a man part (any multiple of 100 man from `1 oku 100 man`).  So the panel is a **memory-corruption candidate for the hang that appears right after the draft screen** (UNPROVEN: what reads `b[34]` / `b[36]` later was not followed).  The compact form removes the write for every salary word below 10010 (`100 oku 1000m` is the first compact text over 12 bytes; the original Japanese text overflowed there too, so the game does not reach it).  A disc built from the current tree contains the fix; prop7 / prop7r do NOT.
* **Correction of 3 / 4.7.1: seven call sites pass `flag = 1`** (DRSLIST, G_INCOME x4, NEWCON x2, `tools/re/skm_flags.py`).  Only cosmetic (the jp cave ignores the flag).  The remaining direct callers were looked at for destination size: CAP_SLCT / ENDOPT / EVENT `0x27f20` stack buffer 20 bytes, GETREP 32, HOMETOWN 28 and 32, DRSLIST 21, GAME static, NEWCON two static buffers 16 bytes apart (`15` characters + NUL fit; `16` would run into the second).  Nothing else writes by byte count.  G_INCOME / SPONSOR / SPONSOR2 / EVENT `0xbb5e` position the text by `(N - len) * 12` px (window width not checked: a window that keeps its original pixel width clips a longer text at the right; 160 px for `1 oku 300 man` against 96 px for N = 8 in G_INCOME).  Not verified in game.
* **`O` versus `0` is real and worse than reported**: `build/skm/money_glyphs.png` (`tools/re/skm_render.py`, patched font, advances from the table) shows `1 oku 8500 man` as `1 0ku 8500 man`; the compact form does not help because `oku` itself stays.  Lower case `1 oku 8500 man` reads correctly in the same render.  The fix is the user's call (lower-case unit words everywhere = cave `s_oku`, 187 records with a literal `oku` and 140 with `man` in `translation/`, the oku / man sprites; or a redrawn capital `O`, which is a FONT.BIN edit outside the money scope).

## 5. Other number formats in the text (libc sprintf, shared library, GAME) - CONVERTED in mn6 (section 11)

Formats that contain the Japanese units themselves are filled by `sprintf` (widths work) or by the library with arguments computed by game code.  The first rounds converted only the ones
that stayed as wide as the Japanese (`%6d00 man`, `%s man`).  Since the second playtest all of them print the oku / man text through code (section 11):

| Japanese format | args | English format now | prints (example) |
|---|---|---|---|
| `%2d億%02d00万円` (ABROAD FIRE PLNUMSET SELNAT) | oku, hundreds of man | `%2d oku %02d00m` | `13 oku 1500m` (12 characters, field of 12) |
| `%6d00万円` (same 4) | hundreds of man | `%6d00 man` | `    2600 man` |
| `%d兆%04d億%02d00万円` (INVEST) | cho, oku, hundreds | `%d cho%04d oku%02d00m` | `11123 oku 500 man` (cho = 10,000 oku: no cho word) |
| `    %4d億%02d00万円` (INVEST, 18 characters) | oku, hundreds | `    %4d oku %02d00m` | ` 1234 oku 5600 man` (right aligned in 18) |
| `          %4d万円` (INVEST, 18 characters) | man | `          %4d man` | `          4500 man` |
| `%s億%s万円`, `@R/%s億%s万円@` (library: CHALMODE DRSHRANK DRSISEKI DRSJAPAN DRSLIST DRSSRANK GETREP PL_EDIT SELNAT) | hi (space padded), lo (4 digits) | `%s %s man`, `@R/%s %s man@` | `3 oku 9000 man`, `@R/2 oku 4300 man@` |
| `%s万円`, `@R/%s万円@` (same) | man | `%s man`, `@R/%s man@` | `58 man` |
| `%s円` (same: the zero) / `0円` (GETREP, no argument) | | `%s Yen` / the pool word points at a `0 Yen` string of the cave | `0 Yen` |
| `%d円` (G_INCOME income / costs rows, plain yen) | yen | `%d Yen` | `3 oku 9000 man` (390,000,000 yen), `5000 Yen`, `0 Yen` |
| `%d億` `%d万` `0万円` `%s円` (GAME: strcat of the pieces) | | (dead: GAME's text function jumps into the money cave) | `13 oku 1500 man` |
| `%s万%s人` etc. (people in 10,000s) | | unchanged in the nine library overlays (not money); **NENREP** (annual report attendance) translated in place: `%sman %sppl`, `@R/%sman %sppl@`, `%sppl`, `@R/%sppl@` (section 13) | `  1man 2345ppl`, ` 345ppl` |
| `%3d %-13s %d円 %d年` (HELP / TITLE / LOCAL / SCDRF / SPF_READ lists) | | `%3d %-13s Y%d %d yr` (open: 20 bytes, no room for `%d Yen`; looks like a debug list) | |

The library's lo part is zero padded to four digits and hi space padded (`mov #48,r7 / mov #4,r6` before the string conversion in CHALMODE `0x8c4d783a`), which is why printf alone could not
print `1 oku 4642 man` and the old English formats printed `Y   390000000` (`Y` + `   3` + `9000` + `0000`).  See section 11 for how the amounts are read back and printed.

## 6. Translation records

* `FLOW_PRG/*#...` unit pieces (405 records, ja `億` `万円` `円` `0円`, listed in `build/money/piece_ids.txt` by
  `moneypatch.piece_ids()`): **cleared** with `tools/re/clear_en_ids.py` (`en = ""`, `skip: true`).  With the patch they are never
  read; without it the original Japanese pieces print correct (Japanese) amounts.  3 piece records of NENREP are not in the database
  (its extraction base is wrong, the strings stay Japanese).
* 12 format texts (91 records, shared by many overlays) re-translated in the first round with `transmerge.py merge --overwrite` from
  `build/trans/results_money/{0011,0072,0082}.json` (section 5).
* All `%m` / `%D` texts use the Japanese tokens correctly (`@Y/%m@`, no unit after it); stage 2 re-wrapped 57 of them for the longer jp text (section 4.6).
* **Audit list:** `python -I -X utf8 tools/re/money_audit.py` writes `build/trans/money_records.tsv` (2,261 records: 100 `%m`,
  21 `%D`, 405 pieces, 142 sprintf-yen, 69 literal yen, 5 `%s` money, 1,519 other numeric formats), columns id, family, formatter
  (expander / sprintf / either), ja and en tokens, tokens_equal, flags, ja, en.  `tools/re/mny_findY.py` lists records that still contain a western
  amount (`Y10M`, `Y%s`, ...; person names such as `Y. Sato` match too).

## 7. Open points

* Nothing here was seen on screen.  The playtest examples map exactly onto the reproduced strings (`130015000,00`, `60000,00`,
  `810050000,00`, `１003000,00`).
* **Validator budget:** `translib._fmt_cells` charges `%m` as 8 cells (and `tools/pixelwidth.py` 8 x 12 px); for jp style it should be **15** (or 16).  The
  build owner decides; with 8 the validator accepts texts that overflow, with 15 the 100 current records pass (section 4.6).
* TV card: the capital is compact (`32 oku 5000m`), x = 456 .. 603; look at the card in a playtest (section 4.4).
* Whether the money function is called with `flag != 0` anywhere: found in G_INCOME and NEWCON (`mov #1,r6`, zero padded `lo`); jp prints the same text for flag 1 (4.1).  Flag 77 is new and only the 4 panel sites and `%M` pass it (4.7).
* The unit words are ` oku`, ` man` (lower case since mn6) and ` Yen`; three constants in `_JP_SRC` (`s_oku`).
* `docs/patch-engine.md` (section 2 table) still says "428 byte formatter" for `money.cave`; the default is now the 388 byte jp cave (368 before the compact form) (the 428 byte western cave is
  unchanged); the reserve (0x200) and the registry claim did not change.

## 8. Stage 2 helper scripts (`tools/re/mny_*.py`, none is part of the build)

| script | what |
|---|---|
| `mny_baseline_cmp.py FILE` | the western style is byte-identical to the output `pe_baseline.py record` wrote before the jp style existed |
| `mny_budget.py [--only-bad]` | worst-case width of every `%m` text at 8 / 15 / 17 / 20 glyphs (cells and pixels) -> `build/mny/budget.tsv` |
| `mny_rewrap.py [--apply]` | re-wrap the `%m` texts that do not fit at 16 glyphs (+ 7 hand shortened) |
| `mny_literals.py [--apply]` | literal western amounts -> oku / man |
| `mny_findY.py` | list records that still carry a western amount |
| `mny_caps.py`, `mny_caps2.py` | look for the 10^k - 1 money cap literals, show the code around one |
| `mny_dis.py` | capstone listing of a range of an overlay |
| `mny_examples.py` | prints the example table of section 4.6 |
| `mn5_callers.py`, `mn5_padsites.py` | every direct (non-expander) call site of the original money function (list: `build/mn5/callers.txt`) and the field-width idiom after it (4.7.1) |
| `mn5_findref.py`, `mn5_peek.py`, `mn5_dis.py` | literal-pool xrefs, word peek, a capstone listing that resyncs over data and resolves `mov.l @(d,pc)` literals (overlay base 0x8c2d0000 for FLOW_PRG unless the file says otherwise) |
| `mn5_expcmp.py` | locates the tsString expander in all 98 overlays and proves their code bytes identical (4.7.3) |
| `mn5_slack.py` | the `%m` records whose window allows fewer than 17 glyphs (reads `build/mn5/budget.tsv` of `mny_budget.py`) |
| `mn5_glyphs.py`, `mn5_oh.py` | `0` versus `O` in the original and the patched font (4.7.4) |
| `mn5_texpng.py`, `mn5_uvfind*.py`, `mn5_xref1st.py`, `mn5_div10k.py` | header bar texture crop, the (negative) searches for the header sprite cells (4.7.5) |

## 9. Stage 2 skeptic review (sk2)

* Independent re-check (`tools/re/sk2_money_edges.py`: own Python formatter vs the cave executed in sh4sim; V = 0, 1, 9999, 10000, 99999999,
  100000000, 131500, 1315000000, 9999999999999 (wraps to int32), INT_MIN/MAX, negatives): all correct, ASCII only, callee-saved registers and
  stack intact, no write outside the output.  `moneycheck.py --style both` 0 failures; western identical to the recorded baseline.
* Converted after the review (`tools/re/sk2_money_lib.py`, 23 records, zero extra width): `%6d00万円` -> `%6d00 man`, `%s万円` -> `%s man`,
  `@R/%s万円@` -> `@R/%s man@` (section 5 rows 2 and 6, partially).  Still western: `%s億%s万円` family, `%2d億%02d00万円`, INVEST, GAME, `%d円`
  (3+ cells wider, needs the screens).  Variant B overlays (COMM, CON_REP, ...) are not hooked (INFERRED dead) and keep their old western unit pieces.

## 10. Stage 2 integration notes

* Build: `tools/build_patch.py --money-style jp|western` (default jp) is passed as `moneypatch.make_patches(style=...)`; a standard build log
  line reads `money format (jp style): 102 overlays hooked, formatter 0x8c299a00 (388 bytes)`.
* Validator: `translib._fmt_cells` (used by transcheck and pixelwidth) charges `%m` 15 cells (was 8); `test_transwork` expects it.  With 15 all 100
  `%m` records pass; 17 (the cap `9999 oku 9999 man`) is not charged (25 records exceed their window only there).
* The cave returns the length in r0 and does **not** NUL-terminate; every caller (`strncpy` of the original function path, 116 overlay copies in
  moneycheck step 5/6) uses the returned length.
* `moneycheck.py` has no argument parser for `--help` (it runs the full check, ~4 min): use `--quick` (13 s), `--e2e`, `--style jp|western|both`.
* The unit sprites beside the digit sprites (BAR.TBD header, YOUTH, LOADBAR, mon.tbd, ESTABLIS, INVEST, MON_INST, the PLATE.ZAR money plates)
  read `oku` / `man` / `Yen`, matching the formatter (docs/art-translation.md s9).  The old `x10k Y` / `x100M Y` wording of build/art/groups.json is obsolete.
* Real disc check: `python -I -X utf8 tools/re/int_disc_money.py <disc dir> <name> [jp|western]` reads the cave and the 102 overlay hooks back from a
  built disc and runs the cave from the disc bytes on example values (`0 Yen`, `6000 man`, `1 oku`, `1 oku 3000 man`, `13 oku 1500 man`,
  `32 oku 5000 man`, `200 oku`, `9999 oku 9999 man`, `-1 man`): all correct on the integrator trial disc `prop5`.
* ESTABLIS: 15 facility-cost texts (two `%m` each) were cut to three rows of at most 39 cells with `%m` = 15 (see docs/layout-issues.md s7).

## 11. Playtest round 3 (mn6): lower case, the finances screens, the numeric formats, the TV card

Everything here was obtained by static analysis and by executing the real built bytes in `tools/sh4sim.py` (`tools/re/mn6_libsim.py`, `tools/moneycheck.py` section 9).  Nothing was run in an emulator.

**11.1 Lower case.**  `s_oku` is ` oku` / ` man` / ` Yen` (words `0x756B6F20`, `0x6E616D20`, `0x6E655920`), the compact unit is `m` (character 109; the flag stays 77 and `%M`).  `reference()`,
moneycheck, test_moneypatch_tv, 26 English records with `digit + space + Oku|Man` (`tools/re/mn6_db_case.py`: names and football words such as `Target Man`, `Man of the Match`, the surname Oku keep their
capitals), the guide and the style guide were converted.  Compact form decision: `1 oku 300m` (10 characters) rather than `1 oku 300 man` where a field is narrower than the full text; `m` could be read as
a metre or "million", but it only ever follows digits behind an `oku` part, and the guide says so.

**11.2 Why the finances screens printed `Y 390000000`.**  Two kinds of code print amounts without the money function:

1. A **number library** carried by nine overlays (CHALMODE DRSHRANK DRSISEKI DRSJAPAN DRSLIST DRSSRANK GETREP PL_EDIT SELNAT).  `F2a(V signed, x, y, mode)` (all nine) and GETREP's `F1(obj, V, flag)`
   (V in man; `mode` 0..4 = the cap 9,999 .. 99,999,999 man = the width of hi) split `hi = V / 10000`, `lo = V % 10000`, write `itoa(hi, width, ' ')` and `itoa(lo, 4, '0')` into two small stack strings
   and create a text object with the stack-argument printf `real(fmt, hi, lo)`:  `hi > 0: %s億%s万円`, `hi == 0: %s万円`, `V == 0: %s円` (F1: the no-argument `0円`); a negative V uses the `@R/..@` form (red).
   The old English formats `Y%s%s0000` printed `Y` + `   3` + `9000` + `0000`.  `real` is the same code in all nine overlays (`tools/re/mn6_realcmp.py`).
2. **G_INCOME** (the income / costs table): `%d円` with a plain yen integer; the row function right-aligns the object by `(8 - digits) * 12` px with a digit counter
   (`FUN 0x8c4d0152`, one call site) and creates the text with the same library printf (`0x8c4d43dc`).

**11.3 The library wrapper (`money.lib`, 240 bytes at 0x8c299400, jp style).**  The literal-pool word of `real` in each library overlay (`LIB_SITES`; 10 words) now points at a 16 byte stub that the patch
writes into the dead body of the overlay's own money function copy (+12): `r1 = real; r0 = LIB; jmp @r0`.  LIB (`LIB_SRC`) looks at the format: the text behind the last `%s` must be ` ma..` or ` Ye..`, anything
else is passed to `real` with the stack and PR untouched (the people formats `%s%s`, ...).  Otherwise: prefix (up to the first `%`) + `money(V)` + suffix (behind the 4 characters ` man` / ` Yen`),
`V = digits(a1) [digits(a2)]` (hi then the 4 digit lo), then `real('%s', text)`.  The English formats are therefore **`%s %s man`, `@R/%s %s man@`, `%s man`, `@R/%s man@`, `%s Yen`**; the middle of a
two-argument format is never printed (it is only there so that the fallback without the patch is readable and fits the 12 / 16 byte slots).  GETREP's `0円` pool word (`LIB_ZERO`) is repointed at a
`0 Yen` string in the cave (4 bytes were too few); its record is cleared (en "", skip).  Registered caves: `money.lib` 0x8c299400 (0x200).

**11.4 The numeric wrapper (`money.libn`, 644 bytes at 0x8c299c00, carved from the START of the planned bank, which now starts at 0x8c29a000).**  The remaining formats use libc `sprintf(dst r4, fmt, args...)` (arguments on
the stack) or, in G_INCOME, the library printf.  `n_core` reads the English format as a tiny grammar: every `%` is `%[0-9]*d` followed by zeros (`00` = x100), spaces and a unit letter `c` (cho 10^8 man), `o` (oku 10^4),
`m` (man), `y` / `Y` (yen, 1/10^4); the value in man is `sum(arg * 10^zeros * unit)`.  The text is the jp money text (compact form when the full text is wider than the field W), right aligned in W (12 for the
four player-info overlays, 18 for INVEST), or `N Yen` for a yen amount below one man.  A format that is not of this shape passes through (`n_ps`: original r4, stack untouched).  Entries: `n_sp` (libc sprintf,
24 byte stub at money function + 32 with `r1 = real`, `r2 = W`), `n_al` (G_INCOME: `real('%s', text)`), `n_gd` (G_INCOME's digit counter: the number of characters minus 2, so that the object ends where the
Japanese text with its 2 byte 円 ended), `n_gm` (GAME's own money text function at 0x8c3c7b74: `money(dst, V, 0)` + NUL; hooked with the 12 byte entry hook).  Pool words (`LIBN_SITES`): ABROAD 0x7e4c, FIRE 0x6be0,
PLNUMSET 0x9874, SELNAT 0xddfc (the 12 byte fields live in a 13 byte stride: the text must be exactly 12 characters, hence the right alignment and the compact form), INVEST 0x1ce0, G_INCOME 0x1a54 and 0x1a58.
`libn_reference()` is the Python model.  Amounts the game keeps in plain yen are shown rounded down to whole man (G_INCOME); below one man the exact yen are kept (`5000 Yen`).

**11.5 Executed (real values).**  `python -I -X utf8 tools/re/mn6_libsim.py [--quick] [--functions] [--libn]` and `moneycheck.py` section 9: the wrapper through the patched overlays, then the REAL library
functions F1 and F2a executed with real amounts on the built overlays (itoa and the division helpers run natively; `real` is observed): `3 oku 9000 man` (39000 man = 390,000,000 yen),
`2 oku 4300 man`, `1 oku 4642 man`, `58 man`, `0 Yen`, `999 oku 9999 man` (the cap), negative amounts as `@R/..@`; the argument shapes of the ORIGINAL formats are asserted (hi space padded, lo four digits);
pass-through of non-money formats leaves r4, the stack and PR untouched.  The numeric wrapper: G_INCOME `390000000 yen -> 3 oku 9000 man`, `243000000 -> 2 oku 4300 man`, `146420000 -> 1 oku 4642 man`,
`58000000 -> 5800 man`, `5000 -> 5000 Yen`, `0 -> 0 Yen`; ABROAD `(13, 15) -> 13 oku 1500m`, `(1, 3) -> '  1 oku 300m'`, `26 -> '    2600 man'`; INVEST `(1234, 56) -> ' 1234 oku 5600 man'`; GAME 15 values.
**UNKNOWN (needs a screen):** the x position of the library text objects (`F2a` computes the x of the object from its mode argument and a constant, the same for every text: the English text is wider than the Japanese in most columns);
the exact column edges of the finances table; whether the debug lists (`%3d %-13s Y%d %d yr`) are ever shown.

**11.6 Files.**  `tools/moneypatch.py` (LIB_SRC, LIBN_SRC, LIB_SITES, LIBN_SITES, LIBN_GAME, `lib_reference`, `libn_reference`, `make_patches(..., lib=True, libn=True)`; both default on, jp style only, default cave address only),
`tools/moneycheck.py` (section 9), `tools/re/mn6_*.py`: `mn6_libsim.py` (the executions), `mn6_libscan.py` / `mn6_sprsites.py` / `mn6_realcmp.py` / `mn6_fnstart.py` / `mn6_findref2.py` / `mn6_dis1st.py` (site
finders), `mn6_db_lib.py` / `mn6_db_num.py` / `mn6_db_case.py` (record edits through `mn6_db.py`: one read-modify-write per file with an atomic replace), `mn6_formats.py` (the audit list), `mn6_case_scan.py`.

## 12. Skeptic review of mn6 (skm7)

Re-run: `test_moneypatch_tv` 16, `test_patchengine` 26, `test_sh4sim` 15 OK; `moneycheck.py --quick` 0 failures; a fresh trial disc (standard flags, empty textures dir, deleted afterwards) read back with
`tools/re/mn6_discfmt.py` / `mn6_discsim.py --quick`: library, numeric and GAME checks OK, formats read `oku` / `man`.  Found and fixed: 8 records `Profit of Y200M` (NEWS_ED, OFFICE, SCHE0, SCHE1, SPONSOR,
SPONSOR2, TOWN, WEEKLY) that the literal-amount pass had missed -> `Profit of 2 oku` (`tools/re/skm7_db_fix.py`).  **NENREP** (annual report; money formats and people formats done in stage 8b / section 13) carries its own copy of the library formats as a data block
(file offsets 0x24efc..0x24f4c: `@R/%s億%s万円@`, `%s億%s万円`, `@R/%s万円@`, `%s万円`, `%s円`, people formats) loaded by code at 0xf49e / 0xf58e / 0xf8c2 / 0xfadc / 0xfcfa; it is not in `LIB_SITES`
(`mn6_libscan.py` finds 8 false hits on the float constants at 0x24ef4..0x24ef8) so positive amounts there stay Japanese kanji and the red form reads `Y%s/%s` (DB record NENREP#24ef8, which also holds the
float 0.7).  Helpers: `tools/re/skm7_nen*.py`.  `tools/re/sk2_money_edges.py` still expects capitals (reports BAD only for the case).

## 13. NENREP people formats (annual report attendance, `%s万%s人`)

NENREP has its own number function (file `0xe3cc`, literal-pool callers at `0x514`, `0x582`, `0x5158`, `0x51b0`; mode 3, one caller mode 4) that prints a head count V in people.  NENREP loads at `0x8c2d0000`
(not `0x8c2e0000`: that wrong base is why the money and people strings looked unreferenced before).  Executed in `tools/sh4sim.py` on the original bytes (`V` -> text handed to the library printf `real` = file `0xafcc`):

| V | `real(fmt, ...)` | arguments |
|---|---|---|
| 12345 | `%s万%s人` | hi `'  1'` (V / 10000, space padded to the mode), lo `'2345'` (V % 10000, four digits, zero padded) |
| 345 | `%s人` | lo `' 345'` (space padded to four); the object is moved right by `12 * mode + 24` px so the Japanese text ends at the same x as the long form |
| -12345 / -345 | `@R/%s万%s人@` / `@R/%s人@` | the same, red, no minus sign |

The four formats that end in `@` without `@R/` (`-%s万%s人@`, `%s万%s人@`, `-%s人@`, `%s人@`) go to the debug printf `0x8c0111b4` only (`mov #22,r4` + stack arguments; gated by the flag
bytes `0x8c230bd6` / `0x8c193c04`, both 0 in the image and in all seven RAM dumps of `build/emu`): never shown.  A second function at `0xe606` uses the same strings and has no caller.

English, kept in the Japanese style (`man` = 10,000, like `%soku %sman`; 人 = `ppl`), in place in the slots (string + NUL + zero padding up to the next string):

| offset | Japanese | English | bytes (slot) | role |
|---|---|---|---|---|
| `0x24f34` | `@R/%s万%s人@` | `@R/%sman %sppl@` | 15 (16) | shown, negative, hi > 0 |
| `0x24f50` | `%s万%s人` | `%sman %sppl` | 11 (12) | shown, hi > 0 |
| `0x24f68` | `@R/%s人@` | `@R/%sppl@` | 9 (12) | shown, negative, hi == 0 |
| `0x24f7c` | `%s人` | `%sppl` | 5 (8) | shown, hi == 0 |
| `0x24f44` `0x24f5c` `0x24f74` `0x24f84` | `-%s万%s人@` `%s万%s人@` `-%s人@` `%s人@` | `-%sman %sp@` `%sman %sp@` `-%sppl@` `%sppl@` | 11 (12) 10 (12) 7 (8) 6 (8) | debug printf only (abbreviated to fit) |

Prints `  1man 2345ppl`, ` 12man 3456ppl`, `123man 4567ppl` (hi space padded to 3), ` 345ppl`.  The text object keeps the Japanese x position; English is wider than the Japanese 132 px of the long form: 162 px with the
open font table (digits and spaces 12 px; mode 4: 174 vs 144), the short form 77 vs 72 px, so the right end moves right by 30 px (5 px).  The callers draw the long form at x = 422 / 410 (right end 584)
and x = 466 (`mov.w` literal `0x5248`, right end 628 of 640; Japanese 598): NOT looked at on a screen; if it is crowded, the literal words (466 at `0x5248`, 422 at `0x5d2`) can be moved left.  Executed on the BUILT NENREP.BIN
(`tools/sh4sim.py`, mode 3): V 12345 -> `  1man 2345ppl`, 123456 -> ` 12man 3456ppl`, 9999999 -> `999man 9999ppl`, 345 -> ` 345ppl`, -12345 -> `@R/  1man 2345ppl@`, -345 -> `@R/ 345ppl@`.  The nine library overlays carry the same eight strings (CHALMODE, DRSHRANK, DRSISEKI,
DRSJAPAN, DRSLIST, GETREP, PL_EDIT, SELNAT, DRSSRANK; TV_EVENT has one `%s人`) behind the money wrapper, which passes them through: still Japanese there.
Files: `tools/textfmt_gap.py` (GAPS), `tools/re/p1_nenrep_people.py` (records), `tools/test_gap.py`.
