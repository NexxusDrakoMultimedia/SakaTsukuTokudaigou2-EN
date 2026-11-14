"""Size of the translation job: JP bytes per source (from translation/*.jsonl), duplicates, pinned/orphan counts."""
import json,glob,os,collections
tot=collections.OrderedDict()
allja=collections.Counter()
rows=[]
for p in sorted(glob.glob('translation/*.jsonl')):
    n=0;b=0;orph=0;refs0=0;sj=set();ub=0
    for l in open(p,encoding='utf8'):
        r=json.loads(l); n+=1; mb=r['max_bytes'] or len(r['ja'].encode('cp932','replace'))+1; b+=mb; 
        if r.get('orphan'): orph+=1
        if r['ja'] not in sj: sj.add(r['ja']); umb=r['max_bytes'] or len(r['ja'].encode('cp932','replace'))+1; b+=mb
        allja[r['ja']]+=1
    rows.append((os.path.basename(p)[:-6],n,b,orph,len(sj),ub))
tn=sum(r[1] for r in rows); tb=sum(r[2] for r in rows)
fl=[r for r in rows if r[0].startswith(('FLOW_PRG','ATFIRST'))]
print('all sources: records',tn,'JP bytes (incl NUL, max_bytes)',tb)
print('overlays (FLOW_PRG+ATFIRST): files',len(fl),'records',sum(r[1] for r in fl),'JP bytes',sum(r[2] for r in fl),'orphans',sum(r[3] for r in fl),'unique ja per file sum',sum(r[4] for r in fl),'unique bytes per file sum',sum(r[5] for r in fl))
# global unique across overlays
g=set(); gb=0
for p in sorted(glob.glob('translation/FLOW_PRG__*.jsonl'))+sorted(glob.glob('translation/ATFIRST__*.jsonl')):
    for l in open(p,encoding='utf8'):
        r=json.loads(l)
        if r['ja'] not in g: g.add(r['ja']); gmb=r['max_bytes'] or len(r['ja'].encode('cp932','replace'))+1; b+=mb
print('globally unique ja strings in overlays',len(g),'bytes',gb)
rows.sort(key=lambda r:-r[2])
for r in rows[:25]: print('%-40s n=%6d bytes=%8d orph=%5d uniq=%6d uniqbytes=%8d'%r)
