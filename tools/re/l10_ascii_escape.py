"""l10 ascii escape: rewrite every non-ASCII character of the given Python files as a backslash-u escape (so that the
source stays ASCII; only valid inside string / regex literals and comments).  usage: l10_ascii_escape.py FILE.."""
import sys

BS = chr(92)
for p in sys.argv[1:]:
    s = open(p, encoding='utf-8', newline='').read()
    out = []
    n = 0
    for c in s:
        if ord(c) > 0x7f:
            out.append(BS + 'u%04x' % ord(c))
            n += 1
        else:
            out.append(c)
    if n:
        open(p, 'w', encoding='utf-8', newline='').write(''.join(out))
    print(p, n, 'characters escaped')
