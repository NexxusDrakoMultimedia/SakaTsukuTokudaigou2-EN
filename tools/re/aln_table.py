"""aln: print the proportional advance table (printable ASCII) and the glyphs wider than 12 px."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(HERE, 'layout'))
import prop_widths as PW  # noqa: E402

t = PW.table()
rows = []
for c in range(0x20, 0x7f):
    rows.append('%s=%d' % (chr(c), t[c]))
print(' '.join(rows))
print('wider than 12:', ' '.join('%s=%d' % (chr(c), t[c]) for c in range(0x20, 0x7f) if t[c] > 12))
print('exactly 12:', ''.join(chr(c) for c in range(0x20, 0x7f) if t[c] == 12))
