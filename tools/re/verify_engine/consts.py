import struct
d=open('extracted/1ST_READ.BIN','rb').read()
B=0x8c010000
def w(a): return struct.unpack_from('<H',d,a-B)[0]
def sw(a): return struct.unpack_from('<h',d,a-B)[0]
def l(a): return struct.unpack_from('<I',d,a-B)[0]
for a in [0x8c15e820,0x8c15e822,0x8c15e824,0x8c15e826,0x8c15e828,0x8c15e82c,0x8c15e82e,0x8c15e860,0x8c15e934,0x8c15e936,0x8c15ea58,0x8c15ea68,0x8c15ea5a,0x8c15ea5c,0x8c15ea7c,0x8c15ea80,0x8c15ed42,0x8c15ed44,0x8c15ed48]:
    print(hex(a),'s16',sw(a),hex(w(a)))
for a in [0x8c15e93c,0x8c15e940,0x8c15e944,0x8c15ed50,0x8c15ed54,0x8c15ed58,0x8c15ee9c,0x8c15eea0,0x8c15ea84,0x8c15ebec,0x8c15ebf0]:
    print(hex(a),hex(l(a)))
