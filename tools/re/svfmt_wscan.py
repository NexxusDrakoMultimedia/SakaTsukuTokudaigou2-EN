"""svfmt_wscan.py LO HI : aligned 32-bit words in [LO,HI] (hex) in 1ST_READ and every FLOW_PRG/ATFIRST overlay (static address references)."""
import sys, os, struct, glob
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
lo = int(sys.argv[1], 16); hi = int(sys.argv[2], 16)
files = [os.path.join(ROOT, 'extracted', '1ST_READ.BIN')] + sorted(glob.glob(os.path.join(ROOT, 'extracted', 'FLOW_PRG', '*.BIN')))
tot = 0
for f in files:
    d = open(f, 'rb').read(); hits = []
    for off in range(0, len(d) - 3, 4):
        v = struct.unpack_from('<I', d, off)[0]
        if lo <= v <= hi: hits.append((off, v))
    if hits: tot += len(hits); print(os.path.basename(f), len(hits), ['%x:%x' % h for h in hits[:6]])
print('total', tot)
