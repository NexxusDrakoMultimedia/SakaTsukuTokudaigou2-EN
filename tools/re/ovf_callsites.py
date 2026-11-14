"""ovf: every call site of the club-name composer in the 20 overlays: what is passed as the output pointer (5th argument, pushed last
before the jsr).  Backward slice of the pushed register (<= 14 instructions), pc-relative halfword literals resolved.
usage: ovf_callsites.py [OVERLAY ...]"""
import os, re, struct, sys
import capstone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import layoutpatch as LP
md = capstone.Cs(capstone.CS_ARCH_SH, capstone.CS_MODE_SH4 | capstone.CS_MODE_LITTLE_ENDIAN)


def ins(d, o):
    w = struct.unpack_from('<H', d, o)[0]
    i = list(md.disasm(d[o:o + 2], o))
    t = '%s %s' % (i[0].mnemonic, i[0].op_str) if i else '.word %04x' % w
    if w >> 12 == 9 and o + 4 + (w & 0xFF) * 2 + 2 <= len(d):
        t += '  ; =%#x' % struct.unpack_from('<H', d, o + 4 + (w & 0xFF) * 2)[0]
    if w >> 12 == 0xD:
        t += '  ; =%#x' % struct.unpack_from('<I', d, ((o + 4) & ~3) + (w & 0xFF) * 4)[0]
    return w, t


names = sys.argv[1:] or LP.CLUB_OVERLAYS
for n in names:
    d = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', n + '.BIN'), 'rb').read()
    a = d.find(LP.CLUB_SIG_A)
    comp_off = a + LP.COMP_DELTA
    fmt_off = d.find(b'%s%s\0\0\0\0Ille')
    base = struct.unpack_from('<I', d, a + LP.CLUB_FMT_DELTA)[0] - fmt_off
    w = struct.pack('<I', base + comp_off)
    lits = [i for i in range(0, len(d) - 3, 4) if d[i:i + 4] == w]
    bsr = []
    for o in range(0, len(d) - 1, 2):
        op = struct.unpack_from('<H', d, o)[0]
        if op >> 12 == 0xB:
            disp = op & 0xFFF
            disp -= 0x1000 if disp & 0x800 else 0
            if o + 4 + disp * 2 == comp_off:
                bsr.append(o)
    uses = []
    for o in range(0, len(d) - 1, 2):
        wd = struct.unpack_from('<H', d, o)[0]
        if wd >> 12 == 0xD and ((o + 4) & ~3) + (wd & 0xFF) * 4 in lits:
            uses.append(o)
    print('== %s: composer %#x, literal(s) %s, loads at %s, bsr at %s' % (n, comp_off, [hex(x) for x in lits], [hex(x) for x in uses], [hex(x) for x in bsr]))
    for u in uses + bsr:
        # find the jsr/bsr and the last push before it
        lo = max(0, u - 0x28)
        lines = [(o,) + ins(d, o) for o in range(lo, u + 14, 2)]
        pushes = [(o, t) for o, wd, t in lines if o < u + 12 and (wd & 0xFF0F) == 0x2F06 + 0 and False]
        # push = mov.l Rm,@-r15 : 0x2fm6
        pushes = [(o, wd, t) for o, wd, t in lines if (wd & 0xF00F) == 0x2006 and ((wd >> 8) & 15) == 15]
        before = [p for p in pushes if p[0] < u + 12]
        print('  site %#x:' % u)
        if before:
            po, pw, pt = before[-1] if (not bsr or u in uses) else before[-1]
            reg = (pw >> 4) & 15
            print('    last push before the call: %#x %s (r%d); definitions:' % (po, pt, reg))
            for o, wd, t in lines:
                if o < po + 2 and o >= po - 0x1c and re.search(r',r%d\b' % reg, t):
                    print('       %#x  %s' % (o, t))
