"""svfmt_vslot.py SLOT_HEX : count `mov.w #SLOT` (pc-relative 16-bit literal == SLOT) sites per overlay and in 1ST_READ (vtable slot of 0x8c159000)."""
import sys, os, struct, glob
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
slot = int(sys.argv[1], 16); tot = 0
files = [os.path.join(ROOT, 'extracted', '1ST_READ.BIN')] + sorted(glob.glob(os.path.join(ROOT, 'extracted', 'FLOW_PRG', '*.BIN')))
for f in files:
    d = open(f, 'rb').read(); n = len(d); hits = []
    for off in range(0, n - 1, 2):
        w = struct.unpack_from('<H', d, off)[0]
        if (w >> 12) != 0x9: continue
        eo = off + 4 + (w & 0xFF) * 2
        if eo + 2 <= n and struct.unpack_from('<H', d, eo)[0] == slot: hits.append(off)
    if hits: tot += len(hits); print(os.path.basename(f), len(hits), ['%x' % h for h in hits[:6]])
print('total', tot)
