"""hrd: SCDRF.BIN of two trial discs vs the original and vs a RAM dump.

usage: hrd_scdrf.py DISC_A DISC_B [RAMDUMP] [--file FLOW_PRG/SCDRF.BIN] [--base 0x8c2d0000] [--table 0x2ff64]
Read-only.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D            # noqa: E402
import texinject as T            # noqa: E402


def opt(argv, name, default):
    if name in argv:
        return argv[argv.index(name) + 1]
    return default


def disc_file(name, path):
    src = D.Source(os.path.join(ROOT, 'build', 'trial', name), name)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    for r in recs:
        if not r.isdir and r.path.upper().strip('/') == path.upper():
            return src.read(r.lba, r.size), r
    raise SystemExit('no %s in %s' % (path, name))


def ranges(a, b, gap=8):
    out = []
    n = min(len(a), len(b))
    for j in range(n):
        if a[j] != b[j]:
            if out and j - out[-1][1] <= gap:
                out[-1][1] = j + 1
            else:
                out.append([j, j + 1])
    return out


def main(argv):
    pos = [a for a in argv[1:] if not a.startswith('--')]
    skip = set()
    for k in ('--file', '--base', '--table'):
        if k in argv:
            skip.add(argv[argv.index(k) + 1])
    pos = [a for a in pos if a not in skip]
    na, nb = pos[0], pos[1]
    ram = pos[2] if len(pos) > 2 else None
    path = opt(argv, '--file', 'FLOW_PRG/SCDRF.BIN')
    base = int(opt(argv, '--base', '0x8c2d0000'), 16)
    tbase = int(opt(argv, '--table', '0x2ff64'), 16)
    orig = open(os.path.join(ROOT, 'extracted', path), 'rb').read()
    da, ra = disc_file(na, path)
    db, rb = disc_file(nb, path)
    print('orig %d bytes; %s: size %d lba %d; %s: size %d lba %d' % (len(orig), na, ra.size, ra.lba, nb, rb.size, rb.lba))
    rg = ranges(da, db)
    print('%s vs %s: %d ranges, %d bytes' % (na, nb, len(rg), sum(e - s for s, e in rg)))
    for s, e in rg[:60]:
        print('   %#08x-%#08x (%d)' % (s, e, e - s))
    for nm, d in (('orig', orig), (na, da), (nb, db)):
        t = T.read_table(d, tbase, 'embedded', True)
        print('table @%#x in %s: %s' % (tbase, nm, 'none' if t is None else '%d records' % t.n))
        if t is None:
            continue
        for r in t.recs:
            s, e = T._rec_slot(d, t, r['i'])
            ps = T.payload_size(r['fmt'], r['dt'], r['w'], r['h'])
            extra = ''
            if r['comp'] in (1, 2):
                c = T.consumed(d[s:], r['comp'])
                extra = ' consumed=%s' % c
                try:
                    pl = T.tbd_plain(d, t, r['i'])
                    extra += ' plain=%d' % len(pl)
                except Exception as ex:   # noqa
                    extra += ' plain ERR %s' % ex
            print('   #%d flags %08x fmt %d dt %#x comp %d %dx%d off %#x stamp %#x slot %#x..%#x (%d) payload %s%s'
                  % (r['i'], r['flags'], r['fmt'], r['dt'], r['comp'], r['w'], r['h'], r['off'], r['stamp'], s, e, e - s, ps, extra))
        last = t.recs[-1]
        s, e = T._rec_slot(d, t, t.n - 1)
        print('   bytes after last slot (%#x): %s' % (e, d[e:e + 48].hex()))
        print('   bytes before table: %s' % d[tbase - 32:tbase].hex())
    if ram:
        r = open(ram, 'rb').read()
        o = base - 0x8c000000
        img = r[o:o + len(orig)]
        for nm, d in ((na, da), (nb, db), ('orig', orig)):
            same = sum(1 for i in range(0, len(d), 64) if d[i:i + 64] == img[i:i + 64])
            rr = ranges(d, img, 64)
            print('RAM @%#x vs %s: %d of %d 64-byte chunks equal, %d differing ranges, %d bytes' % (base, nm, same, (len(d) + 63) // 64, len(rr), sum(e - s for s, e in rr)))
            for s, e in rr[:25]:
                print('      %#08x-%#08x (%d)' % (s, e, e - s))


if __name__ == '__main__':
    main(sys.argv)
