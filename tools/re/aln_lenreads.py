"""aln: list every read of the right-anchor length fields (obj+64..144 step 8 / 4) as `mov.w @(r0,rO),rL` with r0 set just before,
and say whether the read belongs to one of the idiom sites (x = anchor - 12*len).

    python -I -X utf8 tools/re/aln_lenreads.py OVERLAY [START END]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aln_scan12 as S12  # noqa: E402

name = sys.argv[1]
d = open(os.path.join(S12.DIR, name + '.BIN'), 'rb').read()
ws = struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])
idiom = [h for h in S12.scan(ws) if S12.near_xstore(ws, h)]
lo = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0
hi = int(sys.argv[3], 16) if len(sys.argv) > 3 else len(d)
K = {64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144}
for i in range(1, len(ws)):
    w = ws[i]
    if w & 0xF00F == 0x000D:                      # mov.w @(r0,rm),rn
        # find a mov #imm,r0 within the 3 words before
        for j in range(i - 1, max(i - 4, 0), -1):
            if ws[j] >> 12 == 0xE and (ws[j] >> 8) & 15 == 0 and (ws[j] & 0xFF) in K:
                a = i * 2
                if lo <= a < hi:
                    near = [h for h in idiom if h - 24 <= a <= h + 4]
                    print('read len+%3d at %#x  rn=r%d  idiom=%s' % (ws[j] & 0xFF, a, (w >> 8) & 15, ('%#x' % near[0]) if near else 'NO'))
                break
