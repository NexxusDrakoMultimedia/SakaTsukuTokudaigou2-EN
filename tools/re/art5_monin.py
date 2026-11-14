"""art5_monin - MON_INST.TBD #0 (03333)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art5_lib as L
CLR = {'mode': 'clear'}
MK = {'mode': 'mask', 'ink': [{'luma_gt': 125}, {'luma_lt': 24}], 'dilate': 2, 'fill': 'diffuse'}
METAL = [[0, '#ffffff'], [0.55, '#d0d0d0'], [1, '#808080']]
def lab(t, x, y, w, h, erase, outline, size=22, align='center', **kw):
    d = {'id': t + str(x), 'text': t, 'x': x, 'y': y, 'w': w, 'h': h, 'erase': erase,
         'font': ['arial-bold'], 'gradient': [[0, '#f8f8f8'], [1, '#b0b0b0']],
         'outline': {'color': outline, 'width': 1.3}, 'size': 'auto', 'max_size': size, 'min_sx': 0.7,
         'align': align, 'valign': 'middle', 'pad': 0}
    d.update(kw)
    return d
def met(t, x, y, w, h, size, erase=None):
    return {'id': t + str(x), 'text': t, 'x': x, 'y': y, 'w': w, 'h': h, 'erase': erase,
            'font': ['arial-narrow-bold', 'arial-black'], 'gradient': METAL, 'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0},
            'size': 'auto', 'max_size': size, 'min_sx': 0.6, 'align': 'center', 'valign': 'middle', 'pad': 0}
regs = [
    {'id': 'clr_units', 'x': 279, 'y': 33, 'w': 70, 'h': 32, 'erase': CLR},
    met('man', 280, 36, 30, 28, 20), met('oku', 313, 36, 30, 28, 20),
    lab('Ad Budget', 262, 66, 92, 32, CLR, '#3c3c1c', 21),
    lab('Ticket Price', 262, 113, 92, 34, CLR, '#1c1c40', 21),
    lab('Matches', 8, 167, 70, 26, MK, '#202020', 16, 'left', outline_w=1),
    lab('Games', 104, 167, 50, 26, MK, '#202020', 16),
    lab('Home Matches', 8, 198, 70, 26, MK, '#202020', 16, 'left'),
    lab('Games', 104, 198, 50, 26, MK, '#202020', 16),
    {'id': 'clr_yen', 'x': 180, 'y': 224, 'w': 66, 'h': 32, 'erase': CLR},
]
for d in regs:
    d.pop('outline_w', None)
L.finish('03333', L.render('03333', {'regions': regs}))
