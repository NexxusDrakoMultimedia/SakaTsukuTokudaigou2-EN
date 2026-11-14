"""mny_examples.py : print the example table of docs/number-formats.md s4.6 (both styles, width in glyphs and in proportional-font px)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moneypatch as MP
import pixelwidth as PX

for v in (0, 1, 15, 150, 1234, 6000, 9999, 10000, 10300, 100050, 131500, 325000, 815000, 990000, 9450000, 99999999, 2 ** 31 - 1, -50, -131500):
    j, w = MP.reference(v, 0, 'jp'), MP.reference(v, 0, 'western')
    print('| %d | %s | %s | %d / %d px | %s |' % (v, j, '%d yen' % (v * 10000), len(j), PX.line_px(j)[0], w))
