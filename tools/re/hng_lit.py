"""hng: find 4-aligned literal words in an extracted overlay and the instructions that load them.
usage: hng_lit.py OVERLAY HEXVALUE [BASE]   (e.g. EVENT 8c42a4c4)"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import moneypatch as MP
n, v = sys.argv[1], int(sys.argv[2], 16)
base = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x8c2d0000
d = MP.read_extracted('FLOW_PRG/%s.BIN' % n)
pat = struct.pack('<I', v)
i = d.find(pat)
while i >= 0:
    if i % 4 == 0:
        users = [o for o in range(0, len(d) - 1, 2)
                 if (struct.unpack_from('<H', d, o)[0] >> 12) == 0xD and ((o + 4) & ~3) + (struct.unpack_from('<H', d, o)[0] & 0xFF) * 4 == i]
        print('literal at %#x (%#x) loaded by %s' % (i, base + i, [hex(base + u) for u in users]))
    i = d.find(pat, i + 1)
