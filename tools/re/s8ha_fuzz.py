"""s8ha: fuzz the align cave in the real layout function: random code arrays (blanks, runs, newlines, controls, full-width, glyphs), the window's
code count (+0x22) different from the revealed count (+0x2c), random W, A in {24, 16, 32}; step-limit / simulator errors are reported.
usage: s8ha_fuzz.py [N=300] [SEED=1]"""
import random
import sys
import os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import test_alignfix as T
import sh4sim

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
out, rep, ctl = T.built()
rel = 'FLOW_PRG/MEETING.BIN'
_, h1 = T.h1_of(rel)
exa, nata = T.caves(T.table(), True)
exc, natc = T.caves(T.table(), False)
ALPHA = [0x2020] * 6 + [0x8000 | ord(c) for c in 'abcWiM.,1'] + [0x200A, 0x2012, 0x2001, 0x0123, 0x0124, 0xC0A1]
bad = 0
for k in range(N):
    n = random.randint(0, 60)
    codes = [random.choice(ALPHA) for _ in range(n)]
    W = random.choice([10, 20, 26, 40])
    A = random.choice([24, 24, 24, 16, 32])
    try:
        n22 = random.choice([None, 0, 1, 7, 200, 0x7fff, 0xffff, 0x8000]); a = T.run_layout(out['/' + rel], h1, codes, W=W, A=A, extra=exa, native=nata, n22=n22)
        b = T.run_layout(ctl['/' + rel], h1, codes, W=W, A=A, extra=exc, native=natc)
    except sh4sim.SimError as e:
        bad += 1
        print('SIMERROR', e, [hex(c) for c in codes], W, A)
        continue
    if len(a) != len(b):
        bad += 1
        print('LENGTH', len(a), len(b))
print('done', N, 'bad', bad)
