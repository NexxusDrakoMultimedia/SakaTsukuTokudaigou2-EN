"""ovmem: compare 1ST_READ scene record field b (slot index?) with overlay base / desc_count from build/memmap/overlays.tsv (read-only)."""
import csv, struct
D = open('extracted/1ST_READ.BIN', 'rb').read()
B = 0x8C010000
def u32(a): return struct.unpack_from('<I', D, a - B)[0]
def cs(a):
    o = a - B
    e = D.index(b'\0', o)
    return D[o:e].decode('latin1')
rec = {}
for a in range(0x8c16c2e8, 0x8c16cc00, 4):
    w = u32(a)
    if 0x8c16a000 <= w < 0x8c16c000:
        try: n = cs(w)
        except Exception: continue
        if n.endswith('.BIN'):
            rec.setdefault(n, (u32(a-12), u32(a-8), u32(a-4)))
rows = list(csv.DictReader(open('build/memmap/overlays.tsv'), delimiter='\t'))
slots = {i: (0x8c2b0000 if i == 0 else 0x8c2d0000 + (i-1)*0x100000) for i in range(0, 9)}
slots.update({9: 0x8cad0000, 10: 0x8cb60000, 11: 0x8cba0000})
for r in rows:
    if r['dir'] != 'FLOW_PRG': continue
    x = rec.get(r['overlay'])
    if not x: print(r['overlay'], 'no record', r['base']); continue
    b = x[1]
    lo = b & 0xff
    ok = (slots.get(lo) == int(r['base'], 16)) if lo in slots else None
    print('%-14s base %s b=%#x low=%d slot_base_match=%s desc_count=%s' % (r['overlay'], r['base'], b, lo, ok, r['desc_count']))
