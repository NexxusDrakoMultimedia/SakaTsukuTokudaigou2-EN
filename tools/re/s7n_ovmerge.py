"""s7n: merge ONLY my overlay records from a scratch rfit_gen run into translation/refit (the other owners' / the generator's other
records stay as they are).

usage: s7n_ovmerge.py SCRATCH_DIR [--apply]
My ja set = the `ja` of every forms.tsv line that is new / changed / removed against build/s7/bak/forms.tsv.orig.
For those ja: records of translation/refit/*.jsonl are replaced by the records of SCRATCH_DIR (same id: new form; ids that the
scratch run did not place: dropped, i.e. the DB short form stays).  Prints a summary and writes build/s7/n/ovmerge_report.tsv.
Per-file backup of every touched overlay file to build/s7/bak/s7n/refit/.
"""
import glob
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REF = os.path.join(ROOT, 'translation', 'refit')
ORIG = os.path.join(ROOT, 'build', 's7', 'bak', 'forms.tsv.orig')
BAK = os.path.join(ROOT, 'build', 's7', 'bak', 's7n', 'refit')
NL = chr(10)
T = chr(9)


def forms_lines(p):
    return {ln for ln in open(p, encoding='utf8').read().split(NL) if ln and not ln.startswith('#')}


def my_ja():
    a, b = forms_lines(ORIG), forms_lines(os.path.join(REF, 'forms.tsv'))
    return {ln.split(T)[1] for ln in (a ^ b) if len(ln.split(T)) > 2}


def load(d):
    out = {}
    for p in glob.glob(os.path.join(d, '*.jsonl')):
        rows = []
        for ln in open(p, encoding='utf8'):
            if ln.strip():
                rows.append(json.loads(ln))
        out[os.path.basename(p)] = rows
    return out


def main():
    scratch = sys.argv[1]
    apply = '--apply' in sys.argv
    mine = my_ja()
    cur, new = load(REF), load(scratch)
    rep = []
    plan = {}
    for fn in sorted(set(cur) | set(new)):
        old_rows = cur.get(fn, [])
        keep = [r for r in old_rows if r['ja'] not in mine]
        add = [r for r in new.get(fn, []) if r['ja'] in mine]
        old_mine = {r['id']: r['en'] for r in old_rows if r['ja'] in mine}
        new_mine = {r['id']: r['en'] for r in add}
        if old_mine == new_mine:
            continue
        for i in sorted(set(old_mine) | set(new_mine)):
            if old_mine.get(i) != new_mine.get(i):
                rep.append(T.join([i, str(old_mine.get(i)), str(new_mine.get(i))]))
        rows = keep + add
        rows.sort(key=lambda r: int(r['id'].rsplit('#', 1)[1], 16))
        plan[fn] = rows
    print('my ja: %d; files touched: %d; id changes: %d' % (len(mine), len(plan), len(rep)))
    with open(os.path.join(ROOT, 'build', 's7', 'n', 'ovmerge_report.tsv'), 'w', encoding='utf8', newline=NL) as fh:
        fh.write(NL.join(rep) + NL)
    if not apply:
        return
    os.makedirs(BAK, exist_ok=True)
    for fn, rows in plan.items():
        p = os.path.join(REF, fn)
        if os.path.exists(p):
            b = os.path.join(BAK, fn + '.pre')
            if not os.path.exists(b):
                shutil.copy2(p, b)
        if rows:
            with open(p + '.s7n.tmp', 'w', encoding='utf-8', newline=NL) as fh:
                for r in rows:
                    fh.write(json.dumps(r, ensure_ascii=False) + NL)
            os.replace(p + '.s7n.tmp', p)
        elif os.path.exists(p):
            os.remove(p)
    print('applied')


main()
