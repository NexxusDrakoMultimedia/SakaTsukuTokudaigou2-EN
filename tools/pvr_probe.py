"""Ad-hoc probe: why does build_file() not rebuild some PVR file headers? (prints a histogram of header bytes)"""
import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pvr  # noqa: E402
import pvr_scan  # noqa: E402

hist = collections.Counter()


def on(t):
    if t.kind == 'PVR' and t.blob is not None:
        f = pvr.parse_file(t.blob)
        reb = pvr.build_file(f.pix, f.dat, f.w, f.h, t.blob[f.data_off:f.data_off + f.data_len], f.gbix)
        if reb != t.blob:
            diff = [i for i in range(min(len(reb), len(t.blob))) if reb[i] != t.blob[i]]
            hist[(tuple(diff[:6]), len(reb) - len(t.blob), t.blob[12:16].hex())] += 1


pvr_scan.scan_all('extracted', on_texture=on, keep_rows=False, only=['GAME/BIND', 'DPTEX'])
for k, v in hist.most_common(8):
    print(v, k)
