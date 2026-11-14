"""Absolute 32-bit words pointing into 1ST_READ's in-file zero/BSS region and its filler tail."""
import sys,struct,glob,os,collections
LO,HI=0x8c16eebb,0x8c2b0000
srcs=[('1ST_READ.BIN','extracted/1ST_READ.BIN')]+[('FLOW_PRG/'+os.path.basename(p),p) for p in sorted(glob.glob('extracted/FLOW_PRG/*.BIN'))]+[('ATFIRST/'+n,'extracted/ATFIRST/'+n) for n in ('HELP.BIN','TITLE.BIN','FACEMDUL.BIN')]
hits=collections.defaultdict(list)   # addr -> [(src,off)]
for s,p in srcs:
    d=open(p,'rb').read(); n=len(d)//4
    for i,w in enumerate(struct.unpack('<%dI'%n,d[:n*4])):
        if LO<=w<HI: hits[w].append((s,i*4))
print('distinct target addrs',len(hits),'total hits',sum(len(v) for v in hits.values()))
blk=collections.Counter()
for a,v in hits.items(): blk[a//0x1000*0x1000]+=len(v)
for b in sorted(blk): print('%08x %5d'%(b,blk[b]), end=' | ')
print()
print('highest target:',hex(max(hits)))
# targets above 0x8c240000
for a in sorted(hits):
    if a>=0x8c239000: print(hex(a),[(s,hex(o)) for s,o in hits[a][:4]],len(hits[a]))
