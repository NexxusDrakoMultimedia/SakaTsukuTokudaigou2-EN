"""Search RAM dump(s) for cp932 strings: ramfind.py DUMP STR... (prints address 0x8C000000+off and context)"""
import sys
d = open(sys.argv[1], 'rb').read()
for s in sys.argv[2:]:
    p = s.encode('cp932')
    k = d.find(p)
    n = 0
    while k != -1 and n < 12:
        ctx = d[max(0, k - 8):k + len(p) + 16]
        print('%-14s %#010x  %r' % (s, 0x8C000000 + k, ctx.decode('cp932', 'replace')))
        n += 1
        k = d.find(p, k + 1)
