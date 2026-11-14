"""Statistics on sample.jsonl and extrapolation to the whole overlay DB.  Run:
python -I -X utf8 tools/re/capacity/ratio/analyze.py > tools/re/capacity/ratio/analyze_out.txt
(also writes analyze_out.json)."""
import os, sys, json, random, statistics, collections
os.chdir(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, 'tools/re/capacity/ratio')
from common import *
import importlib.util
spec = importlib.util.spec_from_file_location('bs', 'tools/re/capacity/ratio/build_sample.py')
src = open('tools/re/capacity/ratio/build_sample.py', encoding='utf8').read().replace('\nmain()\n', '\n')
bs = {}
exec(compile(src, 'bs', 'exec'), bs)
vwidth, wrap = bs['vwidth'], bs['wrap']

rows = [r for r in load() if is_ov(r)]
byid = {r['id']: r for r in rows}
sample = [json.loads(l) for l in open('tools/re/capacity/ratio/sample.jsonl', encoding='utf8')]
S = [s for s in sample if not s['skip']]
print('sample total', len(sample), 'skipped junk', len(sample) - len(S), 'used', len(S))
CATS = ['prose_meeting', 'prose_news', 'prose_event', 'prose_training', 'prose_other', 'help', 'label', 'name', 'place', 'numunit']
rnd = random.Random(7)


def pct(v, p):
    v = sorted(v)
    k = (len(v) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(v) - 1)
    return v[f] + (v[c] - v[f]) * (k - f)


for s in S:
    r = byid[s['id']]
    s['jb'] = jb(s['ja'])
    s['eb'] = eb(s['en'])
    s['fit'] = s['eb'] <= s['max_bytes']
    s['mov'] = movable(r)
    s['file'] = r['file']
    s['ratio'] = s['eb'] / s['jb']
    s['ratio_max'] = s['eb'] / s['max_bytes']
    s['jpchars'] = nchars(s['ja'])

# ------------------------------------------------------------ population
pop = {}
for c in CATS:
    P = [r for r in rows if category(r) == c]
    pop[c] = dict(n=len(P), distinct=len({r['ja'] for r in P}), jb=sum(jb(r['ja']) for r in P),
                  maxb=sum(r['max_bytes'] for r in P), jpchars=sum(nchars(r['ja']) for r in P),
                  mov_n=sum(movable(r) for r in P), mov_jb=sum(jb(r['ja']) for r in P if movable(r)),
                  mov_maxb=sum(r['max_bytes'] for r in P if movable(r)))
tot_n = sum(p['n'] for p in pop.values())
tot_jb = sum(p['jb'] for p in pop.values())
print('POPULATION (FLOW_PRG + ATFIRST overlay records): n=%d jp_bytes(incl NUL)=%d maxb=%d' % (tot_n, tot_jb, sum(p['maxb'] for p in pop.values())))

# ------------------------------------------------------------ per category
print()
print('PER CATEGORY (sample): n, JP bytes, EN bytes, sumEN/sumJP, mean(per-string), p50 p75 p90 p99 of per-string EN/JP, fit-in-slot %, fit<=JP-bytes %')
res = {}
for c in CATS:
    X = [s for s in S if s['cat'] == c]
    J = sum(s['jb'] for s in X); E = sum(s['eb'] for s in X)
    rr = [s['ratio'] for s in X]
    fit = sum(s['fit'] for s in X) / len(X)
    fitj = sum(s['eb'] <= s['jb'] for s in X) / len(X)
    # bootstrap CI of pooled ratio
    bt = []
    for _ in range(2000):
        b = [X[rnd.randrange(len(X))] for _ in X]
        bt.append(sum(s['eb'] for s in b) / sum(s['jb'] for s in b))
    res[c] = dict(n=len(X), J=J, E=E, ratio=E / J, mean=statistics.mean(rr), p50=pct(rr, 50), p75=pct(rr, 75), p90=pct(rr, 90),
                  p99=pct(rr, 99), fit=fit, fitj=fitj, lo=pct(bt, 2.5), hi=pct(bt, 97.5),
                  fit_mov=(sum(s['fit'] for s in X if s['mov']) / max(1, sum(s['mov'] for s in X)), sum(s['mov'] for s in X)),
                  fit_pin=(sum(s['fit'] for s in X if not s['mov']) / max(1, sum(not s['mov'] for s in X)), sum(not s['mov'] for s in X)),
                  p_n=pop[c]['n'])
    q = res[c]
    print('%-15s n=%3d J=%6d E=%6d ratio=%.3f [95%% CI %.3f-%.3f] mean=%.3f p50=%.2f p75=%.2f p90=%.2f p99=%.2f fit=%.1f%% fit<=JPbytes=%.1f%%  (movable n=%d fit %.0f%%; pinned n=%d fit %.0f%%)' % (
        c, q['n'], q['J'], q['E'], q['ratio'], q['lo'], q['hi'], q['mean'], q['p50'], q['p75'], q['p90'], q['p99'], 100 * fit, 100 * fitj,
        q['fit_mov'][1], 100 * q['fit_mov'][0], q['fit_pin'][1], 100 * q['fit_pin'][0]))

