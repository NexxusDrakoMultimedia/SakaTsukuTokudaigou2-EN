"""mn5_div10k.py: find literal-pool words 10000 (0x2710) and 100000000 in 1ST_READ / overlays, and the code loading them (candidates for header money digit code)."""
import os, sys, struct, glob
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
files = [os.path.join(ROOT, 'extracted', '1ST_READ.BIN')] + sorted(glob.glob(os.path.join(ROOT, 'extracted', 'FLOW_PRG', '*.BIN')))
want = {10000: 'x10000', 100000000: 'x1e8'}
for p in files:
    d = open(p, 'rb').read()
    n = 0
    for k in range(0, len(d) - 3, 4):
        v = struct.unpack_from('<I', d, k)[0]
        if v in want:
            for j in range(max(0, k - 1020), k, 2):
                w = d[j] | d[j + 1] << 8
                if (w >> 12) == 0xD and ((j + 4) & ~3) + (w & 0xFF) * 4 == k:
                    print('%s %s pool %x code %x' % (os.path.relpath(p, ROOT), want[v], k, j)); n += 1
        elif False:
            pass
    # also mov.w #10000 pool (u16)
