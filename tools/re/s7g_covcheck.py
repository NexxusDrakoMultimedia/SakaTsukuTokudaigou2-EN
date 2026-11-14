"""s7g_covcheck: artcoverage.resolve before (build/s7/bak/artcoverage.py.s7g_orig) and after the by-order / run-member extension.
Every sheet id that resolved before must resolve identically; reports the newly resolved ids (by source file) and the ones still unresolved."""
import os, sys, importlib.util, importlib.machinery, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
def load(n, p):
    s = importlib.util.spec_from_file_location(n, p, loader=importlib.machinery.SourceFileLoader(n, p)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
new = load('ac_new', os.path.join(ROOT, 'tools', 'artcoverage.py'))
old = load('ac_old', os.path.join(ROOT, 'build', 's7', 'bak', 'artcoverage.py.s7g_orig'))
sheet, tx = new.load_sheet(), new.load_texindex()
same = diff = newly = still = 0
bysrc = collections.Counter(); unres = collections.Counter()
ids = [i for k, i in enumerate(sorted(sheet)) if k % 12 == 0 or sheet[i]['source'].startswith('GAME/')]
for i in ids:
    try: a = old.resolve(i, sheet, tx)
    except KeyError: a = None
    try: b = new.resolve(i, sheet, tx)
    except KeyError: b = None
    if a is not None:
        if a == b: same += 1
        else: diff += 1; print('CHANGED', i, a, b)
    elif b is not None:
        newly += 1; bysrc[sheet[i]['source']] += 1
    else:
        still += 1; unres[sheet[i]['source']] += 1
print('ids checked %d of %d: unchanged %d, CHANGED %d, newly resolved %d, still unresolved %d' % (len(ids), len(sheet), same, diff, newly, still))
print('newly resolved by file:', dict(bysrc.most_common(12)))
print('still unresolved by file:', dict(unres.most_common(12)))
for i in ('34703', '34708', '34716', '34719', '34723', '00056'):
    print(i, new.resolve(i, sheet, tx))
sys.exit(1 if diff else 0)
