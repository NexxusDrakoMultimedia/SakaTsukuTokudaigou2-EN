"""List, per club word, the ctx signature groups and sample ids/en.  usage: python -I -X utf8 tools/re/cw_survey2.py [k ...]"""
import json, glob, re, unicodedata, collections, csv, sys
N = lambda s: unicodedata.normalize('NFKC', s)
words = {}
for row in csv.reader(open('translation/clubwords_art.tsv', encoding='utf8'), delimiter='\t'):
    if row[0].isdigit(): words[int(row[0])] = row
nw = {N(r[1]): int(k) for k, r in words.items()}
grp = collections.defaultdict(lambda: collections.defaultdict(list))
for f in sorted(glob.glob('translation/*.jsonl')):
    for l in open(f, encoding='utf8'):
        r = json.loads(l); j = N(r['ja'])
        if j in nw:
            c = r.get('ctx') or ''
            if r.get('fmt') == 'hwptr' and 'hwptr tbl' in c: s = 'hwptr-tbl'
            elif r.get('fmt') == 'hwptr': s = 'hwpool'
            elif r.get('fmt') == 'recarr': s = re.sub(r'n=\d+ ', '', c.split(' modeshare')[0]) 
            elif r.get('fmt') == 'bcast': s = 'bcast ' + re.sub(r'_\d+|yh_name_.*', '', c.split(' seg')[0])
            else: s = 'other:' + re.sub(r'#?\d+', '#', c)
            grp[nw[j]][s].append((f[-28:-6], r['en'], r['id'].split('#')[1], r.get('skip')))
want = [int(a) for a in sys.argv[1:]]
summ = collections.defaultdict(set)
for k in sorted(grp):
    for s, v in grp[k].items(): summ[s].add(k)
for s, ks in sorted(summ.items()): print(len(ks), s, sorted(ks))
for k in want:
    print('==', k, words[k][2], words[k][9])
    for s, v in grp[k].items(): print('  ', s, len(v), collections.Counter(x[1] for x in v).most_common(4))
