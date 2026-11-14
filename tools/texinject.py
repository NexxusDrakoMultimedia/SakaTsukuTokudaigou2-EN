"""texinject - put a replaced (repainted) texture back into a SakaTsuku Tokudaigou 2 data file.

    import sys; sys.path.insert(0, 'tools')
    import texinject
    new_bytes = texinject.replace_texture('GAME/STAFFLST.ZAR', 's_xxx.pvr', pvr_bytes)      # -> patched file bytes
    patches['/GAME/STAFFLST.ZAR'] = new_bytes                                                # tools/build_patch.py / discbuild

Read docs/texture-injection.md first (what the game's loader tolerates, with proofs and open points).

Containers handled (texture id grammar in parentheses):
  * plain PVR file (GBIX+PVRT)                        id ''          e.g. DPTEX/*.PVR, 0GDTEX.PVR
  * ZSARC member holding a PVR file                   id 'name' or '[k]' (k = member index)
  * ZSARC member holding a TBD bundle                 id 'name#i' or '[k]#i'
  * whole-file TBD bundle (.TBD/.DAT, some .ZAR/.BIN) id '#i'
  * TBD table in the tail of a ZSARC (GAME/STD_*.ZAR) id '@tail#i' or '@<hexoffset>#i'
  * TBD table embedded in an overlay or other blob    id '@<hexoffset>#i'   (FLOW_PRG/*.BIN, FACE/*.BIN, ESTABLIS.ARC, ...)
TBD = u32 count, count x 16-byte records (u32 flags/pixfmt/datatype, u16 w, u16 h, u32 offset, u32 stamp), data.

API
  list_textures(data)                          -> [TexInfo]
  extract_pvr(source, texture_id)              -> PVR file bytes (synthesised GBIX+PVRT for TBD records)
  replace_texture(source, texture_id, pvr, policy='exact', keep_gbix=True, force=False) -> patched bytes
  inject(...)                                  same, returns Result(data, info) with a fit report
  replace_textures(source, {id: pvr})          several textures of one file
  encode(plain, method, limit)                 bz/bzw compression that tries hard to fit a size limit
  compress_bz_opt / compress_bzw_opt           optimal-parse encoders for the game's two LZ formats

policy 'exact': the output has exactly the input's length and only the texture's own bytes (plus the CRC fields of the
ZSARC member header) change; raises FitError when the repainted data does not fit its original slot.
policy 'grow' : a larger slot is allowed where the container can be re-laid-out (see docs); the file grows.

Pure python 3 stdlib.  Run with  python -I -X utf8 tools/texinject.py --help
"""
import os
import re
import sys
import struct
import hashlib
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
EXTRACTED = os.path.join(ROOT, 'extracted')
sys.path.insert(0, HERE)
import bzlib  # noqa: E402


class TexInjectError(Exception):
    pass


class FitError(TexInjectError):
    """The repainted texture does not fit where the original lived and policy='exact'."""

    def __init__(self, msg, need=None, have=None):
        TexInjectError.__init__(self, msg)
        self.need, self.have = need, have


class FormatMismatch(TexInjectError):
    """Replacement PVR differs from the original in pixel format, data type, width, height or payload size."""


# =============================================================== PVR files
def payload_size(fmt, dt, w, h):
    """(bytes, exact) of the pixel payload implied by the PVR data type; (None, False) for types not understood.
    exact=False: mipmapped types, the payload is at least this long.  PROVEN for all but 4 palette textures of the disc."""
    if dt in (1, 9, 0xD):
        return w * h * 2, True
    if dt == 3:
        return 2048 + w * h // 4, True
    if dt == 0x10:
        nc = 16 if w <= 16 else 32 if w <= 32 else 128 if w <= 64 else 256
        return nc * 8 + w * h // 4, True
    if dt == 2:
        return w * h * 2, False
    if dt == 4:
        return 2048 + w * h // 4, False
    if dt == 0x11:
        nc = 16 if w <= 16 else 64 if w <= 32 else 256
        return nc * 8 + w * h // 4, False
    return None, False


class Pvr:
    """Parsed GBIX/PVRT file.  gbix_chunk is the full GBIX chunk (header included) or b''."""

    def __init__(self, gbix_chunk, index, fmt, dt, w, h, reserved, payload, trailer):
        self.gbix_chunk, self.index = gbix_chunk, index
        self.fmt, self.dt, self.w, self.h = fmt, dt, w, h
        self.reserved, self.payload, self.trailer = reserved, payload, trailer

    @property
    def header(self):
        return (self.fmt, self.dt, self.w, self.h)

    def tobytes(self):
        return (self.gbix_chunk + b'PVRT' + struct.pack('<I', len(self.payload) + 8) +
                struct.pack('<BB2sHH', self.fmt, self.dt, self.reserved, self.w, self.h) + self.payload + self.trailer)


def parse_pvr(b):
    """Parse a PVR file; raises TexInjectError when it is not one."""
    b = bytes(b)
    o = 0
    gb = b''
    idx = None
    if b[:4] == b'GBIX':
        ln = struct.unpack_from('<I', b, 4)[0]
        gb = b[:8 + ln]
        if ln >= 4:
            idx = struct.unpack_from('<I', b, 8)[0]
        o = 8 + ln
    if b[o:o + 4] != b'PVRT' or len(b) < o + 16:
        raise TexInjectError('not a PVR file (no PVRT chunk)')
    ln = struct.unpack_from('<I', b, o + 4)[0]
    fmt, dt, res, w, h = struct.unpack_from('<BB2sHH', b, o + 8)
    pl_end = o + 8 + ln
    if pl_end > len(b) or ln < 8:
        raise TexInjectError('PVRT chunk length %d exceeds the file (%d bytes)' % (ln, len(b)))
    return Pvr(gb, idx, fmt, dt, w, h, res, b[o + 16:pl_end], b[pl_end:])


def build_pvr(fmt, dt, w, h, payload, gbix_index=None):
    """Make a PVR file: [GBIX u32 8, index, 0] + PVRT (len = payload + 8)."""
    gb = b'GBIX' + struct.pack('<III', 8, gbix_index & 0xffffffff, 0) if gbix_index is not None else b''
    return Pvr(gb, gbix_index, fmt, dt, w, h, b'\0\0', bytes(payload), b'').tobytes()


# =============================================================== optimal LZ encoders
def _bz_lengths(plain):
    """For each position: longest match for a 2-byte token (distance <= 16, length <= 9) and for a 3-byte token
    (distance <= 128, length <= 256).  Candidates are enumerated nearest first with str.rfind (C speed)."""
    n = len(plain)
    ls = [0] * n
    ll = [0] * n
    rfind = plain.rfind
    fb = int.from_bytes
    for i in range(n - 1):
        m = n - i
        if m > 256:
            m = 256
        key = plain[i:i + 2]
        lo = i - 128 if i > 128 else 0
        p = rfind(key, lo, i + 1)
        if p < 0:
            continue
        cur = fb(plain[i:i + m], 'big')
        bl = bs = 0
        mm8 = m * 8
        smax = 9 if m > 9 else m
        while p >= 0:
            d = i - p
            x = fb(plain[p:p + m], 'big') ^ cur
            L = m if x == 0 else (mm8 - x.bit_length()) >> 3
            if L > bl:
                bl = L
            if d <= 16 and L > bs:
                bs = L if L < 9 else 9
            if bl >= m and (bs >= smax or d >= 16):
                break
            p = rfind(key, lo, p + 1)
        ll[i] = bl
        ls[i] = bs
    return ls, ll


