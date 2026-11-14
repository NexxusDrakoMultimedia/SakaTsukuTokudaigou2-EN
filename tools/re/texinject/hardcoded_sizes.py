"""Does any code/data image on the disc hard-code the size, sector count or LBA of a file?

    python -I -X utf8 tools/re/texinject/hardcoded_sizes.py

Searches every 4-byte aligned little-endian word of 1ST_READ.BIN, 2_DP.BIN and FLOW_PRG/*.BIN, ATFIRST/*.BIN (SH-4
images) for values equal to the byte size, the sector count (ceil(size/2048)) or the start LBA of each file in
extracted/_filelist.tsv.  Only files >= 4096 bytes are considered (smaller values collide with ordinary constants)."""
import os
import sys
import struct
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
ext = os.path.join(ROOT, 'extracted')

files = []
for line in open(os.path.join(ext, '_filelist.tsv'), encoding='utf8'):
    p = line.rstrip('\r\n').split('\t')
    if len(p) >= 3 and p[1].isdigit():
        files.append((p[0], int(p[1]), int(p[2])))
by_size = collections.defaultdict(list)
by_sect = collections.defaultdict(list)
by_lba = collections.defaultdict(list)
for name, lba, size in files:
    if size < 4096:
        continue
    by_size[size].append(name)
    by_sect[(size + 2047) // 2048].append(name)
    by_lba[lba].append(name)

images = ['1ST_READ.BIN', '2_DP.BIN']
for sub in ('FLOW_PRG', 'ATFIRST'):
    for fn in sorted(os.listdir(os.path.join(ext, sub))):
        if fn.upper().endswith('.BIN'):
            images.append(sub + '/' + fn)
hits = collections.Counter()
detail = collections.defaultdict(list)
for im in images:
    d = open(os.path.join(ext, *im.split('/')), 'rb').read()
    n = len(d) // 4
    words = struct.unpack('<%dI' % n, d[:n * 4])
    for k, w in enumerate(words):
        if w in by_size:
            hits['size'] += 1
            detail['size'].append((im, k * 4, w, by_size[w][:3]))
        if w in by_lba and w > 50000:
            hits['lba'] += 1
            detail['lba'].append((im, k * 4, w, by_lba[w][:3]))
        if w in by_sect and w > 2000:
            hits['sectors'] += 1
            detail['sectors'].append((im, k * 4, w, by_sect[w][:3]))
print('images scanned', len(images), 'files considered', sum(len(v) for v in by_size.values()))
print(dict(hits))
for k in ('size', 'lba', 'sectors'):
    for r in detail[k][:12]:
        print(k, r)
