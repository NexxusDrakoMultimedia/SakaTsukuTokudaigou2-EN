"""Generalised scan: half-width advance sequence with wildcards for the offset/registers.
python -I -X utf8 tools/re/font/scan_sig2.py"""
import os, re, collections
PAT = re.compile(rb'([\x00-\xff])\xe0(.)\x02\x00\xe3\x27\x33(.)\x32\x21\x42(.)\x3a|([\x00-\xff])\xe0', re.S)
# precise: E0 ofs,  ec 02 (mov.b @(r0,rM),r2 with M enc in 2nd byte), 00e3, 2733, 3e32, 2142, 2c3X, 04a0, 017X
P = re.compile(rb'(.)\xe0(.)\x02\x00\xe3\x27\x33\x3e\x32\x21\x42\x2c([\x3a\x3b])\x04\xa0\x01([\x7a\x7b])'
               rb'(.)\xe0(.)\x03\x02([\x7a\x7b])\x3c([\x3a\x3b])', re.S)
res = collections.defaultdict(list)
for r, ds, fs in os.walk('extracted'):
    for f in sorted(fs):
        p = os.path.join(r, f).replace(chr(92), '/')
        d = open(p, 'rb').read()
        for m in P.finditer(d):
            if m.start() % 2: continue
            res[p].append((m.start(), m.group(1)[0], m.group(2).hex(), m.group(3).hex(), m.group(4).hex()))
for p, v in res.items():
    print(p, [(hex(a), 'adv_ofs=%d' % o, 'regs(%s,%s)' % (x, y)) for a, o, x, y, z in v])
print(len(res), 'files')
