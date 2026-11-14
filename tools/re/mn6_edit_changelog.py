"""mn6_edit_changelog.py: one-off, idempotent edit of CHANGELOG.md for the second-playtest money work (mn6).  One read-modify-write with an atomic replace."""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, 'CHANGELOG.md')
raw = open(P, 'rb').read()
crlf = b'\r\n' in raw
s = raw.decode('utf-8').replace('\r\n', '\n')
if 'Money, second playtest' in s:
    sys.exit('already applied')

OLD = [
    ('Event panel: the salary lost its first digits and `Centre Push` was cut; fixed in the build (`1 Oku 300M`, right-aligned labels)',
     'Event panel: the salary lost its first digits and `Centre Push` was cut; fixed in the build (`1 oku 300m`, right-aligned labels)'),
    ('- The capital `O` of `Oku` looks like a zero in the game font (`1 0ku 8500 Man`).  Open decision: lower-case `oku` / `man`, or keep the capitals.',
     '- The capital `O` of `Oku` looked like a zero in the game font (`1 0ku 8500 Man`).  Decided in the second playtest: lower-case `oku` / `man` everywhere (see Money, second playtest).'),
    ('amounts are shown in Oku and Man (`13 Oku 1500 Man`, `6000 Man`, `1 Oku`, `0 Yen`)', 'amounts are shown in oku and man (`13 oku 1500 man`, `6000 man`, `1 oku`, `0 Yen`)'),
]
for old, new in OLD:
    if old not in s:
        sys.exit('text not found: %r' % old[:60])
    s = s.replace(old, new)

NOTE = '''### Money, second playtest (money owner mn6; proven in the interpreter on the real built overlays, not yet seen on screen)

- **Lower case `oku` / `man`** (user decision): `13 oku 1500 man`, `6000 man`, `1 oku`; compact form `13 oku 1500m`.  `Yen` keeps its capital (`0 Yen`).  Done in the money formatter, in
  every English text with a digit before the word (26 records), in the validators' examples and in the translators' guide.  The unit pictures (`Oku` / `Man` sprites of the header, plates and
  strips) still need the same repaint (art owner).
- **Finances screens printed western amounts** (`Y 390000000`, `Y 243000000`, `Y 146420000`).  They come from a number library of nine overlays (data-room screens, monthly report, ...) and from the
  income / costs table (`G_INCOME`, plain yen), which never used the money formatter.  A new wrapper in the 1ST_READ tail (`money.lib`, `money.libn`) now reads their English formats and prints
  the same text as everywhere else: `3 oku 9000 man`, `2 oku 4300 man`, `1 oku 4642 man`, `58 man`, `0 Yen`, red `@R/..@` kept for negative amounts.  Also converted: the player-info fields of
  ABROAD / FIRE / PLNUMSET / SELNAT (12 characters, compact form), the investment screen (`INVEST`, `11123 oku 500 man`), the match-engine text function of `GAME`, and the right-alignment of the
  `G_INCOME` yen rows.  The debug lists `%3d %-13s Y%d %d yr` (HELP, TITLE, LOCAL, SCDRF, SPF_READ) keep their `Y`.
- **TV station card:** the capital no longer runs over the `Capital` capsule and past the plate: compact form (`32 oku 5000m`, 147 px) from x = 456.

'''
anchor = '### Known issues (found in the first playtest'
assert s.count(anchor) == 1
s = s.replace(anchor, NOTE + anchor)
data = (s.replace('\n', '\r\n') if crlf else s).encode('utf-8')
fd, tmp = tempfile.mkstemp(dir=ROOT, suffix='.mn6tmp')
with os.fdopen(fd, 'wb') as f:
    f.write(data)
os.replace(tmp, P)
print('ok')
