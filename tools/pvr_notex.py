"""List files in extracted/ that pvr_scan found no texture in (for review).
usage: pvr_notex.py [DIRNAME ...]   (directories to leave out)"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pvr_scan  # noqa: E402


def main():
    skip = set(sys.argv[1:])
    sc, notex = pvr_scan.scan_all('extracted', keep_rows=False)
    for rel, n in notex:
        if rel.split('/')[0] in skip:
            continue
        data = open(os.path.join('extracted', rel), 'rb').read(16)
        print('%-34s %9d  %s' % (rel, n, data.hex()))
    print()
    print('size != expected:')


main()