# ------------------------------------------------------------ overall
print()
print('OVERALL')
J = sum(s['jb'] for s in S); E = sum(s['eb'] for s in S)
print('unweighted sample (n=%d): sumEN/sumJP = %.3f, fit in own slot %.1f%%' % (len(S), E / J, 100 * sum(s['fit'] for s in S) / len(S)))
# post-stratified to population
wr = sum(pop[c]['jb'] * res[c]['ratio'] for c in CATS) / tot_jb
wfit_n = sum(pop[c]['n'] * res[c]['fit'] for c in CATS) / tot_n
wfit_b = sum(pop[c]['jb'] * sum(s['jb'] * s['fit'] for s in S if s['cat'] == c) / sum(s['jb'] for s in S if s['cat'] == c) for c in CATS) / tot_jb
wr_str = sum(pop[c]['n'] * res[c]['mean'] for c in CATS) / tot_n
print('population-weighted (post-stratified by category): sumEN/sumJP (byte-weighted) = %.3f ; mean per-string ratio (record-weighted) = %.3f' % (wr, wr_str))
print('population-weighted fit-in-own-slot: %.1f%% of records, %.1f%% of JP bytes' % (100 * wfit_n, 100 * wfit_b))
bt = []
for _ in range(1000):
    num = 0
    for c in CATS:
        X = [s for s in S if s['cat'] == c]
        b = [X[rnd.randrange(len(X))] for _ in X]
        num += pop[c]['jb'] * sum(s['eb'] for s in b) / sum(s['jb'] for s in b)
    bt.append(num / tot_jb)
print('bootstrap 95%% CI of population-weighted sumEN/sumJP: %.3f - %.3f' % (pct(bt, 2.5), pct(bt, 97.5)))
overall_ci = (pct(bt, 2.5), pct(bt, 97.5))
# 'text volume' categories only (prose + help): the part that matters for capacity
pc = ['prose_meeting', 'prose_news', 'prose_event', 'prose_training', 'prose_other', 'help']
pj = sum(pop[c]['jb'] for c in pc)
print('prose+help share of JP bytes: %.1f%%  weighted ratio %.3f' % (100 * pj / tot_jb, sum(pop[c]['jb'] * res[c]['ratio'] for c in pc) / pj))
allp = [s['ratio'] for s in S if s['cat'] in pc]
print('prose+help per-string EN/JP ratio: p50=%.2f p75=%.2f p90=%.2f p99=%.2f  max=%.2f' % tuple([pct(allp, 50), pct(allp, 75), pct(allp, 90), pct(allp, 99), max(allp)]))
allr = [s['ratio'] for s in S]
print('ALL sampled strings per-string ratio: p50=%.2f p75=%.2f p90=%.2f p99=%.2f' % (pct(allr, 50), pct(allr, 75), pct(allr, 90), pct(allr, 99)))

# ------------------------------------------------------------ grouped by overlay in the sample
print()
print('SAMPLE POOLED PER OVERLAY (files with >= 10 sampled strings): n, sumJP, sumEN, ratio, fit%')
g = collections.defaultdict(list)
for s in S:
    g[s['file'].replace('FLOW_PRG__', '').replace('ATFIRST__', 'ATFIRST/')].append(s)
