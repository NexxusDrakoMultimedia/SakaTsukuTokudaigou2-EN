"""s8ha: compare a Flycast RAM dump (16 MB, address 0x8c000000 + offset) with a file loaded at BASE over [LO, HI); list differing runs.
usage: s8ha_ramcmp.py DUMP FILE BASE LO HI    (hex addresses)"""
import sys
ram = open(sys.argv[1], 'rb').read()
f = open(sys.argv[2], 'rb').read()
base, lo, hi = (int(x, 16) for x in sys.argv[3:6])
runs = []
for a in range(lo, hi):
    r = ram[a - 0x8c000000]
    o = f[a - base] if 0 <= a - base < len(f) else 0
    if r != o:
        if runs and a - runs[-1][1] <= 8:
            runs[-1][1] = a + 1
        else:
            runs.append([a, a + 1])
print(len(runs), 'differing runs')
for s, e in runs[:60]:
    print('%08x..%08x (%d) ram=%s file=%s' % (s, e, e - s, ram[s - 0x8c000000:min(e, s + 12) - 0x8c000000].hex(), f[s - base:min(e, s + 12) - base].hex()))
