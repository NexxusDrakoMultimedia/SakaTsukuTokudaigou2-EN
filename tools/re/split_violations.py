"""Split build/trans/width_violations.tsv into build/trans/wfix/NNNN.json (one file per shard, rows as dicts).
   Prints 'shard count' lines; python -I -X utf8 tools/re/split_violations.py"""
import csv, json, os, collections
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src = os.path.join(root, 'build', 'trans', 'width_violations.tsv')
out = os.path.join(root, 'build', 'trans', 'wfix')
os.makedirs(out, exist_ok=True)
for f in os.listdir(out):
    os.remove(os.path.join(out, f))
by = collections.defaultdict(list)
with open(src, encoding='utf8', newline='') as fh:
    for row in csv.DictReader(fh, delimiter='\t'):
        by[int(row['shard'])].append(row)
for n, rows in sorted(by.items()):
    with open(os.path.join(out, '%04d.json' % n), 'w', encoding='utf8') as fh:
        json.dump({'shard': n, 'violations': rows}, fh, ensure_ascii=False, indent=0)
    print(n, len(rows))
