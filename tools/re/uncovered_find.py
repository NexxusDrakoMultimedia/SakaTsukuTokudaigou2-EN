"""Find byte patterns (cp932) for given strings in extracted/, build/unpacked/ and RAM dumps.

usage: python -I -X utf8 tools/re/uncovered_find.py STR [STR...]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def walk(base):
    for dp, dn, fn in os.walk(base):
        for f in fn:
            yield os.path.join(dp, f)


def main():
    pats = {s: s.encode('cp932') for s in sys.argv[1:]}
    files = list(walk(os.path.join(ROOT, 'extracted'))) + list(walk(os.path.join(ROOT, 'build', 'unpacked')))
    files += [os.path.join(ROOT, 'build', 'emu', 'pt1_ram.bin')]
    for fp in files:
        try:
            d = open(fp, 'rb').read()
        except OSError:
            continue
        for s, p in pats.items():
            k = d.find(p)
            n = 0
            while k != -1 and n < 5:
                print('%-60s %-12s @%#x' % (os.path.relpath(fp, ROOT), s, k))
                n += 1
                k = d.find(p, k + 1)


main()
