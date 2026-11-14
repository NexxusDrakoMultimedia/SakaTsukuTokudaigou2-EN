"""Disassemble a range of HOMETOWN.BIN (base 0x8c2d0000) with capstone, resolving pc-relative literals.
usage: hnm_dis.py START END [file]"""
import sys, os, re, struct
import capstone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
start = int(sys.argv[1], 16); end = int(sys.argv[2], 16)
path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, 'extracted', 'FLOW_PRG', 'HOMETOWN.BIN')
base = int(os.environ.get('HNM_BASE', '8c2d0000'), 16)
d = open(path, 'rb').read()
md = capstone.Cs(capstone.CS_ARCH_SH, capstone.CS_MODE_SH4 | capstone.CS_MODE_LITTLE_ENDIAN)
off = start
while off < end:
    ins = list(md.disasm(d[off:off + 2], base + off))
    if not ins:
        print('%08x  .word  %04x' % (base + off, struct.unpack_from('<H', d, off)[0]))
        off += 2
        continue
    i = ins[0]
    note = ''
    m = re.match(r'(mov\.[wl]) @\(0x([0-9a-f]+), pc\), r(\d+)', i.mnemonic + ' ' + i.op_str)
    if m:
        disp = int(m.group(2), 16)
        a = (off if False else off)
        if m.group(1) == 'mov.l':
            ea = ((base + off) & ~3) + 4 + disp * 1 if False else None
        # capstone gives disp already scaled? compute both
        for sc in (1,):
            pass
    print('%08x  %s\t%s' % (base + off, i.mnemonic, i.op_str))
    off += 2
