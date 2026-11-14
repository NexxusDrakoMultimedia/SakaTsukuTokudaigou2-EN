"""find raw byte pattern (text, cp932) in a file: hnm_grep.py FILE TEXT"""
import sys
d = open(sys.argv[1], 'rb').read()
p = sys.argv[2].encode('cp932')
i = d.find(p)
while i >= 0:
    print(hex(i), d[max(0, i - 8):i + len(p) + 8])
    i = d.find(p, i + 1)
