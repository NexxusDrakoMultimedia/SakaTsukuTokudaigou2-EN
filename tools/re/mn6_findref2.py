"""mn6_findref2.py REL OFFSET_HEX... : code that loads the address of file offset OFFSET (literal pool word == base + offset) in overlay REL (base from textdb)."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moneypatch as MP      # noqa: E402
import textdb                # noqa: E402

rel = sys.argv[1]
d = MP.read_extracted(rel)
base = textdb.load_image(rel).base
print('base %#x' % base)
for a in sys.argv[2:]:
    va = base + int(a, 16)
    pat = struct.pack('<I', va)
    i = 0
    while True:
        i = d.find(pat, i)
        if i < 0:
            break
        if i % 4 == 0:
            for j in range(max(0, i - 1020), i, 2):
                w = d[j] | d[j + 1] << 8
                if (w >> 12) == 0xD and ((j + 4) & ~3) + (w & 0xFF) * 4 == i:
                    print('%s: pool %#x, loaded at %#x (r%d)' % (a, i, j, (w >> 8) & 15))
        i += 1
