"""s7n: pixel check of lines.  usage: s7n_px.py CELLS "line1" "line2" ... (\n inside an argument splits lines)"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import pixelwidth as PW
cells = int(sys.argv[1])
for a in sys.argv[2:]:
    for l in a.replace('\n', chr(10)).split(chr(10)):
        c = PW.check_line(l, cells)
        print('%-4s px=%4d start=%4d limit=%d  %s' % ('ok' if c['ok'] else 'OVER', c['px'], c['start'], PW.start_limit_px(cells), l))
