"""s7m_glv [--write]: town level panel glv.tbd#5 (12 TWND*.ZAR copies): 景気 tag -> Economy, five levels Boom / Good / Steady / Weak / Slump.
128x128 ARGB4444; rows y 17,33,49,65,81 (13 px tall) x 1..49; tag x 96..127 y 17..31 (blue gradient)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7m_lib as L
import art7_lib

WORDS = ['Boom', 'Good', 'Steady', 'Weak', 'Slump']
write = '--write' in sys.argv
t = L.load('FLOW_PRG/TWND1.ZAR', 'glv.tbd#5')
items = []
for k, w in enumerate(WORDS):
    items.append(dict(rect=(1, 17 + 16 * k, 49, 13), text=w, font='arial-narrow-bold', pad=0, align='left', valign='middle',
                      size=14, min_sx=0.8, erase={'mode': 'clear'}, dx=1, dy=0))
items.append(dict(rect=(97, 18, 30, 12), text='Economy', font='arial-narrow-bold', pad=0, align='center', valign='middle',
                  size=10, min_sx=0.7, erase={'mode': 'mask', 'ink': [{'luma_gt': 170}, {'luma_lt': 30}], 'dilate': 1, 'fill': 'diffuse'}, style={'fill': '#ffffff', 'outline': {'color': '#0a1c3c', 'width': 1}}, autostyle=False))
out, rep = art7_lib.repaint(t, items, 'argb4444')
for w in rep['warnings']:
    print('WARN', w)
for r in rep['regions']:
    print(repr(r['text']), r['font'], r['size'], r['squash'], r['block'])
L.sheet(t['arr'], out, os.path.join(L.OUT, '08688_ba.png'), 5, rect=(0, 0, 128, 100))
if write:
    new, paths, bad = L.write(t, out)
    print('wrote', len(paths), 'bad', bad)
