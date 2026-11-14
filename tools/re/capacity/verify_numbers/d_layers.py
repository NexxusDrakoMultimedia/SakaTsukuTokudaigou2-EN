import sys,json,glob,os,random,collections
sys.path.insert(0,'tools'); import textdb
def run(scale,seed=5,spread=0.5):
    rnd=random.Random(seed)
    N=0; L0=0; L1lo=0; L1hi=0
    for f in sorted(glob.glob('translation/*.jsonl')):
        nm=os.path.basename(f)
        if not nm.startswith(('FLOW_PRG','ATFIRST')): continue
        recs=[json.loads(l) for l in open(f,encoding='utf-8')]
        mov=[];fx=[]
        for r in recs:
            r['off']=int(r['id'].split('#')[1],16); j=len(textdb.encode_text(r['ja']))
            r['e']=max(1,round(j*scale*(1+spread*rnd.uniform(-1,1))))+1; r['j']=j+1
            (fx if (r['refs'] is None or 'stride-table' in r['ctx'] or 'interior-ptrs' in r['ctx']) else mov).append(r)
        N+=len(recs)
        fxfit=sum(r['e']<=r['max_bytes'] for r in fx)
        L0+=fxfit+sum(r['e']<=r['max_bytes'] for r in mov); 
        mov.sort(key=lambda r:r['off']); pools=[];cur=[]
        for r in mov:
            if cur and cur[-1]['off']+cur[-1]['max_bytes']==r['off']: cur.append(r)
            else:
                if cur: pools.append(cur)
                cur=[r]
        if cur: pools.append(cur)
        fit_no=0; spare=0; need_tot=0; cap_tot=0
        for p in pools:
            cap=sum(r['max_bytes'] for r in p); need=sum(r['e'] for r in p)
            cap_tot+=cap
            if need<=cap: fit_no+=len(p); spare+=cap-need
            else:
                # revert largest growth first
                ps=sorted(p,key=lambda r:r['e']-r['j'],reverse=True); n=len(p)
                while need>cap and ps:
                    r=ps.pop(0); need-= r['e']-r['j']; n-=1
                    # reverting leaves JP of r.j bytes: need accounts relative to JP
                fit_no+=n
        L1lo+=fxfit+fit_no
        # upper bound cross-pool: reverted strings can instead be moved if total spare allows; approximate by image-wide total
        need_img=sum(r['e'] for r in mov); 
        if need_img<=cap_tot: L1hi+=fxfit+len(mov)
        else:
            ps=sorted(mov,key=lambda r:r['e']-r['j'],reverse=True); n=len(mov)
            while need_img>cap_tot and ps:
                r=ps.pop(0); need_img-=r['e']-r['j']; n-=1
            L1hi+=fxfit+n
    return N,L0/N,L1lo/N,L1hi/N
for s in (1.214,1.033):
    N,a,b,c=run(s); print('scale %.3f N=%d L0 %.3f  L0+L1(no cross) %.3f  L0+L1(perfect cross, image-wide bound) %.3f'%(s,N,a,b,c))
