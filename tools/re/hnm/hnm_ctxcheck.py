import glob, json, os, re, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
names = json.load(open(os.path.join(ROOT, 'build', 'hnm_names.json'), encoding='utf-8'))
T = re.compile(r'^tbl@[0-9a-f]+\[\d+/(1270|1268)\]')
bad = collections.Counter(); n = 0
for p in sorted(glob.glob(os.path.join(ROOT, 'translation', 'FLOW_PRG__*.jsonl'))):
    for ln in open(p, encoding='utf-8'):
        if not ln.strip(): continue
        r = json.loads(ln)
        if r['ja'] in names and r['en'] == names[r['ja']]:
            n += 1
            if not (T.match(r.get('ctx') or '') or (r['id'].startswith('FLOW_PRG/HOMETOWN.BIN#') and r.get('max_bytes') == 35)):
                bad[(os.path.basename(p), (r.get('ctx') or '')[:20])] += 1
print(n, dict(bad))
