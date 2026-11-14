"""hwprobe.py SOURCE HEXOFF : base, pointer words to a string and neighbours (textdb.load_image)."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import textdb as T

src = sys.argv[1]
off = int(sys.argv[2], 16)
img = T.load_image(src)
d = img.data
print('base %#x size %#x' % (img.base, len(d)))
tgt = img.base + off
n = len(d) // 4
w = struct.unpack('<%dI' % n, d[:n * 4])
hits = [i * 4 for i, x in enumerate(w) if x == tgt]
print('words == %#x at' % tgt, [hex(h) for h in hits])
for h in hits:
    print(' neighbours at', hex(h), [hex(x) for x in w[h // 4 - 3:h // 4 + 4]])
