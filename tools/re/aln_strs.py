"""aln: list the NUL-terminated byte strings of an overlay in a file-offset range (cp932 decoded), with the pool references to them.

    python -I -X utf8 tools/re/aln_strs.py OVERLAY START END
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aln_xref as X  # noqa: E402

name, a, b = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
d = open(os.path.join(X.ROOT, 'extracted', 'FLOW_PRG', name + '.BIN'), 'rb').read()
i = a
while i < b:
    j = d.index(b'\0', i)
    if j > i:
        s = d[i:j].decode('cp932', 'replace')
        refs = [hex(x[0]) for x in X.xrefs(d, 0x8c2d0000 + i)]
        print('%#x %r  refs %s' % (i, s, ' '.join(refs)))
    i = j + 1
