"""rfit_short: classify the records whose English is a shortened variant of a longer English of the same Japanese string.

    python -I -X utf8 tools/re/rfit_short.py [OUT.txt]

A record is `short` when another record with the same `ja` has a longer English that starts with the same 3 letters (or the
short form ends with '.') and the short form is not a prefix-only county / -gun variant.  Output: counts per class
(fmt / ctx kind / movable) and the records of the small classes.  Read-only.
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def kind(r):
    ctx = r.get('ctx') or ''
    fmt = r.get('fmt') or 'ptr'
    if 'hwpool' in ctx:
        return 'hwpool'
    if 'orphan' in ctx:
        return 'orphan'
    if 'interior' in ctx:
        return 'interior'
    if fmt == 'recarr':
        return 'recarr'
    if fmt == 'hwptr':
        return 'hwptr'
    return 'ptr'


def main(argv):
    recs = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        with open(p, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    if r.get('en'):
                        recs.append(r)
    by = defaultdict(set)
    for r in recs:
        by[r['ja']].add(r['en'])
    cnt = Counter()
    lst = defaultdict(list)
    for r in recs:
        en = r['en']
        longer = [x for x in by[r['ja']] if len(x) > len(en) and '\n' not in x]
        if not longer:
            continue
        L = max(longer, key=len)
        if L.endswith('-gun') or L.endswith('-cho') or L.endswith('-mura') or L.endswith(' Pref.'):
            continue
        if not (en.endswith('.') or L[:3].lower() == en[:3].lower()):
            continue
        k = kind(r)
        cnt[k] += 1
        lst[k].append((r['id'], r['ja'], en, L))
    print(dict(cnt))
    out = argv[0] if argv else None
    if out:
        with open(out, 'w', encoding='utf-8') as fo:
            for k, v in lst.items():
                fo.write('## %s %d\n' % (k, len(v)))
                for x in v[:400]:
                    fo.write('%s\t%s\t%s\t%s\n' % x)
    for k in ('interior', 'ptr', 'orphan'):
        print('--', k)
        for x in lst[k][:12]:
            print('  ', x)


if __name__ == '__main__':
    main(sys.argv[1:])
