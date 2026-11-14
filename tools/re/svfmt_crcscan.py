"""svfmt_crcscan.py OVERLAY|1ST_READ... : CRC evidence: CCITT table (00 00 21 10 42 20), X.25 reflected table, 0x1021 / 0x8408 / 0xedb88320 literals."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svfmt_xref import load
pats = {'ccitt-table-LE16': bytes.fromhex('0000 2110 4220 6330'.replace(' ', '')),
        'x25-table-LE16': bytes.fromhex('0000 8911 1223 9b32'.replace(' ', '')),
        'crc32-table': bytes.fromhex('00000000 96300777'.replace(' ', '')),
        'crc32-table-b': bytes.fromhex('00000000 77073096'.replace(' ', ''))}
for n in sys.argv[1:]:
    d, base = load(n)
    for k, p in pats.items():
        i = d.find(p)
        while i >= 0:
            print(n, k, hex(base + i)); i = d.find(p, i + 1)
    for off in range(0, len(d) - 3, 2):
        h = struct.unpack_from('<H', d, off)[0]
        if h in (0x1021, 0x8408, 0xA001, 0x8005) and (struct.unpack_from('<H', d, off - 2)[0] >> 12) in (0x9, 0xD, 0xE, 0x7 + 0 * 1) or h == 0x1021 and off % 4 == 0 and False:
            pass
    for v in (0xEDB88320, 0x04C11DB7):
        b = struct.pack('<I', v); i = d.find(b)
        while i >= 0:
            print(n, 'lit32', hex(v), hex(base + i)); i = d.find(b, i + 1)
