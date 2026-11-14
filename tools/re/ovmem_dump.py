"""ovmem: list the 5-word scene/overlay records of 1ST_READ.BIN (dir, a, b, c, name ptr) with file sizes (read-only)."""
import os, struct
D = open('extracted/1ST_READ.BIN', 'rb').read()
B = 0x8C010000
def u32(a): return struct.unpack_from('<I', D, a - B)[0]
def cs(a):
    o = a - B
    if not (0 <= o < len(D)): return None
    e = D.index(b'\0', o)
    s = D[o:e]
    return s.decode('latin1') if 0 < len(s) < 20 and all(32 <= c < 127 for c in s) else None
dirs = ['SOUND', 'FLOW_PRG', 'ETC_DATA', 'GAME', 'BCAST']
rows = []
for a in range(0x8c16b000, 0x8c16f000, 4):
    w = u32(a)
    n = cs(w) if 0x8c16a000 <= w < 0x8c16c000 else None
    if n and n.endswith('.BIN') or (n and '.' in n):
        rows.append((a, [u32(a - 16 + 4 * i) for i in range(4)], n))
print(len(rows))
for a, f, n in rows:
    p = 'extracted/FLOW_PRG/' + n
    sz = os.path.getsize(p) if os.path.exists(p) else -1
    print(hex(a), [hex(x) for x in f], n, sz)
