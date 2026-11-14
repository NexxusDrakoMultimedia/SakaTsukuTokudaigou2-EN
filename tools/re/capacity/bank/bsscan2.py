import struct
names=['ram_2400','ram_5400','live1_ram','live3_ram']
D={n:open('build/emu/%s.bin'%n,'rb').read() for n in names}
fr=open('extracted/1ST_READ.BIN','rb').read()
for n in names:
    d=D[n]
    nz=[a for a in range(0x8c23d000,0x8c2a0000,4) if d[a-0x8c000000:a-0x8c000000+4]!=b'\0\0\0\0']
    print(n,'nonzero words in [8c23d000,8c2a0000):',len(nz),[hex(a) for a in nz[:20]])
# the file's own content there
print('file nonzero words in [8c23d000,8c2a0000):',sum(1 for a in range(0x8c23d000,0x8c2a0000,4) if fr[a-0x8c010000:a-0x8c010000+4]!=b'\0\0\0\0'))
# filler start
o=0x8c2a0000-0x8c010000
print(fr[o-8:o+8].hex())
# filler period
pat=fr[o:o+64]
k=0
while fr[o+k*64:o+k*64+64]==pat and o+k*64<len(fr): k+=1
print('filler period 64 repeats',k,'bytes',k*64,'end off',hex(o+k*64),'file len',hex(len(fr)))
print(pat)
