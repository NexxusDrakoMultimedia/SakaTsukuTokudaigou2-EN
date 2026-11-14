"""s7n: every translation/*.jsonl and refit overlay line parses, has id/ja/en; counts the changed ids of build/s7n_changed_ids.tsv."""
import glob, json, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
bad = n = 0
for p in glob.glob(os.path.join(ROOT, 'translation', '*.jsonl')) + glob.glob(os.path.join(ROOT, 'translation', 'refit', '*.jsonl')):
    for i, ln in enumerate(open(p, encoding='utf8'), 1):
        if not ln.strip():
            continue
        n += 1
        try:
            r = json.loads(ln)
            assert 'id' in r and 'ja' in r and 'en' in r
        except Exception as e:
            bad += 1
            print('BAD', p, i, e)
print('lines', n, 'bad', bad)
ids = collections.OrderedDict()
rules = collections.Counter()
for ln in open(os.path.join(ROOT, 'build', 's7n_changed_ids.tsv'), encoding='utf8'):
    p = ln.rstrip('\n').split('\t')
    if p[0] not in ids:
        ids[p[0]] = p
        rules[p[3].split('+')[0][:3]] += 1
print('unique changed ids', len(ids), dict(rules))
