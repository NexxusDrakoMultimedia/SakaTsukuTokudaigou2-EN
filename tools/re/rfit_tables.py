"""rfit_tables: the pointer tables (`tbl@ADDR[i/n]`) of the hwptr records, grouped by size n and content (names owner helper).

    python -I -X utf8 tools/re/rfit_tables.py [OUT.txt]

For every table size n: number of (source, table) pairs, sources, and the distinct (ja -> en) pairs of the family with the
slot sizes seen.  With OUT.txt the full distinct lists are written (small tables only, n < 200); read-only.
"""
import glob
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TBL = re.compile(r'tbl@([0-9a-f]+)\[(\d+)/(\d+)\]')


def main(argv):
    fam = defaultdict(lambda: {'tables': set(), 'pairs': defaultdict(set)})
    for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        with open(p, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if r.get('fmt') != 'hwptr' or not r.get('en'):
                    continue
                m = TBL.search(r.get('ctx') or '')
                if not m:
                    continue
                n = int(m.group(3))
                src = r['id'].rsplit('#', 1)[0]
                f = fam[n]
                f['tables'].add((src, m.group(1)))
                f['pairs'][(r['ja'], r['en'])].add(r.get('slot') or r['max_bytes'])
    for n in sorted(fam):
        f = fam[n]
        srcs = {s for s, _ in f['tables']}
        print('n=%-5d tables=%-3d sources=%-3d distinct pairs=%d' % (n, len(f['tables']), len(srcs), len(f['pairs'])))
    if argv:
        with open(argv[0], 'w', encoding='utf-8') as fo:
            for n in sorted(fam):
                if n >= 200:
                    continue
                fo.write('## n=%d\n' % n)
                for (ja, en), slots in sorted(fam[n]['pairs'].items()):
                    fo.write('%s\t%s\t%s\n' % (ja, en, sorted(slots)))


if __name__ == '__main__':
    main(sys.argv[1:])
