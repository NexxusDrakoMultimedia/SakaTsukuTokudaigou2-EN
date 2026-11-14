"""aln: read the panel overlays and 1ST_READ.BIN back from a built trial disc and check that the align fix can be applied on top of them
(read-only): the panel idioms / strlen pools are intact, the align cave area is zero, the font hooks are present.

    python -I -X utf8 tools/re/aln_discprobe.py DISC_DIR DISC_NAME      e.g. build/trial/hsk_full1 hsk_full1
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import discbuild as D   # noqa: E402
import fontpatch as FP  # noqa: E402

src = D.Source(sys.argv[1], sys.argv[2])
_p, _rl, _rs, recs = D.read_filesystem(src)
files = {r.path.upper(): r for r in recs if not r.isdir}


def rd(p):
    r = files['/' + p.upper()]
    return src.read(r.lba, r.size)


k = rd('1ST_READ.BIN')
a0 = FP.align_address() - FP.IMG_BASE
ct = FP.PLACEMENTS['tail']
c0 = ct[0] - FP.IMG_BASE
print('1ST_READ align cave area zero:', not any(k[a0:a0 + 0x100]))
print('font cave on the disc == default cave_bytes (the default build is byte-identical):', k[c0:c0 + FP.CAVE_SIZE] == FP.cave_bytes(ct))
for rel in FP.ALIGN_FILES:
    d = rd(rel)
    shl, pools = FP.panel_scan(d, rel)
    hooks = FP.find_sites(d, rel)
    print('%-24s panel idioms %d pools %d   unpatched hook sites %d (0 = hooks already on the disc)' % (rel, len(shl), len(pools), len(hooks)))
for rel in ('FLOW_PRG/PLNUMSET.BIN',):
    d = rd(rel)
    print(rel, 'unpatched hook sites:', len(FP.find_sites(d, rel)))
