"""Dump u32 literal-pool words of 1ST_READ.BIN (base 0x8c010000) for a list of addresses.
usage: python -I -X utf8 litpool.py 8c15a7d4 8c15a7d8 ...   (prints addr: value)"""
import sys, struct, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
data = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
BASE = 0x8c010000
for a in sys.argv[1:]:
    ad = int(a, 16)
    o = ad - BASE
    if a.startswith('s'):
        continue
    v = struct.unpack_from('<I', data, o)[0]
    s = ''
    if BASE <= v < BASE + len(data):
        p = v - BASE
        e = data.find(b'\0', p, p + 80)
        t = data[p:e if e > 0 else p + 40]
        if t and all(32 <= c < 127 for c in t):
            s = ' "%s"' % t.decode()
    print('%08x: %08x%s' % (ad, v, s))
