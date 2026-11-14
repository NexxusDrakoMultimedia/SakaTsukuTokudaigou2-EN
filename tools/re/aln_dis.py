"""aln: SH-4 listing with FPU decoding (capstone SHFPU) of an overlay or a RAM-free file range, literal pools annotated.

usage: aln_dis.py OVERLAY START END [BASE]
   OVERLAY = name of an extracted FLOW_PRG overlay (CAP_SLCT), or a path; START / END are hex FILE offsets; BASE defaults to 0x8c2d0000.
   Use the pseudo name 1ST_READ for extracted/1ST_READ.BIN (base 0x8c010000, file offset = address - base).
Read-only helper for docs/layout-issues.md addendum (alignment root cause).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
import capstone as cs

MD = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_SHFPU | cs.CS_MODE_LITTLE_ENDIAN)


def load(spec):
    if os.path.isfile(spec):
        return open(spec, 'rb').read(), 0x8c2d0000
    if spec.upper() in ('1ST_READ', '1ST_READ.BIN'):
        return open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read(), 0x8c010000
    return open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', spec + '.BIN'), 'rb').read(), 0x8c2d0000


def listing(d, a, b, base):
    out = []
    o = a
    while o < b:
        w = struct.unpack_from('<H', d, o)[0]
        i = list(MD.disasm(d[o:o + 2], base + o))
        t = '%s %s' % (i[0].mnemonic, i[0].op_str) if i else '.word %04x' % w
        if w >> 12 == 0xD:
            t += '   ; =%#x' % struct.unpack_from('<I', d, ((o + 4) & ~3) + (w & 0xFF) * 4)[0]
        elif w >> 12 == 9:
            t += '   ; =%#x' % struct.unpack_from('<H', d, o + 4 + (w & 0xFF) * 2)[0]
        out.append('%08x  %04x  %s' % (base + o, w, t))
        o += 2
    return out


if __name__ == '__main__':
    d, base = load(sys.argv[1])
    if len(sys.argv) > 4:
        base = int(sys.argv[4], 16)
    print('\n'.join(listing(d, int(sys.argv[2], 16), int(sys.argv[3], 16), base)))
