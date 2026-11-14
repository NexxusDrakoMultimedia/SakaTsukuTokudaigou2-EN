"""hng: word-by-word SH-4 listing of an extracted overlay range with literal annotations.
usage: hng_dis.py FILE-or-OVERLAY START END [BASE]   (hex file offsets; overlay name like EVENT -> extracted/FLOW_PRG/EVENT.BIN, or a path to a dumped file)"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, HERE)
import capstone as cs
md = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)


def load(spec):
    if os.path.isfile(spec):
        return open(spec, 'rb').read()
    return open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', spec + '.BIN'), 'rb').read()


def listing(d, a, b, base=0x8c2d0000):
    out = []
    o = a
    while o < b:
        w = struct.unpack_from('<H', d, o)[0]
        i = list(md.disasm(d[o:o + 2], base + o))
        t = '%s %s' % (i[0].mnemonic, i[0].op_str) if i else '.word %04x' % w
        if w >> 12 == 0xD:
            t += '   ; =%#x' % struct.unpack_from('<I', d, ((o + 4) & ~3) + (w & 0xFF) * 4)[0]
        elif w >> 12 == 9:
            t += '   ; =%#x' % struct.unpack_from('<H', d, o + 4 + (w & 0xFF) * 2)[0]
        out.append('%08x  %04x  %s' % (base + o, w, t))
        o += 2
    return out


if __name__ == '__main__':
    d = load(sys.argv[1])
    base = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x8c2d0000
    print('\n'.join(listing(d, int(sys.argv[2], 16), int(sys.argv[3], 16), base)))
