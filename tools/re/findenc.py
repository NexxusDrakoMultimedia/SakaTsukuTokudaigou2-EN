"""findenc.py STR: search extracted/, build/unpacked/ and pt1_ram.bin for STR in several encodings."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
s = sys.argv[1]
encs = {}
for e in ('cp932', 'euc_jp', 'utf-16-le', 'utf-16-be', 'utf-8', 'iso2022_jp'):
    try:
        encs[e] = s.encode(e)
    except Exception:
        pass
# JIS row/col raw (no escape)
try:
    encs['jis-raw'] = s.encode('iso2022_jp')[3:-3]
except Exception:
    pass
files = []
for base in ('extracted', 'build/unpacked'):
    for dp, dn, fn in os.walk(os.path.join(ROOT, base)):
        for f in fn:
            files.append(os.path.join(dp, f))
files.append(os.path.join(ROOT, 'build/emu/pt1_ram.bin'))
for fp in files:
    d = open(fp, 'rb').read()
    for e, p in encs.items():
        if e == 'cp932' or len(p) < 4:
            continue
        k = d.find(p)
        if k >= 0:
            print(os.path.relpath(fp, ROOT), e, hex(k))
print('done', {e: p.hex() for e, p in encs.items()})
