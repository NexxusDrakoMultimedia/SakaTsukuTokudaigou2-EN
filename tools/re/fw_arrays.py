"""fw_arrays.py : census of the fixed-stride record arrays (`recarr` records, ctx 'recarray S=.. n=.. W=..') and of the half-width
pointer pools (`hwptr`) across translation/*.jsonl: per (S, W) number of source files, arrays, records, distinct ja; per hw slot size
number of records / pointer-referenced share.  Read-only helper of the field-width study."""
import collections
import glob
import json
import re

arr = collections.defaultdict(lambda: {'files': set(), 'recs': 0, 'ja': set(), 'arrays': set()})
hw = collections.defaultdict(lambda: {'recs': 0, 'ptr': 0, 'pool': 0, 'files': set(), 'ja': set()})
for p in sorted(glob.glob('translation/*.jsonl')):
    src = p.split('__', 1)[-1].replace('.jsonl', '') if '__' in p else p
    for ln in open(p, encoding='utf8'):
        r = json.loads(ln)
        f = r.get('fmt')
        ctx = r.get('ctx') or ''
        if f == 'recarr':
            m = re.search(r'S=(\d+) n=(\d+) W=(\d+)', ctx)
            if m:
                k = (int(m.group(1)), int(m.group(3)))
                a = arr[k]
                a['files'].add(src)
                a['recs'] += 1
                a['ja'].add(r['ja'])
                a['arrays'].add((src, int(m.group(2))))
        elif f == 'hwptr':
            k = r['max_bytes']
            h = hw[k]
            h['recs'] += 1
            h['files'].add(src)
            h['ja'].add(r['ja'])
            if 'refs' in r and r['refs']:
                h['ptr'] += 1
            else:
                h['pool'] += 1
print('recarr arrays (S=stride, W=name field):')
for k, a in sorted(arr.items()):
    print('  S=%-4d W=%-3d files=%-3d arrays(file,n)=%-3d records=%-6d distinct_ja=%-5d' % (k[0], k[1], len(a['files']), len(a['arrays']), a['recs'], len(a['ja'])))
print('hw pools by slot size (max_bytes):')
for k, h in sorted(hw.items()):
    print('  slot=%-3d records=%-6d pointer-referenced=%-6d index-addressed(pool)=%-5d files=%-3d distinct_ja=%d' % (k, h['recs'], h['ptr'], h['pool'], len(h['files']), len(h['ja'])))