for f, X in sorted(g.items(), key=lambda a: -len(a[1])):
    if len(X) < 10:
        continue
    print('%-18s n=%3d JP=%6d EN=%6d ratio=%.3f fit=%.0f%%' % (f, len(X), sum(s['jb'] for s in X), sum(s['eb'] for s in X),
                                                           sum(s['eb'] for s in X) / sum(s['jb'] for s in X), 100 * sum(s['fit'] for s in X) / len(X)))

# ------------------------------------------------------------ size-class view
print()
print('BY JP SIZE (fit rate depends on slot padding): JP bytes bucket -> n, ratio, fit%')
for lo, hi in [(0, 8), (8, 17), (17, 40), (40, 80), (80, 120), (120, 10000)]:
    X = [s for s in S if lo <= s['jb'] < hi]
    if X:
        print('  JP %3d-%-5d n=%3d sumratio=%.3f fit=%.0f%% meanpad(max-jb)=%.1f' % (lo, hi, len(X), sum(s['eb'] for s in X) / sum(s['jb'] for s in X),
                                                                                    100 * sum(s['fit'] for s in X) / len(X), statistics.mean(s['max_bytes'] - s['jb'] for s in X)))

# ------------------------------------------------------------ line feasibility
print()
print('LINE FEASIBILITY (prose + help; width 39 half-width cells; substitution tokens expanded: #sname#/#tkNN# 10, $N 6, %s 8, %d 3)')
LF = {}
for expand in (True, False):
    tot = 0; over = 0; extra = collections.Counter(); over3 = 0; jp_le3 = 0
    byc = collections.defaultdict(lambda: [0, 0])
    detail = []
    for s in S:
        if s['cat'] not in pc:
            continue
        jl = s['ja'].split(chr(10))
        while jl and jl[-1] == '':
            jl.pop()
        L = len(jl)
        el = wrap(s['en_flat'], 39, expand)
        while el and el[-1] == '':
            el.pop()
        E_ = len(el)
        tot += 1
        byc[s['cat']][0] += 1
        if E_ > L:
            over += 1; byc[s['cat']][1] += 1
        extra[E_ - L] += 1
        if L <= 3:
            jp_le3 += 1
            if E_ > 3:
                over3 += 1
        s['L'] = L; s['EL'] = E_ if expand else s.get('EL')
        detail.append((s['cat'], L, E_))
    print(' expand=%s: strings %d, English needs MORE lines than the Japanese had: %d (%.1f%%); fewer/equal: %d' % (expand, tot, over, 100 * over / tot, tot - over))
    print('   extra-lines histogram (EN lines - JP lines):', dict(sorted(extra.items())))
    print('   of %d strings with JP <=3 lines, English needs >3 lines: %d (%.1f%%)' % (jp_le3, over3, 100 * over3 / max(1, jp_le3)))
    print('   by category: ' + ', '.join('%s %d/%d (%.0f%%)' % (c, v[1], v[0], 100 * v[1] / v[0]) for c, v in byc.items()))
    LF[expand] = dict(tot=tot, over=over, extra=dict(extra), jp_le3=jp_le3, over3=over3, byc={c: v for c, v in byc.items()}, detail=detail)
# JP window use
jw = []
for s in S:
    if s['cat'] in pc:
        for ln in s['ja'].split(chr(10)):
            v = CTRL_ = visible(ln)
            if v.strip():
                w = sum(1 if (0xff61 <= ord(ch) <= 0xff9f or ord(ch) < 128) else 2 for ch in v)
                jw.append(w)
print('JP line width in half-width cells (non-empty lines of sampled prose/help): mean %.1f p50 %.0f p90 %.0f max %d (window = 39/40)' % (statistics.mean(jw), pct(jw, 50), pct(jw, 90), max(jw)))
jl_hist = collections.Counter()
for s in S:
    if s['cat'] in pc:
        jl_hist[s['L']] += 1
print('JP line-count histogram (sampled prose/help):', dict(sorted(jl_hist.items())))
# English line fill ratio: lines needed vs JP lines in terms of total chars
ec = [vwidth(s['en_flat'].replace('|', ' ')) for s in S if s['cat'] in pc]
print('English flat text width (cells) of sampled prose/help: mean %.0f p50 %.0f p90 %.0f max %d; JP total cells mean %.0f' % (
    statistics.mean(ec), pct(ec, 50), pct(ec, 90), max(ec),
    statistics.mean([sum(1 if (0xff61 <= ord(ch) <= 0xff9f or ord(ch) < 128) else 2 for ch in visible(s['ja']).replace(chr(10), '')) for s in S if s['cat'] in pc])))

