import struct
F=open('extracted/1ST_READ.BIN','rb').read()
FONT=open('extracted/FONT.BIN','rb').read()
regs={'tail':(0x8c299400,0x8c2b0000,'k'),'gap1':(0x8c13bb80,0x8c159000,'k'),'gap2':(0x8c1196a0,0x8c11cafa,'k'),'gap3':(0x8c1289e8,0x8c12cae5,'k'),'fontTail':(0x8cdfdf1c,0x8ce02000,'f'),'matrix(0x8c299000-400)':(0x8c299000,0x8c299400,'k')}
dumps=['ram_2400','ram_5400','live1_ram','live3_ram']
D={n:open('build/emu/%s.bin'%n,'rb').read() for n in dumps}
for r,(lo,hi,k) in regs.items():
    fb = F[lo-0x8c010000:hi-0x8c010000] if k=='k' else b'\0'*(hi-lo)
    out=[]
    for n in dumps:
        d=D[n][lo-0x8c000000:hi-0x8c000000]
        out.append('%s:diff=%d'%(n,sum(1 for a,b in zip(d,fb) if a!=b)))
    print(r,hex(lo),hex(hi),hi-lo,'nonzero-in-file=%d'%sum(1 for x in fb if x),' '.join(out))
# crt0 overlap
bss=[(0x8c16f800,0x8c299400),(0x8c193c30,0x8c1fc180),(0x8c227000,0x8c239000)]
for r,(lo,hi,k) in regs.items():
    ov=[(max(lo,a),min(hi,b)) for a,b in bss if max(lo,a)<min(hi,b)]
    print(r,'overlap with crt0/boot zero-fill:',[(hex(a),hex(b)) for a,b in ov])
