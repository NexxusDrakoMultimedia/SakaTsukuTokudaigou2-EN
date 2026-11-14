"""Joint capacity model (agent synth): combines the ratio agent's measured per-category EN/JP distributions
(tools/re/capacity/ratio/sample.jsonl) with the pool agent's planner (textrepack.plan_pools) over ALL 114 images,
the memmap agent's per-overlay append budgets (build/memmap/overlays.tsv) and the bank's shared region size.

  python -I -X utf8 tools/re/capacity/synth/joint.py [scale ...]        (default scales 1.0 0.85 0.80)

English length of string s (category c, JP raw length L bytes without NUL): f = quantile_c(u(raw)) * scale, where
quantile_c is the empirical per-string EN/JP ratio distribution of category c (EN and JP both incl. NUL) and u(raw) is a
hash of the JP bytes in [0,1) (equal Japanese -> equal English, like a translation memory).
en_len = max(1, round(f*(L+1)) - 1).
Layers (absorption counted in strings and in JP bytes of the strings):
  L0  fits its own slot (len+1 <= max_bytes)                                      [textdb in-place]
  L1  fits after pool repacking incl. cross-pool moves, no sharing                [textrepack share=none]
  L1s fits when identical strings additionally share one copy                     [textrepack share=dup] (UNPROVEN: read-only strings)
  rest: movable overflow (needs L2/L3) and fixed overflow (orphans/stride/interior: only L4 = shorter English)
  L2  append after the overlay behind a raised `_end`; per overlay budget = append_cons (overlays.tsv); 0 for GAME/ESTABLIS/no-slot rows
  L3  shared bank in 1ST_READ padding + FONT tail (259,771 B), deduplicated by Japanese text, strings served per byte
Order used for the movable remainder: L3 first (no heap cost), then L2.  'L2 alone' is printed as well.
"""
import sys, os, json, hashlib, collections, csv, importlib.util, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
os.chdir(ROOT)
sys.path.insert(0, 'tools')
import textdb as T
import textrepack as R


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


RC = load_mod('ratio_common', 'tools/re/capacity/ratio/common.py')
PC = load_mod('pool_common', 'tools/re/capacity/pool/common.py')
BANK = 259771
SPECIAL_NO_APPEND = ('GAME.BIN', 'ESTABLIS.BIN')


def emp_ratios():
    S = [json.loads(l) for l in open('tools/re/capacity/ratio/sample.jsonl', encoding='utf8')]
    out = collections.defaultdict(list)
    for s in S:
        if s['skip']:
            continue
        out[s['cat']].append((len(T.encode_text(s['en'])) + 1) / (len(T.encode_text(s['ja'])) + 1))
    return {k: sorted(v) for k, v in out.items()}


def quant(v, u):
    return v[min(len(v) - 1, int(u * len(v)))]


def uhash(raw):
    d = hashlib.blake2b(raw, digest_size=4, key=b'synth').digest()
    return int.from_bytes(d, 'little') / 2 ** 32


_dm = {}


