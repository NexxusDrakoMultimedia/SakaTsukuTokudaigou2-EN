"""Evidence for the 'restore' hazard in tools/emu/fonttest.lua: FT.saved[addr] keeps the ORIGINAL bytes of every site ever hooked and
restore_hooks() writes them back to those absolute addresses without checking what is in RAM now.  Overlay slots are reused.

For every pair of dumps (A = state when the sites were hooked, B = state when 'restore' runs later) take A's sites, look at what B
holds at the same absolute addresses (16 B at H1 and the H2 span) and report whether restore would overwrite code that is neither the
original signature nor the hooked bytes (= a different overlay's code)."""
import os
import re
import struct
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
BASE = 0x8C000000
lua = open(os.path.join(ROOT, 'tools', 'emu', 'fonttest.lua'), encoding='utf8').read()
V = {}
for v, m in re.findall(r'(\w) = \{(h1_old=.*?)\}', lua):
    V[v] = {k: bytes.fromhex(x) for k, x in re.findall(r'(\w+)="([0-9a-f]+)"', m)}
    V[v]['back'] = int(re.search(r'h2_back=(\d+)', m).group(1))
names = ('ram_2400', 'live1_ram', 'live3_ram', 't1_ram')
D = {n: open(os.path.join(ROOT, 'build', 'emu', n + '.bin'), 'rb').read() for n in names}


def sites(d):
    arr = np.frombuffer(d, dtype='<u4')
    a0, a1 = (0x8C2D0000 - BASE) >> 2, (0x8CD5C000 - BASE - 16) >> 2
    seg = arr[a0:a1]
    w = {struct.unpack('<I', V[v]['h1_old'][:4])[0] for v in V}
    cand = np.nonzero(np.isin(seg, list(w)))[0]
    out = []
    for c in cand:
        a = 0x8C2D0000 + int(c) * 4
        s = d[a - BASE:a - BASE + 16]
        for v, t in V.items():
            if s == t['h1_old']:
                h2 = a - t['back']
                if d[h2 - BASE:h2 - BASE + len(t['h2_old'])] == t['h2_old']:
                    out.append((v, a, h2))
    return out


for a_name in names:
    sa = sites(D[a_name])
    for b_name in names:
        if a_name == b_name:
            continue
        db = D[b_name]
        for v, a, h2 in sa:
            t = V[v]
            cur1 = db[a - BASE:a - BASE + 16]
            cur2 = db[h2 - BASE:h2 - BASE + len(t['h2_old'])]
            ok1 = cur1 in (t['h1_old'], t['h1_new'])
            ok2 = cur2 in (t['h2_old'], t['h2_new'])
            if not (ok1 and ok2):
                diff = sum(1 for x, y in zip(cur2, t['h2_old']) if x != y) + sum(1 for x, y in zip(cur1, t['h1_old']) if x != y)
                print('hooked in %-9s site %#x (H2 %#x)  -> restore in %-9s would overwrite %d bytes of foreign code (%d of %d bytes differ from the signature)' % (
                    a_name, a, h2, b_name, len(cur1) + len(cur2), diff, len(cur1) + len(cur2)))
