"""hrd: stored ZSARC members inside a file of a disc / a dump dir / a RAM dump: header CRC and data CRC16 state.

usage: hrd_members.py SPEC [FILE ...] [--all]
  SPEC = trial disc name (build/trial/NAME), or dir:PATH (a --dump directory), or orig (extracted/), or
         ram:PATH@HEXBASE (RAM dump, the file is taken at HEXBASE with the original length)
  FILE = ISO-style paths (default FLOW_PRG/SCDRF.BIN).  --all = every FLOW_PRG/*.BIN overlay.
For every '-nc--' / '-bz--' / '-bzw-' member header found anywhere in the file whose header CRC is valid IN THE ORIGINAL:
prints offset, name, method, sizes, whether header CRC and data CRC16 hold in SPEC, and the TBD tables inside it.
Read-only.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import bzlib                     # noqa: E402
import discbuild as D            # noqa: E402
import texinject as T            # noqa: E402

_cache = {}


def getter(spec):
    if spec == 'orig':
        return lambda p: open(os.path.join(ROOT, 'extracted', p), 'rb').read()
    if spec.startswith('dir:'):
        base = spec[4:]

        def g(p):
            for cand in (os.path.join(base, p), os.path.join(base, p.replace('/', '__')), os.path.join(base, os.path.basename(p))):
                if os.path.isfile(cand):
                    return open(cand, 'rb').read()
            return None
        return g
    if spec.startswith('ram:'):
        path, hb = spec[4:].rsplit('@', 1)
        ram = open(path, 'rb').read()
        o = int(hb, 16) - 0x8c000000

        def g(p):
            n = os.path.getsize(os.path.join(ROOT, 'extracted', p))
            return ram[o:o + n]
        return g
    src = D.Source(os.path.join(ROOT, 'build', 'trial', spec), spec)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    files = {r.path.upper().strip('/'): r for r in recs if not r.isdir}

    def g(p):
        r = files.get(p.upper())
        return None if r is None else src.read(r.lba, r.size)
    return g


def members(orig):
    """Members (any method) with a valid header CRC found anywhere in the original image."""
    out = []
    for meth in (b'-nc--', b'-bz--', b'-bzw-'):
        o = orig.find(meth, 2)
        while o >= 0:
            m = bzlib.parse_member(orig, o - 2, with_data=False)
            if m is not None and m.hdr_crc_ok and m.end_offset <= len(orig):
                out.append(m)
            o = orig.find(meth, o + 1)
    out.sort(key=lambda m: m.offset)
    return out


def data_ok(d, m):
    blk = bytes(d[m.data_offset:m.end_offset])
    try:
        plain = blk if m.method == '-nc--' else bzlib.decompress(blk, m.orig_size, m.method)
    except Exception:           # noqa
        return False
    return len(plain) == m.orig_size and bzlib.crc16(plain) == m.crc16


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('--')]
    spec = args[0]
    files = args[1:] or ['FLOW_PRG/SCDRF.BIN']
    if '--all' in argv:
        files = ['FLOW_PRG/' + f for f in sorted(os.listdir(os.path.join(ROOT, 'extracted', 'FLOW_PRG'))) if f.upper().endswith('.BIN')]
    g = getter(spec)
    tot = bad = 0
    for p in files:
        orig = open(os.path.join(ROOT, 'extracted', p), 'rb').read()
        ms = members(orig)
        if not ms:
            continue
        d = g(p)
        if d is None:
            print('%s: not in %s' % (p, spec))
            continue
        tabs = T.scan_tables(orig)
        for m in ms:
            n = bzlib.parse_member(d, m.offset, with_data=False)
            hok = n is not None and n.hdr_crc_ok
            dok = n is not None and data_ok(d, n)
            ook = data_ok(orig, m)
            changed = bytes(d[m.data_offset:m.end_offset]) != bytes(orig[m.data_offset:m.end_offset])
            hchanged = bytes(d[m.offset:m.data_offset]) != bytes(orig[m.offset:m.data_offset])
            inside = [t for t in tabs if m.data_offset <= t.base < m.end_offset]
            tot += 1
            st = 'OK'
            if ook and not (hok and dok):
                st = 'STALE'
                bad += 1
            print('%-24s member @%#07x %-14s %s packed %7d orig %7d data %#07x..%#07x  orig-valid %s | %s: hdrCRC %s dataCRC %s data-changed %s hdr-changed %s  tables %s  %s'
                  % (p, m.offset, m.name, m.method, m.packed_size, m.orig_size, m.data_offset, m.end_offset, ook, spec.split(':')[0], hok, dok,
                     changed, hchanged, ['@%x(%d)' % (t.base, t.n) for t in inside], st))
    print('members %d, stale %d' % (tot, bad))


if __name__ == '__main__':
    main(sys.argv)
