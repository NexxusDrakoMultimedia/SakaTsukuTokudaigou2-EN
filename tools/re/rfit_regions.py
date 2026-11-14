"""rfit_regions: restart points of the sorted name pools (foreign name region -> Japanese name region), read-only.

    python -I -X utf8 tools/re/rfit_regions.py FLOW_PRG/AUTOSAVE.BIN

For every pointer table (`tbl@ADDR[i/n]`, n >= 60) of the source: the indexes where the byte order of `ja` goes backwards
(a restart of the alphabetical order), the neighbouring strings and the table size.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TBL = re.compile(r'tbl@([0-9a-f]+)\[(\d+)/(\d+)\]')


def main(argv):
    source = argv[0]
    p = os.path.join(ROOT, 'translation', source.replace('/', '__') + '.jsonl')
    tabs = {}
    with open(p, encoding='utf-8') as fh:
        for line in fh:
            r = json.loads(line)
            m = TBL.search(r.get('ctx') or '')
            if r.get('fmt') == 'hwptr' and m and int(m.group(3)) >= 60:
                tabs.setdefault(m.group(1), {})[int(m.group(2))] = r
    for a, t in sorted(tabs.items()):
        n = len(t)
        prev = None
        marks = []
        for i in sorted(t):
            k = t[i]['ja'].encode('cp932', 'replace')
            if prev is not None and k < prev[1]:
                marks.append((i, prev[0], t[i]['ja']))
            prev = (t[i]['ja'], k)
        print('tbl@%s n=%d first=%s last=%s restarts=%s' % (a, n, t[min(t)]['ja'], t[max(t)]['ja'], [(i, x, y) for i, x, y in marks][:6]))
    seq = []
    for a, t in sorted(tabs.items(), key=lambda kv: int(kv[0], 16)):
        for i in sorted(t):
            seq.append((a, i, t[i]['ja']))
    prev = None
    for a, i, ja in seq:
        b = ja.encode('cp932', 'replace')[0]
        if prev is not None and prev >= 0xD0 and b <= 0xB8:
            print('COARSE restart at tbl@%s[%d] %s (prev first byte %#x)' % (a, i, ja, prev))
        prev = b


if __name__ == '__main__':
    main(sys.argv[1:])
