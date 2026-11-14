"""art5_prep - resolve the group-5 texture ids, list their dup copies, decode originals to PNG.
python -I -X utf8 tools/re/art5_prep.py"""
import os, sys, json, csv
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject as T, pvr
IDS = json.load(open(os.path.join(HERE, 'art5_ids.json')))
rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'build', 'tex', 'index.tsv'), encoding='utf8')][1:]
by = {r[0][:5]: r for r in rows}
tix = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'build', 'texindex.tsv'), encoding='utf8')][1:]
man = {}
for i in IDS:
    r = by[i]
    f, mem, rec = r[1], r[2], r[9]
    tid = (mem + '#' + rec) if mem else '#' + rec
    me = [t for t in tix if t[0] == f and t[1] == tid]
    assert me, (i, f, tid)
    me = me[0]
    key = (me[3], me[4], me[5], me[6], me[12])
    copies = [(t[0], t[1]) for t in tix if (t[3], t[4], t[5], t[6], t[12]) == key]
    src = open(os.path.join(ROOT, 'extracted', *f.split('/')), 'rb').read()
    p = T.extract_pvr(src, tid)
    open(os.path.join(ROOT, 'build', 'art5', 'orig', i + '.pvr'), 'wb').write(p)
    pvr.to_png(pvr.decode(p), os.path.join(ROOT, 'build', 'art5', 'orig', i + '.png'))
    man[i] = {'file': f, 'tid': tid, 'w': me[5], 'h': me[6], 'copies': copies}
    print(i, f, tid, me[5], me[6], 'copies', len(copies))
json.dump(man, open(os.path.join(ROOT, 'build', 'art5', 'manifest.json'), 'w'), indent=1)
