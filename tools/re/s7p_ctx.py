"""s7p_ctx FILE OFFSET [BEFORE AFTER] - print printable strings around an offset of an extracted overlay."""
import sys, re, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
f = os.path.join(ROOT, 'extracted', sys.argv[1])
off = int(sys.argv[2], 0)
b = int(sys.argv[3]) if len(sys.argv) > 3 else 400
a = int(sys.argv[4]) if len(sys.argv) > 4 else 400
d = open(f, 'rb').read()
seg = d[max(0, off - b):off + a]
for m in re.finditer(rb'[\x20-\x7e]{4,}', seg):
    print('%#x %s' % (max(0, off - b) + m.start(), m.group().decode()))
