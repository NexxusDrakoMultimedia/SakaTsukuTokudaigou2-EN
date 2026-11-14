"""art5_estab - ESTABLIS.BIN @1ee08#1 (07309) Expand / Remove / View / Exit."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art5_lib as L
def r(t, x, y, w, h):
    return {'id': t, 'text': t, 'x': x, 'y': y, 'w': w, 'h': h, 'erase': {'mode': 'clear'},
            'font': ['arial-bold-italic'], 'gradient': [[0, '#fbfbf0'], [1, '#dcdccc']],
            'shadow': {'color': '#0c1448', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0},
            'size': 'auto', 'max_size': 26, 'min_sx': 0.8, 'align': 'left', 'valign': 'middle', 'pad': 0}
regs = [r('Expand', 0, 49, 70, 27), r('Remove', 72, 49, 78, 27), r('View', 0, 82, 70, 27), r('Exit', 72, 82, 78, 27)]
L.finish('07309', L.render('07309', {'regions': regs}))
