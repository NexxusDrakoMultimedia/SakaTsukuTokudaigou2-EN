"""mn5_findref.py REL VA [VA...]: find 32-bit literal-pool words equal to VA in an extracted overlay (base 0x8c2d0000 for FLOW_PRG) and list the code that loads them."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moneypatch as MP
rel = sys.argv[1]
base = 0x8C2D0000
d = MP.read_extracted(rel)
for a in sys.argv[2:]:
    va = int(a, 16)
    pat = struct.pack('<I', va)
    i = 0
    while True:
        i = d.find(pat, i)
        if i < 0:
            break
        if i % 4 == 0:
            # find mov.l @(disp,pc),rn  (0xD n dd) that reach this word
            for j in range(max(0, i - 1020), i, 2):
                w = d[j] | d[j + 1] << 8
                if (w >> 12) == 0xD:
                    disp = w & 0xFF
                    tgt = ((j + 4) & ~3) + disp * 4
                    if tgt == i:
                        print('%s ref %08x: code at %08x (r%d)' % (a, base + i, base + j, (w >> 8) & 15))
        i += 1
