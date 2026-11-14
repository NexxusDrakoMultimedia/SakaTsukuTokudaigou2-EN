"""rfit_variants: Japanese strings that carry more than one English form in the DB (names owner helper, read-only).

    python -I -X utf8 tools/re/rfit_variants.py OUT.txt [--max-ja-len N]

A short form that exists only because a slot was small shows up as a variant of a longer form of the same `ja` elsewhere.
Output per ja: the forms with the number of records, the sources and the slots they sit in.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def main(argv):
    out = argv[0]
    maxlen = 40
    if '--max-ja-len' in argv:
        maxlen = int(argv[argv.index('--max-ja-len') + 1])
    by = {}
    for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        with open(p, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                en = r.get('en')
                if not en or len(r['ja']) > maxlen or '\n' in en or '\n' in r['ja']:
                    continue
                slot = r.get('slot') or r.get('max_bytes') or 0
                by.setdefault(r['ja'], {}).setdefault(en, []).append((r['id'].rsplit('#', 1)[0], slot, r.get('fmt') or 'ptr', 'interior' in (r.get('ctx') or ''), r['id']))
    n = 0
    with open(out, 'w', encoding='utf-8') as fo:
        for ja, forms in sorted(by.items()):
            if len(forms) < 2:
                continue
            if '--nonhw' in argv and ('ｦ' <= ja[0] <= 'ﾟ' or ja[-1] in '市郡町村区島'):
                continue
            n += 1
            fo.write('%s\n' % ja)
            for en, lst in sorted(forms.items(), key=lambda kv: -len(kv[0])):
                slots = sorted({x[1] for x in lst})
                fmts = sorted({x[2] for x in lst})
                inter = sum(1 for x in lst if x[3])
                fo.write('    %-28s n=%-3d slots=%s fmt=%s%s  e.g. %s\n' % (en, len(lst), slots[:6], ','.join(fmts), ' interior=%d' % inter if inter else '', lst[0][4]))
    print('%d japanese strings with several english forms -> %s' % (n, out))


if __name__ == '__main__':
    main(sys.argv[1:])
