"""ramjp2.py DUMP: NUL-bounded strong-Japanese runs (>=3 chars, >=2 kana, >=80% non-ASCII) in a RAM dump."""
import re
import sys
d = open(sys.argv[1], 'rb').read()
DB = rb'[\x81-\x84\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]'
pat = re.compile(rb'(?<![^\x00])((?:' + DB + rb'|[\x20-\x7e]|[\xa1-\xdf])+)(?=\x00)')
kana = re.compile('[぀-ヿｦ-ﾟ]')
for m in pat.finditer(d):
    try:
        s = m.group(1).decode('cp932')
    except Exception:
        continue
    nj = sum(1 for c in s if ord(c) > 0x7f)
    if len(s) < 3 or nj * 5 < len(s) * 4 or len(kana.findall(s)) < 2:
        continue
    print('%#010x %s' % (0x8C000000 + m.start(1), s))
