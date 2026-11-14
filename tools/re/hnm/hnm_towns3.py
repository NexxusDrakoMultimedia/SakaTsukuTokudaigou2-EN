"""All 1270 records: name (+2) and reading (+37) with current en; join with pointer table entries by ja. Output build/hnm_all.tsv"""
import json, os, re, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
recs = [json.loads(l) for l in open(os.path.join(ROOT, 'translation', 'FLOW_PRG__HOMETOWN.BIN.jsonl'), encoding='utf-8')]
byoff = {int(r['id'].split('#')[1], 16): r for r in recs}
BASE = 0x15970
tb = collections.defaultdict(list)
for r in recs:
    m = re.match(r'tbl@(\w+)\[(\d+)/1270\]', r.get('ctx') or '')
    if m: tb[r['ja']].append((m.group(1), int(m.group(2)), r['en'], r['max_bytes']))
n_name = n_read = 0
rows = []
for k in range(1270):
    o = BASE + 126 * k + 2
    a = byoff.get(o); b = byoff.get(o + 35)
    if a: n_name += 1
    if b: n_read += 1
    rows.append((k, hex(o), a and a['ja'], a and a['en'], b and b['ja'], b and b['en'], tb.get(a['ja']) if a else None))
print(n_name, n_read)
with open(os.path.join(ROOT, 'build', 'hnm_all.tsv'), 'w', encoding='utf-8') as f:
    for r in rows:
        f.write('\t'.join(str(x) for x in r) + '\n')
