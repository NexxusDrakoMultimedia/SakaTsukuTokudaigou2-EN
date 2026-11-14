"""skm7_nenfind.py: where do the money pieces / formats sit in extracted FLOW_PRG/NENREP.BIN and which pool words point at them (any base).  Read only."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moneypatch as MP      # noqa: E402

d = MP.read_extracted('FLOW_PRG/NENREP.BIN')
print('size %#x' % len(d))
for pat in ['%s億%s万円', '%s万円', '億', '万円']:
    b = pat.encode('cp932')
    offs, i = [], 0
    while True:
        i = d.find(b, i)
        if i < 0:
            break
        offs.append(i)
        i += 1
    print(pat, len(offs), [hex(o) for o in offs[:12]])
# pool words that equal base + off for the candidates, for a few bases
for pat in ['%s億%s万円']:
    b = pat.encode('cp932')
    o = d.find(b)
    s = o
    while s > 0 and d[s - 1] != 0:
        s -= 1
    print('string starts at %#x: %r' % (s, bytes(d[s:s + 30]).split(b'\0')[0].decode('cp932', 'replace')))
    for base in (0x8c2e0000, 0x8c2e0000 - 0x20, 0x8c2e0000 + 0x20):
        hits = [hex(i) for i in range(0, len(d) - 4, 4) if struct.unpack_from('<I', d, i)[0] == base + s]
        print('base %#x: pool words -> %s' % (base, hits))
