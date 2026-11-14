"""s7t: scan extracted/ (plain files; overlays are flat) for a Shift-JIS string.
usage: python -I -X utf8 tools/re/s7t_scan.py TEXT [--ctx N] [--root DIR]
Prints file, offset, and the NUL-delimited cp932 string around each hit.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def main():
    args = sys.argv[1:]
    text = args[0]
    root = os.path.join(ROOT, 'extracted')
    ctx = 0
    i = 1
    while i < len(args):
        if args[i] == '--root':
            root = args[i + 1]
            i += 2
        elif args[i] == '--ctx':
            ctx = int(args[i + 1])
            i += 2
        else:
            i += 1
    pat = text.encode('cp932')
    for dp, dn, fn in os.walk(root):
        for f in sorted(fn):
            p = os.path.join(dp, f)
            try:
                d = open(p, 'rb').read()
            except OSError:
                continue
            o = 0
            n = 0
            while True:
                o = d.find(pat, o)
                if o < 0:
                    break
                a = d.rfind(b'\0', 0, o) + 1
                b = d.find(b'\0', o)
                s = d[a:b if b >= 0 else o + 40]
                try:
                    st = s.decode('cp932', 'replace')
                except Exception:
                    st = repr(s)
                print('%s 0x%x str@0x%x len=%d %r' % (os.path.relpath(p, root), o, a, len(s), st[:80]))
                n += 1
                o += 1
                if n > 6:
                    break


main()
