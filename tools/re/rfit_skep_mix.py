"""skeptic: refit forms whose same ja keeps a DIFFERENT en in non-refit records (visible inconsistency on one disc)."""
import collections
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
recs = []
for f in sorted(glob.glob(os.path.join(ROOT, 'translation', 'refit', '*.jsonl'))):
    for ln in open(f, encoding='utf-8'):
        if ln.strip():
            r = json.loads(ln)
            r['_f'] = os.path.basename(f)
            recs.append(r)
db = {}
for f in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')):
    for ln in open(f, encoding='utf-8'):
        if ln.strip():
            r = json.loads(ln)
            db[r['id']] = r
ref = {r['id']: r['en'] for r in recs}
newen = collections.defaultdict(set)
for r in recs:
    newen[r['ja']].add(r['en'])
mix = collections.defaultdict(collections.Counter)
for i, d in db.items():
    if d['ja'] in newen and i not in ref:
        if d['en'] not in newen[d['ja']]:
            mix[d['ja']][(d['en'], d['id'].split('#')[0], d.get('fmt'))] += 1
print('ja with differing kept en:', len(mix), 'records', sum(sum(c.values()) for c in mix.values()))
for j, c in sorted(mix.items(), key=lambda kv: -sum(kv[1].values())):
    print(j, sorted(newen[j]), 'kept', sum(c.values()), list(c.items())[:3])
# refit en differing from the DB en in the same ja? how many refit records change the en at all
chg = sum(1 for r in recs if db[r['id']]['en'] != r['en'])
print('records whose en differs from DB en:', chg, 'of', len(recs))
