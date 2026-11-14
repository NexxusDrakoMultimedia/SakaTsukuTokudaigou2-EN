"""capstone-based SH-4 disassembler helper (capstone 5.0.7, CS_ARCH_SH). usage: shd.py FILE BASE START END (absolute addrs).
Resyncs on undecodable words (prints .word)."""
import sys, struct, capstone as c
md = c.Cs(c.CS_ARCH_SH, c.CS_MODE_SH4 | c.CS_MODE_LITTLE_ENDIAN)
def one(data, base, a):
    o = a - base
    for i in md.disasm(data[o:o+2], a):
        return i.size, '%s %s' % (i.mnemonic, i.op_str)
    return 2, '.word 0x%04x' % struct.unpack_from('<H', data, o)[0]
def dis(data, base, lo, hi):
    out = []; a = lo
    while a < hi:
        sz, t = one(data, base, a)
        out.append('%08x  %s  %s' % (a, data[a-base:a-base+sz].hex(), t.strip()))
        a += sz
    return out
if __name__ == '__main__':
    f, base, lo, hi = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0), int(sys.argv[4], 0)
    d = open(f, 'rb').read()
    print('\n'.join(dis(d, base, lo, hi)))
