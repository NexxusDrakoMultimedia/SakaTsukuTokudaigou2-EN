"""s7p_xref - find PC-relative literal loads (mov.l/mov.w @(disp,PC)) that reference a string / address of an overlay.
usage: s7p_xref.py OVERLAY FILEOFFSET_OF_STRING [BASE]   -> prints each load site VA and the file offset (use aln_dis.py to list)"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
name = sys.argv[1]
off = int(sys.argv[2], 0)
base = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x8c2d0000
d = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', name + '.BIN'), 'rb').read()
target = base + off
lits = [i for i in range(0, len(d) - 3, 4) if struct.unpack_from('<I', d, i)[0] == target]
print('literal words holding %#x: %s' % (target, [hex(x) for x in lits]))
for L in lits:
    for i in range(0, len(d) - 1, 2):
        w = struct.unpack_from('<H', d, i)[0]
        if (w & 0xF000) == 0xD000:
            ea = (i & ~3) + 4 + 4 * (w & 0xFF)
            if ea == L:
                print('  mov.l load at file %#x (va %#x) -> r%d' % (i, base + i, (w >> 8) & 15))
