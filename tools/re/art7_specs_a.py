"""art7 specs, part A: hometown, local, support, option, help, VM, report."""
ER_WB = {'mode': 'mask', 'ink': [{'luma_gt': 200}, {'luma_lt': 30}], 'dilate': 2, 'fill': 'hfill'}
WHITE = {'fill': '#ffffff', 'outline': {'color': '#000000', 'width': 1}}
PLAIN = {'fill': '#ffffff'}   # TOWNDATA is tight in its slot: an outline or shadow does not fit the compressed stream

SPECS = {}

SPECS['04077'] = {'items': [
    dict(rect=(78, 142, 37, 21), text='man', erase=ER_WB, font='arial-bold', pad=0, style=WHITE),
    dict(rect=(195, 173, 56, 22), text='By Region'),
    dict(rect=(193, 205, 58, 23), text='By Kana Order', wrap=True, line_spacing=0.9),
    dict(rect=(290, 174, 56, 22), text='By Region', erase=ER_WB),
    dict(rect=(384, 174, 58, 22), text='By Kana Order', erase=ER_WB, wrap=True, line_spacing=0.9),
    dict(rect=(290, 214, 56, 22), text='By Region', erase=ER_WB),
    dict(rect=(384, 214, 58, 22), text='By Kana Order', erase=ER_WB, wrap=True, line_spacing=0.9),
]}


def L(rect, text, **kw):
    d = dict(rect=rect, text=text, erase=ER_WB, align='left', pad=0, style=PLAIN, autostyle=False, erase_grow=1)
    d.update(kw)
    return d

SPECS['04073'] = {'items': [
    L((55, 60, 150, 26), 'Population'),
    L((57, 88, 148, 17), 'vs Last Month'),
    L((213, 64, 18, 19), 'ppl', align='center'),
    L((213, 88, 18, 17), 'ppl', align='center'),
    L((7, 118, 82, 23), 'Population'),
    L((8, 143, 84, 18), 'vs Last Month'),
    L((97, 122, 24, 14), '10k', align='left', font='arial-narrow-bold', max_size=14, erase_grow=3),
    L((165, 120, 17, 17), 'ppl', align='center'),
    L((165, 145, 17, 16), 'ppl', align='center'),
    L((10, 178, 170, 27), 'Land Price'),
    L((10, 219, 170, 27), 'Transport'),
    L((7, 262, 170, 26), 'Soccer Popularity'),
    L((7, 292, 150, 26), 'Annual Rainfall / Temp'),
    L((7, 320, 56, 16), 'vs Last Yr'),
    L((379, 324, 92, 24), 'Housing'),
    L((379, 366, 92, 22), 'Commerce'),
    L((379, 405, 92, 23), 'Sports'),
    L((380, 446, 92, 22), 'Nature'),
    L((379, 486, 92, 22), 'Other'),
]}

def O(rect, text, **kw):
    d = dict(rect=rect, text=text, font='arial-narrow-bold', min_sx=0.5, pad=1, erase_grow=[2, 2, 3, 3], max_size=17)
    d.update(kw)
    return d

SPECS['03550'] = {'items': [
    O((145, 162, 70, 20), 'Player Names'),
    O((145, 191, 95, 21), 'Commentary Voice'),
    O((145, 217, 105, 23), 'Commentary Text'),
    O((145, 244, 48, 23), 'Camera'),
    O((145, 287, 115, 21), 'Screen Saver'),
    O((272, 169, 103, 22), 'Tournament Results'),
    O((272, 200, 103, 22), 'Match Results'),
    O((272, 230, 103, 25), 'Standings Changes'),
    O((272, 260, 123, 28), 'Goal Rankings'),
    O((272, 327, 126, 26), 'Rating Rankings'),
    O((272, 360, 101, 25), 'Index'),
]}

HY = {'outline': {'color': '#ffe800', 'width': 2}}
BLUE_INK = [{'color': [200, 225, 255], 'tol': 70}, {'color': [90, 140, 215], 'tol': 85}, {'color': [30, 60, 130], 'tol': 75}]
SPECS['00067'] = {'items': [
    dict(rect=(29, 10, 192, 40), text='Dr. Tsukuro', font='arial-black', pad=0,
         erase={'mode': 'mask', 'ink': BLUE_INK, 'dilate': 2, 'fill': 'hfill'},
         style={'gradient': [[0, [215, 232, 255]], [0.5, [90, 140, 215]], [1, [40, 70, 150]]],
                'outline': {'color': '#1c3a7a', 'width': 2}}),
    dict(rect=(9, 61, 173, 31), text='Command Guide', font='arial-black', pad=0, autostyle=False,
         style=dict(gradient=[[0, [20, 120, 200]], [1, [0, 70, 150]]], **HY), min_sx=0.6,
         erase={'mode': 'clear'}, erase_grow=[3, 3, 3, 3]),
    dict(rect=(31, 100, 130, 34), text='Training Guide', font='arial-black', pad=0, autostyle=False,
         style=dict(gradient=[[0, [60, 150, 30]], [1, [10, 100, 30]]], **HY), min_sx=0.6,
         erase={'mode': 'clear'}, erase_grow=[3, 3, 3, 3]),
    dict(rect=(4, 139, 181, 36), text='Soccer Glossary', font='arial-black', pad=0, autostyle=False,
         style=dict(gradient=[[0, [200, 20, 20]], [1, [120, 0, 0]]], **HY), min_sx=0.6,
         erase={'mode': 'clear'}, erase_grow=[3, 3, 3, 3]),
]}

