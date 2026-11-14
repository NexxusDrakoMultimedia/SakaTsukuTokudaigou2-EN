"""Round-trip + mutation tests for all textfmt_* tools (run from repo root).
python -I -X utf8 tools/re/datatext/test_all.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import textfmt_common as C
import textfmt_ini as I
import textfmt_bpinfo as B
import textfmt_ptrblob as P


def rd(rel):
    return open(os.path.join(ROOT, 'extracted', rel), 'rb').read()


# --- codec: every byte string round trips (random + all single/double byte combos) ---
import random
random.seed(1)
n = 0
for _ in range(20000):
    b = bytes(random.randrange(256) for _ in range(random.randrange(1, 9)))
    assert C.encode_text(C.decode_text(b)) == b, b
    n += 1
for a in range(256):
    for c in range(256):
        b = bytes([a, c])
        assert C.encode_text(C.decode_text(b)) == b, b
        n += 1
assert C.encode_text(C.decode_text(b'<41>a<3C>')) == b'<41>a<3C>'
print('codec: %d byte strings round-trip' % n)

# --- MESSAGE.INI ---
d = rd('DPETC/MESSAGE.INI')
e = I.extract(d)
assert I.apply(d, e) == d
m = [dict(x) for x in e]
m[0]['en'] = 'Connecting to host...'
m[5]['en'] = 'A much longer English replacement string than the Japanese original <br>second line'
new = I.apply(d, m)
e2 = I.extract(new)
assert len(e2) == len(e) and e2[0]['ja'] == m[0]['en'] and e2[5]['ja'] == m[5]['en']
assert [x['ja'] for x in e2[1:5]] == [x['ja'] for x in e[1:5]] and [x['ja'] for x in e2[6:]] == [x['ja'] for x in e[6:]]
print('INI: identity + mutation OK (%d strings)' % len(e))

# --- BPINFO ---
for rel in ('ETC_DATA/BPINFO.BIN', 'ATFIRST/BPINFO.BIN'):
    d = rd(rel)
    e = B.extract(d, rel)
    assert B.apply(d, e) == d
    m = [dict(x) for x in e]
    m[0]['en'] = 'K. Kawamoto'
    m[5320]['en'] = 'Watanabe S.'
    new = B.apply(d, m)
    assert len(new) == len(d)
    e2 = B.extract(new, rel)
    assert e2[0]['ja'] == 'K. Kawamoto' and e2[5320]['ja'] == 'Watanabe S.'
    assert [x['ja'] for x in e2[1:5320]] == [x['ja'] for x in e[1:5320]]
    diff = [i for i in range(len(d)) if d[i] != new[i]]
    assert all(((i - 64) % 92) < 14 for i in diff), 'bytes outside name fields changed'
    try:
        m[1]['en'] = 'X' * 14
        B.apply(d, m)
        raise SystemExit('too long name accepted')
    except ValueError:
        pass
print('BPINFO: identity + mutation + overflow check OK (2 copies)')

# --- ptrblob (2_DP, HELP, TITLE, 1ST_READ) ---
for rel, base, pref, unref in P.FILES:
    d = rd(rel)
    e = P.extract(d, base, rel, unref=unref)
    P.selftest(d, base, e)
    print('ptrblob %-18s %4d strings: identity, ja==en, relocation mutation OK' % (rel, len(e)))
print('ALL OK')
