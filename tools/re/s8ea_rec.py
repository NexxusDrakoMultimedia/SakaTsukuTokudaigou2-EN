"""s8ea: map the differing ranges (A=hsk_full1, B=prop10c dumps) of an overlay to translation records.

usage: s8ea_rec.py NAME FILEKEY [LO] [HI]     e.g. s8ea_rec.py FLOW_PRG__EVENT.BIN FLOW_PRG__EVENT.BIN
Per range: the record whose [offset, offset+max_bytes) holds the range start (id offset), its ja/en/ctx/orphan/skip, else UNCOVERED.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
D = os.path.join(ROOT, 'build', 's8ea', 'dump')


def main(argv):
    name, key = argv[1], argv[2]
    lo = int(argv[3], 16) if len(argv) > 3 else 0
    hi = int(argv[4], 16) if len(argv) > 4 else 1 << 30
    a = open(os.path.join(D, 'A_' + name), 'rb').read()
    b = open(os.path.join(D, 'B_' + name), 'rb').read()
    hi = min(hi, len(a), len(b))
    recs = []
    for ln in open(os.path.join(ROOT, 'translation', key + '.jsonl'), encoding='utf-8'):
        j = json.loads(ln)
        try:
            off = int(j['id'].split('#')[1].split('.')[0], 16)
        except Exception:
            continue
        recs.append((off, j))
    recs.sort(key=lambda x: x[0])
    rg = []
    for i in range(lo, hi):
        if a[i] != b[i]:
            if rg and i - rg[-1][1] <= 3:
                rg[-1][1] = i + 1
            else:
                rg.append([i, i + 1])
    import bisect
    offs = [r[0] for r in recs]
    for s, e in rg:
        k = bisect.bisect_right(offs, s) - 1
        hit = None
        if k >= 0:
            off, j = recs[k]
            if s < off + max(j.get('max_bytes') or 0, len(j.get('ja', '').encode('cp932', 'replace')) + 1):
                hit = (off, j)
        if hit:
            off, j = hit
            print('%#8x-%#8x  rec #%x ja=%r en=%r ctx=%s%s%s' % (s, e, off, j['ja'][:30], j['en'][:40], (j.get('ctx') or '')[:40],
                                                                 ' ORPHAN' if j.get('orphan') else '', ' SKIP' if j.get('skip') else ''))
        else:
            print('%#8x-%#8x  UNCOVERED  A=%s B=%s' % (s, e, a[s:s + 8].hex(), b[s:s + 8].hex()))


if __name__ == '__main__':
    main(sys.argv)
