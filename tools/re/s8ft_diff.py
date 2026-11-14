"""s8ft: byte-range diff between SCDRF.BIN images, classified by region.
usage: s8ft_diff.py A B   (paths to files)
"""
import sys

a = open(sys.argv[1], 'rb').read()
b = open(sys.argv[2], 'rb').read()
print(len(a), len(b))
out = []
i = 0
n = min(len(a), len(b))
while i < n:
    if a[i] != b[i]:
        j = i
        last = i
        while j < n and j - last <= 16:
            if a[j] != b[j]:
                last = j
            j += 1
        out.append((i, last + 1))
        i = last + 1
    else:
        i += 1
print('ranges', len(out), 'bytes', sum(e - s for s, e in out))
for s, e in out[:int(sys.argv[3]) if len(sys.argv) > 3 else 100]:
    print('%#x-%#x (%d)  A=%s  B=%s' % (s, e, e - s, a[s:min(e, s + 24)].hex(), b[s:min(e, s + 24)].hex()))
