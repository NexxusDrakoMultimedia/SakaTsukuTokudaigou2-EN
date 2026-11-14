"""For every zero run >=4 KB of the 1ST_READ file: still zero in each RAM dump? literal refs (aligned words) from 1ST_READ/overlays into it?"""
import re,struct,glob,os
fr=open('extracted/1ST_READ.BIN','rb').read()
B=0x8c010000
names=['ram_2400','ram_5400','live1_ram','live3_ram']
D={n:open('build/emu/%s.bin'%n,'rb').read() for n in names}
srcs=[('1ST_READ.BIN',fr)]+[('FLOW_PRG/'+os.path.basename(p),open(p,'rb').read()) for p in sorted(glob.glob('extracted/FLOW_PRG/*.BIN'))]+[('ATFIRST/'+n,open('extracted/ATFIRST/'+n,'rb').read()) for n in ('HELP.BIN','TITLE.BIN','FACEMDUL.BIN')]
words=[]
for s,d in srcs:
    n=len(d)//4
    for i,w in enumerate(struct.unpack('<%dI'%n,d[:n*4])):
        if 0x8c010000<=w<0x8c2b0000: words.append((w,s,i*4))
for m in re.finditer(rb'\0{4096,}',fr):
    a=B+m.start(); e=B+m.end()
    zeros=[]
    for n in names:
        seg=D[n][a-0x8c000000:e-0x8c000000]
        zeros.append(len(seg)-len(seg.lstrip(b'\0')) if False else seg.count(0))
    hit=[(w,s,o) for w,s,o in words if a<=w<e]
    hs=set(s for w,s,o in hit)
    print('zero run %x-%x len %6d | zero bytes in dumps %s | literal refs %d from %d sources %s'%(a,e,e-a,zeros,len(hit),len(hs),sorted(hs)[:3]))
print()
for a,e in ((0x8c1196a0,0x8c11cb3a),(0x8c1289e8,0x8c12cb25),(0x8c13bae0,0x8c159000)):
    for w,s,o in words:
        if a<=w<e: print('%x-%x: word %08x in %s @%#x'%(a,e,w,s,o))
