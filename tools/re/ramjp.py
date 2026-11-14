"""ramjp.py DUMP [MINCH] : list NUL-bounded Japanese runs still present in a RAM dump (base 0x8C000000),
with the address, and whether the run is also present (as exact bytes) in any file of extracted/FLOW_PRG,
1ST_READ.BIN, ATFIRST/*.BIN (so it is a copy of a known untranslated image string)."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = open(sys.argv[1], 'rb').read()
minch = int(sys.argv[2]) if len(sys.argv) > 2 else 2
DB = rb'[\x81-\x84\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]'
pat = re.compile(rb'(?:' + DB + rb'|[\x20-\x7e]|[\xa1-\xdf])+')
out = []
for m in pat.finditer(d):
    b = m.group()
    try:
        s = b.decode('cp932')
    except Exception:
        continue
    nj = sum(1 for c in s if ord(c) > 0x7f)
    if nj < minch:
        continue
    o = m.start()
    pre = d[o - 1] if o else 0
    post = d[m.end()] if m.end() < len(d) else 0
    out.append((o, s, pre, post))
for o, s, pre, post in out:
    print('%#010x %02x|%02x %s' % (0x8C000000 + o, pre, post, s))
