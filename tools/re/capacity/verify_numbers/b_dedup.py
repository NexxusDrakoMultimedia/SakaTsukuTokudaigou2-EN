import sys,json,glob,os,collections
sys.path.insert(0,'tools'); import textdb
enc=lambda s: bytes(textdb.encode_text(s))
tot=collections.Counter(); per={}
for f in sorted(glob.glob('translation/*.jsonl')):
    nm=os.path.basename(f)
    if not (nm.startswith('FLOW_PRG') or nm.startswith('ATFIRST')): continue
    k=nm[:-6]; recs=[json.loads(l) for l in open(f,encoding='utf-8')]
    mov=[]; fixed=0
    for r in recs:
        if r['refs'] is None or 'stride-table' in r['ctx'] or 'interior-ptrs' in r['ctx']: fixed+=1; continue
        r['off']=int(r['id'].split('#')[1],16); r['b']=enc(r['ja']); mov.append(r)
    mov.sort(key=lambda r:r['off'])
    pools=[]; cur=[]
    for r in mov:
        if cur and cur[-1]['off']+cur[-1]['max_bytes']==r['off']: cur.append(r)
        else:
            if cur: pools.append(cur)
            cur=[r]
    if cur: pools.append(cur)
    c=collections.Counter(); c['fixed']=fixed; c['mov']=len(mov); c['pools']=len(pools)
    allb=collections.Counter()
    for p in pools:
        cap=sum(r['max_bytes'] for r in p); need=sum(len(r['b'])+1 for r in p)
        c['cap']+=cap; c['jp']+=need
        d=collections.Counter(r['b'] for r in p)
        dup=sum((n-1)*(len(b)+1) for b,n in d.items()); c['dup_pool']+=dup
        # suffix on distinct strings (char level on ja text)
        ds=sorted({r['ja'] for r in p},key=len,reverse=True)
        longer=set(); suf=0
        # check suffix: s is suffix of longer distinct t
        sset=set(ds)
        # all proper suffixes of each distinct string
        cover=set()
        for t in ds:
            for i in range(1,len(t)): 
                if t[i:] in sset: cover.add(t[i:])
        suf=sum(len(enc(s))+1 for s in cover); c['suf_pool_extra']+=suf
        allb.update(r['b'] for r in p)
    dupall=sum((n-1)*(len(b)+1) for b,n in allb.items()); c['dup_image']+=dupall
    per[k]=c; tot.update(c)
print(dict(tot))
print('dup_pool %% of movable jp: %.2f' % (100*tot['dup_pool']/tot['jp']))
print('slack',tot['cap']-tot['jp'])
for k,c in sorted(per.items(),key=lambda x:-x[1]['dup_pool'])[:8]: print(k,c['dup_pool'],c['dup_image'],c['suf_pool_extra'])