def _dist_of(plain, i, ln, maxd):
    """smallest distance <= maxd at which plain[i:i+ln] repeats (it exists by construction)."""
    seg = plain[i:i + ln]
    for d in range(1, maxd + 1):
        if d > i:
            break
        # overlap-safe comparison
        if plain[i - d:i - d + ln] == seg:
            return d
    raise AssertionError('no distance for match at %d len %d' % (i, ln))


def compress_bz_opt(plain):
    """Optimal-parse encoder for -bz-- (minimum packed size over the game's token set; ties arbitrary).
    Token costs in bits: literal 9, 2-byte token (len 2..9, dist 1..16) 9, 3-byte token (len 2..256, dist 1..128) 17."""
    plain = bytes(plain)
    n = len(plain)
    ls, ll = _bz_lengths(plain)
    best = [0] * (n + 2)
    kind = bytearray(n)
    clen = [1] * n
    for i in range(n - 1, -1, -1):
        c = 9 + best[i + 1]
        k = 0
        ln = 1
        a = ls[i]
        if a >= 2:
            seg = best[i + 2:i + a + 1]
            mn = min(seg)
            if mn + 9 < c:
                c = mn + 9
                k = 1
                ln = 2 + seg.index(mn)
        b = ll[i]
        if b >= 2:
            seg = best[i + 2:i + b + 1]
            mn = min(seg)
            if mn + 17 < c:
                c = mn + 17
                k = 2
                ln = 2 + seg.index(mn)
        best[i] = c
        kind[i] = k
        clen[i] = ln
    w = bzlib._FlagWriter(8, False)
    i = 0
    while i < n:
        k, ln = kind[i], clen[i]
        if k == 0:
            w.put(True, plain[i:i + 1])
        elif k == 1:
            d = _dist_of(plain, i, ln, 16)
            w.put(False, bytes([0x80 | ((16 - d) << 3) | (ln - 2)]))
        else:
            d = _dist_of(plain, i, ln, 128)
            w.put(False, bytes([128 - d, ln - 1]))
        i += ln
    w.put(False, b'\x00\x00')
    w.flush()
    out = bytes(w.out)
    if bzlib.decompress_bz(out, n) != plain:
        raise TexInjectError('internal error: bz optimal encoder does not round-trip')
    return out


def compress_bzw_opt(plain):
    """Optimal-parse encoder for -bzw-: every item (literal word or match of 2..256 words at distance 1..256 words)
    costs one flag bit + 16 bits, so the parse minimises the number of items."""
    plain = bytes(plain)
    if len(plain) % 2:
        raise ValueError('-bzw- data must have an even length (got %d)' % len(plain))
    n = len(plain) // 2
    ll = [0] * n
    rfind = plain.rfind
    fb = int.from_bytes
    for i in range(n - 1):
        m = n - i
        if m > 256:
            m = 256
        m2 = m * 2
        key = plain[2 * i:2 * i + 4]
        lo = 2 * (i - 256) if i > 256 else 0
        p = rfind(key, lo, 2 * i + 3)
        cur = fb(plain[2 * i:2 * i + m2], 'big')
        bl = 0
        while p >= 0:
            if p % 2 == 0:
                x = fb(plain[p:p + m2], 'big') ^ cur
                L = m if x == 0 else ((m2 * 8 - x.bit_length()) >> 3) // 2
                if L > bl:
                    bl = L
                    if bl >= m:
                        break
            p = rfind(key, lo, p + 3)
        ll[i] = bl
    best = [0] * (n + 2)
    clen = [1] * n
    for i in range(n - 1, -1, -1):
        c = 1 + best[i + 1]
        ln = 1
        b = ll[i]
        if b >= 2:
            seg = best[i + 2:i + b + 1]
            mn = min(seg)
            if mn + 1 < c:
                c = mn + 1
                ln = 2 + seg.index(mn)
        best[i] = c
        clen[i] = ln
    w = bzlib._FlagWriter(16, True)
    i = 0
    while i < n:
        ln = clen[i]
        if ln == 1:
            w.put(True, plain[2 * i:2 * i + 2])
        else:
            seg = plain[2 * i:2 * i + 2 * ln]
            d = None
            for dd in range(1, min(256, i) + 1):
                if plain[2 * (i - dd):2 * (i - dd) + 2 * ln] == seg:
                    d = dd
                    break
            if d is None:
                raise AssertionError('bzw match without source')
            w.put(False, bytes([256 - d, ln - 1]))
        i += ln
    w.put(False, b'\x00\x00')
    w.flush()
    out = bytes(w.out)
    if bzlib.decompress_bzw(out, len(plain)) != plain:
        raise TexInjectError('internal error: bzw optimal encoder does not round-trip')
    return out


def encode(plain, method, limit=None):
    """Packed bytes for `plain` in `method`.  Fast greedy encoder first; if a size `limit` is given and the result is
    larger, the optimal-parse encoder is tried (never larger than greedy).  The caller checks len() against the limit."""
    if method == '-nc--':
        return bytes(plain)
    g = bzlib.compress(plain, method)
    if limit is not None and len(g) <= limit:
        return g
    o = compress_bz_opt(plain) if method == '-bz--' else compress_bzw_opt(plain)
    return o if len(o) < len(g) else g


# =============================================================== TBD tables
def _align4(x):
    return (x + 3) & ~3


def consumed(blk, comp):
    """Bytes of `blk` the game's decoder reads for a stream of kind comp (1 = bzw, 2 = bz), through the end token."""
    i = 0
    try:
        if comp == 2:
            while True:
                fl = blk[i]
                i += 1
                for _ in range(8):
                    if fl & 1:
                        i += 1
                    else:
                        b = blk[i]
                        i += 1
                        if not b & 0x80:
                            b2 = blk[i]
                            i += 1
                            if b2 == 0:
                                return i
                    fl >>= 1
        else:
            while True:
                fl = (blk[i] << 8) | blk[i + 1]
                i += 2
                for _ in range(16):
                    if fl & 1:
                        i += 2
                    else:
                        hi = blk[i + 1]
                        i += 2
                        if hi == 0:
                            return i
                    fl >>= 1
    except IndexError:
        return None


class Table:
    """A TBD table at `base` inside a buffer.  recs[i] = dict(i, fmt, dt, comp, w, h, off, stamp, flags)."""

    def __init__(self, base, recs, kind):
        self.base, self.recs, self.kind = base, recs, kind
        self.n = len(recs)


def read_table(d, base=0, kind='file', strict=True):
    """Parse the TBD table at d[base:] (returns None if it is not one).  strict adds the plausibility rules
    used to find tables inside blobs (pixel format <= 6, known data types, sane sizes)."""
    if base < 0 or base + 20 > len(d):
        return None
    n = struct.unpack_from('<I', d, base)[0]
    if not 0 < n < 4096 or base + 4 + 16 * n > len(d):
        return None
    recs = []
    prev = 4 + 16 * n
    for i in range(n):
        f, wh, off, st = struct.unpack_from('<IIII', d, base + 4 + 16 * i)
        w, h = wh & 0xffff, wh >> 16
        if w == 0 or h == 0 or w > 2048 or h > 2048:
            return None
        if strict and ((f & 0xff) > 6 or ((f >> 8) & 0xff) not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 0xD, 0x10, 0x11)):
            return None
        if (i == 0 and off != prev) or off < prev or base + off > len(d):
            return None
        prev = off
        recs.append(dict(i=i, flags=f, fmt=f & 0xff, dt=(f >> 8) & 0xff, comp=f >> 30, w=w, h=h, off=off, stamp=st))
    return Table(base, recs, kind)


