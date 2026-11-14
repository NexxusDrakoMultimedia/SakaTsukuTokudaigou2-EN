import glob, json, os, re, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
TBL = re.compile(r'^tbl@[0-9a-f]+\[\d+/(1270|1268)\]')
by = collections.defaultdict(lambda: collections.defaultdict(list))
over = []
chg = collections.Counter()
nonmun = 0
bak = os.path.join(ROOT, 'build', 'hnm_bak')
for f in sorted(glob.glob(os.path.join(ROOT, 'translation', 'FLOW_PRG__*.jsonl'))):
    n = os.path.basename(f)
    old = {}
    bf = os.path.join(bak, n)
    if os.path.exists(bf):
        for l in open(bf, encoding='utf-8'):
            if l.strip():
                r = json.loads(l); old[r['id']] = r
    for l in open(f, encoding='utf-8'):
        if not l.strip(): continue
        r = json.loads(l)
        if TBL.match(r.get('ctx', '') or ''):
            by[r['ja']][r['en']].append(n)
            mb = r.get('max_bytes')
        o = old.get(r['id'])
        if o and o['en'] != r['en']:
            if not TBL.match(r.get('ctx', '') or '') and not (n.endswith('HOMETOWN.BIN.jsonl')):
                nonmun += 1; print('NONTBL change', n, r['id'], o['en'], '->', r['en'])
            chg[n] += 1
        if o and set(o) != set(r) : print('keys differ', r['id'])
print('files changed', len(chg), 'nontbl', nonmun)
for ja, d in by.items():
    if len(d) > 1:
        print('INCONSISTENT', ja, {k: v[:3] for k, v in d.items()})
