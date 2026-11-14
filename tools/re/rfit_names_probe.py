"""rfit_names_probe: how much of the half-width name pool has an authoritative longer English form (read-only statistics).

    python -I -X utf8 tools/re/rfit_names_probe.py [OUT.tsv]

Classes of the distinct (ja, en) pairs of hwptr / recarr records:
  A  a longer English of the same `ja` exists in the BPINFO name tables (13 / 14-byte fields)         -> authoritative
  B  the English is a kunrei / squeezed spelling of hepburn(ja) (hepburn(ja) differs only by sh/ch/ts/f/j or one dropped letter)
  C  the English is a subsequence of hepburn(ja) but not B                                            -> unverified
  D  anything else (foreign names, words)
"""
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import rfit_kana as K  # noqa: E402


def is_subseq(a, b):
    it = iter(b)
    return all(c in it for c in a)


def main(argv):
    bp = defaultdict(Counter)
    recs = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        with open(p, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if not r.get('en'):
                    continue
                src = r['id'].rsplit('#', 1)[0]
                if src.endswith('BPINFO.BIN'):
                    bp[r['ja']][r['en']] += 1
                    bp[r['ja'].replace(' ', '')][r['en']] += 1
                elif r.get('fmt') in ('hwptr', 'recarr'):
                    recs.append(r)
    pairs = {}
    for r in recs:
        k = (r['ja'], r['en'])
        pairs.setdefault(k, 0)
        pairs[k] += 1
    cls = Counter()
    rows = []
    for (ja, en), n in sorted(pairs.items()):
        c = 'D'
        can = ''
        b = bp.get(ja) or bp.get(ja.replace(' ', ''))
        hep = K.hepburn(ja)
        if b:
            top = b.most_common(1)[0][0]
            if len(top) > len(en) and top != en:
                c, can = 'A', top
        if c == 'D' and hep and hep != en:
            h = hep.replace(' ', '')
            e = en.replace(' ', '').replace('.', '')
            kun = re.sub(r'(?<!s)si', 'shi', e.lower())
            if h.lower() == kun or (len(h) <= len(e) + 1 and is_subseq(e.lower(), h.lower()) and len(h) > len(e)):
                c, can = 'B', hep
            elif is_subseq(e.lower(), h.lower()) and len(h) > len(e):
                c, can = 'C', hep
        cls[c] += n
        rows.append((c, ja, en, can, n))
    print(dict(cls))
    if argv:
        with open(argv[0], 'w', encoding='utf-8') as fo:
            for c, ja, en, can, n in rows:
                if c != 'D':
                    fo.write('%s\t%s\t%s\t%s\t%d\n' % (c, ja, en, can, n))
        print('written', argv[0])


if __name__ == '__main__':
    main(sys.argv[1:])
