import struct,os,glob,collections
rows=[l.rstrip('\n').split('\t') for l in open('extracted/_filelist.tsv',encoding='utf8')]
rows=[r for r in rows if len(r)>=3 and r[1].isdigit()]
files=[(r[0],int(r[1]),int(r[2])) for r in rows]
targets={}  # value -> list of (kind,path)
for p,lba,sz in files:
    if sz>=20000 and sz%2048:
        targets.setdefault(sz,[]).append(('size',p))

    if lba>=45000: targets.setdefault(lba,[]).append(('LBA',p))
codes=['1ST_READ.BIN','2_DP.BIN','SG_DPLDR.BIN','IP.BIN','MAIGO.BIN']+['FLOW_PRG/'+os.path.basename(x) for x in glob.glob('extracted/FLOW_PRG/*.BIN')]
res=collections.defaultdict(list)
for c in codes:
    d=open('extracted/'+c,'rb').read()
    n=len(d)//2*2
    for a in range(0,len(d)-3,2):   # 2-aligned: SH-4 literal pools may be 2 aligned
        v=struct.unpack_from('<I',d,a)[0]
        if v in targets:
            res[c].append((a,v,targets[v]))
for c,l in res.items():
    for a,v,t in l:
        print(c,hex(a),v,t[:3])
print('total hits',sum(len(v) for v in res.values()))
