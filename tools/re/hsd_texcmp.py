"""hsd: decode an embedded TBD record in the original and in a built overlay, compare header words and the decoded payload.
usage: hsd_texcmp.py ORIG_FILE NEW_FILE TABLE_OFFSET(hex) [INDEX].  Uses texinject.game_load_tbd (re-implementation of FUN_8c15a776). Read-only."""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject as T
a = open(sys.argv[1], 'rb').read(); b = open(sys.argv[2], 'rb').read()
base = int(sys.argv[3], 16); idx = int(sys.argv[4]) if len(sys.argv) > 4 else 0
print('table header orig', a[base:base+4+16*struct.unpack_from('<I', a, base)[0]].hex())
print('table header new ', b[base:base+4+16*struct.unpack_from('<I', b, base)[0]].hex())
ga = T.game_load_tbd(a, base); gb = T.game_load_tbd(b, base)
fa, da, wa, ha, sa, pa = ga[idx]; fb, db, wb, hb, sb, pb = gb[idx]
print('fmt/dt/w/h/stamp orig', fa, da, wa, ha, hex(sa), 'new', fb, db, wb, hb, hex(sb), 'payload len', len(pa), len(pb))
print('payload first 64 orig', pa[:64].hex()); print('payload first 64 new ', pb[:64].hex())
# per-pixel difference in untwiddled space is not needed: report 16-bit word diff count and byte span
n = len(pa) // 2
wd = [i for i in range(n) if pa[2*i:2*i+2] != pb[2*i:2*i+2]]
print('differing 16-bit words', len(wd), 'of', n, 'first/last', (wd[0], wd[-1]) if wd else None)
# what follows the record slot in the new file vs orig
