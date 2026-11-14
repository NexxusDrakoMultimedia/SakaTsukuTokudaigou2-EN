"""pol: odd-shape census (reference rule) over the town table of EACH of the 20 club-name overlays of a built dump, so a copy that
was missed by the text edit shows up.   python -I -X utf8 tools/re/pol_tables20.py DUMPDIR"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import ovf_sim as OVF
import layoutpatch as LP
from collections import Counter
dump = sys.argv[1]
first = open(os.path.join(OVF.ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
bad = 0
for n in LP.CLUB_OVERLAYS:
    p = os.path.join(dump, 'FLOW_PRG', n + '.BIN')
    try:
        comp = OVF.Composer(open(p, 'rb').read(), first)
        towns, _, pool = comp.tables()
    except Exception as e:
        print('%-9s cannot read: %s' % (n, e)); bad += 1; continue
    odd = Counter(); cut = 0
    for t in towns:
        for w in pool:
            for wf in (False, True):
                res = OVF.reference(t, w, wf, True)
                if not wf and res != t + b' ' + w: cut += 1
                for s in (b'. .', b'-.', b'..', b' .', b'- '):
                    if s in res: odd[s.decode()] += 1
    flagged = sum(1 for t in towns if any(c in t for c in b' -.'))
    print('%-9s towns %d with space/hyphen/dot %d, cut pairs %d, odd shapes %d' % (n, len(towns), flagged, cut, sum(odd.values())))
    bad += sum(odd.values())
print('TOTAL odd', bad)
