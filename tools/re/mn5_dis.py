"""mn5_dis.py REL BASE START END : capstone SH-4 listing that resyncs over data and resolves mov.l/mov.w @(d,pc) literals.  offsets are file offsets (hex)."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import capstone as cs
import moneypatch as MP
rel, base, a, b = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16), int(sys.argv[4], 16)
d = MP.read_extracted(rel)
md = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)
o = a
while o < b:
    ins = list(md.disasm(d[o:o + 2], base + o, 1))
    if not ins:
        print('%08x  .word %04x' % (base + o, d[o] | d[o + 1] << 8)); o += 2; continue
    i = ins[0]
    w = d[o] | d[o + 1] << 8
    note = ''
    if (w >> 12) == 0xD:
        t = ((o + 4) & ~3) + (w & 0xFF) * 4
        note = '   ; =%08x' % struct.unpack_from('<I', d, t)[0]
    elif (w >> 12) == 0x9:
        t = o + 4 + (w & 0xFF) * 2
        note = '   ; =%04x (%d)' % (struct.unpack_from('<H', d, t)[0], struct.unpack_from('<h', d, t)[0])
    print('%08x  %s %s%s' % (base + o, i.mnemonic, i.op_str, note))
    o += 2
