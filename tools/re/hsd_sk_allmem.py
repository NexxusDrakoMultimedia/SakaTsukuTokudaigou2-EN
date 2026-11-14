"""hsd_sk: over a whole trial disc, every ZSARC member (any method; header found by method string at any 2-byte offset) that is valid in the
ORIGINAL (extracted/) file (header CRC, data CRC16 of the decoded data) but not valid at the same offset in the disc's file.  Same-size files only
(others are reported).  usage: hsd_sk_allmem.py DISC [PATH-SUBSTRING].  Read-only."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D
import bzlib

disc = sys.argv[1]
sub = sys.argv[2].upper() if len(sys.argv) > 2 else ''
src = D.Source(os.path.join(ROOT, 'build', 'trial', disc), disc)
_p, _rl, _rs, recs = D.read_filesystem(src)
files = [r for r in recs if not r.isdir]
nfiles = nchg = nbad = nskip = 0
for r in sorted(files, key=lambda r: r.path):
    if sub and sub not in r.path.upper():
        continue
    op = os.path.join(ROOT, 'extracted', *r.path.strip('/').split('/'))
    if not os.path.isfile(op):
        continue
    old = open(op, 'rb').read()
    nfiles += 1
    if r.size != len(old):
        nskip += 1; print('SIZE-DIFFERS', r.path, len(old), '->', r.size); continue
    new = src.read(r.lba, r.size)
    if new == old:
        continue
    nchg += 1
    for meth in (b'-nc--', b'-bz--', b'-bzw-'):
        o = old.find(meth, 2)
        while o >= 0:
            m = bzlib.parse_member(old, o - 2, with_data=True)
            if m is not None and m.method == meth.decode() and m.hdr_crc_ok:
                try:
                    plain = m.extract()
                except Exception:
                    plain = None
                if plain is not None:
                    n = bzlib.parse_member(new, m.offset, with_data=True)
                    why = None
                    if n is None: why = 'no header'
                    elif not n.hdr_crc_ok: why = 'header CRC'
                    else:
                        try:
                            n.extract()
                        except Exception as e:
                            why = 'data: %s' % e
                    if why:
                        nbad += 1
                        print('STALE %s @%#x %s %r (%s)' % (r.path, m.offset, m.method, m.name, why))
            o = old.find(meth, o + 1)
print(disc, 'files compared', nfiles, 'changed', nchg, 'size-differs', nskip, 'stale members', nbad)
