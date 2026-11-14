"""hsd: find ZSARC member headers anywhere inside an overlay (any 2-byte offset), report the ones whose stored data CRC16 does not match.
usage: hsd_scan.py FILE [LABEL].  Read-only."""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import bzlib
d = open(sys.argv[1], 'rb').read()
n = len(d)
good = bad = 0
for o in range(0, n - 30, 2):
    if d[o+2:o+7] not in (b'-nc--', b'-bz--', b'-bzw-'):
        continue
    hl = struct.unpack_from('<H', d, o)[0]
    if not 24 < hl <= 0x400:
        continue
    packed, orig, mtime, crc = struct.unpack_from('<IIIH', d, o + 7)
    if o + hl + packed > n or packed > 0x400000:
        continue
    try:
        plain = bzlib.decompress(bytes(d[o+hl:o+hl+packed]), None, d[o+2:o+7].decode())
    except Exception as e:
        continue
    c = bzlib.crc16(plain)
    ok = (c == crc and len(plain) == orig)
    if ok: good += 1
    else:
        bad += 1
        print('  BAD member @%x %s packed=%#x orig=%#x stored=%04x calc=%04x len=%d name=%r' % (o, d[o+2:o+7].decode(), packed, orig, crc, c, len(plain), d[o+24:o+hl][:20]))
print(sys.argv[1], 'members ok', good, 'bad', bad)
