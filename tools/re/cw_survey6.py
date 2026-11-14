"""hwpool runs containing club words.  usage: python -I -X utf8 tools/re/cw_survey6.py"""
import json, glob, re, unicodedata, collections, csv
N = lambda s: unicodedata.normalize('NFKC', s)
words = {}
for row in csv.reader(open('translation/clubwords_art.tsv', encoding='utf8'), delimiter='\t'):
    if row[0].isdigit(): words[int(row[0])] = row
nw = {N(r[1]): int(k) for k, r in words.items()}
c = collections.defaultdict(list)
for f in sorted(glob.glob('translation/*.jsonl')):
    for l in open(f, encoding='utf8'):
        r = json.loads(l); ctx = r.get('ctx') or ''
        if 'hwpool' in ctx and N(r['ja']) in nw:
            c[(f[-30:-6], ctx)].append(nw[N(r['ja'])])
for k, v in c.items(): print(k, len(v), sorted(v)[:12])
