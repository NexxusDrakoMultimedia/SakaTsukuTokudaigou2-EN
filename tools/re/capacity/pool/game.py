"""Game-wide overflow fraction vs uniform ratio (fine grid) -> results/game_s<spread><suffix>.json
usage: SPREAD=0.5 [PAD=safe] python -I -X utf8 tools/re/capacity/pool/game.py"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim
from common import *
spread = float(os.environ.get('SPREAD', '0'))
PAD = os.environ.get('PAD', 'full')
SUF = '' if PAD == 'full' else '_' + PAD
imgs = load_all(PAD)
modes = ['a_inplace', 'b0_pool_local', 'b1_pool_cross', 'b2_pool_dup_cross']
ratios = [round(0.5 + 0.05 * i, 2) for i in range(0, 41)]
res = {}
t0 = time.time()
for r in ratios:
    res[str(r)] = {}
    for m in modes:
        tot = dict(n=0, n_over=0, bytes_over=0, en_bytes=0, mov_over=0, fix_over=0, mov_n=0, fix_n=0)
        for source, img, strs, ptrs in imgs:
            x = sim.measure(strs, r, m, spread)
            for k in tot:
                tot[k] += x[k]
        res[str(r)][m] = tot
    print(r, round(time.time() - t0), flush=True)
json.dump(res, open(os.path.join(HERE, 'results', 'game_s%g%s.json' % (spread, SUF)), 'w'))
