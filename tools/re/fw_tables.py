"""fw_tables.py SOURCE : group the pointer-table records ('tbl@HEX[i/n]') of one source by table, print n, slot sizes, first ja/en and id range."""
import json, sys, re, collections
p = 'translation/%s.jsonl' % sys.argv[1].replace('/', '__')
T = collections.OrderedDict()
for ln in open(p, encoding='utf8'):
    r = json.loads(ln)
    m = re.search(r'tbl@([0-9a-f]+)\[(\d+)/(\d+)\]', r.get('ctx') or '')
    if not m:
        continue
    k = (m.group(1), int(m.group(3)))
    t = T.setdefault(k, {'slots': collections.Counter(), 'first': None, 'last': None, 'n': 0, 'enlen': collections.Counter()})
    t['slots'][r['max_bytes']] += 1
    t['n'] += 1
    t['first'] = t['first'] or (r['ja'][:12], r['en'][:14])
    t['last'] = (r['ja'][:12], r['en'][:14])
    t['enlen'][len(r['en'])] += 0
for k, t in T.items():
    print(k, t['n'], dict(t['slots']), t['first'], t['last'])
