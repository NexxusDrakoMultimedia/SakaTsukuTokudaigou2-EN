import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), 'tools'))
import widths as W
names = {0x7c: r'\|', 0x5c: r'\ (yen glyph)', 0x7e: '~ (overline glyph)', 0x60: '` (grave)'}
rows = ['| code | char | ink cols (any) | ink cols (strong) | shift left | blank right (strong) | advance |', '|---|---|---|---|---|---|---|']
for c in range(0x21, 0x7f):
    m = W.M[c]
    ch = names.get(c, chr(c))
    if c not in names: ch = '`%s`' % ch
    rows.append('| 0x%02X | %s | %d-%d | %d-%d | %d | %d | %d |' % (c, ch, m['any_l'], m['any_r'], m['st_l'], m['st_r'], m['shift'], m['right_blank_strong'], W.advance(c, 'H')))
print('\n'.join(rows))
