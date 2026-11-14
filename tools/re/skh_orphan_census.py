"""skh: census of APPLIED orphan records ('orphan (no pointer)', en non-empty, not skip) that are NOT in the skip set of skh_mkskip.py.

usage: skh_orphan_census.py [TDBDIR]      (default translation/; pass build/skh/tdb to see what is left after skipping)
Groups them: (1) 'stride/table' ctx text, (2) short pure-kanji ja (<= 6 chars, no kana, no space: typical binary-decoded-as-cp932 junk),
(3) everything else; prints the group sizes and the group-2 rows.  Read-only.
"""
import glob
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
KANA = re.compile(r'[぀-ヿ｡-ﾟ ]')


def main(argv):
    d = argv[1] if len(argv) > 1 else os.path.join(ROOT, 'translation')
    g = Counter()
    rows = []
    for p in sorted(glob.glob(os.path.join(d, '*.jsonl'))):
        for ln in open(p, encoding='utf-8'):
            r = json.loads(ln)
            if not r.get('orphan') or r.get('skip') or not (r.get('en') or '').strip():
                continue
            ja = r['ja']
            if 'stride' in (r.get('ctx') or ''):
                g['stride'] += 1
            elif len(ja) <= 6 and not KANA.search(ja) and not re.search(r'[A-Za-z0-9]', ja):
                g['short kanji'] += 1
                rows.append((r['id'], ja, r['en'], r.get('max_bytes')))
            else:
                g['other'] += 1
    print(dict(g))
    c = Counter((x[1], x[2]) for x in rows)
    for (ja, en), n in c.most_common(60):
        ex = [x[0] for x in rows if x[1] == ja and x[2] == en][:2]
        print('%3d  %r -> %r   e.g. %s' % (n, ja, en, ex))


if __name__ == '__main__':
    main(sys.argv)
