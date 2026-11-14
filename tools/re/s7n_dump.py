"""s7n: dump DB records of one source in an offset range.  usage: s7n_dump.py FLOW_PRG/EVENT.BIN lo hi (hex)"""
import json, sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src, lo, hi = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
p = os.path.join(ROOT, 'translation', src.replace('/', '__') + '.jsonl')
for ln in open(p, encoding='utf8'):
    if not ln.strip():
        continue
    r = json.loads(ln)
    off = int(r['id'].rsplit('#', 1)[1], 16)
    if lo <= off <= hi:
        print('%x\t%s\t%s\t%s\t%s' % (off, r['ja'].replace('\n', '\\n'), r['en'].replace('\n', '\\n'), r.get('max_bytes'), (r.get('ctx') or '')[:60]))
