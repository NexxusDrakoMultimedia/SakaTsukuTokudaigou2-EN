"""s8ha: count font hooks (cave entry literals) in a file.  usage: s8ha_hooks.py FILE BASE"""
import struct, sys
d = open(sys.argv[1], 'rb').read()
base = int(sys.argv[2], 16)
for ent in (0x8c299800, 0x8c299804, 0x8c29982a, 0x8c29982e):
    pat = struct.pack('<I', ent)
    offs = []
    i = d.find(pat)
    while i >= 0:
        if i % 4 == 0:
            offs.append(i)
        i = d.find(pat, i + 1)
    print('%08x: %d literals' % (ent, len(offs)), ['%x' % (base + o) for o in offs][:10])
