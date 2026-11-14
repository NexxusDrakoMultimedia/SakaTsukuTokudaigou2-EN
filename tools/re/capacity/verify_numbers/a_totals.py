import json,glob,os,collections
tot=collections.OrderedDict(); n=0; J=0; MB=0; refs0=0
for f in sorted(glob.glob('translation/*.jsonl')):
    nm=os.path.basename(f)[:-6]
    c=b=m=0
    for line in open(f,encoding='utf-8'):
        if not line.strip(): continue
        r=json.loads(line)
        try: L=len(r['ja'].encode('cp932'))
        except Exception: L=len(r['ja'].encode('cp932',errors='replace'))
        c+=1;b+=L;m+=(r['max_bytes'] or 0); nn=globals().setdefault('NONE',[0]); nn[0]+= r['max_bytes'] is None
    tot[nm]=(c,b,m)
N=sum(v[0] for v in tot.values()); B=sum(v[1] for v in tot.values()); M=sum(v[2] for v in tot.values())
print('files',len(tot),'records',N,'ja_cp932_bytes',B,'ja+NUL',B+N,'max_bytes sum',M)
fp=[(k,v) for k,v in tot.items() if k.startswith('FLOW_PRG')]
print('FLOW_PRG files',len(fp),'rec',sum(v[0] for k,v in fp),'bytes',sum(v[1] for k,v in fp))
for k,v in sorted(tot.items(),key=lambda x:-x[1][1])[:12]: print(k,v)
print('max_bytes None:',NONE[0])
