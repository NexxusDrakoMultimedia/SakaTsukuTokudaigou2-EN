"""ovmem: hexdump RAM at an absolute address from a dump in build/emu (read-only). usage: ovmem_gs.py DUMP ADDR_HEX LEN_HEX"""
import sys
dump, a, ln = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
f = open(dump, 'rb'); f.seek(a - 0x8c000000); d = f.read(ln)
for i in range(0, len(d), 16):
    ch = ''.join(chr(c) if 32 <= c < 127 else '.' for c in d[i:i+16])
    print('%08x ' % (a + i), d[i:i+16].hex(' '), ch)
