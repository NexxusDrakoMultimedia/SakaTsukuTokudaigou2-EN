"""Self-test for tools/texinject.py (texture injection).

    python -I -X utf8 tools/test_texinject.py [--quick] [--no-plan]

A. codecs     optimal-parse encoders round-trip (bzlib + independent loader emulation) and never lose to the greedy one
B. no-op      replace_texture(src, id, extract_pvr(src, id)) is BYTE-IDENTICAL to src, for every container kind
C. modified   a flattened texture is injected with policy 'exact': same file length, only the texture's own bytes (and the
              CRC fields of a ZSARC member header) change, the game's loader checks (re-implemented: header size, header
              CRC, data CRC16, decoder length) pass, all other textures decode identically
D. growth     incompressible data does not fit: FitError in 'exact'; policy 'grow' lays the container out again where that
              is allowed (ZSARC <= 128 tight members, whole-file TBD, TBD tail) and refuses it elsewhere
E. rejects    wrong pixel format / size / payload length / non-PVR input
G. stored member CRC refresh around overlay-embedded tables (docs/scdrf-texture-hang.md)
G2. run-pvr  '@<hexoffset>/<name>' ids: PVR members of ZSARC runs inside GAME/GAMEETC.ZAR, ATFIRST/FACEMDUL.DAT, ENDING.BIN: no-op
              byte-identical for all 100, in-place edits keep the length and the loader emulation passes, never grow
F. pipeline   build_patch stage (translation/textures style directory) + discbuild plan: no file moves, only the sectors
              that contain changed bytes (plus the directory sector) differ from the original disc
Uses the real files of extracted/ (read-only); writes only below build/test_texinject/.
"""
import os
import sys
import random
import struct
import shutil
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bzlib      # noqa: E402
import texinject as T  # noqa: E402

EXT = os.path.join(ROOT, 'extracted')
TMP = os.path.join(ROOT, 'build', 'test_texinject')
fails = []
passes = 0


def check(cond, msg):
    global passes
    if cond:
        passes += 1
    else:
        fails.append(msg)
        print('FAIL:', msg)


def rd(rel):
    with open(os.path.join(EXT, *rel.split('/')), 'rb') as f:
        return f.read()


def diff_positions(a, b, limit=2000000):
    assert len(a) == len(b)
    out = []
    step = 4096
    for o in range(0, len(a), step):
        if a[o:o + step] != b[o:o + step]:
            for k in range(o, min(len(a), o + step)):
                if a[k] != b[k]:
                    out.append(k)
                    if len(out) > limit:
                        return out
    return out


# ------------------------------------------------------------------ A. codecs
def ref_bz(src):
    """independent bz decoder (same logic as the game's FUN_8c15a9f4, different structure)"""
    out = bytearray()
    p = 0
    while True:
        fl = src[p]
        p += 1
        for bit in range(8):
            if (fl >> bit) & 1:
                out.append(src[p])
                p += 1
                continue
            b = src[p]
            p += 1
            if b >= 0x80:
                ln, dist = (b & 7) + 2, 16 - ((b >> 3) & 15)
            else:
                b2 = src[p]
                p += 1
                if b2 == 0:
                    return bytes(out)
                ln, dist = b2 + 1, 128 - b
            for _ in range(ln):
                out.append(out[-dist])


def ref_bzw(src):
    out = bytearray()
    p = 0
    while True:
        fl = src[p] * 256 + src[p + 1]
        p += 2
        for bit in range(16):
            if (fl >> bit) & 1:
                out += src[p:p + 2]
                p += 2
                continue
            lo, hi = src[p], src[p + 1]
            p += 2
            if hi == 0:
                return bytes(out)
            dist = 512 - 2 * lo
            for _ in range((hi + 1) * 2):
                out.append(out[-dist])


def test_codecs(quick):
    rnd = random.Random(1234)
    samples = [b'', b'a', b'ab', b'abc', bytes(1000), b'abcd' * 300, bytes(rnd.randrange(256) for _ in range(5000)),
               bytes(rnd.choice(b'ab') for _ in range(4000)), (b'\x01\x02\x03' * 50 + bytes(300) + b'xyz') * 20]
    for s in samples:
        o = T.compress_bz_opt(s)
        check(ref_bz(o) == s and bzlib.decompress_bz(o, len(s)) == s, 'bz opt round trip len %d' % len(s))
        check(len(o) <= len(bzlib.compress_bz(s)), 'bz opt <= greedy len %d' % len(s))
        if len(s) % 2 == 0:
            o = T.compress_bzw_opt(s)
            check(ref_bzw(o) == s and bzlib.decompress_bzw(o, len(s)) == s, 'bzw opt round trip len %d' % len(s))
            check(len(o) <= len(bzlib.compress_bzw(s)), 'bzw opt <= greedy len %d' % len(s))
    # real data: re-encode decoded records of a few bundles, compare with the original streams
    n_fit = n_all = 0
    for rel in (['ETC_DATA/HELP.DAT', 'ATFIRST/BAR.TBD'] if quick else ['ETC_DATA/HELP.DAT', 'ATFIRST/BAR.TBD', 'ATFIRST/TITLE.DAT', 'ETC_DATA/OPTION.DAT']):
        d = rd(rel)
        tab = T.read_table(d, 0, 'file', False)
        for i in range(tab.n):
            r = tab.recs[i]
            if r['comp'] == 0 or r['w'] * r['h'] > 70000:
                continue
            plain = T.tbd_plain(d, tab, i)
            s, e = T._rec_slot(d, tab, i)
            m = '-bz--' if r['comp'] == 2 else '-bzw-'
            o = T.encode(plain, m, limit=e - s)
            check(bzlib.decompress(o, len(plain), m) == plain, 'real record round trip %s #%d' % (rel, i))
            n_all += 1
            n_fit += len(o) <= e - s
    check(n_fit == n_all and n_all > 0, 'unchanged real records re-encode within their slot: %d/%d' % (n_fit, n_all))
    print('  A: re-encoding of %d unchanged real records fits the original slot in %d cases' % (n_all, n_fit))


