"""mn6_edit_nf.py: one-off edit of docs/number-formats.md (lower case oku / man, TV card, converted formats, new section 11).  Idempotent (marker)."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, 'docs', 'number-formats.md')
s = open(P, encoding='utf-8', newline='').read().replace('\r\n', '\n')
if '## 11. Playtest round 3' in s:
    sys.exit('already applied')

# ---- 1. lower case everywhere (historic remarks about the capital form are restored below)
s = re.sub(r'\bOku\b', 'oku', s)
s = re.sub(r'\bMan\b', 'man', s)
s = re.sub(r'(oku \d+)M\b', r'\1m', s)

# ---- 2. headline decision
s = s.replace('''**USER DECISION (binding, stage 2): the game stays appropriately Japanese.**''',
              '''**USER DECISION (binding, stage 2): the game stays appropriately Japanese.  Second playtest (mn6): the words are LOWER CASE, `oku` and `man` (a capital `O` reads as a zero in the half-width
font: `1 Oku` looked like `1 0ku`); `Yen` keeps its capital.  Sections 4.1 - 4.8 were written with capitals and were converted mechanically; section 11 is the new work.**''')

# ---- 3. section 4.4 TV card: new layout
a = s.index('### 4.4 The TV station card capital')
b = s.index('### 4.5 What was verified')
tv = '''### 4.4 The TV station card capital (`FLOW_PRG/TV_EVENT.BIN`, PROVEN by execution)

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

'''
s = s[:a] + tv + s[b:]

# ---- 4. section 5: converted
a = s.index('## 5. Other number formats in the text')
b = s.index('## 6. Translation records')
sec5 = '''## 5. Other number formats in the text (libc sprintf, shared library, GAME) - CONVERTED in mn6 (section 11)

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
| `%s万%s人` etc. (people in 10,000s) | | unchanged (not money) | |
| `%3d %-13s %d円 %d年` (HELP / TITLE / LOCAL / SCDRF / SPF_READ lists) | | `%3d %-13s Y%d %d yr` (open: 20 bytes, no room for `%d Yen`; looks like a debug list) | |

The library's lo part is zero padded to four digits and hi space padded (`mov #48,r7 / mov #4,r6` before the string conversion in CHALMODE `0x8c4d783a`), which is why printf alone could not
print `1 oku 4642 man` and the old English formats printed `Y   390000000` (`Y` + `   3` + `9000` + `0000`).  See section 11 for how the amounts are read back and printed.

'''
s = s[:a] + sec5 + s[b:]

# ---- 5. section 7 open points
s = s.replace('* The sprintf / library formats of section 5 are still western; GAME `%d億` + `%d万` is still fused.\n', '')
s = s.replace('* Table columns that right-align with `%6d` / `%4d` put the `Y` before the padding (`Y    26M`); a variable position for `Y` needs code (jp: `%6d00 man` has no such problem).\n', '')
s = s.replace('* TV card: the capital now ends at x = 624 (`32 oku 5000 man`); look at the card frame in a playtest (section 4.4).',
              '* TV card: the capital is compact (`32 oku 5000m`), x = 456 .. 603; look at the card in a playtest (section 4.4).')
s = s.replace('* The unit words are `oku` and `man` with a capital and a leading space (` oku`, ` man`, ` Yen`); a different spelling (`oku`, `man`) is a three-constant change in `_JP_SRC` (`s_oku`).\n',
              '* The unit words are ` oku`, ` man` (lower case since mn6) and ` Yen`; three constants in `_JP_SRC` (`s_oku`).\n')

# ---- 6. section 11
s = s.rstrip('\n') + '''

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
'''
open(P, 'w', encoding='utf-8', newline='').write(s)
print('ok')
