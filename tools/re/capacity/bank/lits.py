import struct,sys
fr=open('extracted/1ST_READ.BIN','rb').read()
def u32(a): o=a-0x8c010000; return struct.unpack('<I',fr[o:o+4])[0]
def cstr(a):
    o=a-0x8c010000; e=fr.index(b'\0',o); return fr[o:e]
for a in range(0x8c160330,0x8c160380,4):
    v=u32(a); s=''
    if 0x8c010000<=v<0x8c2e0000:
        try: s=cstr(v).decode('ascii')
        except: s=''
    print(hex(a),hex(v),s if s.isprintable() and len(s)>2 else '')
print('boot literals 8c16001c/20:')
for a in (0x8c160008,0x8c16000c,0x8c160010,0x8c160014,0x8c160018,0x8c16001c,0x8c160020,0x8c160164,0x8c160168):
    print(hex(a),hex(u32(a)))
