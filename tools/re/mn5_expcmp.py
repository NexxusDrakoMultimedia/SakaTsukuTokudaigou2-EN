"""mn5_expcmp.py: locate the tsString expander in every overlay (through the money function's `%D` pool literal) and compare its code bytes."""
import os, sys, struct, hashlib
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moneypatch as MP
C = Counter(); where = {}
for rel in MP.overlay_paths():
    d = MP.read_extracted(rel)
    for s in MP.find_sites(d, rel):
        if s['variant'] != 'A':
            continue
        r = MP.find_d_literal(d, s['off'])
        if not r:
            continue
        dlit, base = r
        # expander start: the D literal is pool word 6 (0x2d8); start = dlit - 0x2d8 + 0x128 - ... use MEETING facts: start = dlit - 0x1b0
        start = dlit - 0x1b0
        code = d[start:start + 0x196]        # up to 0x2be region end exclusive 0x2be-0x128=0x196
        h = hashlib.sha1(code).hexdigest()[:10]
        C[h] += 1
        where.setdefault(h, []).append((rel, start, base))
for h, n in C.most_common():
    print(h, n, where[h][0])
print(len(C), 'distinct')
