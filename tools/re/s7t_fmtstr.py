"""s7t: list short printf-ish / ascii strings of an overlay. usage: file [regex]"""
import re, sys
f = sys.argv[1]
rx = re.compile(sys.argv[2]) if len(sys.argv) > 2 else re.compile(r'%')
d = open(f, 'rb').read()
o = 0
for m in re.finditer(rb'[\x20-\x7e\x81-\x9f\xa0-\xdf\xe0-\xea][\x20-\x7e\x80-\xff]{1,40}\x00', d):
    s = m.group(0)[:-1]
    try:
        t = s.decode('cp932')
    except Exception:
        continue
    if rx.search(t):
        print('0x%x %r' % (m.start(), t))
