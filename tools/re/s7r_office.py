"""s7r_office [--write] [t3 t4] : 07405 (+07469, 07539) office menu plates with rows 3 and 4 limited to the original 51 px sprite width."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art5_lib as L
args = [a for a in sys.argv[1:] if not a.startswith('--')]
write = '--write' in sys.argv
t3 = args[0] if args else 'Staff'
t4 = args[1] if len(args) > 1 else 'Facility'
rows = [(2, 31, 'Schedule', 'lime', False, 96), (34, 30, 'Home Town', 'lime', False, 96), (66, 30, t3, 'white', False, 51),
        (98, 30, t4, 'white', False, 51), (129, 31, 'Data Room', 'white', False, 96), (161, 31, 'Quit / Options', 'white', True, 96)]
ST = {'lime': {'gradient': [[0, '#e4ff88'], [0.5, '#ccff55'], [1, '#b4ee40']]},
      'white': {'gradient': [[0, '#ffffff'], [0.6, '#eeffff'], [1, '#c8e8e8']]}}
regs = []
for y, h, t, c, wrap, w in rows:
    narrow = w < 96
    d = {'id': t, 'text': t, 'x': 0, 'y': y, 'w': w, 'h': h, 'erase': {'mode': 'clear'},
         'font': ['arial-narrow-bold'] if narrow else ['arial-bold'], 'outline': {'color': '#000000', 'width': 1},
         'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0} if not narrow else {'color': '#000000', 'dx': 1, 'dy': 1, 'steps': 1, 'alpha': 1.0},
         'size': 'auto', 'max_size': 25, 'min_sx': 0.78 if not narrow else 0.6, 'align': 'left', 'valign': 'middle', 'wrap': wrap, 'line_spacing': 0.9, 'pad': 0}
    d.update(ST[c])
    regs.append(d)
# the swoosh at x>96 on rows 1-2 is not text: erase only the text region (as the existing render does)
img = L.render('07405', {'regions': regs})
img.save('build/s7/r/s7r_07405_new.png')
if write:
    L.finish('07405', img)
    print('written')
