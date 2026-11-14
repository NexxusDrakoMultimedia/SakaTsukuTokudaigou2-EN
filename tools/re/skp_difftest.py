"""skp (skeptic): differential test of --align-fix on REAL strings, in the REAL layout function (tools/sh4sim.py).

For every string the layout (pen after each code, y after each code) is run with and without the align cave:
  * a string WITHOUT a run of 2+ blanks followed by a glyph must lay out identically (no regression for names, titles, bubbles, money text);
  * a string WITH such a run is listed (before / after pen at the end, and the largest per-code difference).
Strings come from translation/*.jsonl `en` (format tokens replaced by sample values), plus synthetic ones (wide letters, long prose, money forms).

    python -I -X utf8 tools/re/skp_difftest.py [OVERLAY=MEETING] [N=400] [W=26]
"""
import glob, json, os, random, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import test_alignfix as T

ov = sys.argv[1] if len(sys.argv) > 1 else 'MEETING'
N = int(sys.argv[2]) if len(sys.argv) > 2 else 400
W = int(sys.argv[3]) if len(sys.argv) > 3 else 26
rel = 'FLOW_PRG/%s.BIN' % ov
out, rep, ctl = T.built() if ov in ('PLNUMSET', 'MEETING') else (None, None, None)
if out is None:
    import fontpatch as FP
    out, rep = FP.make_patches(FP.read_extracted, paths=[rel], align_fix=True)
    ctl, _ = FP.make_patches(FP.read_extracted, paths=[rel], align_fix=False)
    T._cache['b'] = (out, rep, ctl)
_, h1 = T.h1_of(rel)
tbl = rep['table']
exa, nata = T.caves(tbl, True)
exc, natc = T.caves(tbl, False)

root = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'translation')
pool = []
for f in sorted(glob.glob(os.path.join(root, '*.jsonl'))):
    if 'GAME.BIN' in f or 'NEWS' in f:
        continue
    for line in open(f, encoding='utf-8'):
        try:
            r = json.loads(line)
        except Exception:
            continue
        en = r.get('en')
        if not en or len(en) > 120:
            continue
        s = re.sub(r'<br>|\n', '\n', en)
        s = re.sub(r'<[^>]+>', '', s)
        s = s.replace('%2d', '12').replace('%d', '1234').replace('%s', 'Name').replace('%4d', '2026').replace('%f', '1.5')
        if re.search(r'[^\x20-\x7e\n]', s):
            continue
        pool.append(s)
random.seed(7)
random.shuffle(pool)
runs = [s for s in pool if re.search(r'\S {2,}\S', s)]
plain = [s for s in pool if not re.search(r'\S {2,}\S', s)]
synth = ['WWWW MMMM iiii llll', 'The goalkeeper is injured and cannot play in the next match, so please choose another player now.',
         '3 oku 9000 man', '   3 man', '  58 man', '12 oku 3400 man bonus', 'Mwamba Njoroge   12', 'AAAAAAAAAAAA  7', 'Hello,  World', 'a  b']
sample = synth + plain[:N] + runs[:150]
print('overlay %s: %d strings (%d plain, %d with blank runs in the sample)' % (ov, len(sample), min(N, len(plain)), min(150, len(runs))))


def lay(s, align):
    ex, nat = (exa, nata) if align else (exc, natc)
    lines = s.split('\n')
    res = []
    for ln in lines:
        codes = T.codes_of(ln)
        if not codes:
            continue
        res.append(T.run_layout((out if align else ctl)['/' + rel], h1, codes, W=W, A=24, flag=1, x0=40, extra=ex, native=nat))
    return res


bad = 0
changed = []
for s in sample:
    a, b = lay(s, True), lay(s, False)
    hasrun = re.search(r'\S {2,}\S', s) is not None
    if a == b:
        continue
    if not hasrun:
        bad += 1
        print('REGRESSION (no blank run) %r' % s)
        continue
    d = 0
    for la, lb in zip(a, b):
        for x, y in zip(la, lb):
            d = max(d, abs(x[0] - y[0]))
    changed.append((s, d, a[-1][-1][0] if a and a[-1] else None, b[-1][-1][0] if b and b[-1] else None))
print('plain strings that changed: %d' % bad)
print('strings with a blank run that changed: %d' % len(changed))
for s, d, pa, pb in changed[:40]:
    print('  maxdiff %3d  end with %s / without %s  %r' % (d, pa, pb, s[:70]))
