"""rfit_chk: list the tier A candidates that hit record arrays / pools / plain text (review helper, read-only).

    python -I -X utf8 tools/re/rfit_chk.py
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import rfit_gen as G  # noqa: E402


def main():
    by_src = G.BP.load_tdb('translation')
    forms = G.parse_forms(os.path.join(ROOT, 'translation', 'refit', 'forms.tsv'))
    cands, _unfit = G.gen_candidates(by_src, forms, False)
    cnt = Counter()
    for c in cands:
        if c.kind != 'hwptr':
            cnt[(c.kind, c.rec['ja'], c.rec['en'], c.new, c.rec.get('ctx', '')[:40])] += 1
    for k, v in sorted(cnt.items()):
        print(v, k)


if __name__ == '__main__':
    main()
