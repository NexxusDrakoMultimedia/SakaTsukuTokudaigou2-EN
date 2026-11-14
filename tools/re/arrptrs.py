"""arrptrs.py SOURCE HEXOFF [SPAN] : aligned words that point within SPAN bytes (default 0x80) before / at HEXOFF
(start of a record array found by textfmt_recarray) = the probable base pointer of the table; prints the word offsets
and which `mov.l @(disp,PC)` instructions load them."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import textdb as T

src, off = sys.argv[1], int(sys.argv[2], 16)
span = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x80
img = T.load_image(src)
d, base = img.data, img.base
n = len(d) // 4
words = struct.unpack('<%dI' % n, d[:n * 4])
for i, w in enumerate(words):
    if base + off - span <= w <= base + off:
        L = i * 4
        users = []
        for A in range(max(0, L - 1024 - 8), L, 2):
            x = d[A] | d[A + 1] << 8
            if x >> 12 == 0xD and (A & ~3) + 4 + 4 * (x & 0xFF) == L:
                users.append(A)
        print('word @%#x -> %#x (array start - %#x)  loaded at %s' % (L, w, base + off - w, [hex(base + u) for u in users]))
