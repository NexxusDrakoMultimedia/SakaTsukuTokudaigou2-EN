"""List every translation record whose Japanese text contains a money unit (円 億 万 兆) together with a printf token,
grouped by (ja, en).  Read only.   python -I -X utf8 tools/re/mn6_formats.py [out.tsv]"""
import glob
import json
import os
import re
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UNIT = re.compile(r'[円億万兆]')
TOK = re.compile(r'%[-0-9]*[sdDmM]')


def main(argv):
    groups = OrderedDict()
    for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        with open(p, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                ja = r.get('ja', '')
                if UNIT.search(ja) and TOK.search(ja):
                    groups.setdefault((ja, r.get('en', '')), []).append(r['id'])
    out = []
    for (ja, en), ids in groups.items():
        out.append('%d\t%s\t%s\t%s' % (len(ids), ja.replace('\n', '\\n'), en.replace('\n', '\\n'), ','.join(i.split('/')[-1] for i in ids[:6])))
    txt = '\n'.join(out) + '\n'
    if len(argv) > 1:
        with open(argv[1], 'w', encoding='utf-8') as f:
            f.write(txt)
    else:
        sys.stdout.write(txt)


if __name__ == '__main__':
    main(sys.argv)
