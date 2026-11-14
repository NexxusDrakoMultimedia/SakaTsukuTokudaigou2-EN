"""mn5_oh.py: '0' versus 'O' in the original and in the proportional-font patched FONT.BIN (advance, left shift, pixel difference), with the digit '8' and 'Q' / 'D' as scale."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import font as F
import fontpatch as FPT
raw = open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'extracted', 'FONT.BIN'), 'rb').read()
f0 = F.Font(raw)
fnew_b, table = FPT.proportional_font(raw)
fnew = F.Font(fnew_b)


def img(font, c):
    return np.array([15 - v for v in F.nibbles(font.half()[F.half_index(ord(c))])]).reshape(24, 12).astype(int)


def cols(a):
    return [i for i in range(12) if a[:, i].max() >= 4]


for c in '0OoDQ8':
    a0, a1 = img(f0, c), img(fnew, c)
    print('%s original ink cols %s..%s | patched ink cols %s..%s advance %d  rows with ink %d..%d' % (
        c, min(cols(a0)), max(cols(a0)), min(cols(a1)), max(cols(a1)), table[ord(c)],
        min(i for i in range(24) if a1[i].max() >= 4), max(i for i in range(24) if a1[i].max() >= 4)))
a, b = img(fnew, '0'), img(fnew, 'O')
print('patched 0 vs O: sum abs diff %d of ink %d / %d' % (abs(a - b).sum(), a.sum(), b.sum()))
print('ink width 0: %d  O: %d  ; height 0: %d  O: %d' % (len(cols(a)), len(cols(b)), sum(1 for i in range(24) if a[i].max() >= 4), sum(1 for i in range(24) if b[i].max() >= 4)))
# difference map
for r in range(24):
    print(''.join('#' if abs(a[r, x] - b[r, x]) >= 6 else ('+' if a[r, x] >= 6 else ('o' if b[r, x] >= 6 else '.')) for x in range(12)))
