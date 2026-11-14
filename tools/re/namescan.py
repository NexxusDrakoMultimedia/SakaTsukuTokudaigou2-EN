"""namescan.py FILE [LO HI] : list 'Family Given' name candidates (cp932, 1 space, NUL after) with offsets, deltas."""
import re
import sys

d = open(sys.argv[1], 'rb').read()
lo = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0
hi = int(sys.argv[3], 16) if len(sys.argv) > 3 else len(d)
CH = rb'(?:[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc]|[\xa1-\xdf])'
pat = re.compile(rb'(?<![\x81-\x9f\xe0-\xfc])(' + CH + rb'{1,6} ' + CH + rb'{1,8})\x00')
prev = None
for m in pat.finditer(d, lo, hi):
    o = m.start(1)
    try:
        t = m.group(1).decode('cp932')
    except Exception:
        continue
    print('%06x  d=%-6s %s' % (o, '' if prev is None else o - prev, t))
    prev = o
