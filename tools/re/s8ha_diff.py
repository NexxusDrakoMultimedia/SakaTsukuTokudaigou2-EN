"""s8ha: list the differing byte ranges of two files (merged within 16 bytes).   usage: s8ha_diff.py A B [BASE]"""
import sys
a = open(sys.argv[1], 'rb').read()
b = open(sys.argv[2], 'rb').read()
base = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0
print('sizes', len(a), len(b))
rs = []
for i in range(min(len(a), len(b))):
    if a[i] != b[i]:
        if rs and i - rs[-1][1] <= 16:
            rs[-1][1] = i + 1
        else:
            rs.append([i, i + 1])
for s, e in rs:
    print('%#x..%#x (%08x) %d bytes: %s -> %s' % (s, e, base + s, e - s, a[s:min(e, s + 16)].hex(), b[s:min(e, s + 16)].hex()))
print(len(rs), 'ranges')
