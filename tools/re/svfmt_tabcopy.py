"""svfmt_tabcopy.py DUMP : is the gsp section table (15 x {ptr,size,crc}) copied anywhere inside the 64KB arena or its header chunk?"""
import sys, struct
d = open(sys.argv[1], 'rb').read(); B = 0x8c000000
w = lambda a: struct.unpack_from('<I', d, a - B)[0]
gsp = w(0x8c159220)
ent = d[gsp + 0x24 - B: gsp + 0x24 - B + 8]; full = d[gsp + 0x24 - B: gsp + 0x24 - B + 8 * 15]
for tag, pat in (('first entry', ent), ('whole table', full)):
    hits = []; i = d.find(pat)
    while i >= 0: hits.append(hex(B + i)); i = d.find(pat, i + 1)
    print(tag, hits)
print('crc halves differ from arena content? (table crc vs recomputed) -> see svfmt_sec.py')
