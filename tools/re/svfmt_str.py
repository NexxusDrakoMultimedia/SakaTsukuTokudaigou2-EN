"""svfmt_str.py OVERLAY|1ST_READ [regex] : ASCII strings (>=4) with virtual addresses."""
import sys, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svfmt_xref import load
d, base = load(sys.argv[1]); rx = re.compile(sys.argv[2]) if len(sys.argv) > 2 else None
for m in re.finditer(rb'[\x20-\x7e]{4,}', d):
    s = m.group().decode()
    if rx is None or rx.search(s):
        print('%08x %s' % (base + m.start(), s))
