"""covcheck.py STR [STR..] : every occurrence of STR (cp932) in extracted/ top-level overlay/exe files,
with whether a translation record covers it and whether that record has English.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import textfmt_common as C

recs = {}
tdir = os.path.join(ROOT, 'translation')
for fn in os.listdir(tdir):
    if not fn.endswith('.jsonl'):
        continue
    for line in open(os.path.join(tdir, fn), encoding='utf-8'):
        line = line.strip()
        if line:
            r = json.loads(line)
            src, _, off = r['id'].rpartition('#')
            recs.setdefault(src, {})[int(off, 16)] = r

for s in sys.argv[1:]:
    pat = s.encode('cp932')
    for sub in ('FLOW_PRG', 'ATFIRST', ''):
        base = os.path.join(ROOT, 'extracted', sub)
        for fn in sorted(os.listdir(base)):
            fp = os.path.join(base, fn)
            if not os.path.isfile(fp):
                continue
            d = open(fp, 'rb').read()
            src = (sub + '/' if sub else '') + fn
            k = d.find(pat)
            while k != -1:
                # covering record: record whose [off, off+len) contains k
                cov = None
                for o, r in recs.get(src, {}).items():
                    if o <= k < o + len(C.encode_text(r['ja'])) + 1:
                        cov = (o, r)
                        break
                print('%-28s %-8s @%06x %s' % (src, s, k, 'covered en=%r (rec@%x ja=%r)' % (cov[1]['en'], cov[0], cov[1]['ja']) if cov else 'NOT COVERED'))
                k = d.find(pat, k + 1)
