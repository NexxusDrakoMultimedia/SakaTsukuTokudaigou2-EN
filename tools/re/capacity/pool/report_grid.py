"""Aggregate results/grid_s*.json -> game-wide table and per-overlay table (results/grid_s*.tsv)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
for sp in ('0', '0.5'):
    p = os.path.join(HERE, 'results', 'grid_s%s.json' % sp)
    d = json.load(open(p))
    modes = list(next(iter(d.values())).keys())
    ratios = list(next(iter(d.values()))[modes[0]].keys())
    print('=== spread', sp, ': GAME TOTAL (sum over %d images): overflowing strings %% / overflowing English bytes %% (of all English bytes), movable-only strings overflow %%' % len(d))
    print('%-20s' % 'mode' + ''.join('%22s' % ('r=' + r) for r in ratios))
    for m in modes:
        line = '%-20s' % m
        for r in ratios:
            n = sum(v[m][r]['n'] for v in d.values()); no = sum(v[m][r]['n_over'] for v in d.values())
            eb = sum(v[m][r]['en_bytes'] for v in d.values()); bo = sum(v[m][r]['bytes_over'] for v in d.values())
            line += '%22s' % ('%.1f%% / %.1f%%' % (100 * no / n, 100 * bo / eb))
        print(line)
    print('  split at each ratio (b2): movable overflow / movable n ; fixed overflow / fixed n')
    for m in ('a_inplace', 'b2_pool_dup_cross'):
        for r in ratios:
            mo = sum(v[m][r]['mov_over'] for v in d.values()); mn = sum(v[m][r]['mov_n'] for v in d.values())
            fo = sum(v[m][r]['fix_over'] for v in d.values()); fn = sum(v[m][r]['fix_n'] for v in d.values())
            print('   %-18s r=%-4s mov %d/%d (%.1f%%)  fixed %d/%d (%.1f%%)' % (m, r, mo, mn, 100 * mo / mn, fo, fn, 100 * fo / fn))
    with open(os.path.join(HERE, 'results', 'grid_s%s.tsv' % sp), 'w') as f:
        f.write('image\tmode\t' + '\t'.join('n_over@%s\tbytes_over@%s' % (r, r) for r in ratios) + '\tn\ten_bytes@1.0\n')
        for s, v in sorted(d.items()):
            for m in modes:
                f.write('%s\t%s\t' % (s, m) + '\t'.join('%.4f\t%.4f' % (v[m][r]['n_over'] / max(1, v[m][r]['n']),
                        v[m][r]['bytes_over'] / max(1, v[m][r]['en_bytes'])) for r in ratios) +
                        '\t%d\t%d\n' % (v[m][ratios[0]]['n'], v[m]['1.0']['en_bytes']))
