"""hrd: peek into a 16 MB main RAM dump (base 0x8c000000).

usage: hrd_ram.py DUMP w ADDR [N]          N 32-bit words at ADDR (hex)
       hrd_ram.py DUMP b ADDR [N]          N bytes hex + ascii
       hrd_ram.py DUMP find TEXT           every occurrence of an ASCII string (address, and whether 1ST_READ.BIN holds it there)
       hrd_ram.py DUMP findw HEXWORD [LO HI]   every 4-aligned occurrence of a 32-bit word
       hrd_ram.py DUMP dis ADDR END        SH-4 listing of RAM
       hrd_ram.py DUMP slots               the 12 overlay slot structs (0x8c228384, 0x60 bytes each)
Read-only.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BASE = 0x8c000000


def main(argv):
    ram = open(argv[1], 'rb').read()
    cmd = argv[2]
    if cmd == 'w':
        a = int(argv[3], 16)
        n = int(argv[4], 0) if len(argv) > 4 else 8
        for i in range(n):
            v = struct.unpack_from('<I', ram, a - BASE + 4 * i)[0]
            print('%08x: %08x' % (a + 4 * i, v))
    elif cmd == 'b':
        a = int(argv[3], 16)
        n = int(argv[4], 0) if len(argv) > 4 else 64
        for i in range(0, n, 16):
            blk = ram[a - BASE + i:a - BASE + i + 16]
            print('%08x: %-48s %s' % (a + i, blk.hex(' '), ''.join(chr(c) if 32 <= c < 127 else '.' for c in blk)))
    elif cmd == 'find':
        pat = argv[3].encode('cp932')
        first = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
        i = ram.find(pat)
        while i >= 0:
            fo = i - 0x10000
            infile = 0 <= fo < len(first) and first[fo:fo + len(pat)] == pat
            ctx = ram[max(0, i - 16):i + len(pat) + 48]
            print('%08x %s  %r' % (BASE + i, '(1ST_READ image)' if infile else '(NOT in 1ST_READ at this address)', ctx))
            i = ram.find(pat, i + 1)
    elif cmd == 'findw':
        pat = struct.pack('<I', int(argv[3], 16))
        lo = int(argv[4], 16) - BASE if len(argv) > 4 else 0
        hi = int(argv[5], 16) - BASE if len(argv) > 5 else len(ram)
        i = ram.find(pat, lo)
        n = 0
        while 0 <= i < hi:
            if i % 4 == 0:
                print('%08x' % (BASE + i))
                n += 1
                if n > 200:
                    print('...')
                    break
            i = ram.find(pat, i + 1)
    elif cmd == 'dis':
        import capstone as cs
        md = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)
        a, b = int(argv[3], 16), int(argv[4], 16)
        o = a - BASE
        while o < b - BASE:
            w = struct.unpack_from('<H', ram, o)[0]
            i = list(md.disasm(ram[o:o + 2], BASE + o))
            t = '%s %s' % (i[0].mnemonic, i[0].op_str) if i else '.word %04x' % w
            if w >> 12 == 0xD:
                t += '   ; =%#x' % struct.unpack_from('<I', ram, ((o + 4) & ~3) + (w & 0xFF) * 4)[0]
            elif w >> 12 == 9:
                t += '   ; =%#x' % struct.unpack_from('<H', ram, o + 4 + (w & 0xFF) * 2)[0]
            print('%08x  %04x  %s' % (BASE + o, w, t))
            o += 2
    elif cmd == 'slots':
        arr = struct.unpack_from('<I', ram, 0x8c230804 - BASE)[0]
        print('slot array at %#x' % arr)
        for s in range(12):
            ws = struct.unpack_from('<24I', ram, arr - BASE + s * 0x60)
            print('slot %2d: %s' % (s, ' '.join('%08x' % w for w in ws)))


if __name__ == '__main__':
    main(sys.argv)
