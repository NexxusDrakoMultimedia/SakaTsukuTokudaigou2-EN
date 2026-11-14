"""tx5: remaining untranslated distinct commentary lines per speaker set and category (top 40).  python -I -X utf8 tools/re/tx5_remaining.py"""
import collections, json, os, re
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
have = set()
cats = collections.defaultdict(lambda: collections.defaultdict(set))
for ln in open(os.path.join(ROOT, 'translation', 'BCAST__BCAST.BIN.jsonl'), encoding='utf8'):
    r = json.loads(ln)
    m = re.match(r'clip (\w+)\\(\S+) seg', r['ctx'])
    f, stem = m.group(1), m.group(2)
    if f == 'name':
        continue
    if r.get('en'):
        have.add(r['ja'])
        continue
    c = re.sub(r'_?\d+[a-z]?(-\d*)?$', '', stem.split('_', 1)[1])
    cats[f][c].add(r['ja'])
tot = collections.Counter()
rows = []
for f, d in cats.items():
    for c, s in d.items():
        s2 = {x for x in s if x not in have}
        tot[f] += len(s2)
        rows.append((len(s2), f, c))
print('untranslated distinct per folder', dict(tot), 'total', sum(tot.values()))
for n, f, c in sorted(rows, reverse=True)[:60]:
    print('%5d %s %s' % (n, f, c))
