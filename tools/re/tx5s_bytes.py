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
for p in sys.argv[3:]:
    x=rd(sa,fa[p.upper()]); y=rd(sb,fb[p.upper()])
    n=0
    for i in range(len(x)):
        if x[i]!=y[i]:
            print(p,hex(i),x[max(0,i-8):i+8].hex(),'|',y[max(0,i-8):i+8].hex()); n+=1
            if n>12: break
