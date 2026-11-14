"""Survey DB records whose ja is (or contains) a club-word katakana.  usage: python -I -X utf8 tools/re/cw_survey.py"""
import json, glob, re, unicodedata, collections, csv
N = lambda s: unicodedata.normalize('NFKC', s)
words = {}
for row in csv.reader(open('translation/clubwords_art.tsv', encoding='utf8'), delimiter='\t'):
    if row[0].isdigit(): words[int(row[0])] = row
nw = {N(r[1]): int(k) for k, r in words.items()}
exact = collections.defaultdict(list); contains = collections.defaultdict(list)
for f in sorted(glob.glob('translation/*.jsonl')):
    for l in open(f, encoding='utf8'):
        r = json.loads(l); j = N(r['ja'])
        for w, k in nw.items():
            if j == w: exact[k].append((f, r))
            elif w in j: contains[k].append((f, r))
sig = collections.Counter()
for k in sorted(exact):
    for f, r in exact[k]:
        c = r.get('ctx') or ''
        s = (r.get('fmt'), re.sub(r'[0-9a-f]{4,}|\[\d+/\d+\]|n=\d+', '#', c)[:50], r.get('max_bytes'))
        sig[s] += 1
for s, n in sig.most_common(): print(n, s)
print('exact total', sum(len(v) for v in exact.values()), 'contains-only', sum(len(v) for v in contains.values()))
for k in sorted(contains):
    for f, r in contains[k][:4]: print('CONTAINS', k, f[-30:], r['id'], repr(r['ja'])[:50], '|', r['en'][:50], '|', r.get('ctx'))
