"""Read-only: find a byte pattern in files under extracted/ (skips BCAST.BIN unless --all). usage: dxp_find.py PATTERN [--all]"""
import os, sys
pat = sys.argv[1].encode()
allf = '--all' in sys.argv
for root, ds, fs in os.walk('extracted'):
    for f in fs:
        p = os.path.join(root, f)
        if f == 'BCAST.BIN' and not allf: continue
        if os.path.getsize(p) > 300_000_000: continue
        d = open(p, 'rb').read()
        i = d.find(pat)
        if i >= 0: print(p, hex(i), d.count(pat))
