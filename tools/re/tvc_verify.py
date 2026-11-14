"""tvc_verify.py DUMPED_TV_EVENT.BIN : decode the patched card capital routine and show the strings its literals point to."""
import struct, sys
import capstone
d = open(sys.argv[1], 'rb').read()
base = 0x8c2d0000
md = capstone.Cs(capstone.CS_ARCH_SH, capstone.CS_MODE_SH4 | capstone.CS_MODE_LITTLE_ENDIAN)
for o in range(0xed0, 0xf14, 2):
    i = list(md.disasm(d[o:o + 2], base + o))
    print('%x %s %s' % (o, i[0].mnemonic, i[0].op_str) if i else '%x ?' % o)
for lo in (0xf1c, 0xf24, 0xf2c):
    v = struct.unpack_from('<I', d, lo)[0]
    print('lit %x = %08x' % (lo, v))
    if v - base < len(d) and lo != 0xf1c and lo != 0xf2c:
        e = d.index(b'\0', v - base)
        print('   string:', d[v - base:e].decode('cp932'))
