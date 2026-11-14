"""skm_panel.py DISC_DIR DISC_NAME: read SCDRF / SEARCH back from a built disc and show the 4 panel sites (`mov #0,r6` -> `mov #77,r6`), and the compact
text length over every salary word the panel can hold (V = int16 word * 100 Man).  Read-only."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import discbuild as D            # noqa: E402
import moneypatch as MP          # noqa: E402

src = D.Source(sys.argv[1], sys.argv[2])
_p, _rl, _rs, recs = D.read_filesystem(src)
files = {r.path.upper(): r for r in recs if not r.isdir}


def rd(p):
    r = files['/' + p.upper()]
    return src.read(r.lba, r.size)


tot = 0
for rel in MP.overlay_paths():
    orig = MP.read_extracted(rel)
    d = None
    for s in MP.find_sites(orig, rel):
        if s['variant'] != 'A':
            continue
        r = MP.find_d_literal(orig, s['off'])
        if not r:
            continue
        for o in MP.panel_sites(orig, r[1] + s['off']):
            d = d or rd(rel)
            tot += 1
            print('%-22s %#x original %s disc %s' % (rel, o, orig[o:o + 2].hex(), d[o:o + 2].hex()))
print('panel sites:', tot)
over = [w for w in range(0, 32768) if len(MP.reference(w * 100, MP.COMPACT_FLAG)) > 12]
print('salary words 0..32767 whose compact text is over 12 bytes: first %d (%s), count %d' % (over[0], MP.reference(over[0] * 100, 77), len(over)))
