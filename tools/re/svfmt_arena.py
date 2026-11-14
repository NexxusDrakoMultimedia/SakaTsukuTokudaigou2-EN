"""svfmt_arena.py DUMP : text runs (ascii >=4 or cp932 kana/kanji >=3 chars) inside every section of the 64KB save arena."""
import sys, struct, re
d = open(sys.argv[1], 'rb').read(); B = 0x8c000000
w = lambda a: struct.unpack_from('<I', d, a - B)[0]
gsp = w(0x8c159220)
secs = []
for o in range(0x24, 0xa0, 8):
    p = w(gsp + o); sz = w(gsp + o + 4) & 0xffff
    if 0x8ce4c000 <= p < 0x8ce5c000: secs.append((o, p, sz))
for o, p, sz in secs:
    data = d[p - B:p - B + sz]
    runs = []
    for m in re.finditer(rb'(?:[\x20-\x7e]{4,}|(?:[\x81-\x9f\xe0-\xef][\x40-\xfc]|[\xa1-\xdf]){3,})', data):
        try: runs.append((m.start(), m.group().decode('cp932')))
        except Exception: pass
    print('gsp+%03x  arena+%05x size %04x  text runs %d  first: %s' % (o, p - 0x8ce4c000, sz, len(runs), [(hex(a), t[:16]) for a, t in runs[:5]]))