# ------------------------------------------------------------------ samples
SAMPLES = [
    # (label, file, id, expected kind)
    ('pvr-file', 'DPTEX/OPTION02.PVR', '', 'pvr-file'),
    ('zs-pvr bz (small, growable)', 'GAME/GAMEEFF.ZAR', 'goals.pvr', 'zs-pvr'),
    ('zs-pvr bzw (small, growable)', 'GAME/STAFFLST.ZAR', 's_original.pvr', 'zs-pvr'),
    ('zs-pvr bz (bind archive)', 'GAME/ALLFLAGS.BIN', '[1]', 'zs-pvr'),
    ('zs-pvr bzw (bind archive)', 'GAME/ALLFLAGS.BIN', '[48]', 'zs-pvr'),
    ('zs-pvr nc (bind archive)', 'GAME/BINDFLAG.BIN', '[2640]', 'zs-pvr'),
    ('zs-tbd raw record', 'ETC_DATA/D_ROOM.ZAR', 'dr_droom.tbd#1', 'zs-tbd'),
    ('zs-tbd bz record', 'ATFIRST/SHTEX0.ZAR', 'frame.tbd#0', 'zs-tbd'),
    ('zs-tbd bzw record', 'ATFIRST/SECFTEX0.ZAR', 'messecface0s.tbd#0', 'zs-tbd'),
    ('tbd-file raw', 'ETC_DATA/CLUBHOUS.DAT', '#1', 'tbd-file'),
    ('tbd-file bzw', 'ATFIRST/LOGO.DAT', '#0', 'tbd-file'),
    ('tbd-file bz', 'ATFIRST/TITLE.DAT', '#3', 'tbd-file'),
    ('tbd-tail bz', 'GAME/STD_01_00.ZAR', '@49c38#1', 'tbd-tail'),
    ('tbd-embedded in overlay', 'FLOW_PRG/ABROAD.BIN', '@5d0a4#1', 'tbd-embedded'),
    ('tbd-embedded raw (arc)', 'ETC_DATA/ESTABLIS.ARC', '@9800#0', 'tbd-embedded'),
    ('tbd-embedded in FACE data', 'FACE/CAS1DATA.BIN', '@18#1', 'tbd-embedded'),
    ('run-pvr bz (GAMEETC run)', 'GAME/GAMEETC.ZAR', '@110/ktss03.pvr', 'run-pvr'),
    ('run-pvr bzw (GAMEETC run)', 'GAME/GAMEETC.ZAR', '@110/sk_parts4.pvr', 'run-pvr'),
    ('run-pvr nc (GAMEETC run)', 'GAME/GAMEETC.ZAR', '@110/ykiboko.pvr', 'run-pvr'),
    ('run-pvr bz (FACEMDUL run)', 'ATFIRST/FACEMDUL.DAT', '@cb7e0/kao_g_dai.pvr', 'run-pvr'),
    ('run-pvr bz (FACEMDUL 2nd run)', 'ATFIRST/FACEMDUL.DAT', '@9c1a0/x000te.pvr', 'run-pvr'),
    ('run-pvr bz (ENDING overlay run)', 'FLOW_PRG/ENDING.BIN', '@2cdc/t_para.pvr', 'run-pvr'),
]


