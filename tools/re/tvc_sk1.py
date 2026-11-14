import struct
d=open('extracted/FLOW_PRG/TV_EVENT.BIN','rb').read()
for o in range(0xf14,0xf30,4): print(hex(o),hex(struct.unpack_from('<I',d,o)[0]))
for a in (0xb61c,0xb624,0xb62c,0xb634,0xb63c): print(hex(a),d[a:a+12])