# ---- LOCAL / SUPPORT menu plates (128x32 RGB565, black text on cyan)
PLATE_ERASE = {'mode': 'mask', 'ink': {'luma_lt': 120}, 'dilate': 1, 'fill': 'hfill'}
BLK = {'fill': '#0a0a0a'}
def P(text, rect=(6, 6, 116, 21), **kw):
    d = dict(rect=rect, text=text, erase=PLATE_ERASE, autostyle=False, style=BLK, font='arial-bold', pad=0, min_sx=0.6)
    d.update(kw)
    return d
for _i, _t in (('02270', 'Home Data'), ('02273', 'Management'), ('02276', 'Local Voices'), ('02279', 'Capital Investment'),
               ('03882', 'Hear Opinions'), ('03885', 'Chants')):
    SPECS[_i] = {'items': [P(_t)], 'fmt': 'rgb565'}
SPECS['03879'] = {'items': [P('Supporter Rankings', rect=(6, 4, 116, 24), wrap=True, line_spacing=0.85)], 'fmt': 'rgb565'}

# ---- VMCOM flist (VM file list labels)
YSH = {'color': '#1c2450', 'dx': 2, 'dy': 2, 'alpha': 0.7, 'blur': 0}
def Y(rect, text, grad=None, **kw):
    g = grad or [[0, [255, 235, 40]], [1, [255, 215, 0]]]
    d = dict(rect=rect, text=text, autostyle=False, font='arial-bold', pad=0, min_sx=0.6, erase_grow=[2, 2, 4, 4],
             style={'gradient': g, 'shadow': YSH})
    d.update(kw)
    return d
GOLD = [[0, [250, 225, 110]], [1, [245, 160, 70]]]
OR2 = [[0, [255, 215, 60]], [1, [250, 165, 40]]]
LB = [[0, [150, 200, 255]], [1, [110, 180, 240]]]
SPECS['04096'] = {'items': [
    Y((6, 0, 250, 26), 'VM Game Blocks', GOLD),
    Y((0, 30, 16, 28), '', GOLD),
    Y((6, 70, 160, 28), 'Free Blocks', GOLD),
    dict(rect=(11, 110, 66, 36), text='Exit', font='arial-black', pad=0, autostyle=False, min_sx=0.7,
         erase={'mode': 'mask', 'ink': [{'luma_lt': 40}, {'sat_gt': 0.75, 'luma_gt': 120}], 'dilate': 1, 'fill': 'hfill'},
         style={'gradient': [[0, [255, 240, 0]], [1, [250, 130, 0]]], 'outline': {'color': '#101010', 'width': 1},
                'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'alpha': 1.0, 'blur': 0}}),
]}
SPECS['04097'] = {'items': [
    Y((6, 8, 116, 25), 'File Name'),
    Y((128, 8, 44, 25), 'Date'),
    Y((176, 8, 48, 25), 'Size'),
    Y((2, 48, 72, 24), 'Records', OR2),
    Y((88, 48, 96, 24), 'Free Space', OR2),
    Y((8, 84, 142, 25), 'Switch View', LB),
    Y((158, 84, 94, 25), 'Sort', LB),
    Y((8, 126, 120, 24), 'Copy / Delete', LB),
    Y((144, 130, 90, 22), 'Comment'),
    Y((6, 168, 96, 24), 'Newest First'),
    Y((124, 168, 96, 25), 'By Name'),
    Y((10, 206, 217, 27), 'Newest by Name'),
]}

# ar5: the Hometown screen draws its data panel and the money digits from THIS texture (TOWNSEL#0), not from TOWNDATA#1.
# New ink stays inside the old ink columns because the game prints the figures in the gaps (0.02 between Population and 10k ppl).
OKU = {'font': ['segoe-ui-bold', 'arial-bold'], 'gradient': [[0, '#e8ffff'], [1, '#2fb8a8']],
       'shadow': {'color': '#000000', 'dx': 1.5, 'dy': 1.5, 'steps': 2, 'alpha': 1.0}, 'outline': {'color': '#000000', 'width': 1}}
ER_ALL = {'mode': 'mask', 'ink': [{'luma_gt': 200}, {'luma_lt': 40}], 'dilate': 2, 'fill': 'hfill'}
SPECS['04077']['items'] += [
    dict(rect=(462, 266, 30, 32), text='oku', style=OKU, autostyle=False, font=['arial-narrow-bold', 'bahnschrift', 'arial-bold'],
         size=18, min_sx=0.4, pad=0, erase={'mode': 'clear'}),
    L((9, 268, 154, 25), 'Annual Rainfall / Temp'),
    L((11, 302, 57, 22), 'Population', font='arial-narrow-bold'),
    L((117, 304, 40, 17), '10k ppl', font='arial-narrow-bold', max_size=13),
    L((11, 331, 57, 24), 'Land Price', font='arial-narrow-bold'),
    L((11, 363, 57, 24), 'Transport', font='arial-narrow-bold'),
    L((9, 395, 68, 25), 'Soccer Pop.', font='arial-narrow-bold'),
]
