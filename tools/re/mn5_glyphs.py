"""mn5_glyphs.py: ASCII-art dump of half-width glyphs 0, O, o, 1 of the ORIGINAL extracted/FONT.BIN and the proportional advances of the patch."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import font as F
f = F.Font.load()
h = f.half()
chars = sys.argv[1] if len(sys.argv) > 1 else '0O'
rows = {}
for c in chars:
    g = F.nibbles(h[F.half_index(ord(c))])
    rows[c] = [''.join(' .:-=+*#%@'[min(9, (15 - g[r * 12 + x]) * 10 // 16)] for x in range(12)) for r in range(24)]
for r in range(24):
    print('  '.join(rows[c][r] for c in chars))
import numpy as np
a = np.array([15 - v for v in F.nibbles(h[F.half_index(ord(chars[0]))])]).reshape(24, 12)
b = np.array([15 - v for v in F.nibbles(h[F.half_index(ord(chars[1]))])]).reshape(24, 12)
print('ink cols %s: %s' % (chars[0], [i for i in range(12) if a[:, i].max() >= 4]))
print('ink cols %s: %s' % (chars[1], [i for i in range(12) if b[:, i].max() >= 4]))
print('sum abs diff', int(abs(a - b).sum()), 'of total ink', int(a.sum()), int(b.sum()))