def scan_tables(d, start=4, kind='embedded'):
    """All strict TBD tables whose base is a multiple of 4 and >= start.  Pre-filter: first record offset == 4 + 16 n."""
    import array
    n4 = (len(d) - start) // 4
    if n4 < 6:
        return []
    a = array.array('I')
    a.frombytes(bytes(d[start:start + n4 * 4]))
    if sys.byteorder != 'little':
        a.byteswap()
    out = []
    for i in range(n4 - 4):
        c = a[i]
        if 0 < c < 4096 and a[i + 3] == 4 + 16 * c:
            t = read_table(d, start + i * 4, kind, True)
            if t is not None:
                out.append(t)
    return out


def _rec_slot(d, tab, i):
    """(start, end, plain_len_hint) of record i's stored bytes (absolute offsets).  `end` is the first byte that is not
    available to this record: the next record's start, or for the last record the end of its stream rounded up to 4."""
    r = tab.recs[i]
    start = tab.base + r['off']
    if i + 1 < tab.n:
        end = tab.base + tab.recs[i + 1]['off']
        if end <= start:
            raise TexInjectError('record %d shares its data with record %d (not supported)' % (i, i + 1))
        return start, end
    if r['comp'] in (1, 2):
        c = consumed(d[start:], r['comp'])
        if c is None:
            raise TexInjectError('record %d: unterminated stream' % i)
        return start, min(len(d), start + _align4(c))
    ps = payload_size(r['fmt'], r['dt'], r['w'], r['h'])[0]
    if ps is None:
        return start, len(d)
    return start, min(len(d), start + _align4(ps))


def tbd_plain(d, tab, i):
    """Decoded payload of record i (exactly what the game's FUN_8c15a776 hands to the texture creator)."""
    r = tab.recs[i]
    start, end = _rec_slot(d, tab, i)
    blk = bytes(d[start:end])
    if r['comp'] == 0:
        ps, exact = payload_size(r['fmt'], r['dt'], r['w'], r['h'])
        if ps is None or not exact:
            return blk
        return blk[:ps]
    if r['comp'] == 3:
        raise TexInjectError('record %d has both compression flags set (loader uses the data in place, untested)' % i)
    return bzlib.decompress(blk, None, '-bzw-' if r['comp'] == 1 else '-bz--')


def tbd_growable(d, tab):
    """(ok, reason) whether records of this table may change length (layout growth)."""
    if tab.kind == 'embedded':
        return False, 'table embedded in a blob (absolute pointers / index tables outside the table)'
    last = tab.n - 1
    start, end = _rec_slot(d, tab, last)
    if len(d) - end > 0 and any(d[end:end + 64]):
        return False, 'non-zero data follows the last record (%d bytes)' % (len(d) - end)
    return True, ''


class Result:
    """Outcome of an injection: data (patched file bytes) and info (fit report)."""

    def __init__(self, data, info):
        self.data, self.info = data, info


def tbd_replace(d, tab, i, new_plain, policy='exact', force=False):
    """-> (new buffer, info).  Replace record i's decoded payload."""
    r = tab.recs[i]
    old_plain = tbd_plain(d, tab, i)
    start, end = _rec_slot(d, tab, i)
    R = end - start
    info = dict(kind='tbd-' + tab.kind, slot=R, old_plain=len(old_plain), changed=True)
    if bytes(new_plain) == old_plain:
        info['changed'] = False
        return bytes(d), info
    if len(new_plain) != len(old_plain):
        raise FormatMismatch('payload is %d bytes, the record needs %d' % (len(new_plain), len(old_plain)))
    comp = r['comp']
    if comp == 0:
        block = bytes(new_plain)
        info['method'] = 'raw'
        info['packed'] = len(block)
        out = bytes(d[:start]) + block + bytes(d[start + len(block):])
        return out, info
    method = '-bzw-' if comp == 1 else '-bz--'
    packed = encode(new_plain, method, limit=R)
    info['method'] = method
    info['packed'] = len(packed)
    if len(packed) <= R:
        info['pad'] = R - len(packed)
        return bytes(d[:start]) + packed + bytes(R - len(packed)) + bytes(d[end:]), info
    need = _align4(len(packed))
    info['need'] = need
    if policy != 'grow':
        raise FitError('record #%d: repainted data packs to %d bytes (aligned %d), slot is %d (%d over); '
                       'simplify the art (fewer colours / flatter areas) or use policy="grow"' % (i, len(packed), need, R, need - R),
                       need, R)
    ok, why = tbd_growable(d, tab)
    if not ok and not force:
        raise FitError('record #%d cannot grow: %s' % (i, why), need, R)
    delta = need - R
    out = bytearray(d[:start])
    out += packed + bytes(need - len(packed))
    out += d[end:]
    for j in range(i + 1, tab.n):
        po = tab.base + 4 + 16 * j + 8
        struct.pack_into('<I', out, po, tab.recs[j]['off'] + delta)
    info['grown_by'] = delta
    return bytes(out), info


# =============================================================== ZSARC
def zs_members(d):
    """Light member list (no packed data copied) and the offset where the member walk stopped."""
    ms = []
    o = 0
    n = len(d)
    while True:
        while o < n and d[o] == 0:
            o += 1
        if o >= n:
            return ms, n
        m = bzlib.parse_member(d, o, with_data=False)
        if m is None:
            return ms, o
        ms.append(m)
        o = m.end_offset


def zs_plain(d, m):
    return bzlib.decompress(bytes(d[m.data_offset:m.end_offset]), m.orig_size, m.method)


def zs_growable(d, ms, tail):
    """(ok, reason): may a member change size?  Only small, tightly packed, bare containers: the game walks a ZSARC
    sequentially by header, but bind-style containers (many members, sector padded archives) are probably indexed by
    offset from outside (INFERRED, see docs), so they never grow unless forced."""
    if tail != len(d):
        return False, 'archive is followed by a texture table / other data (tail at %#x)' % tail
    if len(ms) > 128:
        return False, '%d members: probably addressed by offset from outside' % len(ms)
    for a, b in zip(ms, ms[1:]):
        if b.offset - a.end_offset > 3:
            return False, 'members are padded apart (%d zero bytes after %r)' % (b.offset - a.end_offset, a.name)
    return True, ''


