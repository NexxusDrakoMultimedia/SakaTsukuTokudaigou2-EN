"""skh: byte ranges of one overlay that differ between extracted/ (original) and a built trial disc, restricted to [LO, HI) (hex file offsets).

usage: skh_orig_diff.py DISC FILE LO HI [--records]      (FILE like FLOW_PRG/EVENT.BIN)
With --records every range is matched against the translation records of that file (id '#hex' = file offset): the record whose
[offset, offset+max_bytes) contains the range start is printed with ja/en/ctx, so ranges that match no record (code patches, hooks)
and records that overwrite DATA (orphans, 'no pointer') stand out.
Read-only.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D            # noqa: E402


def main(argv):
    disc, rel, lo, hi = argv[1], argv[2], int(argv[3], 16), int(argv[4], 16)
    src = D.Source(os.path.join(ROOT, 'build', 'trial', disc), disc)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    files = {r.path.upper(): r for r in recs if not r.isdir}
    r = files['/' + rel.upper()]
    new = src.read(r.lba, r.size)
    old = open(os.path.join(ROOT, 'extracted', rel), 'rb').read()
    hi = min(hi, len(old))
    rg = []
    for i in range(lo, hi):
        if old[i] != new[i]:
            if rg and i - rg[-1][1] <= 3:
                rg[-1][1] = i + 1
            else:
                rg.append([i, i + 1])
    byoff = {}
    if '--records' in argv:
        fn = os.path.join(ROOT, 'translation', rel.replace('/', '__') + '.jsonl')
        for ln in open(fn, encoding='utf-8'):
            j = json.loads(ln)
            try:
                o = int(j['id'].split('#')[1], 16)
            except Exception:
                continue
            byoff[o] = j
    keys = sorted(byoff)
    import bisect
    for s, e in rg:
        line = '%#08x-%#08x (%d) old %s new %s' % (s, e, e - s, old[s:e][:24].hex(), new[s:e][:24].hex())
        if byoff:
            k = bisect.bisect_right(keys, s) - 1
            j = byoff[keys[k]] if k >= 0 else None
            if j and keys[k] + max(j.get('max_bytes', 0), 1) > s:
                line += '   REC %s ja=%r en=%r ctx=%s%s' % (j['id'].split('#')[1], j['ja'][:12], j['en'][:16], j.get('ctx', '')[:30], ' ORPHAN' if j.get('orphan') else '')
            else:
                line += '   (no record)'
        print(line)
    print('ranges: %d' % len(rg))
    src.close()


if __name__ == '__main__':
    main(sys.argv)
