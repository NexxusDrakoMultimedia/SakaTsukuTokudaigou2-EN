"""hng: list records of one source by ctx class that carry English (orphans = no pointer to them; the risk is a code/script byte pattern that
decodes as text).  usage: hng_orphans.py SOURCE-substring [ctx-substring]"""
import glob, json, os, sys
from collections import Counter
src = sys.argv[1]; cx = sys.argv[2] if len(sys.argv) > 2 else None
cnt = Counter()
for p in sorted(glob.glob(os.path.join('translation', '*.jsonl'))):
    if src not in p:
        continue
    for ln in open(p, encoding='utf-8'):
        r = json.loads(ln)
        c = (r.get('ctx') or '').split(' ')[0] + ' ' + (r.get('fmt') or '')
        cnt[(c, bool(r.get('en')))] += 1
        if cx and cx in (r.get('ctx') or '') and r.get('en'):
            print(r['id'], r.get('max_bytes'), repr(r['ja'])[:40], '->', repr(r['en'])[:40], r.get('ctx'))
if not cx:
    for k, v in sorted(cnt.items()):
        print(k, v)
