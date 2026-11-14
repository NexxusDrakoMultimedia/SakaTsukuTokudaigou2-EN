"""s8fg: show the pointer words of the 'Damui' hwptr records (array base) in orig / hsk_full1 / s8e_nofix / prop10c, and the text at the new target.
usage: s8fg_ptrchk.py   (reads build/s8fg extracts; extract first with s8fg_extract.py for the listed files)"""
import os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D
DISCS = {'orig': (ROOT, None), 'hsk': (os.path.join(ROOT, 'build', 'trial', 'hsk_full1'), 'hsk_full1'),
         'nofix': (os.path.join(ROOT, 'build', 'trial'), 's8e_nofix'), 'p10c': (os.path.join(ROOT, 'build', 'trial'), 'prop10c')}
# (file, base, ptr word offset(s) from the DB ctx 'ptr@' = first pointer, string offset)
CASES = [('FLOW_PRG/SPF_READ.BIN', 0, 0x120b8, 0x536d8), ('FLOW_PRG/LOCAL.BIN', 0, 0x5e90, 0x182a8), ('FLOW_PRG/HELP.BIN', 0, 0x6ae0, 0x29320), ('ATFIRST/TITLE.BIN', 0x8c6d0000, 0xa82c, 0x2e8e8), ('FLOW_PRG/TITLE.BIN', 0x8c6d0000, 0xa920, 0x2e998),
         ('FLOW_PRG/ENDING.BIN', 0x8c330000, 0xae78, 0x7532c), ('FLOW_PRG/EVENT.BIN', 0x8c3a0000 - 0, 0x1b54, 0xda184),
         ('FLOW_PRG/SCDRF.BIN', 0x8c2d0000, 0x2ac, 0x37df0), ('FLOW_PRG/SEARCH.BIN', 0x8c4d0000, 0x8b4c, 0x6ae84),
         ('FLOW_PRG/WEEKLY.BIN', 0x8c300000, 0x21d0c, 0x3f66c)]
srcs = {}
fs = {}
for k, (d, n) in DISCS.items():
    s = D.Source(d, n)
    _p, _a, _b, recs = D.read_filesystem(s)
    srcs[k] = s
    fs[k] = {r.path.upper(): r for r in recs if not r.isdir}
for rel, base, po, so in CASES:
    print(rel, 'array-base string at file %#x' % so)
    for k in DISCS:
        r = fs[k]['/' + rel.upper()]
        b = srcs[k].read(r.lba, r.size)
        w = struct.unpack_from('<I', b, po)[0]
        tgt = w - (w - (w & 0xFFFF0000)) if False else None
        # guess base from the original word: orig word - so
        print('   %-6s word@%#x = %08x' % (k, po, w), end='')
        if k == 'orig':
            obase = w - so
            print('  (implies base %08x)' % obase)
        else:
            off = w - obase
            print('  -> file offset %#x %r' % (off, b[off:off + 14]) if 0 <= off < len(b) else '  (outside)')
