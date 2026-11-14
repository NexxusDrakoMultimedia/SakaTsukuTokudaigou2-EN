"""ovf: where is struct offset 0x103a (#sname#, club name) / 0x102c (#YOU#) used as a halfword literal, per overlay?  (2 sites per overlay = the
#sname# expander copy; anything else writes or reads the name elsewhere).   usage: ovf_snamesites.py [VALUE_HEX]"""
import glob, os, struct, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
val = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x103a
for p in sorted(glob.glob(os.path.join(ROOT, 'extracted', '*', '*.BIN')) + glob.glob(os.path.join(ROOT, 'extracted', '*.BIN'))):
    d = open(p, 'rb').read()
    sites = []
    for o in range(0, len(d) - 7, 2):
        w = struct.unpack_from('<H', d, o)[0]
        if w >> 12 == 9:
            t = o + 4 + (w & 0xFF) * 2
            if t + 2 <= len(d) and struct.unpack_from('<H', d, t)[0] == val:
                sites.append(o)
    if len(sites) != 2 and sites:
        print(os.path.relpath(p, ROOT), len(sites), [hex(s) for s in sites])
