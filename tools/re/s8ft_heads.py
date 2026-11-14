"""s8ft: list hwptr records that are the element 0 of a fixed-stride array (DB only, no disc).
Rule A: a `recarr` record `recarray S=n` sits at off+n.   Rule B: ctx is a single pointer (`hwptr ptr@..`, not `tbl@`) and `hwpool`
records sit at off+S and off+2S.   usage: s8ft_heads.py [-v]
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TR = os.path.join(ROOT, 'translation')
tot = 0
names = {}
for fn in sorted(os.listdir(TR)):
    if not fn.endswith('.jsonl') or fn.startswith('BCAST'):
        continue
    db = [json.loads(l) for l in open(os.path.join(TR, fn), encoding='utf-8') if l.strip()]
    offs = {int(r['id'].rsplit('#', 1)[1], 16): r for r in db}
    for r in db:
        if r.get('fmt') != 'hwptr' or not r.get('refs'):
            continue
        off = int(r['id'].rsplit('#', 1)[1], 16)
        ctx = r.get('ctx') or ''
        why = None
        for S in range(4, 257):
            o1 = offs.get(off + S)
            if not o1:
                continue
            m = re.search(r'recarray S=(\d+)', o1.get('ctx') or '')
            if o1.get('fmt') == 'recarr' and m and int(m.group(1)) == S:
                why = 'A S=%d' % S
                break
            o2 = offs.get(off + 2 * S)
            if 'hwptr ptr@' in ctx and 'hwpool' in (o1.get('ctx') or '') and o2 and 'hwpool' in (o2.get('ctx') or ''):
                why = 'B S=%d' % S
                break
        if why:
            tot += 1
            names[r['ja']] = names.get(r['ja'], 0) + 1
            if '-v' in sys.argv:
                print('%-26s %#8x refs %-3s %-6s ja=%r en=%r' % (fn[:-6], off, r['refs'], why, r['ja'], r['en']))
print('heads', tot, names)
