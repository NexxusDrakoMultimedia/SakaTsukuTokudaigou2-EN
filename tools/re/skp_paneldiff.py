"""skp (skeptic): diff the panel overlays of two trial discs (aligned vs baseline): the changed words must be exactly 20 shll2->nop and 8 literal-pool words.

    python -I -X utf8 tools/re/skp_paneldiff.py DISC_A NAME_A DISC_B NAME_B
"""
import os, struct, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import discbuild as D
def reader(d, n):
    src = D.Source(d, n)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    files = {r.path.upper(): r for r in recs if not r.isdir}
    return lambda p: src.read(files['/' + p.upper()].lba, files['/' + p.upper()].size)
ra, rb = reader(sys.argv[1], sys.argv[2]), reader(sys.argv[3], sys.argv[4])
for rel in ['FLOW_PRG/CAP_SLCT.BIN', 'FLOW_PRG/ENDOPT.BIN', 'FLOW_PRG/EVENT.BIN', 'FLOW_PRG/PLNUMSET.BIN', 'FLOW_PRG/SCHE1.BIN', '1ST_READ.BIN']:
    a, b = ra(rel), rb(rel)
    assert len(a) == len(b)
    diff = [i for i in range(0, len(a), 2) if a[i:i + 2] != b[i:i + 2]]
    kinds = collections.Counter()
    for i in diff:
        kinds[(a[i:i + 2].hex(), b[i:i + 2].hex())] += 1
    print(rel, 'changed halfwords', len(diff), dict(list(kinds.items())[:6]))