# ------------------------------------------------------------ extrapolation per overlay
print()
print('EXTRAPOLATION per overlay (all records of FLOW_PRG + ATFIRST HELP/TITLE)')
ratio_c = {c: res[c]['ratio'] for c in CATS}
fitm = {c: res[c]['fit_mov'][0] if res[c]['fit_mov'][1] >= 5 else res[c]['fit'] for c in CATS}
fitp = {c: res[c]['fit_pin'][0] if res[c]['fit_pin'][1] >= 5 else res[c]['fit'] for c in CATS}
ov = collections.defaultdict(lambda: collections.defaultdict(float))
for r in rows:
    c = category(r)
    j = jb(r['ja'])
    o = ov[r['file'].replace('FLOW_PRG__', '').replace('ATFIRST__', 'ATFIRST/')]
    o['n'] += 1; o['jb'] += j; o['maxb'] += r['max_bytes']
    est = j * ratio_c[c]
    o['est'] += est
    if movable(r):
        o['mov_n'] += 1; o['mov_jb'] += j; o['mov_maxb'] += r['max_bytes']; o['mov_est'] += est
        o['fit_inplace_n'] += fitm[c]; o['fit_inplace_b'] += j * fitm[c]
    else:
        o['pin_n'] += 1; o['pin_jb'] += j; o['pin_maxb'] += r['max_bytes']; o['pin_est'] += est
        o['fit_inplace_n'] += fitp[c]; o['fit_inplace_b'] += j * fitp[c]
        o['pin_fit_n'] += fitp[c]
hdr = ['overlay', 'n', 'JPbytes', 'pool(sum max_bytes)', 'slack', 'est EN need', 'need/pool', 'movable pool', 'movable need', 'mov need/pool', 'extra bytes if repacked', 'pinned n', 'pinned fit%']
print('\t'.join(hdr))
OVR = []
for name, o in sorted(ov.items(), key=lambda a: -a[1]['jb']):
    extra = max(0, o['mov_est'] - o['mov_maxb'])
    OVR.append((name, o, extra))
for name, o, extra in OVR[:40]:
    print('%-14s n=%5d JP=%7d pool=%7d slack=%6d est=%8.0f need/pool=%.2f | mov pool=%7d need=%8.0f %.2f extra=%7.0f | pinned n=%5d fit %.0f%%' % (
        name, o['n'], o['jb'], o['maxb'], o['maxb'] - o['jb'], o['est'], o['est'] / o['maxb'], o['mov_maxb'], o['mov_est'],
        o['mov_est'] / o['mov_maxb'] if o['mov_maxb'] else 0, extra, o['pin_n'], 100 * o['pin_fit_n'] / o['pin_n'] if o['pin_n'] else 0))
T = collections.defaultdict(float)
for name, o, extra in OVR:
    for k, v in o.items():
        T[k] += v
    T['extra'] += extra
    T['ov_count'] += 1
    T['ov_over_pool'] += 1 if o['mov_est'] > o['mov_maxb'] else 0
print('ALL %d overlays: n=%d JP=%d pool=%d est EN need=%.0f (%.3f x JP, %.3f x pool); movable pool=%d movable need=%.0f; total extra bytes if every overlay repacks = %.0f ; overlays whose movable need exceeds movable pool: %d' % (
    T['ov_count'], T['n'], T['jb'], T['maxb'], T['est'], T['est'] / T['jb'], T['est'] / T['maxb'], T['mov_maxb'], T['mov_est'], T['extra'], T['ov_over_pool']))
# headline buckets
n_in = T['fit_inplace_n']
b_in = T['fit_inplace_b']
print('HEADLINE (record-weighted): fit in place %.1f%% ; JP-byte-weighted: %.1f%%' % (100 * n_in / T['n'], 100 * b_in / T['jb']))
json.dump(dict(res=res, pop=pop, overall=dict(wr=wr, wr_str=wr_str, wfit_n=wfit_n, wfit_b=wfit_b, ci=overall_ci), T=dict(T),
               ovr=[(n, dict(o), e) for n, o, e in OVR]), open('tools/re/capacity/ratio/analyze_out.json', 'w'), indent=1)
