"""List ASCII strings (>=5 chars) in 1ST_READ.BIN within an address range; optional substring filter.
usage: strs.py lo hi [substr...]"""
import sys, os, re
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
data = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
BASE = 0x8c010000
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
subs = [s.lower() for s in sys.argv[3:]]
for m in re.finditer(rb'[\x20-\x7e]{5,}', data[lo - BASE:hi - BASE]):
    t = m.group().decode()
    if subs and not any(s in t.lower() for s in subs):
        continue
    print('%08x %s' % (lo + m.start(), t))
