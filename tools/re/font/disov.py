"""Disassemble a range of an overlay: python -I -X utf8 disov.py OVERLAY lo hi   (OVERLAY like CAP_SLCT.BIN; lo/hi hex)"""
import os, sys, csv
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sh4dis import Image
R = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))


def load(name):
    for r in csv.DictReader(open(os.path.join(R, 'build', 'memmap', 'overlays.tsv')), delimiter='\t'):
        if r['overlay'] == name:
            d = open(os.path.join(R, 'extracted', r['dir'], name), 'rb').read()
            return Image(d, int(r['base'], 16)), r
    raise SystemExit('no overlay ' + name)


if __name__ == '__main__':
    img, r = load(sys.argv[1])
    for l in img.listing(int(sys.argv[2], 16), int(sys.argv[3], 16)):
        print(l)
