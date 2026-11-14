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
        g[(m.name,len(out),m.crc16,m.mtime)][m.method].add(hashlib.sha1(out).hexdigest())
mixed=[k for k,v in g.items() if len(v)>1]
agree=sum(1 for k in mixed if all(g[k][list(g[k])[0]]&g[k][m] for m in g[k]))
print('name+size+crc+mtime groups',len(g),'mixed',len(mixed),'agree',agree)
