"""s7n: final state table of the fixed clubs / special teams / competitions: art form, DB form per kind, overlay (--refit on) form.

usage: s7n_state2.py out.md        (markdown rows for docs/style-guide.md 12.5; also prints a summary)
Effective form of a record = refit overlay en when there is one, else the DB en.
"""
import collections
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = chr(9)
ART = []
for ln in open(os.path.join(ROOT, 'translation', 'clubwords_art.tsv'), encoding='utf8').read().split(chr(10))[1:]:
    p = ln.split(T)
    if p and p[0][:1] in 'FS' and len(p) > 3:
        ART.append((p[0], p[1], p[2], p[3]))
ART += [('F31b', 'ﾄﾞﾘｰﾑｸﾗﾌﾞ', 'Dream', 'Dream'), ('F02b', 'ﾚｯｽﾞ', 'Red Diamonds', 'Red Diamonds'), ('F03b', 'ｼﾞｪﾌ', 'JEF UNITED', 'JEF United'),
        ('F06b', 'ﾏﾘﾉｽ', 'Yokohama F Marinos', 'Yokohama F Marinos')]
ov = {}
for p in glob.glob(os.path.join(ROOT, 'translation', 'refit', '*.jsonl')):
    for ln in open(p, encoding='utf8'):
        if ln.strip():
            r = json.loads(ln)
            ov[r['id']] = r['en']
recs = collections.defaultdict(list)
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
    for ln in open(p, encoding='utf8'):
        if ln.strip():
            r = json.loads(ln)
            recs[r['ja']].append(r)


def kind(r):
    ctx = r.get('ctx') or ''
    if 'hwpool' in ctx:
        return 'pool (in place)'
    if r['id'].startswith('BCAST/'):
        return 'clip'
    m = re.search(r'tbl@[0-9a-f]+\[\d+/(\d+)\]', ctx)
    return 'table' + (' of %s' % m.group(1) if m and int(m.group(1)) < 30 else '')


rows = []
for key, ja, art, asc in ART:
    c = collections.Counter()
    for r in recs.get(ja, []):
        db = r['en']
        eff = ov.get(r['id'], db)
        c[(kind(r) if kind(r) in ('clip', 'pool (in place)') else 'table', db, eff)] += 1
    if not c:
        continue
    for (k, db, eff), n in sorted(c.items()):
        rows.append((key, art, k, db, eff, n))
with open(sys.argv[1], 'w', encoding='utf8', newline=chr(10)) as fh:
    for key, art, k, db, eff, n in rows:
        fh.write('| %s | %s | %s | `%s` | `%s` | %d |\n' % (key, art, k, db, eff, n))
print(len(rows), 'rows')
