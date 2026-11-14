"""aln: locate the shared player-card panel in CAP_SLCT / ENDOPT / EVENT: idiom sites (x = anchor - 12*len) and the strlen pool loads
that produce the lengths, as offsets relative to the first site; verifies that the three copies agree.

    python -I -X utf8 tools/re/aln_panelmap.py
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aln_scan12 as S12  # noqa: E402
import aln_xref as X  # noqa: E402

STRLEN = 0x8c014de4


def sites(ws):
    out = []
    for h in S12.scan(ws):
        i = h // 2
        rA = None
        w = ws[i]
        a, b = (w >> 4) & 15, (w >> 8) & 15        # a: value reg, b: copy
        okread = any(ws[j] & 0xF00F == 0x000D and (ws[j] >> 8) & 15 == a for j in range(i - 4, i))
        okstore = any(ws[j] & 0xF00F == 0x0005 and (ws[j] >> 4) & 15 == b for j in range(i + 4, i + 12))
        if okread and okstore:
            # locate shll2 a within 8 words
            k = [j for j in range(i + 1, i + 9) if ws[j] == 0x4008 | a << 8]
            out.append((h, k[0] * 2))
    return out


res = {}
for name in ('CAP_SLCT', 'ENDOPT', 'EVENT'):
    d = open(os.path.join(S12.DIR, name + '.BIN'), 'rb').read()
    ws = struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])
    ss = sites(ws)
    # keep the largest cluster of sites (a 0x800 byte window): the panel
    best = max(ss, key=lambda s0: sum(1 for s in ss if 0 <= s[0] - s0[0] < 0x800))
    ss = [s for s in ss if 0 <= s[0] - best[0] < 0x800]
    first = min(s[0] for s in ss)
    loads = sorted(x for x in X.xrefs(d, STRLEN, 0) if first - 0x1000 <= x[0] < first)
    print('%-9s sites %d  first %#x last %#x   strlen loads %d' % (name, len(ss), first, max(s[0] for s in ss), len(loads)))
    res[name] = ([s[0] - first for s in ss], [(x[0] - first, x[1] - first) for x in loads])
a = res['CAP_SLCT']
for n in ('ENDOPT', 'EVENT'):
    print(n, 'site offsets equal:', res[n][0] == a[0], ' load offsets equal:', res[n][1] == a[1])
print('loads relative to first site (load, pool):', ' '.join('%d/%d' % x for x in a[1]))
