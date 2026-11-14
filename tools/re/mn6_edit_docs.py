"""mn6_edit_docs.py: one-off, idempotent edit of doc/TRANSLATORS_NOTES.md (money section and the money mentions) and tools/test_release.py (its
money-example regexes) for the lower-case oku / man style and the converted data-room formats (mn6)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def edit(path, pairs):
    s = open(path, encoding='utf-8', newline='').read()
    crlf = '\r\n' in s
    if crlf:
        s = s.replace('\r\n', '\n')
    done = 0
    for old, new in pairs:
        if old in s:
            s = s.replace(old, new)
            done += 1
        elif new not in s:
            sys.exit('%s: neither old nor new text found: %r' % (path, old[:70]))
    if crlf:
        s = s.replace('\n', '\r\n')
    open(path, 'w', encoding='utf-8', newline='').write(s)
    return done


NOTES = os.path.join(ROOT, 'doc', 'TRANSLATORS_NOTES.md')
pairs = [
    ('money in Oku and Man, kyu and dan ranks', 'money in oku and man, kyu and dan ranks'),
    ('3 Money: Oku and Man - 4 Names', '3 Money: oku and man - 4 Names'),
    ('## 3. Money: Oku and Man', '## 3. Money: oku and man'),
    ('* **Man** = 10,000 yen (the Japanese 万)\n* **Oku** = 100,000,000 yen = 10,000 Man (the Japanese 億)\n\n'
     'An amount is written Oku first, then Man, with a space between them. A part that is zero is left out.\n'
     'To turn it into yen: **yen = Oku x 100,000,000 + Man x 10,000.**',
     '* **man** = 10,000 yen (the Japanese 万)\n* **oku** = 100,000,000 yen = 10,000 man (the Japanese 億)\n\n'
     'An amount is written oku first, then man, with a space between them. A part that is zero is left out.\n'
     'To turn it into yen: **yen = oku x 100,000,000 + man x 10,000.**\n'
     'Both words are in lower case on purpose: a capital `O` looks like a zero in the game font (`1 Oku` read as `1 0ku`).'),
    ('| `1 Man` | 10,000 yen |', '| `1 man` | 10,000 yen |'),
    ('| `150 Man` | 1,500,000 yen |', '| `150 man` | 1,500,000 yen |'),
    ('| `6000 Man` | 60,000,000 yen |', '| `6000 man` | 60,000,000 yen |'),
    ('| `1 Oku` | 100,000,000 yen |', '| `1 oku` | 100,000,000 yen |'),
    ('| `1 Oku 300 Man` | 103,000,000 yen |', '| `1 oku 300 man` | 103,000,000 yen |'),
    ('| `13 Oku` | 1,300,000,000 yen |', '| `13 oku` | 1,300,000,000 yen |'),
    ('| `13 Oku 1500 Man` | 1,315,000,000 yen |', '| `13 oku 1500 man` | 1,315,000,000 yen |'),
    ('| `32 Oku 5000 Man` | 3,250,000,000 yen |', '| `32 oku 5000 man` | 3,250,000,000 yen |'),
    ('| `9999 Oku 9999 Man` | 999,999,990,000 yen |', '| `9999 oku 9999 man` | 999,999,990,000 yen |\n| `3 oku 9000 man` | 390,000,000 yen |'),
    ('Reading `13 Oku 1500 Man`: 13 Oku is 1,300,000,000 yen, 1500 Man is 15,000,000 yen, together 1,315,000,000 yen. A Man part\n'
     'can be at most 9999, because 10,000 Man is already 1 Oku.',
     'Reading `13 oku 1500 man`: 13 oku is 1,300,000,000 yen, 1500 man is 15,000,000 yen, together 1,315,000,000 yen. A man part\n'
     'can be at most 9999, because 10,000 man is already 1 oku.'),
    ('* **There is no `Y` or yen sign in front of amounts and no decimal form** (no `Y1.3bn`). `Yen` appears for an\n'
     '  amount of exactly zero and on the unit pictures.\n'
     '* The Man part is not padded with zeros: `1 Oku 1 Man` is 100,010,000 yen.\n'
     '* A negative amount has a minus sign in front: `-1 Man`.',
     '* **There is no `Y` or yen sign in front of amounts and no decimal form** (no `Y1.3bn`). `Yen` appears for an\n'
     '  amount of exactly zero (`0 Yen`), for a plain yen amount below one man (`5000 Yen`, a ticket price) and on the unit pictures.\n'
     '* The man part is not padded with zeros: `1 oku 1 man` is 100,010,000 yen.\n'
     '* A negative amount has a minus sign in front: `-1 man` (in a few tables red text is used instead).\n'
     '* In a narrow field the word `man` after an oku part is shortened to `m`: `13 oku 1500m` is `13 oku 1500 man`\n'
     '  (the scout panel, the TV station card capital, the 12-character player-info fields).\n'
     '* Amounts that the game keeps in plain yen (the income / costs table) are shown rounded down to whole man:\n'
     '  `3 oku 9000 man` stands for 390,000,000 yen up to 9,999 yen.'),
    ('  `Man`: the graph header reads `People (10k)`.\n* Graph headers and the small unit pictures beside digits were repainted to `Oku`, `Man` and `Yen` to match.\n'
     '* Still-western amounts: a few data-room tables are filled by older game routines that could not be converted; there you\n'
     '  may still meet a plain yen figure such as `Y1315000000` (that is 1,315,000,000 yen written out in full). The meaning is\n'
     '  the same; only the spelling differs. See section 8.',
     '  `man`: the graph header reads `People (10k)`.\n* Graph headers and the small unit pictures beside digits are repainted to `oku`, `man` and `Yen` to match.\n'
     '* The data-room tables, the monthly report, the income / costs table and the investment screen use older game routines;\n'
     '  they were converted with small code patches (`tools/moneypatch.py`) and print the same words. A table of figures of the\n'
     '  `debug` kind (the lists `%3d %-13s Y%d %d yr` in HELP / TITLE / LOCAL) may still show a plain `Y` figure; see section 8.'),
    ('| **Oku**, **Man** | Money units, section 3. |', '| **oku**, **man** | Money units, section 3. |'),
    ('* **Money in a few data-room screens** is still the plain-yen form described in section 3. Some of these amounts sit in\n'
     '  columns that are too narrow for `13 Oku 1500 Man`.',
     '* **Money in debug lists** (`%3d %-13s Y%d %d yr`: HELP, TITLE, LOCAL, SCDRF, SPF_READ) is still a plain `Y` figure; the\n'
     '  lists are not part of normal play as far as we know. Wide amounts (`13 oku 1500 man`, 15 characters) can be wider than the\n'
     '  Japanese column on a few tables; the patch then uses the short form `13 oku 1500m`.'),
    ('`jp` prints Oku / Man (`13 Oku 1500 Man`).', '`jp` prints oku / man (`13 oku 1500 man`).'),
    ('**Why does it say `13 Oku 1500 Man` and not `1.3 billion yen`?**\nBecause the game is Japanese and counts that way. It is a small habit to learn: 1 Man is 10,000 yen, 1 Oku is 10,000 Man.',
     '**Why does it say `13 oku 1500 man` and not `1.3 billion yen`?**\nBecause the game is Japanese and counts that way. It is a small habit to learn: 1 man is 10,000 yen, 1 oku is 10,000 man.'),
]
print('guide: %d edits' % edit(NOTES, pairs))

TR = os.path.join(ROOT, 'tools', 'test_release.py')
pairs = [
    ("GUIDE_HEADINGS = ('What this is', 'Applying the patch', 'Money: Oku and Man',", "GUIDE_HEADINGS = ('What this is', 'Applying the patch', 'Money: oku and man',"),
    ("    for kw in ('Oku', 'Man', 'kyu', 'dan',", "    for kw in ('oku', 'man', 'kyu', 'dan',"),
    ('    # every worked money example "`X Oku Y Man` | N yen" is arithmetically right', '    # every worked money example "`X oku Y man` | N yen" is arithmetically right'),
    ("        oku = re.search(r'(\\d+) Oku', s)\n        man = re.search(r'(\\d+) Man', s)", "        oku = re.search(r'(\\d+) oku', s)\n        man = re.search(r'(\\d+) man', s)"),
]
print('test_release: %d edits' % edit(TR, pairs))
