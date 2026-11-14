import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(W_ROOT := os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'tools'))
import widths as W, font as F
L1 = ['The club manager signs a young striker.',
      'Illegal little will fill Willie Hill\'s pill.',
      'Next match: Vissel Kobe (Home) - Sat. 14:30',
      'You can change the player layout, and select',
      'Budget 1,250,000,000 yen; wages 3.5% up. Wow!']
for name, specs in (('widths_preview_G1.png', [('fixed', 0), ('prop', 1)]),
                    ('widths_preview_G2.png', [('fixed', 0), ('prop', 2)]),
                    ('widths_preview_all.png', [('fixed', 0), ('prop', 1), ('prop', 2)]),
                    ('widths_preview_narrow.png', [('prop', 'H'), ('narrow', 0)]),
                    ('widths_preview_H.png', [('prop', 2), ('prop', 'H')])):
    w, h, rows = W.render_block(L1, specs, scale=2)
    F.write_png(os.path.join(W_ROOT, 'build/font', name), w, h, rows)
    print(name, w, h)