def dummy(raw, n):
    k = (raw, n)
    v = _dm.get(k)
    if v is None:
        base = hashlib.blake2b(raw, digest_size=64).hexdigest().encode()
        v = _dm[k] = (base * (n // len(base) + 1))[:n]
    return v


def budgets():
    b = {}
    with open('build/memmap/overlays.tsv', encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            b[r['dir'] + '/' + r['overlay']] = r
    return b


def main():
    scales = [float(x) for x in sys.argv[1:]] or [1.0, 0.85, 0.80]
    t0 = time.time()
    emp = emp_ratios()
    rows = [r for r in RC.load() if RC.is_ov(r)]
    catof = {r['id']: RC.category(r) for r in rows}
    print('records (overlay sources)', len(rows), 'categories', dict(collections.Counter(catof.values())))
    print('empirical ratio samples per category', {k: len(v) for k, v in emp.items()})
    imgs = PC.load_all('full')
    print('images', len(imgs), 'load %.0fs' % (time.time() - t0))
    bud = budgets()
    print('total strings %d, JP bytes incl NUL %d' % (sum(len(s) for _, _, s, _ in imgs),
                                                      sum(len(x.raw) + 1 for _, _, s, _ in imgs for x in s)))
    pct = lambda a, b: 100.0 * a / b
    for scale in scales:
        print('\n=========== scale %.2f ===========' % scale)
        agg = collections.Counter()
        per_ov = []
        pool_mov = {}
        for source, img, strs, ptrs in imgs:
            enc = {}
            for s in strs:
                cat = catof.get('%s#%x' % (source, s.off), 'label')
                f = quant(emp[cat], uhash(s.raw)) * scale
                n = max(1, int(round(f * (len(s.raw) + 1))) - 1)
                enc[s.off] = dummy(s.raw, n)
            en_total = sum(len(b) + 1 for b in enc.values())
            l0set = {s.off for s in strs if len(enc[s.off]) + 1 <= s.max_bytes}
            jp = {s.off: len(s.raw) + 1 for s in strs}
            raw = {s.off: s.raw for s in strs}
            res = {}
            for tag, share in (('l1', 'none'), ('l1s', 'dup')):
                pl = R.plan_pools(strs, enc, share=share, cross_pool=True)
                res[tag] = ({s.off: len(b) + 1 for s, b in pl.reverted}, {s.off: len(b) + 1 for s, b in pl.fixed_overflow})
            agg['n'] += len(strs)
            agg['jp'] += sum(jp.values())
            agg['en'] += en_total
            agg['l0_n'] += len(l0set)
            agg['l0_jp'] += sum(jp[o] for o in l0set)
            for tag in ('l1', 'l1s'):
                rev, fx = res[tag]
                ok = [s.off for s in strs if s.off not in rev and s.off not in fx]
                agg[tag + '_ok_n'] += len(ok)
                agg[tag + '_ok_jp'] += sum(jp[o] for o in ok)
                agg[tag + '_rev_n'] += len(rev)
                agg[tag + '_rev_en'] += sum(rev.values())
                agg[tag + '_fix_n'] += len(fx)
                agg[tag + '_fix_en'] += sum(fx.values())
            r1, f1 = res['l1']
            r2, f2 = res['l1s']
            per_ov.append((source, len(strs), sum(jp.values()), en_total, len(r1), sum(r1.values()), len(f1), sum(f1.values()),
                           len(r2), sum(r2.values()), len(f2), sum(f2.values())))
            pool_mov[source] = {t: [(raw[o], r[o], jp[o]) for o in r] for t, r in (('l1', r1), ('l1s', r2))}
        print('EN bytes %d = %.3f x JP' % (agg['en'], agg['en'] / agg['jp']))
        print('L0 fits own slot            : %6d strings %5.1f %% | JP bytes %5.1f %%' % (
            agg['l0_n'], pct(agg['l0_n'], agg['n']), pct(agg['l0_jp'], agg['jp'])))
        for tag, lab in (('l1', 'L0+L1 pool repack+cross  '), ('l1s', 'L0+L1+L1s +dup sharing   ')):
            print('%s: %6d strings %5.1f %% | JP bytes %5.1f %% ; left: movable %d str (%d EN B), fixed %d str (%d EN B, %.1f %% of strings)' % (
                lab, agg[tag + '_ok_n'], pct(agg[tag + '_ok_n'], agg['n']), pct(agg[tag + '_ok_jp'], agg['jp']),
                agg[tag + '_rev_n'], agg[tag + '_rev_en'], agg[tag + '_fix_n'], agg[tag + '_fix_en'], pct(agg[tag + '_fix_n'], agg['n'])))
        for tag in ('l1', 'l1s'):
            uniq = collections.defaultdict(lambda: [0, 0, 0])
            for source, d in pool_mov.items():
                for raw_, enb, jpb in d[tag]:
                    u = uniq[raw_]
                    u[0] = max(u[0], enb); u[1] += 1; u[2] = jpb
            order = sorted(uniq.items(), key=lambda kv: (-kv[1][1] / kv[1][0], kv[0]))
            used = 0; served = set(); bank_n = 0
            for raw_, (enb, cnt, jpb) in order:
                if used + enb <= BANK:
                    used += enb; served.add(raw_); bank_n += cnt
            l2_n = l2_b = left_n = left_b = 0
            l2o_n = l2o_b = 0
            short = []
            for source, d in pool_mov.items():
                row = bud.get(source)
                cons = int(row['append_cons']) if (row and row['append_cons'] and not source.endswith(SPECIAL_NO_APPEND)) else 0
                rest = [x for x in d[tag] if x[0] not in served]
                for lst, mode in ((d[tag], 'only'), (rest, 'after')):
                    room = cons
                    gn = gb = 0
                    for raw_, enb, jpb in sorted(lst, key=lambda x: x[1]):
                        if enb <= room:
                            room -= enb; gn += 1; gb += enb
                    if mode == 'only':
                        l2o_n += gn; l2o_b += gb
                    else:
                        l2_n += gn; l2_b += gb
                        left_n += len(rest) - gn
                        left_b += sum(x[1] for x in rest) - gb
                        if len(rest) - gn:
                            short.append((sum(x[1] for x in rest) - gb, source, cons))
            print('  [%s] movable remainder %d str / %d EN B: L3 bank (%d of %d B, %d unique JP texts) absorbs %d str (%.1f %% of all); '
                  'L2 then absorbs %d str (%d EN B); unhoused %d movable str (%d EN B, %.2f %% of all strings) -> L4' % (
                      tag, agg[tag + '_rev_n'], agg[tag + '_rev_en'], used, BANK, len(served), bank_n, pct(bank_n, agg['n']),
                      l2_n, l2_b, left_n, left_b, pct(left_n, agg['n'])))
            print('  [%s] L2 alone (no bank): %d str (%d EN B)' % (tag, l2o_n, l2o_b))
            short.sort(reverse=True)
            print('  [%s] overlays still short after L3+L2 (unhoused EN B, cons budget): %s' % (
                tag, ', '.join('%s %d (cons %d)' % (s.split('/')[-1][:-4], b, c) for b, s, c in short[:12])))
        print('  biggest L1 deficits (n, JP B, EN B | l1 movable str/EN B, fixed str/EN B | l1s movable, fixed)')
        for r in sorted(per_ov, key=lambda r: -(r[5] + r[7]))[:14]:
            print('   %-26s n=%5d JP=%7d EN=%7d | mov %4d/%6d fix %4d/%6d | mov %4d/%6d fix %4d/%6d' % r)
    print('done %.0fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