def zs_replace_member(d, ms, tail, mi, new_plain, policy='exact', force=False):
    """-> (new buffer, info).  Re-encode member mi with its own method and header layout.

    The loader advances from one member to the next by hdrlen + align4(packed_size) (FUN_8c15a45a), so a member may use
    the 0..3 alignment bytes behind its stream without moving the next member: room = align4(end) - data_offset, bounded
    by the next member / end of file."""
    m = ms[mi]
    old_plain = zs_plain(d, m)
    info = dict(kind='zsarc-member', member=m.name, method=m.method, slot=m.packed_size, old_plain=len(old_plain), changed=True)
    if bytes(new_plain) == old_plain:
        info['changed'] = False
        return bytes(d), info
    new_plain = bytes(new_plain)
    same_len = len(new_plain) == len(old_plain)
    nxt = ms[mi + 1].offset if mi + 1 < len(ms) else len(d)
    room = min(nxt, _align4(m.end_offset)) - m.data_offset         # R .. R+3
    info['slot'] = room
    if m.method == '-nc--':
        packed = new_plain
        fits = same_len                                             # the loader insists on packed == orig for stored members
    else:
        packed = encode(new_plain, m.method, limit=room if same_len else None)
        fits = len(packed) <= room
    info['packed'] = len(packed)
    if fits:
        size = max(len(packed), m.packed_size) if m.method != '-nc--' else len(packed)
        body = packed + bytes(size - len(packed))
        info['pad'] = size - len(packed)
        grown = False
    else:
        if policy != 'grow':
            raise FitError('member %r: new data needs %d packed bytes, slot is %d (%d over)%s' % (
                m.name, len(packed), room, len(packed) - room,
                '' if m.method != '-nc--' else ' (stored member: payload length differs)'), len(packed), room)
        ok, why = zs_growable(d, ms, tail)
        if not ok and not force:
            raise FitError('member %r cannot grow: %s' % (m.name, why), len(packed), room)
        body = packed
        grown = True
    hdr = bzlib.build_header(m.name_raw, m.method, len(body), len(new_plain), m.mtime, bzlib.crc16(new_plain),
                             hdrlen=m.hdrlen, ext=m.ext, reserved=m.reserved)
    if len(hdr) != m.hdrlen:
        raise TexInjectError('header length changed (%d -> %d)' % (m.hdrlen, len(hdr)))
    rec = hdr + body
    if not grown:
        assert m.offset + len(rec) <= min(nxt, _align4(m.end_offset))
        out = bytes(d[:m.offset]) + rec + bytes(d[m.offset + len(rec):])
        assert len(out) == len(d)
        return out, info
    new_end = m.offset + len(rec)
    out = bytes(d[:m.offset]) + rec + bytes((-new_end) % 4) + bytes(d[nxt:])
    info['grown_by'] = len(out) - len(d)
    return out, info



# ---------------------------------------------------------------- stored ZSARC members around an overlay-embedded table
# Several overlays keep their TBD tables inside STORED ('-nc--') ZSARC members of the overlay image (FLOW_PRG/SCDRF.BIN
# 'scda.tbd' @0x2ff38, SEARCH.BIN 'schme1.tbd' @0x2c55c and 'scda.tbd' @0x2fcc4, NEWCON.BIN, RECON.BIN).  The game walks such a
# member with FUN_8c15a45a, which checks the CRC16 of the member data against the header (and the header CRC): a table edited
# in place without refreshing both makes the walk fail ("exFileCRC mismatch", the walker returns NULL).  docs/scdrf-texture-hang.md.
def enclosing_stored_member(d, pos):
    """The stored ZSARC member of `d` (a Member with valid header CRC, packed == orig, data CRC16 matching) whose data
    contains offset `pos`, or None."""
    meth = b'-nc--'
    o = d.rfind(meth, 0, pos)
    lowest = max(2, pos - 0x100000)
    while o >= lowest:
        m = bzlib.parse_member(d, o - 2, with_data=False)
        if (m is not None and m.method == '-nc--' and m.hdr_crc_ok and m.packed_size == m.orig_size
                and m.data_offset <= pos < m.end_offset and bzlib.crc16(bytes(d[m.data_offset:m.end_offset])) == m.crc16):
            return m
        o = d.rfind(meth, 0, o)
    return None


def refresh_stored_member(old, new, pos):
    """`new` is `old` with a record edited in place at `pos`.  If `pos` lies in a stored ZSARC member, rewrite that member's
    data CRC16 and header CRC for the new contents.  -> (buffer, member name or None)."""
    m = enclosing_stored_member(old, pos)
    if m is None:
        return new, None
    body = bytes(new[m.data_offset:m.end_offset])
    if body == bytes(old[m.data_offset:m.end_offset]):
        return new, m.name
    same = bzlib.build_header(m.name_raw, m.method, m.packed_size, m.orig_size, m.mtime, m.crc16,
                              hdrlen=m.hdrlen, ext=m.ext, reserved=m.reserved)
    if bytes(same) != bytes(old[m.offset:m.data_offset]):
        raise TexInjectError('member %r at %#x: header does not round-trip, not touching it' % (m.name, m.offset))
    hdr = bzlib.build_header(m.name_raw, m.method, m.packed_size, m.orig_size, m.mtime, bzlib.crc16(body),
                             hdrlen=m.hdrlen, ext=m.ext, reserved=m.reserved)
    out = bytearray(new)
    out[m.offset:m.data_offset] = hdr
    return bytes(out), m.name


def stale_stored_members(old, new):
    """Offsets of stored ZSARC members that are valid in `old` (header CRC, data CRC16) but not in `new` (build-time guard)."""
    bad = []
    meth = b'-nc--'
    o = old.find(meth, 2)
    while o >= 0:
        m = bzlib.parse_member(old, o - 2, with_data=False)
        if (m is not None and m.method == '-nc--' and m.hdr_crc_ok and m.packed_size == m.orig_size
                and bzlib.crc16(bytes(old[m.data_offset:m.end_offset])) == m.crc16):
            n = bzlib.parse_member(new, m.offset, with_data=False)
            if n is None or not n.hdr_crc_ok or bzlib.crc16(bytes(new[n.data_offset:n.end_offset])) != n.crc16:
                bad.append((m.offset, m.name))
        o = old.find(meth, o + 1)
    return bad


# =============================================================== ZSARC runs embedded in a blob
# A blob that is not itself a ZSARC (GAME/GAMEETC.ZAR: a (size, offset) table, then runs; ATFIRST/FACEMDUL.DAT) can hold RUNS
# of back-to-back ZSARC members at 4-aligned offsets (the game walks a run with FUN_8c15a45a, member by member).  Their PVR
# members get the id '@<hexoffset of the run>/<member name>' ('[k]' = member index inside the run when a name repeats).
# Only in-place, same-length edits are supported (the run is addressed by offset from the blob's own table): the member header
# is rebuilt with the new CRC16, nothing moves.  Rule identical to tools/unpack_all.embedded_runs, so the ids agree with
# build/tex/index.tsv.
def scan_run_starts(d, start=0):
    """Offsets >= start of CRC-valid member headers (the same rule as tools/unpack_all.scan_embedded)."""
    hits = []
    for pat in (b'-nc--', b'-bz--', b'-bzw-'):
        k = d.find(pat, start + 2)
        while k != -1:
            m = bzlib.parse_member(d, k - 2, with_data=False)
            if m is not None and m.hdr_crc_ok:
                hits.append(k - 2)
            k = d.find(pat, k + 1)
    return sorted(hits)


def walk_run(d, o):
    """Members of the run that starts at offset o (list of Member, header-CRC checked, 4-aligned chain)."""
    ms = []
    p = o
    while True:
        m = bzlib.parse_member(d, p, with_data=False)
        if m is None or not m.hdr_crc_ok:
            return ms
        ms.append(m)
        p = _align4(m.end_offset)


def find_runs(d, start=0):
    """[(offset, [Member])]: every run of embedded ZSARC members (tools/unpack_all.embedded_runs)."""
    runs = []
    covered = start
    for o in scan_run_starts(d, start):
        if o < covered:
            continue
        ms = walk_run(d, o)
        if ms:
            runs.append((o, ms))
            covered = _align4(ms[-1].end_offset)
    return runs


def run_member_tid(base, ms, k):
    nm = ms[k].name
    if not nm or sum(1 for x in ms if x.name == nm) != 1 or nm.startswith('[') or '#' in nm or '/' in nm:
        nm = '[%d]' % k
    return '@%x/%s' % (base, nm)


