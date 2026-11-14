import os,sys,random
os.chdir(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))); sys.path.insert(0,'tools/re/capacity/ratio')
from common import *
rows=[r for r in load() if is_ov(r)]
C=collections.defaultdict(list)
for r in rows: C[category(r)].append(r)
tot=sum(nchars(r['ja']) for r in rows)
for k,v in sorted(C.items(),key=lambda x:-sum(jb(r['ja']) for r in x[1])):
    print(k,len(v),len({r['ja'] for r in v}),'jpchars',sum(nchars(r['ja']) for r in v),'jpbytes',sum(jb(r['ja']) for r in v),'maxb',sum(r['max_bytes'] for r in v),'movable',sum(movable(r) for r in v))
random.seed(2)
for k in ('name','place','numunit','label'):
    print('==',k)
    for r in random.sample(C[k],14): print('  ',r['file'][10:],r['max_bytes'],repr(r['ja']),r['ctx'][:30])
