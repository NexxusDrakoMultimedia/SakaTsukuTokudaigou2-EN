import sys,json,collections,statistics as st
sys.path.insert(0,'tools'); import textdb
rows=[json.loads(l) for l in open('tools/re/capacity/ratio/sample.jsonl',encoding='utf-8')]
rows=[r for r in rows if not r['skip']]
print('n',len(rows))
cat=collections.defaultdict(lambda:[0,0,0,[]])
for r in rows:
    j=len(textdb.encode_text(r['ja']))+1; e=len(r['en'].encode('ascii'))+1
    r['j']=j; r['e']=e
    c=r['cat'].split('_')[0] if False else r['cat']
    x=cat[c]; x[0]+=1;x[1]+=j;x[2]+=e;x[3].append(e/j)
tj=sum(r['j'] for r in rows); te=sum(r['e'] for r in rows)
print('sample byte-weighted EN/JP %.3f  mean per-string %.3f median %.3f'%(te/tj,st.mean(r['e']/r['j'] for r in rows),st.median(r['e']/r['j'] for r in rows)))
for c,x in sorted(cat.items()): print('%-14s n=%3d jp=%6d en=%6d ratio=%.3f median=%.3f  over-slot(e>max_bytes) '%(c,x[0],x[1],x[2],x[2]/x[1],st.median(x[3])))
print('frac with en>max_bytes',sum(r['e']>r['max_bytes'] for r in rows)/len(rows))
