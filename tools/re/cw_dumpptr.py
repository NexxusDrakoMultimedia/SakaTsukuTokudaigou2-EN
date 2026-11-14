"""Dump 32-bit LE words at file offsets. usage: cw_dumpptr.py FILE START COUNT [base=8c2d0000]"""
import sys, struct
d = open(sys.argv[1], 'rb').read(); s = int(sys.argv[2], 16); n = int(sys.argv[3])
base = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x8c2d0000
for i in range(n):
    v = struct.unpack_from('<I', d, s + 4*i)[0]
    print('%x  %08x  -> file %x' % (s + 4*i, v, v - base))
