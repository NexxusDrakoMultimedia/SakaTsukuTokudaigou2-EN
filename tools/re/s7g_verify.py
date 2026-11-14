"""s7g_verify: apply the installed GAME/GAMEETC.ZAR tag textures to extracted/ with texinject (what the build does) and check
the result: same length, no stale stored ZSARC member, the run at 0x110 passes the loader emulation (game_walk_zsarc),
only bytes inside the five member slots changed, every new texture decodes to the repainted image."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject as T, pvr
import numpy as np
ext = os.path.join(ROOT, 'extracted')
g = T.load_textures_dir(os.path.join(ROOT, 'translation', 'textures'), ext)
tex = g['GAME/GAMEETC.ZAR']
print('GAMEETC textures:', sorted(tex))
src = open(os.path.join(ext, 'GAME', 'GAMEETC.ZAR'), 'rb').read()
cur = src
for tid in sorted(tex):
    r = T.inject(cur, tid, tex[tid], 'exact')
    cur = r.data
    print('  %-22s changed=%s %s' % (tid, r.info.get('changed'), {k: r.info[k] for k in ('slot', 'packed') if k in r.info}))
print('length', len(src), len(cur), 'same' if len(src) == len(cur) else 'DIFFERENT')
print('stale stored members:', T.stale_stored_members(src, cur))
out, end, why = T.game_walk_zsarc(cur, 0x110)
print('loader emulation of the run at 0x110: %d members, ends %#x (%s)' % (len(out), end, why))
diff = [i for i in range(len(src)) if src[i] != cur[i]]
spans = []
for i in diff:
    if spans and i - spans[-1][1] < 64: spans[-1][1] = i
    else: spans.append([i, i])
print('changed bytes %d in %d span(s):' % (len(diff), len(spans)), [(hex(a), hex(b)) for a, b in spans])
for tid, data in sorted(tex.items()):
    got = np.asarray(pvr.decode(T.extract_pvr(cur, tid))).astype(int); want = np.asarray(pvr.decode(data)).astype(int)
    print('  %-22s decoded from patched container == installed file: %s' % (tid, bool((got == want).all())))
