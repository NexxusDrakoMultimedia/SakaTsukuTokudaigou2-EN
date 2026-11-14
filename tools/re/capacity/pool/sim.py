"""Synthetic English at JP-length ratios: capacity simulation of per-string in-place vs pool repacking.
usage: python -I -X utf8 tools/re/capacity/pool/sim.py grid|thresh|textdb  [--only NAME..]
Dummy English for a string of raw JP length L (bytes, without NUL) at ratio r: max(1, round(r*L)) ASCII
chars derived from a hash of the JP bytes (equal ja -> equal en, different ja -> different en)."""
import hashlib, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import textrepack as R

_memo = {}
def dummy(raw, n):
    k = (raw, n)
    v = _memo.get(k)
    if v is None:
        base = _memo.get(raw)
        if base is None:
            base = _memo[raw] = hashlib.blake2b(raw, digest_size=64).hexdigest().encode()
        v = (base * (n // len(base) + 1))[:n]
        if len(_memo) > 3000000:
            _memo.clear()
        _memo[k] = v
    return v

def enc_for(strs, r, spread=0.0):
    """spread d: per-string ratio r*(1 + d*(2u-1)) with u in [0,1) from a hash of the JP bytes (mean r)"""
    out = {}
    for s in strs:
        f = r
        if spread:
            u = hashlib.blake2b(s.raw, digest_size=2, key=b'u').digest()
            f = r * (1 + spread * ((u[0] * 256 + u[1]) / 32768.0 - 1))
        out[s.off] = dummy(s.raw, max(1, int(f * len(s.raw) + 0.5)))
    return out

_IMG = [None]
MODES = ['a_inplace', 'a2_textdb', 'b0_pool_local', 'b1_pool_cross', 'b2_pool_dup_cross']

def measure(strs, r, mode, spread=0.0):
    """-> dict(n, n_over, bytes_over, deficit, mov_over, fix_over, mov_n, fix_n, en_bytes)"""
    enc = enc_for(strs, r, spread)
    en_bytes = sum(len(b) + 1 for b in enc.values())
    mov = [s for s in strs if R.is_movable(s)]
    out = dict(n=len(strs), mov_n=len(mov), fix_n=len(strs) - len(mov), en_bytes=en_bytes,
               n_over=0, mov_over=0, fix_over=0, bytes_over=0, deficit=0)
    if mode == 'a_inplace':
        for s in strs:
            need = len(enc[s.off]) + 1
            if need > s.max_bytes:
                out['n_over'] += 1
                out['mov_over' if R.is_movable(s) else 'fix_over'] += 1
                out['bytes_over'] += need
                out['deficit'] += need - s.max_bytes
        return out
    if mode == 'a2_textdb':
        # the existing pipeline: in place where it fits, else relocation into pooled freed regions
        # (textdb.insert_image strategy A/B).  Needs an Image + recs; image passed via global.
        img = _IMG[0]
        recs = [{'id': '%s#%x' % (img.source, s.off), 'ja': T.decode_text(s.raw), 'en': enc[s.off].decode()} for s in strs]
        new, rep = T.insert_image(img, recs, extracted=(strs, None, None))
        byoff = {s.off: s for s in strs}
        for fid, need, why in rep.failed:
            s = byoff[int(fid.rsplit('#', 1)[1], 16)]
            out['n_over'] += 1
            out['mov_over' if R.is_movable(s) else 'fix_over'] += 1
            out['bytes_over'] += need
            out['deficit'] += need - s.max_bytes
        return out
    share = 'dup' if mode == 'b2_pool_dup_cross' else 'none'
    cross = mode != 'b0_pool_local'
    pl = R.plan_pools(strs, enc, share=share, cross_pool=cross)
    for s, b in pl.reverted:
        out['n_over'] += 1; out['mov_over'] += 1; out['bytes_over'] += len(b) + 1
        out['deficit'] += len(b) + 1 - (len(s.raw) + 1)
    for s, b in pl.fixed_overflow:
        out['n_over'] += 1; out['fix_over'] += 1; out['bytes_over'] += len(b) + 1
        out['deficit'] += len(b) + 1 - s.max_bytes
    return out

def thresholds(strs, mode, which, spread=0.0):
    """largest r (step 0.005) with zero overflow among 'mov' (movable strings only) or 'all'; plus r where
    overflowing English bytes first exceed 1 % / 5 % of all English bytes."""
    def f(r):
        m = measure(strs, r, mode, spread)
        return m['mov_over'] if which == 'mov' else m['n_over'], m['bytes_over'] / max(1, m['en_bytes'])
    res = {}
    for name, pred in (('zero', lambda c, fr: c == 0), ('p1', lambda c, fr: fr < 0.01), ('p5', lambda c, fr: fr < 0.05)):
        lo, hi = 0.3, 4.0
        if not pred(*f(lo)):
            res[name] = 0.3; continue
        if pred(*f(hi)):
            res[name] = 4.0; continue
        while hi - lo > 0.005:
            mid = (lo + hi) / 2
            if pred(*f(mid)):
                lo = mid
            else:
                hi = mid
        res[name] = round(lo, 3)
    return res

if __name__ == '__main__':
    what = sys.argv[1]
    only = None
    if '--only' in sys.argv:
        only = sys.argv[sys.argv.index('--only') + 1:]
    PAD = os.environ.get('PAD', 'full')
    SUF = '' if PAD == 'full' else '_' + PAD
    if os.environ.get('SKIP_A2'):
        MODES.remove('a2_textdb')
    imgs = [x for x in load_all(PAD) if not only or any(o in x[0] for o in only)]
    outdir = os.path.join(HERE, 'results'); os.makedirs(outdir, exist_ok=True)
    t0 = time.time()
    if what == 'grid':
        ratios = [0.8, 1.0, 1.2, 1.5, 2.0]
        spread = float(os.environ.get('SPREAD', '0'))
        res = {}
        for source, img, strs, ptrs in imgs:
            _IMG[0] = img
            res[source] = {m: {str(r): measure(strs, r, m, spread) for r in ratios} for m in MODES}
            print(source, round(time.time() - t0), flush=True)
        json.dump(res, open(os.path.join(outdir, 'grid_s%g%s.json' % (spread, SUF)), 'w'), indent=0)
    elif what == 'thresh':
        spread = float(os.environ.get('SPREAD', '0'))
        res = {}
        for source, img, strs, ptrs in imgs:
            _IMG[0] = img
            res[source] = {m: {w: thresholds(strs, m, w, spread) for w in ('mov', 'all')} for m in MODES if m != 'a2_textdb'}
            print(source, res[source]['b2_pool_dup_cross']['mov'], round(time.time() - t0), flush=True)
        json.dump(res, open(os.path.join(outdir, 'thresh_s%g%s.json' % (spread, SUF)), 'w'), indent=0)
    print('done', time.time() - t0)