def _run_resolve(d, tid):
    j = tid.find('/')
    base = int(tid[1:j], 16)
    key = tid[j + 1:]
    ms = walk_run(d, base)
    if not ms:
        raise TexInjectError('no ZSARC run (valid member header) at offset %#x' % base)
    mi = _member_key(ms, key)
    plain = zs_plain(d, ms[mi])
    if not _is_pvr(plain):
        raise TexInjectError('run member %r at %#x is not a PVR file' % (ms[mi].name, base))
    return dict(type='run-pvr', ms=ms, tail=len(d) + 1, mi=mi, plain=plain, run=base)


# =============================================================== texture ids and listing
class TexInfo:
    """One texture.  Attributes: tid, kind, fmt, dt, w, h, method, plain_len, slot (bytes available in place),
    growable, gbix (index/stamp or None), sha1 (of the payload)."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __repr__(self):
        return '<TexInfo %r %s fmt=%d dt=%#x %dx%d %s slot=%s>' % (self.tid, self.kind, self.fmt, self.dt, self.w, self.h,
                                                                  self.method, self.slot)


_RE_TBD = re.compile(r'^(.*)#(\d+)$')
RE_RUN_ID = re.compile(r'^@[0-9a-fA-F]+/[^#]+$')


def _as_bytes(source):
    if isinstance(source, (bytes, bytearray, memoryview)):
        return bytes(source)
    p = str(source)
    if os.path.isfile(p):
        with open(p, 'rb') as f:
            return f.read()
    q = os.path.join(EXTRACTED, *p.replace('\\', '/').strip('/').split('/'))
    if os.path.isfile(q):
        with open(q, 'rb') as f:
            return f.read()
    raise TexInjectError('no such file: %s (also tried extracted/)' % p)


def _is_pvr(b):
    return b[:4] in (b'GBIX', b'PVRT')


def _member_key(ms, key):
    if key.startswith('[') and key.endswith(']') and key[1:-1].isdigit():
        k = int(key[1:-1])
        if not 0 <= k < len(ms):
            raise TexInjectError('member index %d out of range (0..%d)' % (k, len(ms) - 1))
        return k
    hits = [k for k, m in enumerate(ms) if m.name == key]
    if not hits:
        hits = [k for k, m in enumerate(ms) if (m.name or '').lower() == key.lower()]
    if not hits:
        # a Windows file name cannot hold the backslashes of a member such as '.\TMP\name050.tbd': also match with the
        # separators turned into '/' and a leading './' dropped (file translation/textures/EVENT/E050.DAT/TMP/name050.tbd#0.pvr)
        def norm(x):
            x = (x or '').replace('\\', '/').lower()
            return x[2:] if x.startswith('./') else x
        hits = [k for k, m in enumerate(ms) if norm(m.name) == norm(key)]
    if not hits:
        raise TexInjectError('no member named %r' % key)
    if len(hits) > 1:
        raise TexInjectError('member name %r is ambiguous (members %s): use [k]' % (key, hits))
    return hits[0]


def _find_table(d, base_s, tail_off):
    if base_s == 'tail':
        if tail_off is None:
            raise TexInjectError("'@tail' needs a ZSARC container with a table after the archive")
        base = tail_off
        # tail may be preceded by zero padding the walk did not skip: first valid table at or after it
        for b in range(tail_off, min(len(d) - 20, tail_off + 64), 4):
            t = read_table(d, b, 'tail', True)
            if t:
                return t
        raise TexInjectError('no TBD table found after the archive at %#x' % tail_off)
    base = int(base_s, 16)
    kind = 'file' if base == 0 else ('tail' if tail_off is not None and base >= tail_off else 'embedded')
    t = read_table(d, base, kind, False)
    if t is None:
        raise TexInjectError('no TBD table at offset %#x' % base)
    return t


def resolve(d, tid):
    """-> dict describing the target: type in ('pvr-file','zs-pvr','zs-tbd','tbd')."""
    tid = '' if tid is None else str(tid)
    if tid in ('', '@file'):
        if not _is_pvr(d):
            raise TexInjectError('file is not a PVR file; give a texture id (see list_textures)')
        return dict(type='pvr-file')
    if tid.startswith('@') and RE_RUN_ID.match(tid):
        return _run_resolve(d, tid)
    if tid.startswith('@'):
        j = tid.find('#')
        if j < 0:
            raise TexInjectError('table ids look like @<hexoffset>#<index>')
        ms, tail = zs_members(d) if bzlib.parse_member(d, 0, with_data=False) is not None else ([], None)
        tail_off = tail if ms and tail != len(d) else None
        tab = _find_table(d, tid[1:j], tail_off)
        i = int(tid[j + 1:])
        if not 0 <= i < tab.n:
            raise TexInjectError('record %d out of range (table has %d)' % (i, tab.n))
        return dict(type='tbd', table=tab, index=i)
    m = _RE_TBD.match(tid)
    first = bzlib.parse_member(d, 0, with_data=False)
    if m is not None and m.group(1) == '' and first is None:
        tab = read_table(d, 0, 'file', False)
        if tab is None:
            raise TexInjectError('file is not a TBD bundle')
        i = int(m.group(2))
        if not 0 <= i < tab.n:
            raise TexInjectError('record %d out of range (table has %d)' % (i, tab.n))
        return dict(type='tbd', table=tab, index=i)
    if first is None:
        raise TexInjectError('file is neither a ZSARC container, a TBD bundle nor a PVR file: use an @<hexoffset>#<i> id')
    ms, tail = zs_members(d)
    try:
        mi = _member_key(ms, tid)
        sub = None
    except TexInjectError:
        if m is None:
            raise
        mi = _member_key(ms, m.group(1))
        sub = int(m.group(2))
    plain = zs_plain(d, ms[mi])
    if sub is None:
        if not _is_pvr(plain):
            raise TexInjectError('member %r is not a PVR file (use name#i for a TBD member)' % ms[mi].name)
        return dict(type='zs-pvr', ms=ms, tail=tail, mi=mi, plain=plain)
    tab = read_table(plain, 0, 'file', False)
    if tab is None:
        raise TexInjectError('member %r is not a TBD bundle' % ms[mi].name)
    if not 0 <= sub < tab.n:
        raise TexInjectError('record %d out of range (table has %d)' % (sub, tab.n))
    return dict(type='zs-tbd', ms=ms, tail=tail, mi=mi, plain=plain, table=tab, index=sub)


def _tbd_info(tid_prefix, d, tab, i, base_kind):
    r = tab.recs[i]
    plain = tbd_plain(d, tab, i)
    start, end = _rec_slot(d, tab, i)
    ok, why = tbd_growable(d, tab)
    return TexInfo(tid='%s#%d' % (tid_prefix, i), kind='tbd-' + base_kind, fmt=r['fmt'], dt=r['dt'], w=r['w'], h=r['h'],
                   method={0: 'raw', 1: '-bzw-', 2: '-bz--', 3: 'raw?'}[r['comp']], plain_len=len(plain), slot=end - start,
                   growable=ok, gbix=None if r['stamp'] == 0xffffffff else r['stamp'], sha1=hashlib.sha1(plain).hexdigest())


def list_textures(d, scan=True):
    """Every texture in the buffer (see the module docstring for the kinds)."""
    d = _as_bytes(d)
    out = []
    if _is_pvr(d):
        p = parse_pvr(d)
        out.append(TexInfo(tid='', kind='pvr-file', fmt=p.fmt, dt=p.dt, w=p.w, h=p.h, method='raw', plain_len=len(p.payload),
                           slot=len(d), growable=True, gbix=p.index, sha1=hashlib.sha1(p.payload).hexdigest()))
        return out
    if bzlib.parse_member(d, 0, with_data=False) is not None:
        ms, tail = zs_members(d)
        gok, _ = zs_growable(d, ms, tail)
        for k, m in enumerate(ms):
            if m.method == '-nc--':
                head = bytes(d[m.data_offset:m.data_offset + 64])
            else:
                if m.orig_size < 16:
                    continue
                head = None
            if head is not None and not (_is_pvr(head) or struct.unpack_from('<I', head + bytes(4), 0)[0] < 4096):
                continue
            plain = zs_plain(d, m)
            nm = m.name if sum(1 for x in ms if x.name == m.name) == 1 else '[%d]' % k
            if _is_pvr(plain):
                try:
                    p = parse_pvr(plain)
                except TexInjectError:
                    continue
                out.append(TexInfo(tid=nm, kind='zs-pvr', fmt=p.fmt, dt=p.dt, w=p.w, h=p.h, method=m.method,
                                   plain_len=len(p.payload), slot=m.packed_size, growable=gok, gbix=p.index,
                                   sha1=hashlib.sha1(p.payload).hexdigest()))
            else:
                tab = read_table(plain, 0, 'file', True)
                if tab is not None and tab.n:
                    for i in range(tab.n):
                        t = _tbd_info(nm, plain, tab, i, 'file')
                        t.kind = 'zs-tbd'
                        t.growable = gok and t.growable and m.method == '-nc--'
                        out.append(t)
        if tail != len(d) and scan:
            for tab in scan_tables(d, tail, 'tail')[:1]:
                for i in range(tab.n):
                    out.append(_tbd_info('@%x' % tab.base, d, tab, i, 'tail'))
        return out
    tab = read_table(d, 0, 'file', True)
    if tab is not None:
        for i in range(tab.n):
            out.append(_tbd_info('', d, tab, i, 'file'))
        return out
    if scan:
        for tab in scan_tables(d, 4, 'embedded'):
            for i in range(tab.n):
                out.append(_tbd_info('@%x' % tab.base, d, tab, i, 'embedded'))
        for base, ms in find_runs(d, 0):
            for k, m in enumerate(ms):
                if (m.name or '').lower().endswith(('.tbd', '.bin', '.dat')) or m.orig_size < 16:
                    continue
                try:
                    plain = zs_plain(d, m)
                    if not _is_pvr(plain):
                        continue
                    p = parse_pvr(plain)
                except (TexInjectError, bzlib.DecodeError, struct.error, IndexError, ValueError):
                    continue
                out.append(TexInfo(tid=run_member_tid(base, ms, k), kind='run-pvr', fmt=p.fmt, dt=p.dt, w=p.w, h=p.h,
                                   method=m.method, plain_len=len(p.payload), slot=_align4(m.end_offset) - m.data_offset,
                                   growable=False, gbix=p.index, sha1=hashlib.sha1(p.payload).hexdigest()))
    return out


# =============================================================== extraction / injection
def extract_pvr(source, texture_id=''):
    """PVR file bytes of one texture.  TBD records get a synthesised GBIX (record stamp) + PVRT, so that
    replace_texture(src, id, extract_pvr(src, id)) is a no-op."""
    d = _as_bytes(source)
    t = resolve(d, texture_id)
    if t['type'] == 'pvr-file':
        return d
    if t['type'] in ('zs-pvr', 'run-pvr'):
        return t['plain']
    if t['type'] == 'zs-tbd':
        buf, tab, i = t['plain'], t['table'], t['index']
    else:
        buf, tab, i = d, t['table'], t['index']
    r = tab.recs[i]
    return build_pvr(r['fmt'], r['dt'], r['w'], r['h'], tbd_plain(buf, tab, i), None if r['stamp'] == 0xffffffff else r['stamp'])


def _check_same_format(old_hdr, new, what):
    if old_hdr != new.header:
        raise FormatMismatch('%s: replacement is pixfmt/datatype/w/h = %s but the original is %s '
                             '(the game takes these from the container, a different format changes VRAM use and UV mapping)' % (
                                 what, new.header, old_hdr))


def inject(source, texture_id, new_pvr, policy='exact', keep_gbix=True, force=False):
    """Replace one texture; returns Result(data, info).  new_pvr: PVR file bytes (parse_pvr) of the SAME pixel format,
    data type, size and payload length as the original (a bare payload of the right length is accepted for TBD records)."""
    if policy not in ('exact', 'grow'):
        raise ValueError("policy must be 'exact' or 'grow'")
    d = _as_bytes(source)
    new_pvr = bytes(new_pvr)
    t = resolve(d, texture_id)
    ty = t['type']
    if ty in ('pvr-file', 'zs-pvr', 'run-pvr'):
        old = parse_pvr(d if ty == 'pvr-file' else t['plain'])
        new = parse_pvr(new_pvr)
        _check_same_format(old.header, new, 'texture %r' % texture_id)
        if len(new.payload) != len(old.payload):
            raise FormatMismatch('payload is %d bytes, the original has %d' % (len(new.payload), len(old.payload)))
        gb = old.gbix_chunk if (keep_gbix or not new.gbix_chunk) else new.gbix_chunk
        np_ = Pvr(gb, old.index, old.fmt, old.dt, old.w, old.h, old.reserved, new.payload, old.trailer).tobytes()
        if ty == 'pvr-file':
            return Result(d if np_ == d else np_, dict(kind='pvr-file', changed=np_ != d, slot=len(d)))
        if ty == 'run-pvr':
            # a run is addressed by offset from the blob: never grow, only the member's own slot (+ alignment room)
            out, info = zs_replace_member(d, t['ms'], t['tail'], t['mi'], np_, 'exact', False)
            if info.get('changed') and len(out) == len(d):
                out, mname = refresh_stored_member(d, out, t['run'])
                if mname is not None:
                    info['member_crc_refreshed'] = mname
            return Result(out, info)
        out, info = zs_replace_member(d, t['ms'], t['tail'], t['mi'], np_, policy, force)
        return Result(out, info)
    tab, i = t['table'], t['index']
    buf = t['plain'] if ty == 'zs-tbd' else d
    r = tab.recs[i]
    if _is_pvr(new_pvr):
        new = parse_pvr(new_pvr)
        _check_same_format((r['fmt'], r['dt'], r['w'], r['h']), new, 'texture %r' % texture_id)
        payload = new.payload
    else:
        payload = new_pvr
    newbuf, info = tbd_replace(buf, tab, i, payload, policy, force)
    if ty == 'tbd':
        if tab.kind == 'embedded' and info.get('changed') and len(newbuf) == len(d):
            newbuf, mname = refresh_stored_member(d, newbuf, tab.base)
            if mname is not None:
                info['member_crc_refreshed'] = mname
        return Result(newbuf, info)
    if not info['changed']:
        return Result(d, info)
    out, minfo = zs_replace_member(d, t['ms'], t['tail'], t['mi'], newbuf, policy, force)
    minfo['inner'] = info
    return Result(out, minfo)


def fit_check(source, texture_id, new_pvr):
    """Dry run for the art workflow: would this PVR fit the original slot?  Returns dict(fits, packed, slot, over, growable,
    kind, method).  Never raises FitError (other errors, e.g. FormatMismatch, propagate)."""
    d = _as_bytes(source)
    try:
        r = inject(d, texture_id, new_pvr, 'exact')
        i = r.info
        return dict(fits=True, packed=i.get('packed'), slot=i.get('slot'), over=0, kind=i.get('kind'), method=i.get('method'),
                    changed=i.get('changed', True))
    except FitError as e:
        t = [x for x in list_textures(d, scan=True) if x.tid == (texture_id or '')]
        return dict(fits=False, packed=e.need, slot=e.have, over=(e.need or 0) - (e.have or 0),
                    growable=bool(t and t[0].growable), kind=t[0].kind if t else None, method=t[0].method if t else None)


def replace_texture(source_file, texture_id, new_pvr_bytes, policy='exact', keep_gbix=True, force=False):
    """Patched bytes of `source_file` (bytes, a path, or an ISO-style path below extracted/) with one texture replaced."""
    return inject(source_file, texture_id, new_pvr_bytes, policy, keep_gbix, force).data


def replace_textures(source_file, replacements, policy='exact', keep_gbix=True, force=False):
    """Apply {texture_id: pvr_bytes} in turn.  Returns (data, [info...])."""
    d = _as_bytes(source_file)
    infos = []
    for tid in sorted(replacements, key=str):
        r = inject(d, tid, replacements[tid], policy, keep_gbix, force)
        d = r.data
        infos.append(dict(r.info, tid=tid))
    return d, infos


def make_patches(jobs, policy='exact', current=None):
    """{iso path: {texture id: pvr bytes}} -> {'/ISO/PATH': patched bytes} for tools/discbuild.build_disc (or merged into
    build_patch's res.patches).  `current` {'/ISO/PATH': bytes} supplies already-patched file contents to compose on."""
    out = {}
    for iso, repl in jobs.items():
        rel = iso.replace('\\', '/').strip('/')
        key = '/' + rel
        base = (current or {}).get(key)
        if base is None:
            base = _as_bytes(rel)
        new, _ = replace_textures(base, repl, policy)
        out[key] = new
    return out


# =============================================================== disc / RAM budget facts
# Files the boot code loads to a FIXED RAM address (docs/memory-map.md section 1, from RAM dumps: INFERRED).  Growing such a
# file moves nothing on disc but the loader writes the whole file (rounded up to sectors) at that address, so everything
# up to the next fixed region is the only room (the loader's size check is skipped for registered fixed buffers).
FIXED_LOAD = {
    # iso path (upper case): (ram address, bytes available from that address up to the next fixed region)
    '/ATFIRST/SHTEX0.ZAR': (0x8ce02000, 0x8ce2c000 - 0x8ce02000),
    '/ATFIRST/BAR.TBD': (0x8ce2c000, 0x8ce4c000 - 0x8ce2c000),
    '/ATFIRST/SECFTEX0.ZAR': (0x8ce5c000, 0x8ce80000 - 0x8ce5c000),
    '/FONT.BIN': (0x8cd5c000, 0x8ce02000 - 0x8cd5c000),
}


def iso_slack(length):
    """Bytes a file of `length` bytes may still grow without needing another 2048-byte sector (discbuild keeps the extent)."""
    return (-length) % 2048


def info_text(source, iso_path=None):
    d = _as_bytes(source)
    lines = ['size %d bytes = %d sectors, %d bytes of slack in the last sector' % (len(d), (len(d) + 2047) // 2048, iso_slack(len(d)))]
    key = '/' + (iso_path or (source if isinstance(source, str) else '')).replace('\\', '/').strip('/').upper()
    if key in FIXED_LOAD:
        a, room = FIXED_LOAD[key]
        lines.append('boot-loaded at fixed RAM %#x, %d bytes up to the next fixed region (%d spare)' % (a, room, room - len(d)))
    ts = list_textures(d)
    kinds = {}
    for t in ts:
        kinds.setdefault(t.kind, [0, 0])
        kinds[t.kind][0] += 1
        kinds[t.kind][1] += bool(t.growable)
    for k, (n, g) in sorted(kinds.items()):
        lines.append('%-14s %5d textures, %5d may grow' % (k, n, g))
    return '\n'.join(lines)


# =============================================================== translation/textures directory (build_patch stage)
def load_textures_dir(textures_dir, extracted=None):
    """translation/textures/<iso path>/<texture id>.pvr  ->  {iso path (no leading slash): {texture id: pvr bytes}}.
    <iso path> is the longest leading directory chain that names a file below extracted/; the file name minus one
    trailing '.pvr' is the texture id (so the member 's.pvr' is stored as 's.pvr.pvr', a whole-file PVR as '@file.pvr')."""
    extracted = extracted or EXTRACTED
    groups = {}
    if not os.path.isdir(textures_dir):
        return groups
    for dp, _, fns in os.walk(textures_dir):
        for fn in sorted(fns):
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, textures_dir).replace(os.sep, '/').split('/')
            if not fn.lower().endswith('.pvr'):
                raise TexInjectError('%s: texture files must end in .pvr' % full)
            cont = None
            for i in range(len(rel) - 1, 0, -1):
                if os.path.isfile(os.path.join(extracted, *rel[:i])):
                    cont, tid = '/'.join(rel[:i]), '/'.join(rel[i:])
                    break
            if cont is None:
                raise TexInjectError('%s: no container file in extracted/ matches' % full)
            tid = tid[:-4]
            with open(full, 'rb') as f:
                groups.setdefault(cont, {})[tid] = f.read()
    return groups


# =============================================================== whole-disc index
_SKIP_DIRS = {'SSONG', 'SOUND', 'DPSS', 'DPWWW', 'BCAST'}


def build_index(out_path, extracted=None, scan_all=False, progress=None):
    """Write a TSV with one row per texture of the whole disc (iso path, id, kind, fmt, dt, w, h, method, plain_len, slot,
    growable, gbix, sha1 of the payload).  `dups` uses it to find every copy of a texture."""
    extracted = extracted or EXTRACTED
    rows = 0
    with open(out_path, 'w', encoding='utf8', newline='\n') as f:
        f.write('file\tid\tkind\tfmt\tdt\tw\th\tmethod\tplain\tslot\tgrow\tgbix\tsha1\n')
        for root, dirs, files in os.walk(extracted):
            dirs.sort()
            for fn in sorted(files):
                if fn in ('BCAST.BIN', '_filelist.tsv'):
                    continue
                path = os.path.join(root, fn)
                rel = os.path.relpath(path, extracted).replace('\\', '/')
                if not scan_all and rel.split('/')[0] in _SKIP_DIRS:
                    continue
                with open(path, 'rb') as fh:
                    d = fh.read()
                try:
                    texs = list_textures(d, scan=True)
                except (TexInjectError, bzlib.DecodeError, struct.error, IndexError, ValueError) as e:
                    f.write('%s\t!\terror: %s\t\t\t\t\t\t\t\t\t\t\n' % (rel, e))
                    continue
                for t in texs:
                    f.write('%s\t%s\t%s\t%d\t%d\t%d\t%d\t%s\t%d\t%d\t%s\t%s\t%s\n' % (
                        rel, t.tid, t.kind, t.fmt, t.dt, t.w, t.h, t.method, t.plain_len, t.slot, 'y' if t.growable else 'n',
                        '' if t.gbix is None else '%x' % t.gbix, t.sha1))
                    rows += 1
                if progress:
                    progress(rel, len(texs))
    return rows


def find_copies(index_path, file_rel, tid):
    """Rows of the index whose payload and format equal those of (file_rel, tid): every place the same art lives."""
    rows = []
    with open(index_path, encoding='utf8') as f:
        next(f)
        for line in f:
            p = line.rstrip('\n').split('\t')
            if len(p) >= 13 and p[1] != '!':
                rows.append(p)
    me = [r for r in rows if r[0] == file_rel and r[1] == tid]
    if not me:
        raise TexInjectError('%s %r is not in the index' % (file_rel, tid))
    key = (me[0][3], me[0][4], me[0][5], me[0][6], me[0][12])
    return [r for r in rows if (r[3], r[4], r[5], r[6], r[12]) == key]


# =============================================================== independent loader emulation (used by the tests)
def game_walk_zsarc(d, start=0):
    """Re-implementation of the game's FUN_8c15a45a / FUN_8c15a1cc checks, starting at `start` (the loader does NOT skip
    zero bytes: a u16 0 header length ends the archive).  For every member: the header length must be consistent, the
    header CRC (type-0 extension) and the data CRC16 must match, the decoder must produce orig_size bytes, a stored
    member must have packed == orig.  Returns ([(ext chain bytes, plain)], end offset, why) with why in
    ('terminator', 'eof', 'tail'); raises TexInjectError on a loader error."""
    out = []
    o = start
    n = len(d)
    while True:
        if o + 2 > n:
            return out, o, 'eof'
        hl = struct.unpack_from('<H', d, o)[0]
        if hl == 0:
            return out, o, 'terminator'
        meth = bytes(d[o + 2:o + 7])
        if meth not in (b'-nc--', b'-bz--', b'-bzw-'):
            return out, o, 'tail'
        if hl > 0x400:
            raise TexInjectError('illegal archive format (hdrlen %d) at %#x' % (hl, o))
        packed, orig, mtime, crc = struct.unpack_from('<IIIH', d, o + 7)
        # header length: chain of extensions, then rounded to a multiple of 4 (+2 when needed)
        p = o + 24
        while True:
            sz = struct.unpack_from('<H', d, p)[0]
            if sz == 0:
                p += 2
                break
            p += sz
        calc = p - o
        if calc % 4:
            calc += 2
        if calc != hl:
            raise TexInjectError('headersize mismatch at %#x (%d != %d)' % (o, calc, hl))
        hdr = bytearray(d[o:o + hl])
        q = 24
        hcrc = None
        while True:
            sz = struct.unpack_from('<H', hdr, q)[0]
            if sz == 0:
                break
            if hdr[q + 2] == 0:
                hcrc = struct.unpack_from('<H', hdr, q + 3)[0]
                hdr[q + 3] = hdr[q + 4] = 0
            q += sz
        if hcrc is None or bzlib.crc16(hdr) != hcrc:
            raise TexInjectError('header crc mismatch at %#x' % o)
        data = bytes(d[o + hl:o + hl + packed])
        if len(data) != packed:
            raise TexInjectError('member at %#x runs past the end of the file' % o)
        meth_s = meth.decode()
        plain = bzlib.decompress(data, None, meth_s)
        if len(plain) != orig:
            raise TexInjectError('exFilesize mismatch at %#x (%d != %d)' % (o, len(plain), orig))
        if bzlib.crc16(plain) != crc:
            raise TexInjectError('exFileCRC mismatch at %#x' % o)
        if meth_s == '-nc--' and packed != orig:
            raise TexInjectError('stored member with packed != orig at %#x' % o)
        out.append((bytes(d[o + 24:o + hl]), plain))
        o += hl + packed + ((4 - (packed & 3)) if packed & 3 else 0)     # the loader aligns by the packed size


def game_load_tbd(d, base=0):
    """Re-implementation of FUN_8c15a776: for each record the data pointer is base+offset and the codec is chosen by
    the flag bits 30/31; the decoder runs until its end token.  Returns [(fmt, dt, w, h, stamp, plain)]."""
    n = struct.unpack_from('<I', d, base)[0]
    out = []
    for i in range(n):
        f, wh, off, st = struct.unpack_from('<IIII', d, base + 4 + 16 * i)
        w, h = wh & 0xffff, wh >> 16
        src = bytes(d[base + off:])
        b30, b31 = bool(f & 0x40000000), bool(f & 0x80000000)
        if b31 and not b30:
            plain = bzlib.decompress_bz(src, None)
        elif b30 and not b31:
            plain = bzlib.decompress_bzw(src, None)
        else:
            ps = payload_size(f & 0xff, (f >> 8) & 0xff, w, h)[0]
            plain = src[:ps] if ps else src
        out.append((f & 0xff, (f >> 8) & 0xff, w, h, st, plain))
    return out


# =============================================================== CLI
def _cmd_list(a):
    d = _as_bytes(a.file)
    for t in list_textures(d):
        print('%-28s %-12s fmt=%d dt=%#04x %4dx%-4d %-6s plain=%-7d slot=%-7s grow=%s gbix=%s' % (
            t.tid or "''", t.kind, t.fmt, t.dt, t.w, t.h, t.method, t.plain_len, t.slot, 'y' if t.growable else 'n',
            '-' if t.gbix is None else '%#x' % t.gbix))
    return 0


def _cmd_extract(a):
    b = extract_pvr(a.file, a.id)
    with open(a.out, 'wb') as f:
        f.write(b)
    print('wrote', a.out, len(b), 'bytes')
    return 0


def _cmd_inject(a):
    with open(a.pvr, 'rb') as f:
        pvr = f.read()
    r = inject(a.file, a.id, pvr, a.policy, not a.new_gbix, a.force)
    with open(a.out, 'wb') as f:
        f.write(r.data)
    print('wrote', a.out, len(r.data), 'bytes;', r.info)
    return 0


def _cmd_info(a):
    print(info_text(a.file))
    return 0


def _cmd_index(a):
    n = build_index(a.out, scan_all=a.scan_all)
    print('wrote', a.out, n, 'textures')
    return 0


def _cmd_dups(a):
    rel = a.file.replace('\\', '/').strip('/')
    for r in find_copies(a.index, rel, a.id):
        print('%-32s %-14s %-12s %sx%s %s' % (r[0], r[1] or "''", r[2], r[5], r[6], r[7]))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('info', help='size/sector slack/boot-load room and texture kinds of one file')
    p.add_argument('file')
    p.set_defaults(fn=_cmd_info)
    p = sp.add_parser('index', help='index every texture of extracted/ (build/texindex.tsv)')
    p.add_argument('--out', default=os.path.join(ROOT, 'build', 'texindex.tsv'))
    p.add_argument('--scan-all', action='store_true', help='also scan SSONG/SOUND/DPSS/DPWWW')
    p.set_defaults(fn=_cmd_index)
    p = sp.add_parser('dups', help='list every copy (same payload and format) of a texture, using the index')
    p.add_argument('file', help='iso path below extracted/, e.g. ETC_DATA/TITLE.DAT')
    p.add_argument('id')
    p.add_argument('--index', default=os.path.join(ROOT, 'build', 'texindex.tsv'))
    p.set_defaults(fn=_cmd_dups)
    p = sp.add_parser('list', help='list the textures of a file')
    p.add_argument('file')
    p.set_defaults(fn=_cmd_list)
    p = sp.add_parser('extract', help='write one texture as a PVR file')
    p.add_argument('file')
    p.add_argument('id')
    p.add_argument('out')
    p.set_defaults(fn=_cmd_extract)
    p = sp.add_parser('inject', help='replace one texture and write the patched file')
    p.add_argument('file')
    p.add_argument('id')
    p.add_argument('pvr')
    p.add_argument('out')
    p.add_argument('--policy', choices=['exact', 'grow'], default='exact')
    p.add_argument('--new-gbix', action='store_true', help='take the GBIX chunk of the new PVR instead of the original')
    p.add_argument('--force', action='store_true', help='grow even where the layout is not known to be safe')
    p.set_defaults(fn=_cmd_inject)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except TexInjectError as e:
        print('texinject:', e, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
