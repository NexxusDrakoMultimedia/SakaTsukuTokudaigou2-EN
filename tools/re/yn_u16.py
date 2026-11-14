import struct, sys, glob, os
for f in ['extracted/FLOW_PRG/CAP_SLCT.BIN','extracted/1ST_READ.BIN','extracted/FLOW_PRG/HOMETOWN.BIN']:
    d = open(f,'rb').read()
    for name, ch in (('ha',0x82cd),('i',0x82a2),('e',0x82a6),('sp',0x8140)):
        offs = [o for o in range(0, len(d)-1, 2) if struct.unpack_from('<H', d, o)[0] == ch]
        # only u16 LE at even offsets; ignore if inside big-endian text? just print count
        print(os.path.basename(f), name, len(offs), [hex(o) for o in offs[:12]])