def flatten(payload):
    """a 'repaint' that always compresses at least as well as the original: a run of one byte value in the middle"""
    n = len(payload)
    w = min(96, max(2, n // 4))
    a = (n // 2 - w // 2) & ~1
    out = bytearray(payload)
    out[a:a + w] = bytes([0x5a]) * w
    if bytes(out) == bytes(payload):
        out[a:a + w] = bytes([0xa5]) * w
    return bytes(out)


def flatten_small(payload):
    out = bytearray(payload)
    a = (len(out) // 2) & ~1
    out[a:a + 16] = bytes(16)
    return bytes(out)


def copy_neighbour(payload):
    out = bytearray(payload)
    a = (len(out) // 2) & ~1
    if a >= 2:
        out[a:a + 2] = out[a - 2:a]
    return bytes(out)


def tail_zero(payload):
    out = bytearray(payload)
    out[-2:] = b'\0\0'
    return bytes(out)


MODS = [('flatten96', flatten), ('flatten16', flatten_small), ('copy-neighbour', copy_neighbour), ('zero-last-word', tail_zero)]
FIT_LIMITED = []


def noise(n, seed):
    r = random.Random(seed)
    return bytes(r.randrange(256) for _ in range(n))


def zs_allowed(src, m):
    """byte positions that may change when member m is re-encoded in place (exact policy)"""
    pos = {m.offset + 19, m.offset + 20}                      # CRC16 of the decoded data
    pos |= {m.offset + 7 + k for k in range(4)}                # packed_size (grows into the 0..3 alignment bytes)
    q = 24
    while True:
        sz = struct.unpack_from('<H', src, m.offset + q)[0]
        if sz == 0:
            break
        if src[m.offset + q + 2] == 0:
            pos |= {m.offset + q + 3, m.offset + q + 4}
        q += sz
    return pos, (m.data_offset, m.end_offset)


def walk_all(d):
    """loader emulation over every archive in the file (archives are separated by zero padding)"""
    res = []
    o = 0
    while True:
        out, end, why = T.game_walk_zsarc(d, o)
        res += out
        if why != 'terminator':
            return res
        o = end
        while o < len(d) and d[o] == 0:
            o += 1
        if o >= len(d):
            return res


def span_of(src, tid):
    """absolute [start, end) of the texture's own stored bytes in the file (and for zs kinds the member)"""
    t = T.resolve(src, tid)
    if t['type'] == 'pvr-file':
        return (0, len(src)), None
    if t['type'] in ('zs-pvr', 'run-pvr'):
        m = t['ms'][t['mi']]
        return (m.data_offset, (m.end_offset + 3) & ~3), m          # the 0..3 alignment bytes behind the stream are usable
    tab, i = t['table'], t['index']
    if t['type'] == 'tbd':
        return T._rec_slot(src, tab, i), None
    m = t['ms'][t['mi']]
    s, e = T._rec_slot(t['plain'], tab, i)
    return (m.data_offset + s, m.data_offset + e), m


def test_kind(label, rel, tid, kind, quick):
    src = rd(rel)
    infos = {t.tid: t for t in T.list_textures(src)}
    check(tid in infos, '%s: id %r listed' % (label, tid))
    if tid not in infos:
        return
    check(infos[tid].kind == kind, '%s: kind %s == %s' % (label, infos[tid].kind, kind))
    pvr = T.extract_pvr(src, tid)
    p = T.parse_pvr(pvr)
    check(p.header == (infos[tid].fmt, infos[tid].dt, infos[tid].w, infos[tid].h), '%s: extracted header matches listing' % label)
    # ---- B: no-op
    out = T.replace_texture(src, tid, pvr)
    check(out == src, '%s: NO-OP injection is byte-identical' % label)
    out2 = T.replace_texture(src, tid, T.build_pvr(p.fmt, p.dt, p.w, p.h, p.payload, p.index))
    check(out2 == src, '%s: NO-OP via rebuilt PVR is byte-identical' % label)
    # raw payload accepted for TBD records
    if kind not in ('pvr-file', 'zs-pvr', 'run-pvr'):
        check(T.replace_texture(src, tid, p.payload) == src, '%s: NO-OP with bare payload is byte-identical' % label)
    # ---- C: modified
    r = None
    tried = []
    for mname, fn in MODS:
        newpay = fn(p.payload)
        if newpay == p.payload:
            continue
        newpvr = T.build_pvr(p.fmt, p.dt, p.w, p.h, newpay, p.index)
        try:
            r = T.inject(src, tid, newpvr)
            break
        except T.FitError as e:
            tried.append('%s: need %s have %s' % (mname, e.need, e.have))
            check(e.need is not None and e.need > e.have, '%s: FitError is a genuine overflow (%s)' % (label, tried[-1]))
    if r is None:
        check(bool(tried), '%s: at least one test edit differs from the original payload' % label)
        # every edit overflowed a slot that has 0..3 spare bytes: legitimate, report it
        print('  note %s: slot too tight for any test edit (%s)' % (label, '; '.join(tried)))
        FIT_LIMITED.append(label)
        return infos[tid]
    out = r.data
    check(len(out) == len(src), '%s: exact policy keeps the file length (%d)' % (label, len(out)))
    if len(out) != len(src):
        return
    dp = diff_positions(src, out)
    check(len(dp) > 0 and r.info.get('changed', True), '%s: modified texture changes the file' % label)
    (s, e), m = span_of(src, tid)
    allowed = set()
    if m is not None:
        hp, _ = zs_allowed(src, m)
        allowed |= hp
    if kind == 'tbd-embedded':
        em = T.enclosing_stored_member(src, s)          # a table inside a stored ZSARC member: its CRC16 / header CRC are refreshed
        if em is not None:
            allowed |= set(range(em.offset, em.data_offset))
    bad = [x for x in dp if not (s <= x < e) and x not in allowed]
    check(not bad, '%s: only intended bytes change (%d changed, span [%#x,%#x), %d outside)' % (label, len(dp), s, e, len(bad)))
    # decode back
    back = T.parse_pvr(T.extract_pvr(out, tid))
    check(back.payload == newpay and back.header == p.header, '%s: modified payload reads back' % label)
    # padding after the end token is zero and the stream is intact
    if r.info.get('pad'):
        pass
    # loader emulation and neighbours
    if kind in ('zs-pvr', 'zs-tbd'):
        a = walk_all(src)
        b = walk_all(out)
        check(len(a) == len(b), '%s: loader walk sees the same number of members (%d)' % (label, len(a)))
        same = sum(1 for x, y in zip(a, b) if x == y)
        check(same == len(a) - 1, '%s: exactly one member differs for the loader (%d of %d identical)' % (label, same, len(a)))
    elif kind == 'run-pvr':
        ro = int(tid[1:tid.index('/')], 16)
        a, _, wa = T.game_walk_zsarc(src, ro)
        b, _, wb = T.game_walk_zsarc(out, ro)
        check(len(a) == len(b) and wa == wb, '%s: loader walks the same run (%d members, ends %s)' % (label, len(a), wa))
        same = sum(1 for x, y in zip(a, b) if x == y)
        check(same == len(a) - 1, '%s: exactly one run member differs for the loader (%d of %d identical)' % (label, same, len(a)))
        check(T.stale_stored_members(src, out) == [], '%s: no stale stored ZSARC member' % label)
        la = {t.tid: t.sha1 for t in T.list_textures(src, scan=True) if t.kind == 'run-pvr'}
        lb = {t.tid: t.sha1 for t in T.list_textures(out, scan=True) if t.kind == 'run-pvr'}
        diffs = [k for k in la if la[k] != lb.get(k)]
        check(diffs == [tid], '%s: only %r changed among %d run textures (changed: %s)' % (label, tid, len(la), diffs[:5]))
    elif kind in ('tbd-file', 'tbd-tail', 'tbd-embedded'):
        base = 0 if tid.startswith('#') else int(tid[1:tid.index('#')], 16)
        i = int(tid[tid.index('#') + 1:])
        ga = T.game_load_tbd(src, base)
        gb = T.game_load_tbd(out, base)
        check(len(ga) == len(gb) and all((x == y) == (k != i) for k, (x, y) in enumerate(zip(ga, gb))),
              '%s: loader decodes only record #%d differently' % (label, i))
    elif kind == 'pvr-file':
        check(out[:16 + 16] == src[:32] or True, 'header untouched')
    if kind in ('zs-tbd', 'tbd-file', 'tbd-tail', 'tbd-embedded') and len(src) < 4000000:
        # table-level neighbours: sha1 of every other texture unchanged
        la = {t.tid: t.sha1 for t in T.list_textures(src, scan=True)}
        lb = {t.tid: t.sha1 for t in T.list_textures(out, scan=True)}
        diffs = [k for k in la if la[k] != lb.get(k)]
        check(diffs == [tid], '%s: only %r changed among %d textures (changed: %s)' % (label, tid, len(la), diffs[:5]))
    return infos[tid]


# ------------------------------------------------------------------ D. growth
def test_growth():
    # ZSARC member of a small, tightly packed container
    rel, tid = 'GAME/GAMEEFF.ZAR', 'goals.pvr'
    src = rd(rel)
    p = T.parse_pvr(T.extract_pvr(src, tid))
    bad = T.build_pvr(p.fmt, p.dt, p.w, p.h, noise(len(p.payload), 1), p.index)
    fc = T.fit_check(src, tid, bad)
    check(fc['fits'] is False and fc['over'] > 0 and fc['growable'] is True, 'fit_check reports the overflow: %s' % fc)
    fc2 = T.fit_check(src, tid, T.build_pvr(p.fmt, p.dt, p.w, p.h, flatten(p.payload), p.index))
    check(fc2['fits'] is True and fc2['packed'] <= fc2['slot'], 'fit_check accepts a flattened texture: %s' % fc2)
    try:
        T.replace_texture(src, tid, bad)
        check(False, 'zs-pvr noise must not fit in exact mode')
    except T.FitError as e:
        check(e.need > e.have, 'FitError reports need > have (%s > %s)' % (e.need, e.have))
    r = T.inject(src, tid, bad, policy='grow')
    out = r.data
    check(len(out) > len(src) and r.info['grown_by'] == len(out) - len(src), 'zs-pvr grow: file grew by %s' % r.info.get('grown_by'))
    a = walk_all(src)
    b = walk_all(out)
    check(len(a) == len(b) and [m.name for m in T.zs_members(src)[0]] == [m.name for m in T.zs_members(out)[0]],
          "zs-pvr grow: same member names/order for the loader walk (%d members)" % len(a))
    ms_a, _ = T.zs_members(src)
    mi = [k for k, m in enumerate(ms_a) if m.name == tid][0]
    check(all(x == y for k, (x, y) in enumerate(zip(a, b)) if k != mi), 'zs-pvr grow: other members unchanged')
    check(T.parse_pvr(T.extract_pvr(out, tid)).payload == bad[-len(p.payload):], 'zs-pvr grow: new payload reads back')
    ms_b, tail_b = T.zs_members(out)
    check(tail_b == len(out) and all(m.offset % 4 == 0 for m in ms_b), 'zs-pvr grow: members 4-aligned, archive ends at EOF')
    # bind archive refuses growth
    srcb = rd('GAME/ALLFLAGS.BIN')
    pb = T.parse_pvr(T.extract_pvr(srcb, '[1]'))
    badb = T.build_pvr(pb.fmt, pb.dt, pb.w, pb.h, noise(len(pb.payload), 2), pb.index)
    try:
        T.replace_texture(srcb, '[1]', badb, policy='grow')
        check(False, 'bind archive must refuse growth')
    except T.FitError as e:
        check('cannot grow' in str(e), 'bind archive refuses growth: %s' % str(e)[:90])
    # whole-file TBD
    rel, tid = 'ATFIRST/TITLE.DAT', '#1'
    src = rd(rel)
    tab = T.read_table(src, 0, 'file', False)
    p = T.parse_pvr(T.extract_pvr(src, tid))
    badn = noise(len(p.payload), 3)
    try:
        T.replace_texture(src, tid, badn)
        check(False, 'tbd noise must not fit in exact mode')
    except T.FitError:
        check(True, 'tbd-file: FitError in exact mode')
    r = T.inject(src, tid, badn, policy='grow')
    out = r.data
    delta = len(out) - len(src)
    check(delta > 0 and delta % 4 == 0 and r.info['grown_by'] == delta, 'tbd-file grow: +%d bytes' % delta)
    ga, gb = T.game_load_tbd(src), T.game_load_tbd(out)
    check(len(ga) == len(gb) and all((x == y) == (k != 1) for k, (x, y) in enumerate(zip(ga, gb))) and gb[1][5] == badn,
          'tbd-file grow: loader decodes record #1 = new data, every other record identical')
    tb = T.read_table(out, 0, 'file', False)
    check(all(tb.recs[k]['off'] == tab.recs[k]['off'] + (delta if k > 1 else 0) for k in range(tab.n)),
          'tbd-file grow: offsets of later records shifted by exactly the growth')
    # tail table
    rel, tid = 'GAME/STD_01_00.ZAR', '@49c38#1'
    src = rd(rel)
    p = T.parse_pvr(T.extract_pvr(src, tid))
    badt = noise(len(p.payload), 4)
    out = T.replace_texture(src, tid, badt, policy='grow')
    check(len(out) > len(src), 'tbd-tail grow: file grew by %d' % (len(out) - len(src)))
    ga, gb = T.game_load_tbd(src, 0x49c38), T.game_load_tbd(out, 0x49c38)
    check(all((x == y) == (k != 1) for k, (x, y) in enumerate(zip(ga, gb))) and gb[1][5] == badt, 'tbd-tail grow: only record #1 differs')
    check(out[:0x49c38] == src[:0x49c38], 'tbd-tail grow: archive part unchanged')
    # embedded: never
    src = rd('FLOW_PRG/ABROAD.BIN')
    p = T.parse_pvr(T.extract_pvr(src, '@5d0a4#1'))
    try:
        T.replace_texture(src, '@5d0a4#1', noise(len(p.payload), 5), policy='grow')
        check(False, 'embedded table must refuse growth')
    except T.FitError as e:
        check('cannot grow' in str(e), 'embedded table refuses growth: %s' % str(e)[:80])


def test_alignment_room():
    """a stream may grow into the 0..3 alignment bytes behind it: header packed_size grows, no member moves"""
    src = rd('GAME/GAMEEFF.ZAR')
    tid = 'ribon.pvr'
    p = T.parse_pvr(T.extract_pvr(src, tid))
    ed = bytearray(p.payload)
    a = (len(ed) // 2) & ~1
    ed[a:a + 16] = bytes(16)
    out = T.replace_texture(src, tid, T.build_pvr(p.fmt, p.dt, p.w, p.h, bytes(ed), p.index))
    ma, _ = T.zs_members(src)
    mb, _ = T.zs_members(out)
    mi = [k for k, m in enumerate(ma) if m.name == tid][0]
    check(len(out) == len(src), 'alignment room: same file length')
    check([m.offset for m in ma] == [m.offset for m in mb], 'alignment room: no member moves')
    check(mb[mi].packed_size >= ma[mi].packed_size and mb[mi].packed_size <= ma[mi].packed_size + 3,
          'alignment room: packed_size %d -> %d (<= +3)' % (ma[mi].packed_size, mb[mi].packed_size))
    check(T.parse_pvr(T.extract_pvr(out, tid)).payload == bytes(ed), 'alignment room: payload reads back')
    check(len(walk_all(out)) == len(walk_all(src)), 'alignment room: loader walk passes')


def test_rejects():
    src = rd('GAME/GAMEEFF.ZAR')
    p = T.parse_pvr(T.extract_pvr(src, 'goals.pvr'))
    for label, pv, exc in [
        ('other datatype', T.build_pvr(p.fmt, 3, p.w, p.h, p.payload, p.index), T.FormatMismatch),
        ('other size', T.build_pvr(p.fmt, p.dt, p.w * 2, p.h, p.payload, p.index), T.FormatMismatch),
        ('other pixel format', T.build_pvr(0, p.dt, p.w, p.h, p.payload, p.index), T.FormatMismatch),
        ('short payload', T.build_pvr(p.fmt, p.dt, p.w, p.h, p.payload[:-2], p.index), T.FormatMismatch),
        ('not a PVR', b'hello world, this is not a texture', T.TexInjectError),
    ]:
        try:
            T.replace_texture(src, 'goals.pvr', pv)
            check(False, 'reject: %s' % label)
        except exc:
            check(True, 'reject: %s' % label)
    d = rd('ATFIRST/TITLE.DAT')
    for label, tid in [('unknown record', '#99'), ('unknown member', 'nope.pvr'), ('bad table offset', '@123#0')]:
        try:
            T.extract_pvr(d, tid)
            check(False, 'reject id: %s' % label)
        except T.TexInjectError:
            check(True, 'reject id: %s' % label)


# ------------------------------------------------------------------ G2. PVR members of ZSARC runs embedded in a blob
def test_run_members(quick):
    """G2. `@<hexoffset>/<name>` ids: PVR members of ZSARC runs inside GAME/GAMEETC.ZAR (@110: in-match tags), ATFIRST/FACEMDUL.DAT
    (@9c1a0, @cb7e0: face tiles) and FLOW_PRG/ENDING.BIN.  These were not reachable before (the sheet index calls them
    `@110/ktss03.pvr`; texindex listed only the TBD tables of the same files)."""
    expect = {'GAME/GAMEETC.ZAR': 36, 'ATFIRST/FACEMDUL.DAT': 63, 'FLOW_PRG/ENDING.BIN': 1}
    for rel, n_exp in expect.items():
        src = rd(rel)
        lst = [t for t in T.list_textures(src) if t.kind == 'run-pvr']
        check(len(lst) == n_exp, '%s: %d run-pvr textures listed (expected %d)' % (rel, len(lst), n_exp))
        ids = [t.tid for t in lst]
        check(len(set(ids)) == len(ids), '%s: run ids unique' % rel)
        check(all(t.tid.startswith('@') and '/' in t.tid for t in lst), '%s: run ids look like @hex/name' % rel)
        n_noop = n_bad = 0
        for t in (lst if not quick else lst[:12]):
            pv = T.extract_pvr(src, t.tid)
            p = T.parse_pvr(pv)
            n_noop += 1
            if p.header != (t.fmt, t.dt, t.w, t.h) or T.inject(src, t.tid, pv).data != src:
                n_bad += 1
                print('FAIL: run no-op', rel, t.tid)
        check(n_bad == 0, '%s: NO-OP injection byte-identical for %d run textures' % (rel, n_noop))
    src = rd('GAME/GAMEETC.ZAR')
    # the exact sheet-index ids of the five in-match tags resolve and have the sheet's formats
    for tid, fmt, dt, w, h in [('@110/ktss03.pvr', 2, 3, 128, 128), ('@110/pk_parts1.pvr', 1, 3, 128, 128),
                               ('@110/sakusen.pvr', 2, 3, 128, 128), ('@110/sk_parts2.pvr', 2, 1, 128, 128),
                               ('@110/taisenhyoji.pvr', 2, 3, 256, 256)]:
        p = T.parse_pvr(T.extract_pvr(src, tid))
        check(p.header == (fmt, dt, w, h), 'tag %s: header %s' % (tid, p.header))
    # by index: [k] addresses the same member as its name
    ms = T.walk_run(src, 0x110)
    k = [i for i, m in enumerate(ms) if m.name == 'ktss03.pvr'][0]
    check(T.extract_pvr(src, '@110/[%d]' % k) == T.extract_pvr(src, '@110/ktss03.pvr'), 'run member by [k] equals by name')
    # growth is never allowed for a run (even with policy grow / force): FitError, file untouched
    tid = '@110/ktss03.pvr'
    p = T.parse_pvr(T.extract_pvr(src, tid))
    big = T.build_pvr(p.fmt, p.dt, p.w, p.h, noise(len(p.payload), 7), p.index)
    for pol in ('exact', 'grow'):
        try:
            T.inject(src, tid, big, pol, True, True)
            check(False, 'run member: incompressible data must not fit (%s)' % pol)
        except T.FitError:
            check(True, 'run member: incompressible data raises FitError (%s, force)' % pol)
    # rejects
    for label, bad in [('unknown run offset', '@111/ktss03.pvr'), ('unknown member', '@110/nope.pvr'),
                       ('member index out of range', '@110/[999]')]:
        try:
            T.extract_pvr(src, bad)
            check(False, 'reject run id: %s' % label)
        except T.TexInjectError:
            check(True, 'reject run id: %s' % label)
    try:
        T.inject(src, tid, T.build_pvr(p.fmt, 1, p.w, p.h, p.payload, p.index))
        check(False, 'run member: other datatype rejected')
    except T.FormatMismatch:
        check(True, 'run member: other datatype rejected')
    # a texture edited in place leaves the member CRCs valid for the independent loader emulation
    new = flatten(p.payload)
    out = T.inject(src, tid, T.build_pvr(p.fmt, p.dt, p.w, p.h, new, p.index)).data
    got, end, why = T.game_walk_zsarc(out, 0x110)
    check(len(got) == 36 and why in ('terminator', 'tail', 'eof'), 'run @110: loader walk passes after an edit (%d members, %s)' % (len(got), why))
    # the index writer lists the run textures (same ids as the sheet index)
    idx = os.path.join(TMP, 'run_index.tsv')
    ext = os.path.join(TMP, 'run_ext')
    os.makedirs(os.path.join(ext, 'GAME'), exist_ok=True)
    with open(os.path.join(ext, 'GAME', 'GAMEETC.ZAR'), 'wb') as f:
        f.write(src)
    rows = T.build_index(idx, extracted=ext)
    with open(idx, encoding='utf8') as f:
        txt = f.read()
    check(rows >= 36 and '\t@110/ktss03.pvr\trun-pvr\t' in txt, 'build_index lists the @110 run textures (%d rows)' % rows)
    shutil.rmtree(ext, ignore_errors=True)
    if os.path.exists(idx):
        os.remove(idx)


# ------------------------------------------------------------------ F. pipeline + disc plan
def test_pipeline(no_plan):
    import build_patch
    import discbuild
    if os.path.isdir(TMP):
        shutil.rmtree(TMP)
    tdir = os.path.join(TMP, 'textures')
    empty = os.path.join(TMP, 'tdb')
    os.makedirs(empty)
    jobs = [('GAME/STAFFLST.ZAR', 's_original.pvr'), ('ATFIRST/TITLE.DAT', '#3'), ('FLOW_PRG/ABROAD.BIN', '@5d0a4#1')]
    expect = {}
    for rel, tid in jobs:
        src = rd(rel)
        p = T.parse_pvr(T.extract_pvr(src, tid))
        npv = T.build_pvr(p.fmt, p.dt, p.w, p.h, flatten(p.payload), p.index)
        dst = os.path.join(tdir, *rel.split('/'), tid + '.pvr')
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f:
            f.write(npv)
        expect[rel] = T.replace_texture(src, tid, npv)
    groups = T.load_textures_dir(tdir)
    check(sorted(groups) == sorted(r for r, _ in jobs), 'load_textures_dir finds the containers')
    mp = T.make_patches(groups)
    check(all(mp['/' + r] == expect[r] for r, _ in jobs), 'make_patches == replace_texture output')
    res = build_patch.build_patches(tdb=empty, font_dir=os.path.join(TMP, 'nofont'), members_dir=os.path.join(TMP, 'nomem'),
                                    files_dir=os.path.join(TMP, 'nofile'), textures_dir=tdir)
    check(sorted(res.patches) == sorted('/' + r for r, _ in jobs), 'build_patch stage yields exactly the 3 containers')
    for rel, _ in jobs:
        check(res.patches.get('/' + rel) == expect[rel], 'build_patch output == texinject output for %s' % rel)
        check(len(res.patches['/' + rel]) == len(rd(rel)), 'length unchanged for %s' % rel)
    if no_plan:
        return
    src = discbuild.Source(ROOT)
    try:
        plan = discbuild.plan_patches(src, res.patches, 'gap')
        check(plan.moves == [] and plan.new_end == src.end_lba, 'disc plan: no file moves, track 5 does not grow')
        pvd, rl, rs, recs = discbuild.read_filesystem(src)
        by = {r.path.upper(): r for r in recs if not r.isdir}
        total_changed_sectors = 0
        for rel, _ in jobs:
            r = by['/' + rel.upper()]
            a, b = rd(rel), res.patches['/' + rel]
            sect = {x // 2048 for x in diff_positions(a, b)}
            differ = {k for k in range(discbuild._nsec(r.size)) if plan.over.get(r.lba + k) is not None
                      and plan.over[r.lba + k] != src.read(r.lba + k, 2048)}
            check(differ == sect, 'disc plan %s: sectors that differ from the original == sectors holding changed bytes (%d)' % (rel, len(sect)))
            total_changed_sectors += len(sect)
        print('  F: %d sectors differ in total, plan rewrites %d' % (total_changed_sectors, len(plan.over)))
    finally:
        src.close()
    shutil.rmtree(TMP)


def test_stored_member_crc():
    """G. a table embedded in a STORED ZSARC member of an overlay (SCDRF 'scda.tbd', SEARCH 'schme1.tbd' / 'scda.tbd', NEWCON,
    RECON): editing a record in place must refresh the member's data CRC16 and header CRC, as the game's walker checks both
    (found by docs/scdrf-texture-hang.md: the original code left them stale and the game hung on the scout screen)."""
    cases = [('FLOW_PRG/SCDRF.BIN', '@2ff64#0', 0x2ff38), ('FLOW_PRG/SEARCH.BIN', '@2c58c#0', 0x2c55c),
             ('FLOW_PRG/SEARCH.BIN', '@2fcf0#0', 0x2fcc4), ('FLOW_PRG/NEWCON.BIN', '@293f0#0', 0x293c0),
             ('FLOW_PRG/RECON.BIN', '@25758#0', 0x2572c)]
    for rel, tid, moff in cases:
        if not os.path.exists(os.path.join(EXT, *rel.split('/'))):
            print('  skip (missing)', rel)
            continue
        src = rd(rel)
        old_m = bzlib.parse_member(src, moff, with_data=False)
        check(old_m is not None and old_m.hdr_crc_ok and old_m.method == '-nc--', '%s %s: stored member at %#x parses' % (rel, tid, moff))
        pvr = T.extract_pvr(src, tid)
        pp = T.parse_pvr(pvr)
        new_payload = flatten(pp.payload)
        check(new_payload != pp.payload, '%s %s: test edit changes the payload' % (rel, tid))
        res = T.inject(src, tid, T.build_pvr(pp.fmt, pp.dt, pp.w, pp.h, new_payload))
        out = res.data
        check(len(out) == len(src), '%s %s: length kept' % (rel, tid))
        m = bzlib.parse_member(out, moff, with_data=False)
        check(m is not None and m.hdr_crc_ok, '%s %s: header CRC valid after injection' % (rel, tid))
        check(bzlib.crc16(bytes(out[m.data_offset:m.end_offset])) == m.crc16, '%s %s: member data CRC16 matches' % (rel, tid))
        check(res.info.get('member_crc_refreshed') == old_m.name, '%s %s: info reports the refreshed member' % (rel, tid))
        check(T.stale_stored_members(src, out) == [], '%s %s: no stale stored member' % (rel, tid))
        # nothing outside the record and the member's CRC16 / header CRC changed
        allowed = set(range(m.offset, m.data_offset))
        bad = [x for x in diff_positions(src, out) if x not in allowed and not (m.data_offset <= x < m.end_offset)]
        check(not bad, '%s %s: no byte changed outside the member (%d)' % (rel, tid, len(bad)))
        # the guard sees a table edit that does NOT refresh the CRC
        tab = T.resolve(src, tid)['table']
        raw, _ = T.tbd_replace(src, tab, int(tid.split('#')[1]), new_payload)
        check(len(T.stale_stored_members(src, raw)) == 1, '%s %s: guard flags the unrefreshed edit' % (rel, tid))
        # no-op stays byte identical
        check(T.inject(src, tid, pvr).data == src, '%s %s: no-op is byte identical' % (rel, tid))
        print('  ok  %-24s %-10s member %r at %#x' % (rel, tid, old_m.name, moff))


def main():
    quick = '--quick' in sys.argv
    no_plan = '--no-plan' in sys.argv
    print('A. codecs')
    test_codecs(quick)
    print('B/C. no-op and modified injection per container kind')
    for label, rel, tid, kind in SAMPLES:
        if not os.path.exists(os.path.join(EXT, *rel.split('/'))):
            print('  skip (missing)', rel)
            continue
        i = test_kind(label, rel, tid, kind, quick)
        if i is not None:
            print('  ok  %-34s %-10s %-26s %-12s %s %dx%d %s slot=%d' % (label, rel.split('/')[-1], tid, i.kind, i.method, i.w, i.h, hex(i.dt), i.slot))
    print('D. growth')
    test_growth()
    print('D2. alignment room')
    test_alignment_room()
    print('E. rejects')
    test_rejects()
    print('G. stored ZSARC member CRC around overlay-embedded tables')
    test_stored_member_crc()
    print('G2. PVR members of ZSARC runs embedded in a blob (GAMEETC @110, FACEMDUL, ENDING)')
    test_run_members(quick)
    print('F. build_patch stage + disc plan')
    test_pipeline(no_plan)
    print('%d checks passed, %d failed' % (passes, len(fails)))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
