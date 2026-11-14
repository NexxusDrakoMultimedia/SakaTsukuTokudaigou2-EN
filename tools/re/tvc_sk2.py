import struct
d=open('extracted/FLOW_PRG/TV_EVENT.BIN','rb').read()
for t in (0x8c2db61c,0x8c2db624,0x8c2db62c):
    print(hex(t),[hex(o) for o in range(0,len(d)-3,2) if struct.unpack_from('<I',d,o)[0]==t])
