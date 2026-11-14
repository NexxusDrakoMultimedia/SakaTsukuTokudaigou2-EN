import sys, os, glob
sys.path.insert(0, 'tools/re/ghidra')
from members import iter_members
from bz_ghidra import decompress, crc16
files = sys.argv[1:]
tot = ok = bad = 0
for f in files:
    d = open(f, 'rb').read()
    for h, pk, off in iter_members(d):
        tot += 1
        try:
            out = decompress(h['method'], pk, h['orig'])
            good = len(out) == h['orig'] and crc16(out) == h['crc16']
        except Exception as e:
            good = False; out = b''
            print('EXC', f, off, h['name'], e)
        if good: ok += 1
        else:
            bad += 1
            if bad < 15: print('BAD', f, off, h['method'], h['name'], h['packed'], h['orig'], len(out), hex(h['crc16']))
print('members', tot, 'ok', ok, 'bad', bad)
