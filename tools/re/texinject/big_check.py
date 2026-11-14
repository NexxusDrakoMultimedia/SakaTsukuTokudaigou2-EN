"""No-op and exact-length edit on three textures of the 120 MB GAME/BINDUNIF.BIN (20,333 stored PVR members).
python -I -X utf8 tools/re/texinject/big_check.py"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject as T  # noqa: E402

t0 = time.time()
rel = 'GAME/BINDUNIF.BIN'
src = T._as_bytes(rel)
ms, tail = T.zs_members(src)
print('members', len(ms), 'tail==len', tail == len(src), '%.1fs' % (time.time() - t0), flush=True)
ok = True
for k in (0, len(ms) // 2, len(ms) - 1):
    tid = '[%d]' % k
    pvr = T.extract_pvr(src, tid)
    noop = T.replace_texture(src, tid, pvr) == src
    p = T.parse_pvr(pvr)
    ed = bytearray(p.payload)
    ed[len(ed) // 2:len(ed) // 2 + 8] = bytes(8)
    out = T.replace_texture(src, tid, T.build_pvr(p.fmt, p.dt, p.w, p.h, bytes(ed), p.index))
    m = ms[k]
    lo, hi = m.offset, (m.end_offset + 3) & ~3
    same_len = len(out) == len(src)
    outside = out[:lo] == src[:lo] and out[hi:] == src[hi:]
    back = T.parse_pvr(T.extract_pvr(out, tid)).payload == bytes(ed)
    print('%s method=%s noop=%s same_len=%s only_member_changed=%s readback=%s %.1fs' % (tid, m.method, noop, same_len, outside, back, time.time() - t0), flush=True)
    ok = ok and noop and same_len and outside and back
print('BIG OK' if ok else 'BIG FAILED')
sys.exit(0 if ok else 1)
