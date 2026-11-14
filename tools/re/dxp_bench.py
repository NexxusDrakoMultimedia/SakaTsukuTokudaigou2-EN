"""Read-only: benchmark discbuild.encode_sector (pure python) -> time to regenerate all raw sectors. usage: dxp_bench.py"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import discbuild as D
import random
random.seed(1)
u = [bytes(random.getrandbits(8) for _ in range(2048)) for _ in range(20)]
N = 3000
t = time.time()
for i in range(N):
    D.encode_sector(60000 + i, u[i % 20])
dt = time.time() - t
print('%.1f us/sector -> %.0f s for 504150 sectors' % (dt / N * 1e6, dt / N * 504150))
