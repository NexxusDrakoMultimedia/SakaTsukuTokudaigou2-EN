"""s7n apply: write the planned `en` changes (status ok / grow) and the manual overrides into translation/*.jsonl.

usage: s7n_apply.py [--dry]
* every touched file: backup to build/s7/bak/s7n/<file>.pre (first time only), read-modify-write in one go, atomic replace
* only the value of the `en` key changes, inside the raw JSON line (the file keeps its own spacing); a line whose old value cannot be found aborts the run
* the list of changed ids is appended to build/s7n_changed_ids.tsv (id <TAB> old en <TAB> new en <TAB> rule)
"""
import glob
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import s7n_plan as P  # noqa: E402
import s7n_over as O  # noqa: E402

NL = chr(10)
BAK = os.path.join(ROOT, 'build', 's7', 'bak', 's7n')
LOG = os.path.join(ROOT, 'build', 's7n_changed_ids.tsv')


def swap_en(ln, old, new):
    """replace the value of the "en" key in the raw JSON line (the line keeps its own spacing / key order)"""
    jo = json.dumps(old, ensure_ascii=False)
    jn = json.dumps(new, ensure_ascii=False)
    for key in ('"en": ', '"en":'):
        pat = key + jo
        if ln.count(pat) == 1:
            return ln.replace(pat, key + jn)
    raise SystemExit('cannot locate en value in line: %s' % ln[:120])


def main():
    dry = '--dry' in sys.argv
    over = O.OVERRIDES
    seen = set()
    plan = {}                      # id -> (old, new, why, file)   (phase 1: read-only, slow)
    for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        for ln in open(p, encoding='utf8'):
            if not ln.strip():
                continue
            r = json.loads(ln)
            seen.add(r['id'])
            new, why = None, None
            if r['id'] in over:
                new, why = over[r['id']], 'override'
            else:
                res = P.classify(r)
                if res and res[0] in ('ok', 'grow'):
                    new, why = res[1], '+'.join(sorted(set(res[2])))
            if new is not None and new != r.get('en'):
                plan[r['id']] = (r['en'], new, why, p)
    missing = set(over) - seen
    if missing:
        raise SystemExit('override ids not found: %s' % sorted(missing))
    byfile = {}
    for i, (o, n, w, p) in plan.items():
        byfile.setdefault(p, []).append(i)
    print('%d records in %d files' % (len(plan), len(byfile)))
    if dry:
        return
    os.makedirs(BAK, exist_ok=True)
    done, skipped = [], []
    for p, ids in sorted(byfile.items()):          # phase 2: per file read-modify-write, quick, atomic
        want = set(ids)
        lines = open(p, encoding='utf8', newline='').read().split(NL)
        out = []
        for ln in lines:
            if ln.strip() and '"id"' in ln:
                r = json.loads(ln)
                if r['id'] in want:
                    o, n, w, _p = plan[r['id']]
                    if r['en'] == o:
                        out.append(swap_en(ln, o, n))
                        done.append((r['id'], o, n, w))
                        continue
                    skipped.append(r['id'])
            out.append(ln)
        b = os.path.join(BAK, os.path.basename(p) + '.pre')
        if not os.path.exists(b):
            shutil.copy2(p, b)
        with open(p + '.s7n.tmp', 'w', encoding='utf8', newline='') as fh:
            fh.write(NL.join(out))
        os.replace(p + '.s7n.tmp', p)
    with open(LOG, 'a', encoding='utf8', newline=chr(10)) as fh:
        for i, o, n, w in done:
            fh.write(chr(9).join([i, o.replace(NL, '\\n'), n.replace(NL, '\\n'), w]) + chr(10))
    print('written %d, skipped (changed meanwhile) %d %s' % (len(done), len(skipped), skipped[:5]))


main()
