"""Find real embedded PVR images (GBIX chunk + PVRT chunk, or bare PVRT with sane header) in raw files of extracted/
that are not themselves PVR files.   python -I -X utf8 tools/re/texinject/scan_pvr.py"""
import os
import re
import sys
import struct
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
ext = os.path.join(ROOT, 'extracted')
pat = re.compile(rb'GBIX.{4}.{8}PVRT', re.S)
pat2 = re.compile(rb'PVRT.{4}[\x00-\x06][\x01\x02\x03\x04\x09\x0d\x10\x11]\x00\x00', re.S)
out = collections.OrderedDict()
for root, dirs, files in os.walk(ext):
    dirs.sort()
    for fn in sorted(files):
        if fn in ('BCAST.BIN', '_filelist.tsv'):
            continue
        p = os.path.join(root, fn)
        rel = os.path.relpath(p, ext).replace('\\', '/')
        d = open(p, 'rb').read()
        if d[:4] in (b'GBIX', b'PVRT'):
            continue
        a = [m.start() for m in pat.finditer(d)]
        b = [m.start() for m in pat2.finditer(d)]
        # keep bare PVRT only when no GBIX precedes it
        bare = [x for x in b if x - 16 not in a]
        if a or bare:
            out[rel] = (a, bare)
for rel, (a, b) in out.items():
    print('%-34s GBIX+PVRT=%-3d bare-PVRT=%-3d first at %s' % (rel, len(a), len(b), [hex(x) for x in (a + b)[:4]]))
print(len(out), 'files')
