"""Natural vs tight (hand-edited, terse) English for a random 60-string subset of prose+help."""
import os,sys,json,collections
os.chdir(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))); sys.path.insert(0,'tools/re/capacity/ratio')
from common import *
S={}
for l in open('tools/re/capacity/ratio/sample.jsonl',encoding='utf8'):
    s=json.loads(l); S[s['idx']]=s
T={}
for l in open('tools/re/capacity/ratio/tight/tight.txt',encoding='utf8'):
    i,e=l.rstrip('\n').split('|',1); T[int(i)]=e.replace('|',chr(10))
rows=[]
for i,t in T.items():
    s=S[i]; n=eb(s['en']); tg=eb(t); j=jb(s['ja'])
    rows.append((i,s['cat'],j,s['max_bytes'],n,tg))
print('n',len(rows))
def agg(rs,lab):
    J=sum(r[2] for r in rs); N=sum(r[4] for r in rs); Tg=sum(r[5] for r in rs)
    print('%-16s n=%2d  natural/JP=%.3f tight/JP=%.3f tight/natural=%.3f | fit natural %.0f%% tight %.0f%%'%(lab,len(rs),N/J,Tg/J,Tg/N,100*sum(r[4]<=r[3] for r in rs)/len(rs),100*sum(r[5]<=r[3] for r in rs)/len(rs)))
agg(rows,'ALL')
agg([r for r in rows if r[1] in('prose_meeting','prose_news','prose_event','prose_training','prose_other','help') and r[2]>=30],'JP>=30 bytes')
for c in ('help','prose_event','prose_meeting','prose_news','prose_other','prose_training'):
    agg([r for r in rows if r[1]==c],c)
src=open('tools/re/capacity/ratio/build_sample.py',encoding='utf8').read().replace('\nmain()\n','\n')
bs={}; exec(compile(src,'bs','exec'),bs); wrap=bs['wrap']
def L(ja):
    l=ja.split(chr(10))
    while l and l[-1]=='': l.pop()
    return len(l)
nat=tig=n=0; nat3=tig3=0
for i,t in T.items():
    s=S[i]
    if jb(s['ja'])<30: continue
    n+=1
    jl=L(s['ja'])
    a=len([x for x in wrap(s['en_flat']) if x!='' ]) ; b=len([x for x in wrap(t.replace(chr(10),'|')) if x!=''])
    nat+= a>jl; tig+= b>jl; nat3+= a>3; tig3+= b>3
print('LINES (JP>=30 bytes strings, n=%d): English needs more lines than JP had: natural %d (%.0f%%), tight %d (%.0f%%); needs >3 lines: natural %d, tight %d'%(n,nat,100*nat/n,tig,100*tig/n,nat3,tig3))
