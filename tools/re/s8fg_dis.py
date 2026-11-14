"""s8fg: SH-4 listing of a file range with literal pool values.
usage: s8fg_dis.py FILE LO HI [BASE=8c2d0000]    (hex)"""
import struct
import sys
import capstone as cs

md = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)
d = open(sys.argv[1], 'rb').read()
lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
base = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x8c2d0000
for o in range(lo, hi, 2):
    w = struct.unpack_from('<H', d, o)[0]
    i = list(md.disasm(d[o:o + 2], base + o))
    t = '%s %s' % (i[0].mnemonic, i[0].op_str) if i else '.word %04x' % w
    x = ''
    if w >> 12 == 0xD:
        x = '   ; =%#x' % struct.unpack_from('<I', d, ((o + 4) & ~3) + (w & 0xFF) * 4)[0]
    elif w >> 12 == 0x9:
        x = '   ; =%#x' % struct.unpack_from('<H', d, o + 4 + (w & 0xFF) * 2)[0]
    print('%06x %08x  %04x  %s%s' % (o, base + o, w, t, x))
