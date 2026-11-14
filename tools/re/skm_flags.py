"""skm_flags.py: the r6 (flag) value set before the `jsr` of every direct (non-expander) call of the original money function (list: build/mn5/callers.txt).
Read-only.  Prints one line per site; sites with flag 1 are the ones whose original text had a zero padded Man part."""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import moneypatch as MP          # noqa: E402

for line in open(os.path.join(ROOT, 'build', 'mn5', 'callers.txt')):
    m = re.match(r'(\S+) money@(\w+) pool@(\w+) site@(\w+) r(\d+)\s*(\S*)', line)
    if not m or m.group(6):
        continue
    rel, site, reg = m.group(1), int(m.group(4), 16), int(m.group(5))
    d = MP.read_extracted(rel)
    o = site
    while o < site + 80:
        w = d[o] | d[o + 1] << 8
        if (w & 0xF0FF) == 0x400B and ((w >> 8) & 15) == reg:
            break
        o += 2
    flag = None
    for k in range(o - 2, o - 40, -2):
        w = d[k] | d[k + 1] << 8
        if (w >> 12) == 0xE and ((w >> 8) & 15) == 6:
            flag = struct.unpack('b', bytes([w & 0xFF]))[0]
            break
        if (w & 0xF00F) == 0x6003 and ((w >> 8) & 15) == 6:
            flag = 'mov rX,r6'
            break
    print('%-24s site %6s flag %s' % (rel, hex(site), flag))
