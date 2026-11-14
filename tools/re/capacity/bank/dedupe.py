"""How well does a shared (global) bank pay off?  r=1.5 model.  Strings that overflow their slot and are relocatable, grouped by
identical Japanese text.  Greedy: store the entries with most copies first until the budget is full."""
import sys,json,glob,os,math,collections
sys.path.insert(0,'tools')
import textdb
R=float(sys.argv[1]) if len(sys.argv)>1 else 1.5
g=collections.defaultdict(lambda:[0,0,set()])   # ja -> [copies, en_len, overlays]
tot=0;totc=0
for p in sorted(glob.glob('translation/FLOW_PRG__*.jsonl'))+sorted(glob.glob('translation/ATFIRST__*.jsonl')):
    src=os.path.basename(p)[:-6]
    for l in open(p,encoding='utf8'):
        r=json.loads(l)
        ctx=r.get('ctx') or ''
        if not r.get('refs') or 'stride-table' in ctx or 'interior-ptrs' in ctx: continue
        eb=len(textdb.encode_text(r['ja']))
        en=math.ceil(R*eb)+1
        if en<=(r['max_bytes'] or 0): continue
        e=g[r['ja']]; e[0]+=1; e[1]=en; e[2].add(src); tot+=en; totc+=1
print('r=%.2f overflow relocatable strings %d, bytes %d, unique ja %d, unique bytes %d'%(R,totc,tot,len(g),sum(v[1] for v in g.values())))
for k in (2,3,5,10,20,50):
    ent=[v for v in g.values() if len(v[2])>=k]
    print('  strings present in >=%2d overlays: %6d unique, bank bytes %8d, strings served %7d (%.1f%% of all overflow strings), bytes served %8d'%(k,len(ent),sum(v[1] for v in ent),sum(v[0] for v in ent),100*sum(v[0] for v in ent)/totc,sum(v[0]*v[1] for v in ent)))
for budget in (16612,150263,215799,300000):
    items=sorted(g.values(),key=lambda v:-(v[0]*v[1])/v[1])   # by copies desc (value density = copies)
    used=0;served=0;nb=0;sb=0
    for v in items:
        if used+v[1]>budget: continue
        used+=v[1]; served+=v[0]; nb+=1; sb+=v[0]*v[1]
    print('budget %7d: stores %5d unique entries (%d B), serves %6d overflow strings = %.1f%% of strings, %.1f%% of overflow bytes'%(budget,nb,used,served,100*served/totc,100*sb/tot))
