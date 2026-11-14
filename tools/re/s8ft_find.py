"""s8ft: locate message 24906 in original / hsk_full1 / s8e_nofix / prop10c SCDRF.BIN; show pointer table entries, neighbours.
usage: s8ft_find.py DIR
"""
import os
import struct
import sys

d = sys.argv[1]
orig = open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'extracted', 'FLOW_PRG', 'SCDRF.BIN'), 'rb').read()
files = {'orig': orig}
for n in ('hsk_full1', 's8e_nofix', 'prop10c'):
    files[n] = open(os.path.join(d, '%s__SCDRF.BIN' % n), 'rb').read()
BASE = 0x8c010000
ja = '遂に私たちのオファーに応えて頂けました。'.encode('cp932')
en = b"At last, they've accepted"
TBL = 0x1bef4
for n, b in files.items():
    print('==', n, len(b))
    for key, pat in (('ja', ja), ('en', en)):
        i = b.find(pat)
        while i >= 0:
            print('  %s at %#x' % (key, i))
            i = b.find(pat, i + 1)
    # table
    ents = struct.unpack_from('<4I', b, TBL + 273 * 4)
    print('  tbl[272..275]', [hex(x) for x in ents])
