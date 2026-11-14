"""Per-overlay threshold table (results/thresh_table.tsv) + game-wide thresholds from results/game_*.json"""
import json, os, sys, statistics
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, 'results')
pools = json.load(open(os.path.join(R, 'pools.json')))
T0 = json.load(open(os.path.join(R, 'thresh_s0.json')))
T5 = json.load(open(os.path.join(R, 'thresh_s0.5.json')))
rows = []
hdr = ['image', 'strings', 'movable', 'fixed', 'pools', 'pool_cap', 'mov_jp', 'slack_pct', 'dup_pool_pct', 'dup_img_pct',
       'A0', 'B0local', 'B0cross', 'B0dup', 'A5', 'B5local', 'B5cross', 'B5dup', 'B5dup_p5', 'A5_p5']
for s, p in sorted(pools.items()):
    if p['movable'] == 0:
        continue
    t0, t5 = T0[s], T5[s]
    rows.append([s, p['strings'], p['movable'], p['fixed'], p['pools'], p['pool_cap'], p['mov_jp'],
                 round(100 * p['pool_slack'] / p['pool_cap'], 2), round(100 * p['dup_pool_bytes'] / p['mov_jp'], 1),
                 round(100 * p['dup_img_bytes'] / p['mov_jp'], 1),
                 t0['a_inplace']['mov']['zero'], t0['b0_pool_local']['mov']['zero'], t0['b1_pool_cross']['mov']['zero'], t0['b2_pool_dup_cross']['mov']['zero'],
                 t5['a_inplace']['mov']['zero'], t5['b0_pool_local']['mov']['zero'], t5['b1_pool_cross']['mov']['zero'], t5['b2_pool_dup_cross']['mov']['zero'],
                 t5['b2_pool_dup_cross']['mov']['p5'], t5['a_inplace']['mov']['p5']])
with open(os.path.join(R, 'thresh_table.tsv'), 'w') as f:
    f.write('\t'.join(hdr) + '\n')
    for r in rows:
        f.write('\t'.join(str(x) for x in r) + '\n')
print('legend: A=per-string in place, B0/B1/B2 = pool-local / +cross-pool / +dup sharing; suffix 0 = uniform ratio, 5 = spread 0.5;')
print('values = largest uniform EN/JP byte ratio with ZERO overflow among movable strings (step 0.005); p5 = ratio where overflowing English bytes reach 5 %')
print('%-18s %6s %5s %9s %6s %6s | %5s %5s %5s %5s | %5s %5s %5s %5s | %5s %5s' % (
    'image', 'strs', 'pools', 'pool_cap', 'slack%', 'dup%', 'A0', 'B0l', 'B0x', 'B0d', 'A5', 'B5l', 'B5x', 'B5d', 'B5d.p5', 'A5.p5'))
big = sorted(rows, key=lambda r: -r[6])
for r in big[:30]:
    print('%-18s %6d %5d %9d %6.2f %6.1f | %5.3f %5.3f %5.3f %5.3f | %5.3f %5.3f %5.3f %5.3f | %5.3f %5.3f' % (
        r[0][9:], r[2], r[4], r[5], r[7], r[8], *r[10:]))
print('... %d images with movable strings' % len(rows))
for col, name in ((10, 'A0'), (11, 'B0local'), (12, 'B0cross'), (13, 'B0dup'), (14, 'A5'), (17, 'B5dup'), (18, 'B5dup p5')):
    v = [r[col] for r in rows]
    w = [r[6] for r in rows]
    print('%-9s min %.3f  median %.3f  max %.3f   JP-byte-weighted mean %.3f   images with value<=1.0: %d / %d' % (
        name, min(v), statistics.median(v), max(v), sum(a * b for a, b in zip(v, w)) / sum(w), sum(1 for x in v if x <= 1.0), len(v)))
for fn in sorted(os.listdir(R)):
    if fn.startswith('game_') and fn.endswith('.json'):
        g = json.load(open(os.path.join(R, fn)))
        print('--- game-wide thresholds (%s): ratio at which overflowing English bytes first exceed X %% of all English bytes' % fn)
        for m in next(iter(g.values())):
            out = []
            for x in (0.0, 0.01, 0.05, 0.25, 0.5):
                rr = None
                for r in sorted(g, key=float):
                    t = g[r][m]
                    if t['bytes_over'] / t['en_bytes'] > x:
                        rr = r; break
                out.append('>%g%%: r=%s' % (100 * x, rr))
            nn = None
            for r in sorted(g, key=float):
                t = g[r][m]
                if t['n_over'] / t['n'] > 0.05:
                    nn = r; break
            print('  %-18s %s ; strings overflow >5%% at r=%s' % (m, ' | '.join(out), nn))
