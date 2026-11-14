"""mn5_uvfind4.py: single float / u16 values of the header bar unit cells (oku 462,266 ; man 66,141) in 1ST_READ + overlays: count per file."""
import os, sys, struct, glob
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
files = [os.path.join(ROOT, 'extracted', '1ST_READ.BIN')] + sorted(glob.glob(os.path.join(ROOT, 'extracted', 'FLOW_PRG', '*.BIN')))
vals = {'462/512': 462 / 512, '266/512': 266 / 512, '66/512': 66 / 512, '141/512': 141 / 512, '492/512': 492 / 512, '298/512': 298 / 512}
for p in files:
    d = open(p, 'rb').read()
    hits = {}
    for n, v in vals.items():
        pat = struct.pack('<f', v)
        i = d.find(pat)
        c = []
        while i >= 0 and len(c) < 6:
            if i % 4 == 0:
                c.append(i)
            i = d.find(pat, i + 1)
        if c:
            hits[n] = c
    if len(hits) >= 3:
        print(os.path.relpath(p, ROOT), {k: [hex(x) for x in v] for k, v in hits.items()})
