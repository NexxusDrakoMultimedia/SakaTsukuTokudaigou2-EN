"""ctx.py FILE HEXOFF [BEFORE AFTER]: print bytes around an offset decoded as cp932 with NUL shown as |"""
import sys
d = open(sys.argv[1], 'rb').read()
o = int(sys.argv[2], 16)
b = int(sys.argv[3]) if len(sys.argv) > 3 else 40
a = int(sys.argv[4]) if len(sys.argv) > 4 else 80
print(d[max(0, o - b):o + a].decode('cp932', 'replace').replace('\x00', '|').replace('\n', '~'))
