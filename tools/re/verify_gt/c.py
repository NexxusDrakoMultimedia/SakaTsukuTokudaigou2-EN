import sys,os,collections,hashlib
sys.path.insert(0,'tools')
import bzlib
g=collections.defaultdict(lambda:collections.defaultdict(set))
for dp,dn,fn in os.walk('extracted'):
  for f in fn:
    if f=='_filelist.tsv':continue
    p=os.path.join(dp,f); d=open(p,'rb').read()
    for m in bzlib.parse_archive(d)[0]:
        out=m.extract()
        g[(len(out),m.crc16)][m.method].add(hashlib.sha1(out).hexdigest())
mixed=[k for k,v in g.items() if len(v)>1]
bad=[k for k,v in g.items() if len(set().union(*v.values()))>1]
print('groups',len(g),'mixed-method groups',len(mixed),'groups with same size+crc but differing content',len(bad))
agree=dis=0
for k in mixed:
    v=g[k]; ms=list(v)
    sets=[v[m] for m in ms]
    if all(sets[0]&s for s in sets[1:]): agree+=1
    else: dis+=1; print('no common content',k,{m:len(s) for m,s in v.items()})
print('mixed groups sharing identical content',agree,'with no overlap',dis)
