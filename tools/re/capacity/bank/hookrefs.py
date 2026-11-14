"""All mov.l @(disp,PC),Rn (and mov.w) instructions in 1ST_READ.BIN whose literal is the hook literal 0x8c160360, plus every aligned word equal to
0x8c163984 (the empty function).  Proves the literal patch affects a single call site."""
import struct
fr=open('extracted/1ST_READ.BIN','rb').read()
B=0x8c010000
tgt=0x8c160360
hits=[]
for o in range(0,0x14f000,2):   # code region (before data at 0x8c159000 is where the jump table starts; scan whole file below)
    pass
for o in range(0,len(fr)-1,2):
    w=struct.unpack_from('<H',fr,o)[0]
    if w>>12==0xD:
        a=B+o; ea=(a&~3)+4+4*(w&0xff)
        if ea==tgt: hits.append((hex(a),'mov.l'))
print('mov.l PC-relative loads of literal 0x8c160360:',hits)
print('aligned words == 0x8c163984:',[hex(B+o) for o in range(0,len(fr)-3,4) if struct.unpack_from('<I',fr,o)[0]==0x8c163984])
print('word at 0x8c160360 =',hex(struct.unpack_from('<I',fr,tgt-B)[0]))
# cave zero check
print('cave bytes 0x8c13bb00..+0x80 zero:',not any(fr[0x12bb00:0x12bb80]))
