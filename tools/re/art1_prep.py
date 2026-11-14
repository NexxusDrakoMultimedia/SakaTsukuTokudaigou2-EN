"""art1_prep - group 1 (header bar, Yes/No, money strips): extract originals, list dup copies, write manifest.
python -I -X utf8 tools/re/art1_prep.py"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject as T, pvr
IDS = ["00002","00091","03634","07332","10469","10470","10474","10475","37285","04112","00088","03642","07308"]
rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'build', 'tex', 'index.tsv'), encoding='utf8')][1:]
by = {r[0][:5]: r for r in rows}
idx = os.path.join(ROOT, 'build', 'texindex.tsv')
man = {}
for i in IDS:
    r = by[i]
    f, mem, rec = r[1], r[2], r[9]
    tid = (mem + '#' + rec) if mem else '#' + rec
    src = open(os.path.join(ROOT, 'extracted', *f.split('/')), 'rb').read()
    p = T.extract_pvr(src, tid)
    open(os.path.join(ROOT, 'build', 'art1', 'orig', i + '.pvr'), 'wb').write(p)
    pvr.to_png(pvr.decode(p), os.path.join(ROOT, 'build', 'art1', 'orig', i + '.png'))
    cp = T.find_copies(idx, f, tid)
    man[i] = {'file': f, 'tid': tid, 'copies': [list(c)[:2] for c in cp]}
    print(i, f, tid, len(cp))
json.dump(man, open(os.path.join(ROOT, 'build', 'art1', 'manifest.json'), 'w'), indent=1)
