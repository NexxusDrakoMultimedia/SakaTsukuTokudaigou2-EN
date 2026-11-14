# SPDX-License-Identifier: GPL-3.0-or-later
"""skl_snapshot: record (size, mtime_ns) of everything under translation/ and the top of build/trial/bis_* to a json file,
or compare against an earlier json.  Read only.   skl_snapshot.py save OUT.json | cmp OUT.json"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def scan():
    d = {}
    for base in ('translation',):
        for dp, dn, fn in os.walk(os.path.join(ROOT, base)):
            for f in fn:
                p = os.path.join(dp, f)
                st = os.stat(p)
                d[os.path.relpath(p, ROOT)] = [st.st_size, st.st_mtime_ns]
    t = os.path.join(ROOT, 'build', 'trial')
    for n in sorted(os.listdir(t)):
        if n.startswith('bis_'):
            p = os.path.join(t, n)
            if os.path.isdir(p):
                for dp, dn, fn in os.walk(p):
                    for f in fn:
                        q = os.path.join(dp, f)
                        st = os.stat(q)
                        d[os.path.relpath(q, ROOT)] = [st.st_size, st.st_mtime_ns]
    return d


def main():
    if sys.argv[1] == 'save':
        json.dump(scan(), open(sys.argv[2], 'w'))
        print('saved', len(scan()))
    else:
        old = json.load(open(sys.argv[2]))
        new = scan()
        ch = [k for k in set(old) | set(new) if old.get(k) != new.get(k)]
        print('changed/added/removed:', len(ch))
        for k in sorted(ch)[:40]:
            print(' ', k, old.get(k), new.get(k))


main()
