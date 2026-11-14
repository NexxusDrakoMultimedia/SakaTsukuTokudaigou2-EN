"""tx5: category table of the BCAST.BIN clips (stem without the trailing number) per folder, with counts and an example.
python -I -X utf8 tools/re/tx5_bcast_cats.py   (reads build/tx5/bcast_headers.tsv from tx5_bcast_scan.py)"""
import os, re, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'build', 'tx5', 'bcast_headers.tsv'), encoding='utf8')][1:]
cat = collections.defaultdict(list)
for r in rows:
    folder, f = r[2].split('\\')
    stem = f.rsplit('.', 1)[0]
    c = re.sub(r'_?\d+[a-z]?$', '', stem)
    if folder == 'name':
        c = re.sub(r'_\d+$', '', c)
        c = c[:12]
    cat[(folder, c)].append(r[5])
for k in sorted(cat):
    v = cat[k]
    if k[0] == 'name':
        continue
    print('%-3s %-22s %5d  distinct %5d  e.g. %s' % (k[0], k[1], len(v), len(set(v)), v[0][:40]))
print('name groups', sum(1 for k in cat if k[0] == 'name'), sum(len(v) for k, v in cat.items() if k[0] == 'name'))
