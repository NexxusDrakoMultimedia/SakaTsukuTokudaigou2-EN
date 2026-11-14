"""Top-up draw: 4 more 'label' records (3 of the 40 drawn were non-text garbage).  Appends to sample_src.tsv (idx 605..)."""
import os,sys,random
os.chdir(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))); sys.path.insert(0,'tools/re/capacity/ratio')
from common import *
rows=[r for r in load() if is_ov(r)]
have={l.split(chr(9))[2] for l in open('tools/re/capacity/ratio/sample_src.tsv',encoding='utf8')}
havej={l.split(chr(9))[4] for l in open('tools/re/capacity/ratio/sample_src.tsv',encoding='utf8')}
pool=[r for r in rows if category(r)=='label' and r['id'] not in have and r['ja'].replace(chr(10),chr(92)+'n') not in havej]
random.Random(99).shuffle(pool)
out=[]
for r in pool:
    if len(out)>=4: break
    if r.get('orphan'): continue      # skip orphan junk
    out.append(r)
with open('tools/re/capacity/ratio/sample_src.tsv','a',encoding='utf8') as f:
    for k,r in enumerate(out):
        f.write(chr(9).join([str(605+k),'label',r['id'],str(r['max_bytes']),r['ja'].replace(chr(92),chr(92)*2).replace(chr(10),chr(92)+'n')])+chr(10))
        print(605+k,r['id'],r['max_bytes'],r['ja'])
