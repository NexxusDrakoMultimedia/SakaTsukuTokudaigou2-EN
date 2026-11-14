"""Heuristic SH-4 function start finder in 1ST_READ.BIN: prints addresses of 'sts.l pr,@-r15' (0x4f22) prologues
and 'rts' (0x000b) in a range.  usage: fnstarts.py lo hi (hex addresses)"""
import sys, os, struct
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
data = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
BASE = 0x8c010000
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
for a in range(lo, hi, 2):
    w = struct.unpack_from('<H', data, a - BASE)[0]
    if w == 0x4f22:
        # walk back over pushes (2fN6 = mov.l rN,@-r15 : 0x2FN6)
        s = a
        while True:
            pw = struct.unpack_from('<H', data, s - 2 - BASE)[0]
            if (pw & 0xff0f) == 0x2f06:
                s -= 2
            else:
                break
        print('prologue %08x (sts.l pr at %08x)' % (s, a))
    elif w == 0x000b:
        print('   rts    %08x' % a)
