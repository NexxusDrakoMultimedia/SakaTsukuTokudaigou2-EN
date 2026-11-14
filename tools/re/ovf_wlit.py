"""ovf: find mov.w @(disp,pc) loads of a 16-bit literal and show context.  usage: ovf_wlit.py OVERLAY HEXVAL [before after]"""
import os, sys, struct
import capstone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
name = sys.argv[1]; val = int(sys.argv[2], 16)
before = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x20
after = int(sys.argv[4], 0) if len(sys.argv) > 4 else 0x30
d = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', name + '.BIN'), 'rb').read()
md = capstone.Cs(capstone.CS_ARCH_SH, capstone.CS_MODE_SH4 | capstone.CS_MODE_LITTLE_ENDIAN)
op = lambda o: struct.unpack_from('<H', d, o)[0]
uses = [o for o in range(0, len(d) - 1, 2) if op(o) >> 12 == 9 and o + 6 + (op(o) & 0xFF) * 2 <= len(d) and struct.unpack_from('<H', d, o + 4 + (op(o) & 0xFF) * 2)[0] == val]
print(name, hex(val), 'uses', [hex(u) for u in uses])
for u in uses:
    print('--- %#x' % u)
    for o in range(max(0, u - before), u + after, 2):
        ins = list(md.disasm(d[o:o + 2], o))
        t = ('%s\t%s' % (ins[0].mnemonic, ins[0].op_str)) if ins else '.word %04x' % op(o)
        if op(o) >> 12 == 0xD:
            t += '    ; =%08x' % struct.unpack_from('<I', d, ((o + 4) & ~3) + (op(o) & 0xFF) * 4)[0]
        elif op(o) >> 12 == 9:
            t += '    ; =%04x' % struct.unpack_from('<H', d, o + 4 + (op(o) & 0xFF) * 2)[0]
        print('%06x  %s%s' % (o, t, '   <<<' if o == u else ''))
