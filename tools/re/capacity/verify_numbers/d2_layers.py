import sys,json,glob,os,random,collections,re,hashlib
sys.path.insert(0,'tools'); import textdb
CTRL=re.compile(r'@[A-Z]/|@|#[a-z0-9]+#|%[0-9]*[sdDm]')
def grp(f):
    f=f.split('/')[-1].split('.BIN')[0]
    if f=='HELP': return 'HELP'
    if f in('NEWS','NEWS_ED'): return 'NEWS'
    if f.startswith('EVENT'): return 'EVENT'
    return f if f in('MEETING','TRAINING') else 'OTHER'
def klass(ja):
    n=len(CTRL.sub('',ja).replace('\n',''))
    return 'long' if n>=12 else ('mid' if n>=5 else 'short')
S=collections.defaultdict(list); C=collections.defaultdict(list)
for l in open('tools/re/capacity/ratio/sample.jsonl',encoding='utf-8'):
    r=json.loads(l)
    if r['skip']: continue
    q=(len(r['en'].encode())+1)/(len(textdb.encode_text(r['ja']))+1)
    k=(grp(r['id'].split('#')[0]),klass(r['ja'])); S[k].append(q); C[k[1]].append(q)
def run(scale):
    N=L0=lo=hi=0
    for f in sorted(glob.glob('translation/*.jsonl')):
        nm=os.path.basename(f)
        if not nm.startswith(('FLOW_PRG','ATFIRST')): continue
        g=grp(nm.replace('__','/')); recs=[json.loads(l) for l in open(f,encoding='utf-8')]
        mov=[];fx=[]
        for r in recs:
            r['off']=int(r['id'].split('#')[1],16); jb=textdb.encode_text(r['ja']); r['j']=len(jb)+1
            k=(g,klass(r['ja'])); pool=S[k] if len(S[k])>=5 else C[k[1]]; pool=sorted(pool)
            u=int.from_bytes(hashlib.blake2b(bytes(jb),digest_size=4).digest(),'little')/2**32
            r['e']=max(2,round(pool[min(len(pool)-1,int(u*len(pool)))]*scale*r['j']))
            (fx if (r['refs'] is None or 'stride-table' in r['ctx'] or 'interior-ptrs' in r['ctx']) else mov).append(r)
        N+=len(recs); fxfit=sum(r['e']<=r['max_bytes'] for r in fx)
        L0+=fxfit+sum(r['e']<=r['max_bytes'] for r in mov)
        mov.sort(key=lambda r:r['off']); pools=[];cur=[]
        for r in mov:
            if cur and cur[-1]['off']+cur[-1]['max_bytes']==r['off']: cur.append(r)
            else:
                if cur: pools.append(cur)
                cur=[r]
        if cur: pools.append(cur)
        fit=0;cap_t=0
        for p in pools:
            cap=sum(r['max_bytes'] for r in p); cap_t+=cap; need=sum(r['e'] for r in p); n=len(p)
            for r in sorted(p,key=lambda r:r['e']-r['j'],reverse=True):
                if need<=cap: break
                need-=r['e']-r['j']; n-=1
            fit+=n
        lo+=fxfit+fit
        need=sum(r['e'] for r in mov); n=len(mov)
        for r in sorted(mov,key=lambda r:r['e']-r['j'],reverse=True):
            if need<=cap_t: break
            need-=r['e']-r['j']; n-=1
        hi+=fxfit+n
    return N,L0/N,lo/N,hi/N
for s in (1.0,0.85):
    N,a,b,c=run(s); print('scale %.2f: L0 %.1f%%  L0+L1 no-cross %.1f%%  L0+L1 perfect-cross bound %.1f%%'%(s,100*a,100*b,100*c))
