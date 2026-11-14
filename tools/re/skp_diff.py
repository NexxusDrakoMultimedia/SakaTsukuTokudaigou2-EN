"""skp: skeptic check for the pol_ town-short change. Diffs translation/*.jsonl against a baseline dir (read-only), classifies changes.
    python -I -X utf8 tools/re/skp_diff.py BASEDIR"""
import json, os, re, sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
import pol_apply as A
from pol_old import OLD
base = sys.argv[1]
newja = {v[0]: v[1] for v in A.NEW.values()}
oldja = {OLD[k][0]: OLD[k][1] for k in A.NEW}
cnt = Counter(); other = []; badfit = []; nonshort = 0; files = 0
for fn in sorted(os.listdir(os.path.join(ROOT, 'translation'))):
    if not fn.endswith('.jsonl'): continue
    bp = os.path.join(base, fn)
    if not os.path.exists(bp): cnt['nobase'] += 1; continue
    b = {}
    for l in open(bp, encoding='utf-8'):
        if l.strip(): r = json.loads(l); b[r['id']] = r
    chg = 0
    for l in open(os.path.join(ROOT, 'translation', fn), encoding='utf-8'):
        if not l.strip(): continue
        r = json.loads(l); o = b.get(r['id'])
        if o is None: cnt['newid'] += 1; continue
        d = [k for k in ('ja','en') if r.get(k) != o.get(k)]
        if not d: continue
        if d == ['en'] and 'tbl@' in (r.get('ctx') or '') and newja.get(r['ja']) == r['en'] and oldja.get(r['ja']) == o['en']:
            cnt['town_short'] += 1; chg += 1
            if len(r['en']) + 1 > r['max_bytes']: badfit.append((fn, r['id'], r['en'], r['max_bytes']))
        else:
            other.append((fn, r['id'], d, o.get('en'), r.get('en')))
    if chg: files += 1
print('classified', dict(cnt), 'files with town changes', files, 'badfit', badfit[:5])
print('other diffs vs baseline:', len(other))
for x in other[:15]: print('  ', x)
print('--- other diffs whose ja is one of the 107 town forms:')
n = 0
for fn in sorted(os.listdir(os.path.join(ROOT, 'translation'))):
    if not fn.endswith('.jsonl') or not os.path.exists(os.path.join(base, fn)): continue
    b = {}
    for l in open(os.path.join(base, fn), encoding='utf-8'):
        if l.strip(): r = json.loads(l); b[r['id']] = r
    for l in open(os.path.join(ROOT, 'translation', fn), encoding='utf-8'):
        if not l.strip(): continue
        r = json.loads(l); o = b.get(r['id'])
        if o and r['ja'] in newja and r['en'] != o['en'] and not ('tbl@' in (r.get('ctx') or '') and newja[r['ja']] == r['en']):
            n += 1
            if n <= 40: print('  ', fn, r['id'], r['ja'], repr(o['en']), '->', repr(r['en']), (r.get('ctx') or '')[:40])
print('count', n)
