"""Who references the section/pool table words at 0x8c016b68..0x8c016bb0 (which contain 0x8c299400 / 0x8c2e0000)?
Scan every aligned word of 1ST_READ.BIN for a value in [0x8c016b60, 0x8c016bb4); print address, value and 8 words of context."""
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
fr = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
B = 0x8C010000
n = 0
for o in range(0, len(fr) - 3, 2):
    v = struct.unpack_from('<I', fr, o)[0]
    if 0x8C016B60 <= v < 0x8C016BB4:
        n += 1
        print('%#x (aligned4=%s): %#x' % (B + o, o % 4 == 0, v))
print('hits', n)
# table dump
o = 0x8C016B60 - B
print('table words @0x8c016b60:', ['%08x' % struct.unpack_from('<I', fr, o + 4 * i)[0] for i in range(16)])
