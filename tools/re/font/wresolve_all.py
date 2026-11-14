"""Resolve every pointer table / pointer slot of the text DB to window classes. Output: build/trans/width_refs.json
{source: {key: {kind, off, n, recs, refs:[{site, func, direct, closure, callers}]}}}.   key = 'tbl@OFF' or 'ptr@OFF'

python -I -X utf8 tools/re/font/wresolve_all.py [OVERLAY ...]"""
import os, sys, re, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import translib as T
from wresolve import Resolver, cls_name

only = set(sys.argv[1:])
db = T.load_db()
tabs = collections.defaultdict(lambda: collections.defaultdict(lambda: {'recs': 0, 'n': 0}))
for fi, li, r in db.records():
    ctx = r.get('ctx') or ''
    src = T.source_of(r['id'])
    if not (src.startswith('FLOW_PRG/') or src.startswith('ATFIRST/')):
        continue
    m = re.match(r'(tbl|ptr)@([0-9a-f]+)(?:\[(\d+)/(\d+)\])?', ctx)
    if not m:
        continue
    key = '%s@%s' % (m.group(1), m.group(2))
    e = tabs[src][key]
    e['kind'] = m.group(1)
    e['off'] = int(m.group(2), 16)
    e['recs'] += 1
    if m.group(4):
        e['n'] = int(m.group(4))
out = {}
for src in sorted(tabs):
    name = src.split('/')[-1]
    if only and name not in only:
        continue
    try:
        res = Resolver(name)
    except SystemExit:
        continue
    ov = res.ov
    base = ov.base
    # callers map: function -> set of caller functions
    callers = collections.defaultdict(set)
    for f, lst in res.calls_by_func.items():
        for a, t, kind in lst:
            tf = res.func_of(t) if t and ov.base <= t < ov.end else None
            if tf is not None:
                callers[tf].add(f)
    o = {}
    for key, e in tabs[src].items():
        off = e['off']
        # ATFIRST/HELP.BIN has another base; the tool uses the overlay base from overlays.tsv
        if e['kind'] == 'tbl':
            lo, hi = base + off, base + off + 4 * max(e['n'], 1) - 1
            sites = [s for s, v in ov.loads_of(lo, hi)]
        else:
            a = base + off
            sites = ov.pool_loads_at(a) + [s for s, v in ov.loads_of(a, a)]
        refs = []
        for s in sorted(set(sites)):
            f = res.func_of(s)
            if f is None:
                continue
            d = sorted(map(cls_name, res.direct(f)))
            c = sorted(map(cls_name, res.closure(f)))
            cs = set()
            for cf in callers.get(f, ()):
                cs |= {cls_name(x) for x in res.closure(cf, 1)}
            refs.append({'site': '%08x' % s, 'func': '%08x' % f, 'direct': d, 'closure': c, 'callers': sorted(cs)})
        o[key] = {'kind': e['kind'], 'off': off, 'n': e['n'], 'recs': e['recs'], 'refs': refs}
    out[src] = {'factories': [(('%08x' % st), ('%08x' % si), cls_name(c)) for st, si, c in res.fac], 'tabs': o}
    print(name, len(o), 'tables', sum(1 for v in o.values() if any(r['direct'] or r['closure'] for r in v['refs'])), 'with factory evidence')
p = os.path.join(ROOT, 'build', 'trans', 'width_refs.json')
if only and os.path.exists(p):
    old = json.load(open(p))
    old.update(out)
    out = old
json.dump(out, open(p, 'w'), indent=0)
print('wrote', p)
