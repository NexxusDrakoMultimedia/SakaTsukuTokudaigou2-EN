"""ram_resident.py DUMP : which overlays / images are resident in a RAM dump (base 0x8C000000, 16 MB).

For every image of tools/textdb.list_sources() the code area (the first 64 KiB, English text patches live in the string
pools further back) is compared with RAM at the image's load address and at every other 64 KiB aligned address;
reports the fraction of equal 32-byte blocks.  Evidence for 'which overlay was running' (docs/uncovered-text.md)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import textdb as T

ram = open(sys.argv[1], 'rb').read()
BLK = 32
for src, _ in T.list_sources():
    try:
        img = T.load_image(src)
    except ValueError:
        continue
    d = img.data
    n = min(len(d), 0x10000)
    best = (0.0, 0)
    for base in range(0x8C000000, 0x8D000000 - n, 0x10000):
        o = base - 0x8C000000
        eq = tot = 0
        for k in range(0, n, BLK * 8):
            tot += 1
            if ram[o + k:o + k + BLK] == d[k:k + BLK]:
                eq += 1
        if tot and eq / tot > best[0]:
            best = (eq / tot, base)
    if best[0] > 0.3:
        print('%-26s base(file) %#x  best match at %#x  %.0f%% of sampled blocks equal' % (src, img.base, best[1], best[0] * 100))
