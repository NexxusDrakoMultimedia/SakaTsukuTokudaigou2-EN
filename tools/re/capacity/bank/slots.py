import struct,sys,collections
fr=open('extracted/1ST_READ.BIN','rb').read()
def rd(a,n): o=a-0x8c010000; return fr[o:o+n]
# slot table at 0x8c16bf9c
t=0x8c16bf9c
for i in range(16):
    b,s=struct.unpack('<II',rd(t+i*8,8))
    print(i,hex(b),hex(s))
    if b==0: break
