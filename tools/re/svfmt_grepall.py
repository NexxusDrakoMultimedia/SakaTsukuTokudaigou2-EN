"""svfmt_grepall.py REGEX : ASCII strings matching REGEX in all extracted/FLOW_PRG/*.BIN, 1ST_READ.BIN (count per file, first 3 hits)."""
import sys, re, os, glob
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rx = re.compile(sys.argv[1])
files = [os.path.join(ROOT, 'extracted', '1ST_READ.BIN')] + sorted(glob.glob(os.path.join(ROOT, 'extracted', 'FLOW_PRG', '*.BIN')))
for f in files:
    d = open(f, 'rb').read(); hits = []
    for m in re.finditer(rb'[\x20-\x7e]{4,}', d):
        s = m.group().decode()
        if rx.search(s): hits.append('%x:%s' % (m.start(), s))
    if hits: print(os.path.basename(f), len(hits), hits[:3])
