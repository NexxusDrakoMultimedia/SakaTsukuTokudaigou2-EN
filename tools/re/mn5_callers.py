"""mn5_callers.py: every code site that loads the address of the (original) money function from a literal pool, per overlay.
Prints overlay, site offset, pool offset and whether it is the expander (pool neighbours strlen/strncpy)."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moneypatch as MP
tot = 0
for rel in MP.overlay_paths():
    d = MP.read_extracted(rel)
    for s in MP.find_sites(d, rel):
        if s['variant'] != 'A':
            continue
        off = s['off']
        r = MP.find_d_literal(d, off)
        base = r[1] if r else 0x8C2D0000
        va = base + off
        pat = struct.pack('<I', va)
        k = 0
        while True:
            k = d.find(pat, k)
            if k < 0:
                break
            if k % 4 == 0:
                exp = struct.unpack_from('<II', d, k + 4) == (MP.STRLEN_ADDR, MP.STRNCPY_ADDR)
                for j in range(max(0, k - 1020), k, 2):
                    w = d[j] | d[j + 1] << 8
                    if (w >> 12) == 0xD and ((j + 4) & ~3) + (w & 0xFF) * 4 == k:
                        print('%s money@%x pool@%x site@%x r%d %s' % (rel, off, k, j, (w >> 8) & 15, 'EXPANDER' if exp else ''))
                        tot += 1
            k += 1
print('total', tot)
