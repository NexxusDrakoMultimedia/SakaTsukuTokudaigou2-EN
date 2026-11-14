from common import *
rows=load()
fl=[r for r in rows if r['file'].startswith('FLOW_PRG') or r['file'].startswith('ATFIRST')]
print(len(fl))
# length histogram on JP visible chars
def cat0(r):
    return 'orph' if r.get('orphan') else 'ref'
import statistics
c=collections.Counter(); v=collections.Counter()
for r in fl:
    n=nchars(r['ja']); b=min(n//5*5,60)
    c[(cat0(r),b)]+=1; v[(cat0(r),b)]+=n
for k in sorted(c): print(k,c[k],v[k])
# per file tot
t=collections.defaultdict(lambda:[0,0,0,0,0])
for r in fl:
    x=t[r['file']]; x[0]+=1; x[1]+=r['max_bytes']; 
    if r.get('orphan'): x[3]+=1; x[4]+=r['max_bytes']
    else: x[2]+=r['max_bytes']
for k,x in sorted(t.items(),key=lambda a:-a[1][1])[:12]: print(k,x)
