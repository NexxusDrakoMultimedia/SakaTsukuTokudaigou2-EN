"""Layout statistics of PVR files / PVR members (GBIX + PVRT chunks) over the disc.

    python -I -X utf8 tools/re/texinject/analyze_pvr.py
Checks, for every PVR member of every ZSARC container (plaintext decoded with tools/bzlib.py) and for the 24 plain .PVR files:
  * chunk structure (GBIX len, PVRT len), trailing bytes after the PVRT chunk
  * payload length vs the formula implied by (datatype, w, h)
  * pixel formats / datatypes histogram
"""
import os
import sys
import struct
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import bzlib      # noqa: E402


def expected(dt, w, h):
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


def chunks(b):
    o = 0
    out = []
    while o + 8 <= len(b) and b[o:o + 4] in (b'GBIX', b'PVRT'):
        ln = struct.unpack_from('<I', b, o + 4)[0]
        out.append((bytes(b[o:o + 4]), o, ln))
        o += 8 + ln
        if out[-1][0] == b'PVRT':
            break
    return out, o


def check(b, st, tag):
    ch, end = chunks(b)
    names = tuple(c[0] for c in ch)
    st['chunks ' + '+'.join(x.decode() for x in names)] += 1
    if not ch or ch[-1][0] != b'PVRT':
        st['no-pvrt'] += 1
        return
    gb = [c for c in ch if c[0] == b'GBIX']
    if gb:
        st['gbix len %d' % gb[0][2]] += 1
    po = ch[-1][1]
    fmt, dt = b[po + 8], b[po + 9]
    w, h = struct.unpack_from('<HH', b, po + 12)
    st['fmt %d dt %#x' % (fmt, dt)] += 1
    payload = ch[-1][2] - 8
    exp, exact = expected(dt, w, h)
    if exp is None:
        st['dt unknown %#x' % dt] += 1
    elif (payload == exp) if exact else (payload >= exp):
        st['payload ok'] += 1
    else:
        st['payload MISMATCH'] += 1
        if st['payload MISMATCH'] < 6:
            print('MISMATCH', tag, fmt, hex(dt), w, h, payload, exp)
    if end != len(b):
        st['trailing %d' % min(len(b) - end, 64)] += 1
    if b[po + 10:po + 12] != b'\0\0':
        st['hdr reserved nonzero'] += 1


def main():
    ext = os.path.join(ROOT, 'extracted')
    st = collections.Counter()
    members = 0
    for root, dirs, files in os.walk(ext):
        dirs.sort()
        for fn in sorted(files):
            if fn in ('BCAST.BIN', '_filelist.tsv'):
                continue
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, ext).replace('\\', '/')
            d = open(p, 'rb').read()
            if d[:4] in (b'GBIX', b'PVRT'):
                st['plain .PVR file'] += 1
                check(d, st, rel)
                continue
            if bzlib.parse_member(d, 0, with_data=False) is None:
                continue
            ms, tail = bzlib.parse_archive(d)
            for m in ms:
                plain = m.extract(verify=False)
                if plain[:4] not in (b'GBIX', b'PVRT'):
                    continue
                members += 1
                st['member method ' + m.method] += 1
                st['member data_offset%%4=%d' % (m.data_offset % 4)] += 1
                st['member data_offset%32==0'] += (m.data_offset % 32 == 0)
                check(plain, st, rel + ':' + m.name)
    print('pvr members', members)
    for k in sorted(st):
        print('%-34s %d' % (k, st[k]))


if __name__ == '__main__':
    main()
