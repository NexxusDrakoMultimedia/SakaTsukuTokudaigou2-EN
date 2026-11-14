# Scan every code-bearing file for words pointing into / near the proposed bank regions (all mirrors: 8c/ac/0c/2c/4c.. top byte varies)
import struct,glob,os
regions={'tail':(0x299400,0x2b0000),'gap1':(0x13bb80,0x159000),'gap2':(0x1196a0,0x11cafa),'gap3':(0x1289e8,0x12cae5),'fontTail':(0xdfdf1c,0xe02000),
         'matrixstack(0x299000)':(0x299000,0x299400)}
MARG=0x1000
files=[p for p in glob.glob('extracted/**/*',recursive=True) if os.path.isfile(p)]
code=[p for p in files if p.endswith('.BIN') or p.endswith('.DRV') or 'FLOW_PRG' in p]
res={k:[] for k in regions}
for p in code:
    b=open(p,'rb').read()
    n=len(b)
    for al in (4,2):
        # only count 2-aligned odd positions separately
        pass
    ws=struct.unpack_from('<%dI'%(n//4),b,0)
    for idx,w in enumerate(ws):
        phys=w&0x1fffffff
        top=w>>24
        if top not in (0x8c,0xac,0x0c,0x2c,0x4c,0xcc,0xec): continue
        a=phys-0x0c000000
        for k,(lo,hi) in regions.items():
            if lo-MARG<=a<hi+MARG: res[k].append((p,idx*4,w,'IN' if lo<=a<hi else 'near'))
for k,v in res.items():
    print('==',k,len(v))
    for x in v[:60]: print('  ',x[0],hex(x[1]),hex(x[2]),x[3])
