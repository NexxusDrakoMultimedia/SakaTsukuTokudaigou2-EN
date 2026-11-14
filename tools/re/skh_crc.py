"""skh: every ZSARC member of every file of a built trial disc: payload CRC16 and header CRC must be right (compared with the same check on the original).

usage: skh_crc.py DISC [--all]     (default: only files that differ from extracted/; --all: every ZSARC-looking file)
Prints the files with a bad member, and totals.  A member whose original already fails the same check is counted separately (not a regression).
Read-only.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D            # noqa: E402
import bzlib                     # noqa: E402


def members(d):
    ms = []
    o = 0
    n = len(d)
    while True:
        while o < n and d[o] == 0:
            o += 1
        if o >= n:
            break
        m = bzlib.parse_member(d, o, with_data=False)
        if m is None:
            break
        ms.append(m)
        o = m.end_offset
    return ms, o


def check(d):
    bad = []
    ms, tail = members(d)
    for m in ms:
        try:
            plain = bzlib.decompress(bytes(d[m.data_offset:m.end_offset]), m.orig_size, m.method)
        except Exception as e:
            bad.append((m.name, 'decode %r' % e))
            continue
        if len(plain) != m.orig_size:
            bad.append((m.name, 'orig_size %d != %d' % (len(plain), m.orig_size)))
        if bzlib.crc16(plain) != m.crc16:
            bad.append((m.name, 'payload crc %04x != %04x' % (bzlib.crc16(plain), m.crc16)))
        if m.hdr_crc_ok is False:
            bad.append((m.name, 'header crc'))
    return len(ms), bad


def main(argv):
    name = argv[1]
    everything = '--all' in argv
    src = D.Source(os.path.join(ROOT, 'build', 'trial', name), name)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    tot_files = tot_mem = 0
    nbad = 0
    for r in sorted((x for x in recs if not x.isdir), key=lambda x: x.path):
        p = r.path
        if not p.upper().endswith(('.ZAR', '.DAT', '.TBD', '.ZSA', '.ARC')):
            continue
        orig_path = os.path.join(ROOT, 'extracted', p.lstrip('/'))
        if not os.path.exists(orig_path):
            continue
        new = src.read(r.lba, r.size)
        old = open(orig_path, 'rb').read()
        if new == old and not everything:
            continue
        if bzlib.parse_member(new, 0, with_data=False) is None:
            continue
        n, bad = check(new)
        n0, bad0 = check(old)
        tot_files += 1
        tot_mem += n
        regress = [b for b in bad if b not in bad0]
        if regress:
            nbad += len(regress)
            print('%-28s members %d  NEW BAD %s  (orig bad %d)' % (p, n, regress[:4], len(bad0)))
        elif bad0 and everything:
            print('%-28s orig already bad: %d' % (p, len(bad0)))
    print('files checked %d, members %d, regressions %d' % (tot_files, tot_mem, nbad))
    src.close()
    return 1 if nbad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
