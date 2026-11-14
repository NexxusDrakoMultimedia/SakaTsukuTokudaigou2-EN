"""s7n: state of the exact-name records (ja equals a name entry) with DB en, refit overlay en, kind, table size, slot.

usage: s7n_state.py out.tsv
"""
import json, glob, os, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools', 're'))

# ja (exact, as in the DB pool) -> key
ART = {}
for ln in open(os.path.join(ROOT, 'translation', 'clubwords_art.tsv'), encoding='utf8').read().splitlines()[1:]:
    p = ln.split('\t')
    if p[0][0] in 'FS':
        ART[p[1]] = (p[0], p[2])
EXTRA = {'ﾄﾞﾘｰﾑﾁｰﾑ': ('F31', 'Dream'), 'ﾚｯﾄﾞﾀﾞｲﾔﾓﾝｽﾞ': ('F02', 'Red Diamonds'), 'ｼﾞｪﾌﾕﾅｲﾃｯﾄﾞ': ('F03', 'JEF United')}
ART.update(EXTRA)

ov = {}
for p in glob.glob(os.path.join(ROOT, 'translation', 'refit', '*.jsonl')):
    for ln in open(p, encoding='utf8'):
        if ln.strip():
            r = json.loads(ln)
            ov[r['id']] = r['en']

rows = []
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
    for ln in open(p, encoding='utf8'):
        if not ln.strip():
            continue
        r = json.loads(ln)
        ja = r['ja']
        if ja not in ART:
            continue
        ctx = r.get('ctx') or ''
        m = re.search(r'tbl@[0-9a-f]+\[\d+/(\d+)\]', ctx)
        n = m.group(1) if m else '-'
        kind = 'hwpool' if 'hwpool' in ctx else (r.get('fmt') or 'ptr')
        rows.append((ART[ja][0], ja, ART[ja][1], kind, n, str(r.get('slot') or r.get('max_bytes')), r['en'], ov.get(r['id'], ''), r['id']))
c = collections.Counter((a, b, c_, d, e, f, g, h) for a, b, c_, d, e, f, g, h, i in rows)
ex = {}
for a, b, c_, d, e, f, g, h, i in rows:
    ex.setdefault((a, b, c_, d, e, f, g, h), i)
with open(sys.argv[1], 'w', encoding='utf8') as fh:
    for k, v in sorted(c.items()):
        fh.write('\t'.join(k) + '\t%d\t%s\n' % (v, ex[k]))
print(len(rows), 'records', len(c), 'groups')
