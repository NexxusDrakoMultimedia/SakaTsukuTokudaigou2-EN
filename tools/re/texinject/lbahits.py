"""Show context of words that equal a file's start LBA inside the SH-4 images, and how common that is.

    python -I -X utf8 tools/re/texinject/lbahits.py [IMAGE ...]   (default: all images; prints a per-file summary)
For each hit prints neighbouring u32 words (-4..+8 words)."""
import os
import sys
import struct
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
ext = os.path.join(ROOT, 'extracted')
files = {}
for line in open(os.path.join(ext, '_filelist.tsv'), encoding='utf8'):
    p = line.rstrip('\r\n').split('\t')
    if len(p) >= 3 and p[1].isdigit():
        files[int(p[1])] = (p[0], int(p[2]))
imgs = sys.argv[1:]
if not imgs:
    imgs = ['1ST_READ.BIN', '2_DP.BIN']
    for sub in ('FLOW_PRG', 'ATFIRST'):
        for fn in sorted(os.listdir(os.path.join(ext, sub))):
            if fn.upper().endswith('.BIN'):
                imgs.append(sub + '/' + fn)
total = collections.Counter()
for im in imgs:
    d = open(os.path.join(ext, *im.split('/')), 'rb').read()
    n = len(d) // 4
    w = struct.unpack('<%dI' % n, d[:n * 4])
    hits = [k for k in range(n) if w[k] in files and w[k] > 56800]
    if not hits:
        continue
    total[im] = len(hits)
    if len(sys.argv) > 1:
        for k in hits:
            print(im, hex(k * 4), files[w[k]], [hex(x) for x in w[max(0, k - 4):k + 8]])
print({k: v for k, v in total.items()})
print('distinct images with LBA-valued words:', len(total))
