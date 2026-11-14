"""Gaps between the four resident boot loads (root FONT.BIN @8cd5c000, ETC_DATA SHTEX0.ZAR @8ce02000, BAR.TBD @8ce2c000, SECFTEX0.ZAR @8ce5c000):
size, zero in dumps, literal references from 1ST_READ/overlays (aligned words)."""
import struct,glob,os
names=['ram_2400','ram_5400','live1_ram','live3_ram']
D={n:open('build/emu/%s.bin'%n,'rb').read() for n in names}
srcs=[('1ST_READ.BIN',open('extracted/1ST_READ.BIN','rb').read())]+[('FLOW_PRG/'+os.path.basename(p),open(p,'rb').read()) for p in sorted(glob.glob('extracted/FLOW_PRG/*.BIN'))]+[('ATFIRST/'+n,open('extracted/ATFIRST/'+n,'rb').read()) for n in ('HELP.BIN','TITLE.BIN','FACEMDUL.BIN')]
words=[]
for s,d in srcs:
    n=len(d)//4
    for i,w in enumerate(struct.unpack('<%dI'%n,d[:n*4])):
        if 0x8cd40000<=w<0x8cea0000: words.append((w,s,i*4))
sz={'FONT':663324,'SHTEX0':155798,'BAR':122584,'SECF':46638}
ld={'FONT':0x8cd5c000,'SHTEX0':0x8ce02000,'BAR':0x8ce2c000,'SECF':0x8ce5c000}
gaps=[('after FONT',ld['FONT']+sz['FONT'],ld['SHTEX0']),('after SHTEX0',ld['SHTEX0']+sz['SHTEX0'],ld['BAR']),('after BAR',ld['BAR']+sz['BAR'],ld['SECF']),('after SECF',ld['SECF']+sz['SECF'],0x8ce68000),
 ('before FONT (slot11 tail?)',0x8cd40000,0x8cd5c000)]
for nm,a,e in gaps:
    a2=(a+0x7ff)&~0x7ff   # loader reads whole sectors: the sector tail beyond file end is overwritten too
    z=[ (D[n][a2-0x8c000000:e-0x8c000000]).count(0) for n in names]
    hit=[(hex(w),s,hex(o)) for w,s,o in words if a2<=w<e]
    print('%-28s %08x-%08x len %6d (from sector-aligned %08x: %6d) zero in dumps %s refs %d %s'%(nm,a,e,e-a,a2,e-a2,z,len(hit),hit[:4]))
