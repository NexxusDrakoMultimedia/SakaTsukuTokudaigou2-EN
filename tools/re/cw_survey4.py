"""All records whose ja merely CONTAINS a club-word katakana (not equal): class summary.  usage: python -I -X utf8 tools/re/cw_survey4.py"""
import json, glob, re, unicodedata, collections, csv
N = lambda s: unicodedata.normalize('NFKC', s)
words = {}
for row in csv.reader(open('translation/clubwords_art.tsv', encoding='utf8'), delimiter='\t'):
    if row[0].isdigit(): words[int(row[0])] = row
nw = {N(r[1]): int(k) for k, r in words.items()}
cnt = collections.Counter()
for f in sorted(glob.glob('translation/*.jsonl')):
    for l in open(f, encoding='utf8'):
        r = json.loads(l); j = N(r['ja'])
        if j in nw: continue
        for w, k in nw.items():
            if w in j:
                rest = j.replace(w, '#')
                key = (f[-34:-6], re.sub(r'[0-9a-f]{3,}', '', (r.get('ctx') or '')[:22]), rest[:14] if len(rest) < 16 else 'long')
                cnt[key] += 1
for k, v in sorted(cnt.items()): print(v, k)
