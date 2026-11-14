"""Disc-wide sweep of texinject: for every texture-bearing file of extracted/ pick the first, a middle and the last texture and

    1. no-op:     replace_texture(src, id, extract_pvr(src, id)) must be byte-identical
    2. modified:  inject a lightly edited payload with policy 'exact' (first edit from a list that fits); the output must have
                  the same length, differ only inside the texture's slot (+ZSARC member header CRC fields), read back
                  as the edited payload, and (ZSARC, files < 20 MB) pass the game-loader checks of the archive walk.

    python -I -X utf8 tools/re/texinject/sweep.py [--skip-big N]     (files larger than N MB are skipped; default 130)
Prints counts per kind and every failure.  Takes a few minutes."""
import os
import sys
import time
import struct
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject as T  # noqa: E402

skip_mb = int(sys.argv[sys.argv.index('--skip-big') + 1]) if '--skip-big' in sys.argv else 130


def edits(p):
    n = len(p)
    a = (n // 2) & ~1
    out = []
    b = bytearray(p)
    b[a:a + 16] = bytes(16)
    out.append(bytes(b))
    b = bytearray(p)
    if a >= 2:
        b[a:a + 2] = b[a - 2:a]
    out.append(bytes(b))
    b = bytearray(p)
    b[-2:] = b'\0\0'
    out.append(bytes(b))
    b = bytearray(p)                                            # always differs: a 16-byte run of a value unlike the old byte
    b[a:a + 16] = bytes([(p[a] ^ 0x5a) & 0xff]) * 16
    out.append(bytes(b))
    return [x for x in out if x != p]


def span(src, tid):
    t = T.resolve(src, tid)
    if t['type'] == 'pvr-file':
        return 0, len(src), None
    if t['type'] == 'zs-pvr':
        m = t['ms'][t['mi']]
        return m.data_offset, (m.end_offset + 3) & ~3, m
    s, e = T._rec_slot(t['plain'] if t['type'] == 'zs-tbd' else src, t['table'], t['index'])
    if t['type'] == 'tbd':
        return s, e, None
    m = t['ms'][t['mi']]
    return m.data_offset + s, m.data_offset + e, m


def hdr_positions(src, m):
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
    return pos


def diffs(a, b):
    out = []
    for o in range(0, len(a), 4096):
        if a[o:o + 4096] != b[o:o + 4096]:
            out += [k for k in range(o, min(len(a), o + 4096)) if a[k] != b[k]]
    return out


def walk_all(d):
    o = 0
    n = 0
    while True:
        out, end, why = T.game_walk_zsarc(d, o)
        n += len(out)
        if why != 'terminator':
            return n
        o = end
        while o < len(d) and d[o] == 0:
            o += 1
        if o >= len(d):
            return n


stats = collections.Counter()
fails = []
t0 = time.time()
ext = os.path.join(ROOT, 'extracted')
for root, dirs, files in os.walk(ext):
    dirs.sort()
    for fn in sorted(files):
        if fn in ('BCAST.BIN', '_filelist.tsv'):
            continue
        path = os.path.join(root, fn)
        rel = os.path.relpath(path, ext).replace('\\', '/')
        if rel.split('/')[0] in ('SSONG', 'SOUND', 'DPSS', 'DPWWW'):
            continue
        if os.path.getsize(path) > skip_mb * 1024 * 1024:
            stats['skipped big file'] += 1
            continue
        with open(path, 'rb') as f:
            src = f.read()
        try:
            texs = T.list_textures(src)
        except Exception as e:       # noqa: BLE001
            fails.append((rel, 'list', repr(e)))
            continue
        if not texs:
            continue
        stats['files with textures'] += 1
        print('%7.0fs %s (%d textures)' % (time.time() - t0, rel, len(texs)), file=sys.stderr, flush=True)
        n = len(texs)
        for k in sorted({0, n // 2, n - 1}):
            t = texs[k]
            kind = t.kind
            stats['tried ' + kind] += 1
            try:
                pvr = T.extract_pvr(src, t.tid)
                if T.replace_texture(src, t.tid, pvr) != src:
                    fails.append((rel, t.tid, 'no-op differs'))
                    continue
                stats['no-op byte-identical ' + kind] += 1
                p = T.parse_pvr(pvr)
                out = ed = None
                for cand in edits(p.payload):
                    try:
                        out = T.replace_texture(src, t.tid, T.build_pvr(p.fmt, p.dt, p.w, p.h, cand, p.index))
                        ed = cand
                        break
                    except T.FitError:
                        continue
                if out is None:
                    stats['no test edit fits (zero-slack slot) ' + kind] += 1
                    continue
                if len(out) != len(src):
                    fails.append((rel, t.tid, 'length changed'))
                    continue
                s, e, m = span(src, t.tid)
                allowed = hdr_positions(src, m) if m is not None else set()
                dp = diffs(src, out)
                bad = [x for x in dp if not (s <= x < e) and x not in allowed]
                if bad or not dp:
                    fails.append((rel, t.tid, 'diff outside slot: %d bytes (first %s)' % (len(bad), bad[:3])))
                    continue
                if T.parse_pvr(T.extract_pvr(out, t.tid)).payload != ed:
                    fails.append((rel, t.tid, 'readback differs'))
                    continue
                if m is not None and len(src) < 20 * 1024 * 1024:
                    c0, c1 = walk_all(src), walk_all(out)
                    if c0 != c1:
                        fails.append((rel, t.tid, 'loader walk member count %d -> %d' % (c0, c1)))
                        continue
                    stats['loader walk of whole file OK ' + kind] += 1
                stats['modified, exact length, only slot changed ' + kind] += 1
            except Exception as ex:      # noqa: BLE001
                fails.append((rel, t.tid, repr(ex)))
print('%.0fs' % (time.time() - t0))
for k in sorted(stats):
    print('%-62s %d' % (k, stats[k]))
print('FAILURES:', len(fails))
for f in fails[:40]:
    print('  ', f)
sys.exit(1 if fails else 0)
