"""Draw the stratified sample (seeded).  Output: sample_src.tsv (idx, cat, id, max_bytes, ja)."""
import os,sys,random
os.chdir(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))); sys.path.insert(0,'tools/re/capacity/ratio')
from common import *
rows=[r for r in load() if is_ov(r)]
C=collections.defaultdict(list)
for r in rows: C[category(r)].append(r)
tot=sum(nchars(r['ja']) for r in rows)
N0=520
alloc={}
for k,v in C.items():
    share=sum(nchars(r['ja']) for r in v)/tot
    alloc[k]=max(40,round(N0*share))
print(alloc,sum(alloc.values()))
rnd=random.Random(20261110)
out=[]
for k in sorted(C):
    pool=C[k][:]; rnd.shuffle(pool)
    seen=set(); got=[]
    # markup top-up: guarantee >=25% of strings with control tokens where population has them
    tokd=[r for r in pool if re.search(r'@[A-Z]/|%[sd]|#[a-z0-9]+#',r['ja'])]
    want_tok=min(len(tokd),max(5,round(alloc[k]*len(tokd)/len(pool)))) if (tokd and k.startswith(('prose','help','label','numunit'))) else 0
    for r in tokd:
        if len(got)>=want_tok: break
        if r['ja'] in seen: continue
        seen.add(r['ja']); got.append(r)
    for r in pool:
        if len(got)>=alloc[k]: break
        if r['ja'] in seen: continue
        seen.add(r['ja']); got.append(r)
    out+= [(k,r) for r in got]
    print(k,len(C[k]),len(got),'pop token share %.2f'%(len(tokd)/len(pool)),'sample token share %.2f'%(sum(1 for r in got if re.search(r'@[A-Z]/|%[sd]|#[a-z0-9]+#',r['ja']))/len(got)))
with open('tools/re/capacity/ratio/sample_src.tsv','w',encoding='utf8') as f:
    for i,(k,r) in enumerate(out):
        f.write(chr(9).join([str(i),k,r['id'],str(r['max_bytes']),r['ja'].replace(chr(92),chr(92)*2).replace(chr(10),chr(92)+'n')])+chr(10))
print(len(out))
