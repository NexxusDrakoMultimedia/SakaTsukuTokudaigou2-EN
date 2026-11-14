"""Where is 1ST_READ's in-file zero/BSS region touched?  (a) nonzero words in the 4 RAM dumps, (b) absolute literals in
1ST_READ + all overlays + ATFIRST overlays that point into it."""
import os,struct,glob,collections
LO,HI=0x8c16eebb,0x8c2b0000
names=['ram_2400','ram_5400','live1_ram','live3_ram']
D={n:open('build/emu/%s.bin'%n,'rb').read() for n in names}
fr=open('extracted/1ST_READ.BIN','rb').read()
BL=0x1000
def blk(a): return a//BL*BL
print('== (a) 4 KB blocks of [0x8c16e000,0x8c2b0000) with nonzero bytes in any dump (count per dump) ==')
nzblocks=[]
for a in range(0x8c16e000,HI,BL):
    cnt=[]
    for n in names:
        s=D[n][a-0x8c000000:a-0x8c000000+BL]
        cnt.append(BL-s.count(0))
    if any(cnt): nzblocks.append((a,cnt))
print(len(nzblocks),'of',(HI-0x8c16e000)//BL,'blocks have nonzero data in some dump')
# merge into runs of blocks
runs=[];cur=None
nzset={a for a,_ in nzblocks}
for a in range(0x8c16e000,HI,BL):
    if a in nzset:
        if cur and cur[1]==a: cur[1]=a+BL
        else: cur=[a,a+BL]; runs.append(cur)
print('nonzero-block runs:',[('%x-%x'%(r[0],r[1])) for r in runs])
# precise: highest nonzero byte address in any dump below HI
hi=0
for n in names:
    d=D[n]; seg=d[0x16e000:HI-0x8c000000]
    last=len(seg.rstrip(b'\0')); hi=max(hi,0x8c16e000+last)
print('highest nonzero addr (any dump) in range: %x'%hi)
# union of zero bytes in all dumps -> longest zero runs
import re
u=bytearray(HI-0x8c16e000)
for n in names:
    seg=D[n][0x16e000:HI-0x8c000000]
    for i,b in enumerate(seg): pass
