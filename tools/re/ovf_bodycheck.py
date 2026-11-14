"""ovf: is the composer body (signature + 0x90 .. +232) byte-identical in the 20 overlays, and the literal pool layout the same?"""
import os, struct, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import layoutpatch as LP
ref = None
for n in LP.CLUB_OVERLAYS:
    d = open(os.path.join(ROOT, 'extracted', 'FLOW_PRG', n + '.BIN'), 'rb').read()
    a = d.find(LP.CLUB_SIG_A)
    c = a + 0x90
    body = d[c:c + 232]
    pool = d[c + 0xea:c + 0x120]
    lits = [struct.unpack_from('<I', d, c + 0xea + 4 * i)[0] for i in range(0, 14)]
    if ref is None:
        ref = body
    print('%-9s sig %#x comp %#x body==HOMETOWN %s   tail word %s  lit(strlen)=%#x lit(pool)=%#x  next 8 bytes %s' % (
        n, a, c, body == ref, d[c + 232:c + 234].hex(), lits[(0x82c - 0x814) // 4], lits[(0x844 - 0x814) // 4], d[c + 0xe2 - 0x20 : c + 0xe2 - 0x1c].hex()))
