"""crt0 of 1ST_READ.BIN (FUN_8c017160, called from 0x8c017136): which RAM ranges are zero-filled / copied at start-up, and what the
bank regions look like in the file.  Literal pool 0x8c017280..0x8c0172a4 -> cells (linker symbols)."""
import struct
fr=open('extracted/1ST_READ.BIN','rb').read()
B=0x8c010000
def w(a): o=a-B; return struct.unpack('<I',fr[o:o+4])[0]
cell=lambda lit: w(w(lit))
print('loop1 zero-fill words  [%#x, %#x)'%(cell(0x8c017284),cell(0x8c017280)))
print('loop2 copy bytes dst [%#x, %#x) src %#x  (empty if equal)'%(cell(0x8c01728c),cell(0x8c017288),cell(0x8c017290)))
print('loop3 zero-fill bytes  [%#x, %#x)'%(cell(0x8c017298),cell(0x8c017294)))
print('loop4 copy bytes dst [%#x, %#x) src %#x  (empty if equal)'%(cell(0x8c0172a0),cell(0x8c01729c),cell(0x8c0172a4)))
print('section table at 0x8c10dbdc:',[hex(w(a)) for a in range(0x8c10dbdc,0x8c10dc20,4)])
print('pool table at 0x8c016b68:',[hex(w(a)) for a in range(0x8c016b68,0x8c016ba0,4)])
def rng(a,e): return fr[a-B:e-B]
print('file [8c299400,8c2a0000) all zero:',not any(rng(0x8c299400,0x8c2a0000)),'len',0x8c2a0000-0x8c299400)
pat=rng(0x8c2a0000,0x8c2a0040)
print('file [8c2a0000,8c2b0000) = repeated 64-byte filler:',all(rng(0x8c2a0000+i,0x8c2a0000+i+64)==pat for i in range(0,0x10000,64)))
for nm,a,e in (('gap1',0x8c13bae0,0x8c159000),('gap2',0x8c1196a0,0x8c11cb3a),('gap3',0x8c1289e8,0x8c12cb25)):
    print(nm,'zero in file:',not any(rng(a,e)),'len',e-a, 'next byte nonzero:',fr[e-B]!=0,'prev byte nonzero:',fr[a-B-1]!=0)
