import sys, os, collections
sys.path.insert(0, 'tools/re/ghidra')
from members import iter_members
from bz_ghidra import decompress, crc16
st = collections.Counter(); badf = []; nf = 0
for r, ds, fs in os.walk('extracted'):
    for fn in fs:
        p = os.path.join(r, fn)
        if os.path.getsize(p) > 40_000_000 or fn.upper().endswith(('.PVR','.WAV')): continue
        d = open(p, 'rb').read()
        if len(d) < 50 or d[2:4] != b'-n' and d[2:4] != b'-b': 
            # may start later; only first-member check
            continue
        nf += 1
        try:
            for h, pk, off in iter_members(d):
                try:
                    out = decompress(h['method'], pk)
                    g = len(out) == h['orig'] and crc16(out) == h['crc16']
                except Exception as e:
                    g = False
                st[(h['method'], g)] += 1
                if not g: badf.append((p, off, h['method'], h['name']))
        except Exception as e:
            badf.append((p, 'iter', str(e)))
print(nf, 'files'); print(st); print(badf[:20])
