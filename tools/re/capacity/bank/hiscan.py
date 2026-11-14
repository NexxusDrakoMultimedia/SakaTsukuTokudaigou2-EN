"""Region 0x8ce60000-0x8d000000 (after the 4 resident boot loads): per-4KB nonzero in dumps + literal refs."""
import struct,glob,os,collections
names=['ram_2400','ram_5400','live1_ram','live3_ram']
D={n:open('build/emu/%s.bin'%n,'rb').read() for n in names}
fr=open('extracted/1ST_READ.BIN','rb').read()
srcs=[('1ST_READ.BIN',fr)]+[('FLOW_PRG/'+os.path.basename(p),open(p,'rb').read()) for p in sorted(glob.glob('extracted/FLOW_PRG/*.BIN'))]+[('ATFIRST/'+n,open('extracted/ATFIRST/'+n,'rb').read()) for n in ('HELP.BIN','TITLE.BIN','FACEMDUL.BIN')]
LO,HI=0x8ce60000,0x8d000000
refs=collections.defaultdict(list)
for s,d in srcs:
    n=len(d)//4
    for i,w in enumerate(struct.unpack('<%dI'%n,d[:n*4])):
        if LO<=w<HI+4: refs[w//0x1000*0x1000].append(s)
print('addr      nonzero bytes per dump (4KB blocks)          literal-ref words (distinct sources)')
for a in range(LO,HI,0x1000):
    nz=[0x1000-D[n][a-0x8c000000:a-0x8c000000+0x1000].count(0) for n in names]
    r=refs.get(a,[])
    if any(nz) or r: print('%08x %s refs=%d(%d)'%(a,nz,len(r),len(set(r))))
