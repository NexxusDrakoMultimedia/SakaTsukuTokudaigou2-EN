"""Bank demand model.  For each overlay string: relocatable? (has pointer refs, not pinned stride table, no interior ptrs).
English length model: EN bytes = ceil(r * JP bytes) (r = ratio).  A string must go to the bank when it is relocatable and
EN+1 > max_bytes.  Non-relocatable overflow = cannot be translated at that ratio (would stay Japanese / must be shortened)."""
import sys,json,glob,os,math
sys.path.insert(0,'tools')
import textdb
rows=[]
for p in sorted(glob.glob('translation/FLOW_PRG__*.jsonl'))+sorted(glob.glob('translation/ATFIRST__*.jsonl')):
    src=os.path.basename(p)[:-6]
    for l in open(p,encoding='utf8'):
        r=json.loads(l)
        eb=len(textdb.encode_text(r['ja']))
        ctx=r.get('ctx') or ''
        reloc= bool(r.get('refs')) and 'stride-table' not in ctx and 'interior-ptrs' not in ctx
        rows.append((src,r['id'],r['ja'],eb,r['max_bytes'] or eb+1,reloc,r.get('refs') or 0))
n=len(rows)
print('overlay records',n,'relocatable',sum(1 for x in rows if x[5]),'non-relocatable (orphan/pinned/interior)',sum(1 for x in rows if not x[5]))
nrel_b=sum(x[3]+1 for x in rows if x[5]); nn_b=sum(x[3]+1 for x in rows if not x[5])
print('JP bytes relocatable',nrel_b,'non-relocatable',nn_b)
for ratio in (1.0,1.25,1.5,1.75,2.0):
    ov=0; ovn=0; bank=0; ban_u={}; nonreloc_over=0; cnt=0
    for src,i,ja,eb,mb,rel,refs in rows:
        en=math.ceil(ratio*eb)+1
        if en>mb:
            if rel:
                cnt+=1; bank+=en
                k=ja
                if k not in ban_u: ban_u[k]=en
            else: nonreloc_over+=1
    print('r=%.2f: banked strings %d, bank bytes (no dedupe) %d, dedupe-by-ja %d (unique %d); non-relocatable overflow strings %d'%(ratio,cnt,bank,sum(ban_u.values()),len(ban_u),nonreloc_over))
# per overlay at r=1.5 : bank bytes, and with aligned 4
res={}
for src,i,ja,eb,mb,rel,refs in rows:
    en=math.ceil(1.5*eb)+1
    if rel and en>mb: res[src]=res.get(src,0)+en
print('r=1.5 per-overlay bank bytes top:',sorted(res.items(),key=lambda x:-x[1])[:12])
print('r=1.5 overlays needing bank',len(res),'sum',sum(res.values()))
