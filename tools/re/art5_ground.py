"""art5_ground - GROUND.DAT #1 (02208) caption strips."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art5_lib as L
MK = {'mode': 'mask', 'ink': [{'luma_gt': 115}, {'luma_lt': 14}], 'dilate': 2, 'fill': 'diffuse'}
def r(t, x, y, w, h, align='center'):
    return {'id': t, 'text': t, 'x': x, 'y': y, 'w': w, 'h': h, 'erase': MK, 'erase_grow': [0, 0, 0, 2],
            'font': ['arial-bold'], 'gradient': [[0, '#e0ecec'], [1, '#a8bcbc']],
            'outline': {'color': '#0c1414', 'width': 1.1}, 'shadow': {'color': '#000000', 'dx': 1, 'dy': 1, 'alpha': 0.8},
            'size': 'auto', 'max_size': 15, 'min_sx': 0.75, 'align': align, 'valign': 'middle', 'pad': 0}
regs = [r('Condition', 2, 50, 92, 19), r('Re-turf (Short)', 97, 50, 94, 19), r('Re-turf (Long)', 2, 120, 92, 20),
        r('Lighting', 142, 120, 50, 20, 'right')]
L.finish('02208', L.render('02208', {'regions': regs}))
