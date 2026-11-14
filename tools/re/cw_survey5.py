"""Refit overlay records that concern club words.  usage: python -I -X utf8 tools/re/cw_survey5.py"""
import json, glob, unicodedata, collections, csv
N = lambda s: unicodedata.normalize('NFKC', s)
words = {}
for row in csv.reader(open('translation/clubwords_art.tsv', encoding='utf8'), delimiter='\t'):
    if row[0].isdigit(): words[int(row[0])] = row
nw = {N(r[1]): int(k) for k, r in words.items()}
c = collections.Counter(); cls = collections.Counter(); tot = 0
for f in glob.glob('translation/refit/*.jsonl'):
    for l in open(f, encoding='utf8'):
        r = json.loads(l); tot += 1; cls[r.get('cls')] += 1
        if N(r['ja']) in nw or any(w in N(r['ja']) for w in nw):
            c[(r['cls'], N(r['ja']) in nw, r['ja'], r['en'])] += 1
print(tot, dict(cls))
for k, v in sorted(c.items(), key=lambda x: str(x)): print(v, k)
