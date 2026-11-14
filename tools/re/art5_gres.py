"""art5_gres - G_RESULT.DAT #0 (02219) tab pills."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art5_lib as L
def r(t, x, y, w, h, erase, grad, hl, size=22):
    return {'id': t, 'text': t, 'x': x, 'y': y, 'w': w, 'h': h, 'erase': erase,
            'font': ['arial-black'], 'gradient': grad, 'outline': {'color': '#101010', 'width': 1.3},
            'shadow': {'color': hl, 'dx': 1, 'dy': 1, 'alpha': 0.9},
            'size': 'auto', 'max_size': size, 'min_sx': 0.8, 'align': 'center', 'valign': 'middle', 'pad': 0}
HG = {'mode': 'hgrad'}
MK = {'mode': 'flat', 'color': [68, 68, 68, 255]}
regs = [
    r('Other', 16, 5, 82, 29, HG, [[0, '#c4e880'], [1, '#5a9a20']], '#ffd0b0'),
    r('Scorers', 16, 45, 83, 31, HG, [[0, '#ffee00'], [0.6, '#ffc800'], [1, '#ff9000']], '#c8e0b0'),
    r('Player Ratings', 8, 86, 120, 28, MK, [[0, '#b0e0ff'], [0.5, '#4aa8f0'], [1, '#0868c8']], '#c8c8c8', 20),
]
L.finish('02219', L.render('02219', {'regions': regs}))
