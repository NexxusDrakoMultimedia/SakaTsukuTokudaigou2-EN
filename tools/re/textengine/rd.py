import struct,sys
B=0x8C010000
D=open('extracted/1ST_READ.BIN','rb').read()
def u32(a): return struct.unpack_from('<I',D,a-B)[0]
def u16(a): return struct.unpack_from('<H',D,a-B)[0]
def s16(a): return struct.unpack_from('<h',D,a-B)[0]
def cstr(a):
    e=D.index(b'\0',a-B); return D[a-B:e].decode('cp932','replace')
if __name__=='__main__':
    for x in sys.argv[1:]:
        a=int(x,16); v=u32(a); print(hex(a),hex(v),hex(u16(a)))
