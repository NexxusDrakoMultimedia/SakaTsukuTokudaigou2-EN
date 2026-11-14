"""hwptr tables containing club words: table size distribution.  usage: python -I -X utf8 tools/re/cw_survey3.py"""
import json, glob, re, unicodedata, collections, csv
N = lambda s: unicodedata.normalize('NFKC', s)
words = {}
for row in csv.reader(open('translation/clubwords_art.tsv', encoding='utf8'), delimiter='\t'):
    if row[0].isdigit(): words[int(row[0])] = row
nw = {N(r[1]): int(k) for k, r in words.items()}
tabs = collections.defaultdict(list)
for f in sorted(glob.glob('translation/*.jsonl')):
    for l in open(f, encoding='utf8'):
        r = json.loads(l); c = r.get('ctx') or ''
        m = re.search(r'tbl@([0-9a-f]+)\[(\d+)/(\d+)\]', c)
        if m and r.get('fmt') == 'hwptr':
            tabs[(f[-28:-6], m.group(1), int(m.group(3)))].append((int(m.group(2)), N(r['ja']), r['en']))
        elif r.get('fmt') == 'hwptr':
            pass
for (f, a, n), v in sorted(tabs.items()):
    hit = [x for x in v if x[1] in nw]
    if hit: print(f, a, 'size', n, 'entries', len(v), 'club words', len(hit), 'ex', [(x[0], x[2]) for x in hit[:2]])
