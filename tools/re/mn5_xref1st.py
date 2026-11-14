"""mn5_xref1st.py VA...: code sites in 1ST_READ.BIN that load VA from a literal pool (mov.l @(d,pc))."""
import os, sys, struct
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
BASE = 0x8C010000
for a in sys.argv[1:]:
    va = int(a, 16)
    pat = struct.pack('<I', va)
    i = d.find(pat)
    while i >= 0:
        if i % 4 == 0:
            for j in range(max(0, i - 1020), i, 2):
                w = d[j] | d[j + 1] << 8
                if (w >> 12) == 0xD and ((j + 4) & ~3) + (w & 0xFF) * 4 == i:
                    print('%s pool %08x code %08x r%d' % (a, BASE + i, BASE + j, (w >> 8) & 15))
        i = d.find(pat, i + 1)
