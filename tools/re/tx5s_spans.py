import os, sys
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
sys.path.insert(0,os.path.join(ROOT,'tools'))
import discbuild
def files(name):
    d=os.path.join(ROOT,'build','trial',name)
    s=discbuild.Source(d if os.path.isdir(d) else os.path.join(ROOT,'build','trial'),name)
    pvd,rl,rs,rec=discbuild.read_filesystem(s)
    return s,{r.path.upper():r for r in rec if not r.isdir}
def rd(s,r):
    out=bytearray()
    for i in range((r.size+2047)//2048): out+=s.read(r.lba+i,2048)
    return bytes(out[:r.size])
sa,fa=files(sys.argv[1]); sb,fb=files(sys.argv[2])
p=sys.argv[3].upper()
x=rd(sa,fa[p]); y=rd(sb,fb[p])
i=0; spans=[]
while i<len(x):
    if x[i]!=y[i]:
        j=i
        while j<len(x) and (x[j]!=y[j] or (j+1<len(x) and x[j+1]!=y[j+1] and j-i<64) or (j+2<len(x) and x[j+2]!=y[j+2] and j-i<8)): j+=1
        spans.append((i,j)); i=j
    else: i+=1
for a,b in spans[:int(sys.argv[4]) if len(sys.argv)>4 else 60]:
    print(hex(a),b-a,x[a:b][:40],'->',y[a:b][:40])
print(len(spans),'spans')
