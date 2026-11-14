"""tx5 skeptic: list files whose bytes differ between two trial discs (excluding BCAST), and the byte-diff spans of chosen files."""
import os, sys
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
sys.path.insert(0,os.path.join(ROOT,'tools'))
import discbuild
def files(d,name):
    s=discbuild.Source(os.path.join(ROOT,'build','trial',name) if os.path.isdir(os.path.join(ROOT,'build','trial',name)) else os.path.join(ROOT,'build','trial'),name)
    pvd,rl,rs,rec=discbuild.read_filesystem(s)
    return s,{r.path.upper():r for r in rec if not r.isdir}
sa,fa=files(0,sys.argv[1]); sb,fb=files(0,sys.argv[2])
only=set(a.upper() for a in sys.argv[3:])
def rd(s,r):
    out=bytearray()
    for i in range((r.size+2047)//2048): out+=s.read(r.lba+i,2048)
    return bytes(out[:r.size])
for p in sorted(fa):
    if p=='/BCAST/BCAST.BIN': continue
    a=fa[p]; b=fb.get(p)
    if b is None: print('missing',p); continue
    if a.size>50_000_000: continue
    x=rd(sa,a); y=rd(sb,b)
    if x!=y:
        n=sum(1 for i in range(min(len(x),len(y))) if x[i]!=y[i]) if len(x)==len(y) else -1
        print('DIFF',p,len(x),len(y),'bytes differing',n)
