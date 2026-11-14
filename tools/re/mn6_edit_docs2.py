"""mn6_edit_docs2.py: one-off, idempotent edit of the money section 8.3 of docs/style-guide.md (lower case oku / man, the converted formats)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, 'docs', 'style-guide.md')
s = open(P, encoding='utf-8', newline='').read()
crlf = '\r\n' in s
s = s.replace('\r\n', '\n')
a = s.index('- **Money keeps the Japanese oku / man structure, written in English words (USER DECISION, binding).**')
b = s.index('- The currency sign: where a literal sign is still needed')
if 'lower case on purpose' in s[a:b]:
    sys.exit('already applied')
new = '''- **Money keeps the Japanese oku / man structure, written in English words, in LOWER CASE (USER DECISION, binding; lower case since the
  second playtest: the capital `O` of `Oku` reads as a zero in the half-width font, `1 Oku` looked like `1 0ku`).**  *oku* = 100 million
  yen, *man* = 10 thousand yen.  The patched money function prints `13 oku 1500 man`, `6000 man`, `1 oku`, `1 oku 300 man`, `0 Yen`
  (negative: `-1 man`).  There is **no `Y` prefix and no decimal / western form** (`Y1.315bn`, `Y150M`, `1.5 billion yen` are wrong
  in this project).  Nothing is explained in game; the translator's guide does that.  `--money-style western` still builds the old
  decimal text but is not the shipped style (docs/number-formats.md).  `Yen` keeps its capital (a plain amount below one man, `0 Yen`).
- **Compact form `13 oku 1500m`** (`man` after an oku part shrinks to `m`; flag 77 / `%M`): scout panel, TV station card capital, the 12 character
  player-info fields, any field narrower than the full text.  An amount with one part is never shortened.
- `%m` (and every `%s` the game fills with a money string) is printed by that function (tools/moneypatch.py, `--money-format on`, the
  default).  Write `%m` exactly as the Japanese does, never put `Y`, `yen` or a unit after it; budget **15 cells** for it (`13 oku 1500 man`;
  the design maximum is 17 for `9999 oku 9999 man`).  tools/translib.py `_fmt_cells`, transcheck and pixelwidth charge 15.
  Without the patch the translated `%m` texts would show Japanese amounts, so a build that ships English must use it.
- Literal amounts typed in prose are written in the same words, lower case: `2 oku`, `3 oku`, `9 oku 9000 man`, `1000 man bonus`; right-aligned
  columns use `  3 man`, ` 10 man`, `  0 Yen`.  A bare 円 is `Yen`.  The population figure is the exception: 万 beside people is `10k`, not `man`.
  Football words and names keep their capitals (`Target Man`, `Man of the Match`, the surname Oku): the rule is digit + space + `oku` / `man`.
- **Library and sprintf formats (converted by code, docs/number-formats.md s5).**  The English format of an amount keeps the Japanese tokens and names
  the unit after each one; the patch reads that format and prints the money text itself:
  `%s %s man` / `@R/%s %s man@` (hi, lo), `%s man`, `%s Yen` (the shared library of the data-room screens and the monthly report),
  `%2d oku %02d00m` and `%6d00 man` (hundreds of man: ABROAD, FIRE, PLNUMSET, SELNAT), `%d cho%04d oku%02d00m`, `    %4d oku %02d00m`,
  `          %4d man` (INVEST), `%d Yen` (G_INCOME, plain yen rounded down to whole man).  Do not "improve" these strings: the unit letter after
  each conversion (c / o / m / y) is what the patch reads, and a `%d` without a unit makes the format pass through unchanged.
'''
s = s[:a] + new + s[b:]
s = s.replace('oku / man in English words (`13 Oku 1500 Man`, `6000 Man`, `1 Oku`, `0 Yen`), tools/moneypatch.py style jp; in-game test pending',
              'oku / man in English words, lower case (`13 oku 1500 man`, `6000 man`, `1 oku`, `0 Yen`), tools/moneypatch.py style jp; in-game test pending')
s = s.replace('Money (Oku / Man), ranks (kyu / dan)', 'Money (oku / man), ranks (kyu / dan)')
if crlf:
    s = s.replace('\n', '\r\n')
open(P, 'w', encoding='utf-8', newline='').write(s)
print('ok')
