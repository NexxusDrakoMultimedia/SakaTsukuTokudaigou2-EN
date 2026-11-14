"""aln: list every PC-relative literal load (mov.l @(d,PC),rn) of an overlay whose literal VALUE equals a given constant.

    python -I -X utf8 tools/re/aln_xref.py OVERLAY 0x8c014de4 [BASE]

Prints load address, literal pool address and the next three instructions' raw words.  Read-only.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def xrefs(d, value, base=0x8c2d0000):
    out = []
    n = len(d) // 2
    for i in range(n):
        w = struct.unpack_from('<H', d, i * 2)[0]
        if w >> 12 == 0xD:
            pc = i * 2
            lit = ((pc + 4) & ~3) + (w & 0xFF) * 4
            if lit + 4 <= len(d) and struct.unpack_from('<I', d, lit)[0] == value:
                out.append((base + pc, base + lit, (w >> 8) & 15))
    return out


if __name__ == '__main__':
    name = sys.argv[1]
    d = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', name + '.BIN'), 'rb').read()
    for a, l, r in xrefs(d, int(sys.argv[2], 16), int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x8c2d0000):
        print('%08x load r%d  pool %08x' % (a, r, l))
