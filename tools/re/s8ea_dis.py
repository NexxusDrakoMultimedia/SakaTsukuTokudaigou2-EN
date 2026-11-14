"""s8ea: side-by-side SH-4 listing of A (hsk_full1) vs B (prop10c) dumps over every differing range in [LO, HI).

usage: s8ea_dis.py NAME LO HI [BASE] [PAD]     (NAME like FLOW_PRG__EVENT.BIN, dumps in build/s8ea/dump; hex offsets)
Prints, per differing range merged within 16 bytes, the old and new instructions (literal pool words shown as =value for mov.l @(disp,pc)).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
import capstone as cs

md = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)


def dis(d, a, b, base):
    out = []
    for o in range(a, b, 2):
        w = struct.unpack_from('<H', d, o)[0]
        i = list(md.disasm(d[o:o + 2], base + o))
        t = '%s %s' % (i[0].mnemonic, i[0].op_str) if i else '.word %04x' % w
        if w >> 12 == 0xD:
            t += '   ; =%#x' % struct.unpack_from('<I', d, ((o + 4) & ~3) + (w & 0xFF) * 4)[0]
        out.append('%08x  %04x  %s' % (base + o, w, t))
    return out


def main(argv):
    name = argv[1]
    lo, hi = int(argv[2], 16), int(argv[3], 16)
    base = int(argv[4], 16) if len(argv) > 4 else 0x8c2d0000
    pad = int(argv[5], 16) if len(argv) > 5 else 8
    D = os.path.join(ROOT, 'build', 's8ea', 'dump')
    a = open(os.path.join(D, 'A_' + name), 'rb').read()
    b = open(os.path.join(D, 'B_' + name), 'rb').read()
    hi = min(hi, len(a), len(b))
    rg = []
    for i in range(lo, hi):
        if a[i] != b[i]:
            if rg and i - rg[-1][1] <= 16:
                rg[-1][1] = i + 1
            else:
                rg.append([i, i + 1])
    for s, e in rg:
        s0 = max(lo, (s & ~1) - pad)
        e0 = min(hi, ((e + 1) & ~1) + pad)
        print('=== %#x-%#x (%d bytes)  load %#x' % (s, e, e - s, base + s))
        la, lb = dis(a, s0, e0, base), dis(b, s0, e0, base)
        for x, y in zip(la, lb):
            print('%s %-50s | %s' % ('*' if x != y else ' ', x, y[10:]))


if __name__ == '__main__':
    main(sys.argv)
