"""art5_icons - the 128x32 cyan button captions (ESTAICON, GRICON, NRICON)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art5_lib as L
TEXT = {
    '02003': 'Clubhouse', '02006': 'Ground', '02009': 'Stadium',
    '02187': 'Finances', '02190': 'Match Results', '02193': 'Attendance', '02196': 'TV Ratings',
    '02199': "Supporters' Club", '02202': 'Personnel Info', '02205': 'Exit',
    '03530': 'Club Record', '03533': 'Club Popularity', '03536': 'National Team Record',
}
WRAP = {'03536', '02199'}
for i, t in TEXT.items():
    spec = {'regions': [{
        'id': 'cap', 'text': t, 'x': 7, 'y': 3, 'w': 114, 'h': 26,
        'erase_rect': [5, 2, 118, 27], 'erase': {'mode': 'flat', 'color': [165, 239, 239, 255]},
        'font': ['arial-bold'], 'fill': '#000000', 'align': 'center', 'valign': 'middle',
        'size': 'auto', 'max_size': 19, 'min_sx': 0.85, 'wrap': i in WRAP, 'line_spacing': 0.85,
        'shadow': {'color': '#2a5050', 'dx': 1, 'dy': 1, 'alpha': 0.45},
    }]}
    img = L.render(i, spec)
    o = L.over(i, img)
    if o > 0:
        spec['regions'][0].pop('shadow')
        img = L.render(i, spec)
        o = L.over(i, img)
    if o > 0:
        spec['regions'][0]['aa'] = False
        img = L.render(i, spec)
        o = L.over(i, img)
    L.finish(i, img)
    print('done', i, 'over', o)
