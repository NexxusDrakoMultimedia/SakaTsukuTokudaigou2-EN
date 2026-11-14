"""hrd skeptic: compare a build_patch --dump directory (current tools) with a built trial disc (older tools), file by file.

usage: hrd_sk_dumpdiff.py DUMPDIR DISC
Every file of DUMPDIR is read from the disc build/trial/DISC through its directory records and compared.  Prints the
differing ranges of every file that differs, and for each range whether it is one of the two CRC fields (+0x13 data
CRC16, +0x27 header CRC for the 0x2c byte headers) of a stored ZSARC member.  Also lists disc files that differ from the
original but are missing from the dump.  Read-only.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D            # noqa: E402
import bzlib                     # noqa: E402


def ranges(a, b, gap=1):
    out = []
    n = min(len(a), len(b))
    i = 0
    while i < n:
        if i + 4096 <= n and a[i:i + 4096] == b[i:i + 4096]:
            i += 4096
            continue
        end = min(i + 4096, n)
        for j in range(i, end):
            if a[j] != b[j]:
                if out and j - out[-1][1] < gap:
                    out[-1][1] = j + 1
                else:
                    out.append([j, j + 1])
        i = end
    if len(a) != len(b):
        out.append([n, max(len(a), len(b))])
    return out


def members(d):
    ms = []
    o = d.find(b'-nc--', 2)
    while o >= 0:
        m = bzlib.parse_member(d, o - 2, with_data=False)
        if m is not None and m.method == '-nc--' and m.packed_size == m.orig_size:
            ms.append(m)
        o = d.find(b'-nc--', o + 1)
    return ms


def main(argv):
    dump, disc = argv[1], argv[2]
    src = D.Source(os.path.join(ROOT, 'build', 'trial', disc), disc)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    files = {r.path.upper().lstrip('/'): r for r in recs if not r.isdir}
    seen = set()
    ndiff = nsame = unexplained = 0
    for dp, _dn, fn in os.walk(dump):
        for f in sorted(fn):
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, dump).replace('\\', '/').upper()
            seen.add(rel)
            a = open(full, 'rb').read()
            r = files.get(rel)
            if r is None:
                print('%-32s NOT ON DISC' % rel)
                unexplained += 1
                continue
            b = src.read(r.lba, r.size)
            if a == b:
                nsame += 1
                continue
            ndiff += 1
            rs = ranges(a, b)
            print('%-32s size %d/%d  %d range(s), %d byte(s)' % (rel, len(a), len(b), len(rs), sum(e - s for s, e in rs)))
            ms = members(a)
            for s, e in rs[:40]:
                tag = 'UNEXPLAINED'
                for m in ms:
                    if m.offset + 0x13 <= s and e <= m.offset + 0x15:
                        tag = 'data CRC16 of stored member %r @%#x (valid now: %s)' % (
                            m.name, m.offset, bzlib.crc16(bytes(a[m.data_offset:m.end_offset])) == m.crc16 and m.hdr_crc_ok)
                    elif m.offset + 0x18 <= s and e <= m.data_offset:
                        tag = 'header CRC of stored member %r @%#x' % (m.name, m.offset)
                if tag == 'UNEXPLAINED':
                    unexplained += 1
                print('      %#07x-%#07x (%d)  %s' % (s, e, e - s, tag))
    print('dump files: %d identical to the disc, %d differ; unexplained ranges/files: %d' % (nsame, ndiff, unexplained))


main(sys.argv)
