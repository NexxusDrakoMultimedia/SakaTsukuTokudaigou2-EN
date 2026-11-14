"""tx5 skeptic: search the WHOLE original disc (every file incl. those not in extracted/) for 静観 variants; list files missing from extracted/."""
import os, re, sys
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
sys.path.insert(0,os.path.join(ROOT,'tools'))
import discbuild
s=discbuild.Source(ROOT)
pvd,rl,rs,rec=discbuild.read_filesystem(s)
pats={'cp932':re.compile(rb'\x90\xc3.{0,6}\x8a\xcf',re.S),'u16le':re.compile('静観'.encode('utf-16-le')),'u8':re.compile('静観'.encode('utf8')),
      'kan':re.compile(rb'\x8a\xcf')}
missing=[]
for r in rec:
    if r.isdir: continue
    rel=r.path.lstrip('/')
    ex=os.path.join(ROOT,'extracted',rel)
    if not os.path.exists(ex): missing.append((r.path,r.size))
print('files on disc not in extracted/:',len(missing))
for p,sz in sorted(missing,key=lambda x:-x[1])[:40]: print(' ',p,sz)
for p,sz in missing:
    if sz>100_000_000: continue
    r=[x for x in rec if x.path==p][0]
    d=s.read(r.lba,sz)
    for k in ('cp932','u16le','u8'):
        m=pats[k].search(d)
        if m: print('HIT',k,p,hex(m.start()))
