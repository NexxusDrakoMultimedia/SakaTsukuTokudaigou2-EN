import sys,random,collections,importlib.util
sys.path.insert(0,'tools')
spec=importlib.util.spec_from_file_location('rc','tools/re/capacity/ratio/common.py'); rc=importlib.util.module_from_spec(spec); spec.loader.exec_module(rc)
rows=[r for r in rc.load() if rc.is_ov(r)]
byc=collections.defaultdict(list)
for r in rows: byc[rc.category(r)].append(r)
rnd=random.Random(3)
for c in ('place','name'):
    v=byc[c]; print(c,len(v),'distinct ja',len({r['ja'] for r in v}),'orphan',sum(r['refs'] is None for r in v))
    # distribution of last char
    suf=collections.Counter(r['ja'].strip()[-1] for r in v); print(' last chars',suf.most_common(10))
    print(' files',collections.Counter(r['file'] for r in v).most_common(5))
    print(' sample',[ (r['ja'],r['file'].split('__')[1][:8]) for r in rnd.sample(v,25)])
