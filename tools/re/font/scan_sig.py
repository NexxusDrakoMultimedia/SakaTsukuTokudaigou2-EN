"""Scan every file under extracted/ (and the RAM dumps) for the half-width advance signature
(MEETING.BIN 0x8c2de490..0x8c2de4aa).  python -I -X utf8 tools/re/font/scan_sig.py"""
import os, sys
M = open('extracted/FLOW_PRG/MEETING.BIN', 'rb').read()
B = 0x8c2d0000
SIG = M[0x8c2de490 - B:0x8c2de4aa - B]      # 26 bytes: half + full advance
HALF = M[0x8c2de490 - B:0x8c2de4a2 - B]     # 18 bytes
print('SIG', SIG.hex())
hits = {}
tot = 0
for r, ds, fs in os.walk('extracted'):
    for f in sorted(fs):
        p = os.path.join(r, f).replace(chr(92), '/')
        d = open(p, 'rb').read(); tot += 1
        offs = []; i = d.find(SIG)
        while i >= 0:
            offs.append(i); i = d.find(SIG, i + 1)
        if offs:
            hits[p] = offs
for p, o in hits.items():
    print(p, ['0x%x' % x for x in o])
print('files scanned', tot, 'with hits', len(hits))
for dmp in ('ram_2400', 'live1_ram', 'live3_ram', 't1_ram'):
    d = open('build/emu/%s.bin' % dmp, 'rb').read()
    offs = []; i = d.find(SIG)
    while i >= 0:
        offs.append(i); i = d.find(SIG, i + 1)
    print(dmp, ['0x%x' % (0x8c000000 + x) for x in offs])
