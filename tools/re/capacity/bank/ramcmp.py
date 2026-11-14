import sys
B=0x8c000000
def ld(p): return open(p,'rb').read()
dumps={n:ld('build/emu/%s.bin'%n) for n in ['ram_2400','ram_5400','live1_ram','live3_ram']}
fr=ld('extracted/1ST_READ.BIN')
print('1ST_READ size',len(fr),hex(len(fr)),'end',hex(0x8c010000+len(fr)))
for n,d in dumps.items():
    off=0x10000
    seg=d[off:off+len(fr)]
    # per 64KB block: fraction of equal bytes
    out=[]
    blocks=len(fr)//0x10000
    same=0
    res=[]
    for b in range(blocks+1):
        a=fr[b*0x10000:(b+1)*0x10000]; c=seg[b*0x10000:(b+1)*0x10000]
        eq=sum(1 for x,y in zip(a,c) if x==y) if a else 0
        res.append('%x:%d%%'%(0x8c010000+b*0x10000, 100*eq//max(1,len(a))))
    print(n,' '.join(res))
