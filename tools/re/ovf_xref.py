"""ovf: find the mov.l @(disp,pc) loads of a literal and disassemble around each use.
usage: ovf_xref.py OVERLAY LITERAL_FILE_OFFSET [before after]"""
import os, sys, struct
import capstone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
name = sys.argv[1]; lit = int(sys.argv[2], 16)
before = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x30
after = int(sys.argv[4], 0) if len(sys.argv) > 4 else 0x40
d = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', name + '.BIN'), 'rb').read()
md = capstone.Cs(capstone.CS_ARCH_SH, capstone.CS_MODE_SH4 | capstone.CS_MODE_LITTLE_ENDIAN)
BASE = 0x10000


def op(o):
    return struct.unpack_from('<H', d, o)[0]


uses = []
for o in range(0, len(d) - 1, 2):
    w = op(o)
    if w >> 12 == 0xD:
        ea = ((o + 4) & ~3) + (w & 0xFF) * 4
        if ea == lit:
            uses.append(o)
print(name, 'literal %#x used by' % lit, [hex(u) for u in uses])
for u in uses:
    print('--- use at %#x' % u)
    for o in range(max(0, u - before), u + after, 2):
        ins = list(md.disasm(d[o:o + 2], o))
        t = ('%s\t%s' % (ins[0].mnemonic, ins[0].op_str)) if ins else '.word %04x' % op(o)
        if op(o) >> 12 == 0xD:
            ea = ((o + 4) & ~3) + (op(o) & 0xFF) * 4
            t += '    ; =%08x' % struct.unpack_from('<I', d, ea)[0]
        elif op(o) >> 12 == 9:
            ea = o + 4 + (op(o) & 0xFF) * 2
            t += '    ; =%04x' % struct.unpack_from('<H', d, ea)[0]
        print('%06x  %s%s' % (o, t, '   <<<' if o == u else ''))
