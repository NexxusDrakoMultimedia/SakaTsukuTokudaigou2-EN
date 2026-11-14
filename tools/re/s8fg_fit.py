"""s8fg: of the relocated plain-pointer hwptr records listed in build/s8fg/relscan_prop10c.txt, how many have an English form that FITS the
original slot (len(en encoded)+1 <= slot), i.e. were moved although they did not have to be."""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
lines = [l for l in open(os.path.join(ROOT, 'build', 's8fg', 'relscan_prop10c.txt'), encoding='utf-8') if l.strip()]
db = {}
fit = nofit = 0
bad = []
for l in lines:
    rel, off = l.split()[0], l.split()[1]
    if rel not in db:
        db[rel] = {}
        for x in open(os.path.join(ROOT, 'translation', rel.replace('/', '__') + '.jsonl'), encoding='utf-8'):
            if x.strip():
                r = json.loads(x)
                db[rel][r['id']] = r
    r = db[rel]['%s#%s' % (rel, off.lstrip('0') or '0')]
    n = len(r['en'].encode('cp932', 'replace')) + 1
    if n <= (r.get('slot') or 0):
        fit += 1
    else:
        nofit += 1
        bad.append((rel, off, r['en'], r['slot'], n))
print('relocated plain-pointer hwptr: fits slot (needless move):', fit, ' does not fit (needed):', nofit)
for b in bad[:15]:
    print('  needed:', b)
