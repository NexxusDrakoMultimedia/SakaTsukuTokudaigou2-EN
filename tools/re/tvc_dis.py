"""tvc_dis.py FILE BASEADDR START END : capstone SH4 disassembly of file offsets START..END (hex); undecodable words shown as .word."""
import sys
import capstone
f, base, s, e = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16), int(sys.argv[4], 16)
d = open(f, 'rb').read()
md = capstone.Cs(capstone.CS_ARCH_SH, capstone.CS_MODE_SH4 | capstone.CS_MODE_LITTLE_ENDIAN | capstone.CS_MODE_SHFPU)
o = s
while o < e:
    got = list(md.disasm(d[o:o + 2], base + o))
    if got:
        i = got[0]
        print('%08x  %s %s' % (i.address, i.mnemonic, i.op_str))
    else:
        print('%08x  .word %04x   ; long %08x' % (base + o, int.from_bytes(d[o:o+2], 'little'), int.from_bytes(d[o:o+4], 'little') if o + 4 <= len(d) else 0))
    o += 2
