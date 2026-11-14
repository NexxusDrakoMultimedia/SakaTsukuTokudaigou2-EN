"""Compare regenerated refit overlays (build/cw/refit_new) with translation/refit: which records differ, by class.
usage: python -I -X utf8 tools/re/cw_refitdiff.py [--install]   (--install: copy ONLY the club-class differences into translation/refit)"""
import collections, glob, json, os, shutil, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
NEW, OLD = 'build/cw/refit_new', 'translation/refit'
BAK = 'build/cw/db_bak/refit'
inst = '--install' in sys.argv


def load(p):
    d = {}
    if os.path.exists(p):
        for l in open(p, encoding='utf8'):
            if l.strip():
                r = json.loads(l); d[r['id']] = (l.rstrip('\n'), r)
    return d


diff = collections.Counter(); sample = {}
names = sorted({os.path.basename(p) for p in glob.glob(NEW + '/*.jsonl')} | {os.path.basename(p) for p in glob.glob(OLD + '/*.jsonl')})
for n in names:
    a, b = load(os.path.join(OLD, n)), load(os.path.join(NEW, n))
    for i in set(a) | set(b):
        ra, rb = a.get(i), b.get(i)
        if ra and rb and ra[0] == rb[0]:
            continue
        cls = (rb or ra)[1].get('cls')
        kind = 'added' if not ra else 'removed' if not rb else 'changed'
        diff[(cls, kind)] += 1
        sample.setdefault((cls, kind), (n, i, ra and ra[1]['en'], rb and rb[1]['en']))
print(dict(diff)); print(sample)
if inst:
    os.makedirs(BAK, exist_ok=True)
    for n in names:
        a, b = load(os.path.join(OLD, n)), load(os.path.join(NEW, n))
        ids = {i for i in set(a) | set(b) if (a.get(i) and a[i][1].get('cls') == 'club') or (b.get(i) and b[i][1].get('cls') == 'club')}
        if not any((a.get(i) and a[i][0]) != (b.get(i) and b[i][0]) for i in ids):
            continue
        op = os.path.join(OLD, n)
        if os.path.exists(op):
            shutil.copy2(op, os.path.join(BAK, n + '.orig'))
        out = []
        old_lines = [json.loads(l) for l in open(op, encoding='utf8') if l.strip()] if os.path.exists(op) else []
        keep = [(l[1] if False else r) for r in old_lines if r['id'] not in ids]
        # preserve original order and text of non-club lines
        text = [l.rstrip('\n') for l in open(op, encoding='utf8') if l.strip() and json.loads(l)['id'] not in ids] if os.path.exists(op) else []
        text += [b[i][0] for i in sorted(ids) if i in b]
        text.sort(key=lambda l: json.loads(l)['id'])
        tmp = op + '.cwtmp'
        with open(tmp, 'w', encoding='utf8', newline='') as fh:
            fh.write('\n'.join(text) + ('\n' if text else ''))
        os.replace(tmp, op)
        if not text:
            os.remove(op)
        print('installed', n, len(ids))
