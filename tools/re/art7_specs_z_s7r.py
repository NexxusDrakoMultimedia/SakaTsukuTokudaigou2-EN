"""art7 specs, refit pass (s7r): shorter labels for TOWNDATA 04073 / TOWNSEL 04077 so that the glyph ink stays inside the columns of
the old ink (the game prints the digit sprites right after the old label / between label and unit).  Overrides the 04073 / 04077
entries of art7_specs_a (this module sorts after it)."""
import copy
from art7_specs_a import SPECS as A, ER_WB, PLAIN, L as _L

SPECS = {}
NB = 'arial-narrow-bold'

def Ln(rect, text, **kw):
    kw.setdefault('font', NB)
    kw.setdefault('max_size', 20)
    kw.setdefault('min_sx', 0.8)
    kw.setdefault('erase_grow', 3)
    return _L(rect, text, **kw)

# ---- 04077 TOWNSEL: everything of the old spec except the three label rows that touched the digit gap
old = A['04077']['items']
keep = [it for it in old if it['text'] not in ('Population', 'Land Price', 'Transport')]

new77 = keep + [
    Ln((14, 299, 49, 24), 'Pop.', max_size=22, erase_grow=[2, 3, 7, 3]),
    Ln((14, 330, 49, 25), 'Land', max_size=22, erase_grow=[2, 3, 7, 3]),
    Ln((14, 362, 50, 25), 'Transit', max_size=22, erase_grow=[2, 3, 7, 3]),
]
SPECS['04077'] = {'items': new77}

# ---- 04073 TOWNDATA
def P(rect, text, **kw):
    return Ln(rect, text, **kw)
SPECS['04073'] = {'items': [
    P((56, 57, 42, 25), 'Pop.', max_size=22),
    P((58, 86, 44, 19), 'vs Prev', max_size=16),
    _L((213, 64, 18, 19), 'ppl', align='center'),
    _L((213, 88, 18, 17), 'ppl', align='center'),
    P((8, 114, 42, 25), 'Pop.', max_size=22),
    P((9, 143, 44, 19), 'vs Prev', max_size=16),
    _L((97, 122, 24, 14), '10k', align='left', font='arial-narrow-bold', max_size=14, erase_grow=3),
    _L((165, 120, 17, 17), 'ppl', align='center'),
    _L((165, 145, 17, 16), 'ppl', align='center'),
    P((12, 178, 52, 27), 'Land', max_size=22),
    P((12, 219, 52, 27), 'Transit', max_size=22),
    P((6, 259, 66, 26), 'Soccer Pop.', max_size=18, erase_grow=[2, 0, 3, 0]),
    _L((7, 292, 150, 26), 'Annual Rainfall / Temp'),
    P((7, 320, 46, 16), 'vs Last Yr', max_size=14),
    P((377, 324, 48, 24), 'Housing', max_size=18),
    P((377, 363, 50, 26), 'Commerce', max_size=18, min_sx=0.7),
    P((377, 405, 48, 23), 'Sports', max_size=18),
    P((378, 446, 48, 22), 'Nature', max_size=18),
    P((377, 486, 48, 22), 'Other', max_size=18),
]}

# ---- 03869 SUPPORT trait plates: 'Good Connections' was set tiny, 'Coaching Talent' lost its end against the cell edge
from art7_specs_f import SPECS as F
_new = copy.deepcopy(F['03869'])
for _it in _new['items']:
    if _it['text'] == 'Good Connections':
        _it['text'] = 'Connections'
    elif _it['text'] == 'Coaching Talent':
        _it['text'] = 'Coaching'
SPECS['03869'] = _new
# wider erase for the two rows (grey antialias / shadow of the old glyphs survived the luma-only mask as smudges)
ER3 = {'mode': 'mask', 'ink': [{'sat_lt': 0.30}, {'luma_lt': 45}], 'dilate': 1, 'fill': 'hfill'}
for _it in _new['items']:
    # skeptic pass (s7skrefit): the same wider erase now covers every trait row (Future Star / Speed / Roughness kept old-ink remnants)
    if _it['text'] not in ('Chant Edit', 'Club Chant Assign', 'Japan Chant Assign'):
        _it['erase'] = ER3
        _it['erase_grow'] = [3, 1, 5, 1]
