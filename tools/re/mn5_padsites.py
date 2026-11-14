"""mn5_padsites.py: for every direct (non-expander) call of the original money function look at the next 16 instructions for a field-width idiom
(`mov #N,rX` ... `sub rY,rX`, i.e. N - len), the way the SCDRF/SEARCH info panel right-aligns the text in a 12 byte field."""
import os, sys, struct, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moneypatch as MP
for line in open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'build', 'mn5', 'callers.txt')):
    m = re.match(r'(\S+) money@(\w+) pool@(\w+) site@(\w+) r(\d+)\s*(\S*)', line)
    if not m or m.group(6):
        continue
    rel, site = m.group(1), int(m.group(4), 16)
    d = MP.read_extracted(rel)
    # find the jsr @rN after the load, then scan 20 instrs after it
    o = site
    reg = int(m.group(5))
    while o < site + 80:
        w = d[o] | d[o + 1] << 8
        if (w & 0xF0FF) == 0x400B and ((w >> 8) & 15) == reg:
            break
        o += 2
    found = []
    for k in range(o + 2, o + 2 + 44, 2):
        w = d[k] | d[k + 1] << 8
        if (w >> 12) == 0xE and ((w >> 8) & 15) in (2, 4, 5, 6) and 4 <= (w & 0xFF) <= 40:
            found.append('mov #%d,r%d@%x' % (w & 0xFF, (w >> 8) & 15, k))
        if (w & 0xF00F) == 0x3008:
            found.append('sub@%x' % k)
    print('%-26s site %5x jsr %5x : %s' % (rel, site, o, ' '.join(found)))
