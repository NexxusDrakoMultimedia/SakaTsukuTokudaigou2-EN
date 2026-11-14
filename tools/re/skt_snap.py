"""skt_snap: snapshot (path,size,mtime_ns) of translation/ and build/trial/bis_* ; compare mode prints differences."""
import os, sys, json, glob
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
def snap():
    d = {}
    roots = [os.path.join(ROOT, 'translation')] + glob.glob(os.path.join(ROOT, 'build', 'trial', 'bis_*'))
    for r in roots:
        for dp, dn, fn in os.walk(r):
            for f in fn:
                p = os.path.join(dp, f)
                st = os.stat(p)
                d[os.path.relpath(p, ROOT)] = [st.st_size, st.st_mtime_ns]
    return d
if __name__ == '__main__':
    out = sys.argv[2]
    if sys.argv[1] == 'save':
        json.dump(snap(), open(out, 'w'))
        print(len(snap()), 'files')
    else:
        old = json.load(open(out)); new = snap()
        ch = [k for k in new if k in old and old[k] != new[k]]
        add = [k for k in new if k not in old]; rem = [k for k in old if k not in new]
        print('changed', len(ch), 'added', len(add), 'removed', len(rem))
        for k in (ch + add + rem)[:20]: print(' ', k)
