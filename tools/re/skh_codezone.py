"""skh: translation records that are APPLIED (en non-empty, not skip) but lie in the code zone of an overlay, i.e. below the lowest
offset of any pointer-referenced text record of the same file.  Such a record rewrites machine code or literal tables with ASCII.

usage: skh_codezone.py [FILE-substring] [-v]
Read-only.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def main(argv):
    pat = ''
    for a in argv[1:]:
        if not a.startswith('-'):
            pat = a
    tot = 0
    for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        if pat not in p:
            continue
        rows = []
        for ln in open(p, encoding='utf-8'):
            r = json.loads(ln)
            try:
                off = int(r['id'].split('#')[1], 16)
            except Exception:
                continue
            rows.append((off, r))
        ptr = [o for o, r in rows if not r.get('orphan') and (r.get('refs') or 0) >= 1 and not r.get('skip')]
        if not ptr:
            continue
        lo = min(ptr)
        bad = [(o, r) for o, r in rows if o < lo and (r.get('en') or '').strip() and not r.get('skip')]
        if bad:
            tot += len(bad)
            print('%s: lowest referenced text at %#x, %d applied records below it' % (os.path.basename(p), lo, len(bad)))
            if '-v' in argv or pat:
                for o, r in bad[:40]:
                    print('    #%x max=%s ja=%r en=%r ctx=%s' % (o, r.get('max_bytes'), r['ja'][:12], r['en'][:14], (r.get('ctx') or '')[:30]))
    print('total', tot)


if __name__ == '__main__':
    main(sys.argv)
