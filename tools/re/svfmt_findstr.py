"""svfmt_findstr.py DUMP TEXT : addresses of TEXT (ascii or cp932) in a RAM dump."""
import sys
d = open(sys.argv[1], 'rb').read(); t = sys.argv[2].encode('cp932'); i = d.find(t)
while i >= 0:
    print(hex(0x8c000000 + i)); i = d.find(t, i + 1)
