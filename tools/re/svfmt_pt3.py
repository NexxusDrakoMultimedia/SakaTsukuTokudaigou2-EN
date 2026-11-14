"""svfmt_pt3.py DUMP : probe 288-byte table: how many records have a decodable name, in which index ranges."""
import sys
d = open(sys.argv[1], 'rb').read(); B = 0x8c000000
ok = []
for n in range(0, 5400):
    a = 0x8ce4c004 + n * 0x120
    r = d[a - B:a - B + 14].split(b'\0')[0]
    try:
        t = r.decode('cp932')
    except Exception:
        continue
    if t and all(ord(c) >= 32 and c != '�' and not (0xe000 <= ord(c) <= 0xf8ff) for c in t): ok.append(n)
print(len(ok), ok[:10], ok[-5:])
runs = []; s = ok[0]; p = s
for x in ok[1:]:
    if x != p + 1: runs.append((s, p)); s = x
    p = x
runs.append((s, p)); print(runs[:20])
