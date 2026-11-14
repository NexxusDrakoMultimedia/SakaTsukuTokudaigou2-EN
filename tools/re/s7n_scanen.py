"""s7n: list records whose EN contains a given regex.  usage: s7n_scanen.py out.tsv REGEX"""
import json, glob, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rx = re.compile(sys.argv[2])
rows = []
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
    for ln in open(p, encoding='utf8'):
        if not ln.strip():
            continue
        r = json.loads(ln)
        en = r.get('en') or ''
        m = rx.search(en)
        if m:
            rows.append('\t'.join([r['id'], m.group(0), r['ja'].replace('\n', '\\n')[:60], en.replace('\n', '\\n')[:140], str(r.get('max_bytes')), str(r.get('slot', ''))]))
open(sys.argv[1], 'w', encoding='utf8').write('\n'.join(rows) + '\n')
print(len(rows))
