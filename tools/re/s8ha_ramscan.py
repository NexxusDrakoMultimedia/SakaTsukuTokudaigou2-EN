"""s8ha: scan a Flycast RAM dump for tsString window objects (variant A layout) and for the font hook literals.
usage: s8ha_ramscan.py DUMP"""
import struct, sys
ram = open(sys.argv[1], 'rb').read()
B = 0x8c000000
def u8(a): return ram[a - B]
def u16(a): return struct.unpack_from('<H', ram, a - B)[0]
def u32(a): return struct.unpack_from('<I', ram, a - B)[0]
for ent in (0x8c299800, 0x8c29982a):
    pat = struct.pack('<I', ent)
    i = ram.find(pat)
    hits = []
    while i >= 0:
        if i % 4 == 0:
            hits.append(B + i)
        i = ram.find(pat, i + 1)
    print('literal %08x: %s' % (ent, [hex(h) for h in hits][:20]))
cands = []
for a in range(0x8c300000, 0x8d000000 - 0x100, 4):
    p = u32(a + 0x30)
    if not (0x8c000000 <= p < 0x8d000000) or p & 1:
        continue
    cnt22 = u16(a + 0x22)
    idx = u16(a + 0x2c)
    W, R, adv, lh = u8(a + 0x3c), u8(a + 0x3d), u8(a + 0x3e), u8(a + 0x3f)
    if 1 <= W <= 60 and 1 <= R <= 20 and adv in (24, 16, 32, 10, 12, 20, 48) and 8 <= lh <= 60 and idx <= cnt22 <= 4000 and u8(a + 0x46) < 4:
        cands.append(a)
print(len(cands), 'candidate windows')
for a in cands[:80]:
    print('%08x ptr=%08x n=%d idx=%d W=%d R=%d adv=%d lh=%d x0=%d y0=%d vis=%d' % (a, u32(a + 0x30), u16(a + 0x22), u16(a + 0x2c), u8(a + 0x3c), u8(a + 0x3d), u8(a + 0x3e), u8(a + 0x3f), struct.unpack_from('<h', ram, a + 0x4a - B)[0], struct.unpack_from('<h', ram, a + 0x4c - B)[0], u8(a + 0x43)))
