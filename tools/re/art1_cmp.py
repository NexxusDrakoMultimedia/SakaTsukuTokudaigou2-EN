"""art1_cmp - size + diff count of two files. python -I -X utf8 tools/re/art1_cmp.py A B"""
import sys
a = open(sys.argv[1], 'rb').read(); b = open(sys.argv[2], 'rb').read()
n = min(len(a), len(b)); d = [i for i in range(n) if a[i] != b[i]]
print(len(a), len(b), len(d), d[:5], d[-3:])
