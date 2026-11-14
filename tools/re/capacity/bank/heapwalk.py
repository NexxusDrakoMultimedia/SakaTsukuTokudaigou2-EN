"""Walk the module heap (allocator FUN_8c16325a: header 0x20 bytes {size, state, prev, next}; state 0xfeedfeed=used, 0xdeaddead=free;
PROVEN from decompile + dump) in the live dumps.  Gives free/used bytes of the arena of the active overlay."""
import struct,sys
def walk(dump,start,limit):
    d=open('build/emu/%s.bin'%dump,'rb').read()
    def r32(a): o=a-0x8c000000; return struct.unpack('<I',d[o:o+4])[0]
    a=start; used=free=nu=nf=0; maxfree=0; blocks=[]
    seen=set()
    while True:
        if a in seen: break
        seen.add(a)
        sz,st,pv,nx=[r32(a+4*i) for i in range(4)]
        if st==0xfeedfeed: used+=sz;nu+=1
        elif st==0xdeaddead: free+=sz;nf+=1;maxfree=max(maxfree,sz)
        else: print('bad state at %x: %x'%(a,st)); break
        blocks.append((a,sz,st))
        a=nx
        if a==start or not (0x8c000000<=a<0x8d000000): break
    return used,free,nu,nf,maxfree,blocks
for dump,start,name in (('live3_ram',0x8c3062a0,'CLUBEDIT (8c2d0000, arena 8c3062a0..8c3d0000)'),('live1_ram',0x8c8e1660,'N_ENTRY (8c8d0000)')):
    try:
        u,f,nu,nf,mf,b=walk(dump,start,0)
        print(name,'blocks',len(b),'used bytes',u,'(%d blocks)'%nu,'free bytes',f,'(%d blocks, largest %d)'%(nf,mf),'chain total',u+f,'last block end %x'%(b[-1][0]+b[-1][1]))
    except Exception as e: print(name,'error',e)
print('--- restricted to the arena [start, slot end) ---')
for dump,start,end,name in (('live3_ram',0x8c3062a0,0x8c3d0000,'CLUBEDIT'),('live1_ram',0x8c8e1660,0x8c9d0000,'N_ENTRY')):
    u,f,nu,nf,mf,b=walk(dump,start,0)
    b=[x for x in b if start<=x[0]<end]
    uu=sum(x[1] for x in b if x[2]==0xfeedfeed); ff=sum(x[1] for x in b if x[2]==0xdeaddead)
    print(name,'arena bytes',end-start,'blocks in arena',len(b),'used',uu,'free',ff,'largest free',max([x[1] for x in b if x[2]==0xdeaddead] or [0]),'used %.1f%%'%(100*uu/(end-start)))

# ---- generic CLI:  heapwalk.py DUMP ENDVAR_VALUE ARENA_END   (e.g. live3_ram 0x8c30629d 0x8c3d0000)
if len(sys.argv) == 4:
    dump = sys.argv[1]; endv = int(sys.argv[2], 0); aend = int(sys.argv[3], 0)
    start = (((endv | 0x80000000) & ~0x1f) + 0x20) & 0xFFFFFFFF
    start = 0x8c000000 | (start & 0x00ffffff)
    u, f, nu, nf, mf, b = walk(dump, start, 0)
    b = [x for x in b if start <= x[0] < aend]
    uu = sum(x[1] for x in b if x[2] == 0xfeedfeed); ff = sum(x[1] for x in b if x[2] == 0xdeaddead)
    hi = max([x[0] + x[1] for x in b if x[2] == 0xfeedfeed] or [start])
    print('arena %x..%x blocks %d used %d free %d largest free %d highest used block end %x' % (start, aend, len(b), uu, ff, max([x[1] for x in b if x[2] == 0xdeaddead] or [0]), hi))
