import sys,json,glob,os,re,collections,random
sys.path.insert(0,'tools'); import textdb
CTRL=re.compile(r'@[A-Z]/|@|#[a-z0-9]+#|%[0-9]*[sdDm]')
def grp(path):
    f=path.split('/')[-1].split('.BIN')[0]
    if f=='HELP': return 'HELP'
    if f in('NEWS','NEWS_ED'): return 'NEWS'
    if f.startswith('EVENT'): return 'EVENT'
    return f if f in('MEETING','TRAINING') else 'OTHER'
def klass(ja):
    n=len(CTRL.sub('',ja).replace('\n',''))
    return 'long' if n>=12 else ('mid' if n>=5 else 'short')
pop=collections.Counter(); popn=collections.Counter()
for f in glob.glob('translation/*.jsonl'):
    nm=os.path.basename(f)
    if not nm.startswith(('FLOW_PRG','ATFIRST')): continue
    for l in open(f,encoding='utf-8'):
        r=json.loads(l); k=(grp(nm.replace('__','/')),klass(r['ja'])); pop[k]+=len(textdb.encode_text(r['ja']))+1; popn[k]+=1
S=collections.defaultdict(lambda:[0,0,0])
rows=[json.loads(l) for l in open('tools/re/capacity/ratio/sample.jsonl',encoding='utf-8')]
rows=[r for r in rows if not r['skip']]
for r in rows:
    k=(grp(r['id'].split('#')[0]),klass(r['ja'])); s=S[k]
    s[0]+=1; s[1]+=len(textdb.encode_text(r['ja']))+1; s[2]+=len(r['en'].encode())+1
tp=sum(pop.values()); est=0; miss=0
for k,v in sorted(pop.items(),key=lambda x:-x[1]):
    s=S.get(k)
    print(k,'pop n=%d jp=%d (%.1f%%)'%(popn[k],v,100*v/tp),'sample n=%d ratio=%s'%(s[0] if s else 0,'%.3f'%(s[2]/s[1]) if s else '-'))
# fallback: if bin empty use same class across groups
cl=collections.defaultdict(lambda:[0,0])
for k,s in S.items(): cl[k[1]][0]+=s[1]; cl[k[1]][1]+=s[2]
for k,v in pop.items():
    s=S.get(k)
    if s and s[0]>=5: est+=v*s[2]/s[1]
    else: est+=v*cl[k[1]][1]/cl[k[1]][0]; miss+=v
print('reweighted population EN/JP = %.3f (bytes using class-fallback: %.1f%%)'%(est/tp,100*miss/tp))
# bootstrap of sample byte ratio
rnd=random.Random(1); jr=[(len(textdb.encode_text(r['ja']))+1,len(r['en'].encode())+1) for r in rows]
bs=[]
for _ in range(2000):
    s=[rnd.choice(jr) for _ in jr]; bs.append(sum(e for j,e in s)/sum(j for j,e in s))
bs.sort(); print('sample raw ratio %.3f bootstrap95 [%.3f,%.3f]'%(sum(e for j,e in jr)/sum(j for j,e in jr),bs[50],bs[1950]))
print('--- per-string in-place fit (en+NUL <= max_bytes) reweighted by string COUNT')
F=collections.defaultdict(lambda:[0,0]); import statistics as st
for r in rows:
    k=(grp(r['id'].split('#')[0]),klass(r['ja'])); F[k][0]+=1; F[k][1]+= (len(r['en'].encode())+1<=r['max_bytes'])
clf=collections.defaultdict(lambda:[0,0])
for k,v in F.items(): clf[k[1]][0]+=v[0]; clf[k[1]][1]+=v[1]
tn=sum(popn.values()); fit=0
for k,n in popn.items():
    v=F.get(k)
    f=(v[1]/v[0]) if (v and v[0]>=5) else clf[k[1]][1]/clf[k[1]][0]
    fit+=n*f
print('reweighted fit share by count: %.3f'%(fit/tn), 'raw sample: %.3f'%(sum(v[1] for v in F.values())/sum(v[0] for v in F.values())))
for c,v in clf.items(): print(c,v[0],'%.3f'%(v[1]/v[0]))
rr=[(len(r['en'].encode())+1)/(len(textdb.encode_text(r['ja']))+1) for r in rows]
print('per-string ratio sd %.3f p10 %.3f p90 %.3f'%(st.pstdev(rr),sorted(rr)[len(rr)//10],sorted(rr)[9*len(rr)//10]))
