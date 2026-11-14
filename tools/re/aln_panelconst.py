"""aln: print the relative-offset constants (shll2 sites, strlen pools) used by fontpatch.PANEL_* from the three real overlays."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aln_panelmap as M  # noqa: E402,F401  (prints its own summary)
import aln_scan12 as S12  # noqa: E402
import aln_xref as X  # noqa: E402

name = 'CAP_SLCT'
d = open(os.path.join(S12.DIR, name + '.BIN'), 'rb').read()
ws = struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])
ss = M.sites(ws)
best = max(ss, key=lambda s0: sum(1 for s in ss if 0 <= s[0] - s0[0] < 0x800))
ss = [s for s in ss if 0 <= s[0] - best[0] < 0x800]
first = min(s[0] for s in ss)
print('SITES_REL =', [s[1] - first for s in ss])
loads = sorted(x for x in X.xrefs(d, M.STRLEN, 0) if first - 0x1000 <= x[0] < first)
print('POOLS_REL =', sorted(set(x[1] - first for x in loads)))
print('LOADS_REL =', [x[0] - first for x in loads])
