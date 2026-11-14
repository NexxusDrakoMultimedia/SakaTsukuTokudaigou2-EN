"""art5_office - FLOW_PRG/OFFD1.ZAR oficons.tbd#0 (07405) menu labels."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art5_lib as L
rows = [(2, 31, 'Schedule', 'lime', False), (34, 30, 'Home Town', 'lime', False), (66, 30, 'Personnel', 'white', False),
        (98, 30, 'Facilities', 'white', False), (129, 31, 'Data Room', 'white', False), (161, 31, 'Quit / Options', 'white', True)]
ST = {'lime': {'gradient': [[0, '#e4ff88'], [0.5, '#ccff55'], [1, '#b4ee40']]},
      'white': {'gradient': [[0, '#ffffff'], [0.6, '#eeffff'], [1, '#c8e8e8']]}}
regs = []
for y, h, t, c, wrap in rows:
    d = {'id': t, 'text': t, 'x': 0, 'y': y, 'w': 96, 'h': h, 'erase': {'mode': 'clear'},
         'font': ['arial-bold'], 'outline': {'color': '#000000', 'width': 1},
         'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0},
         'size': 'auto', 'max_size': 25, 'min_sx': 0.78, 'align': 'left', 'valign': 'middle', 'wrap': wrap, 'line_spacing': 0.9, 'pad': 0}
    d.update(ST[c])
    regs.append(d)
img = L.render('07405', {'regions': regs})
L.finish('07405', img)
