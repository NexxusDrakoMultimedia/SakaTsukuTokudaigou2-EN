"""s7x specs (match owner, package E): Practice left menu, pre-match menu, post-match news plates.  Run with s7x_run.py."""
SPECS = {}

# ---------------------------------------------------------------- 37285 TRAINING.TBD#0 (Practice screen sheet), lower part
# the stage-6 header (y < 170) is kept: base = installed file
M = {'fill': '#d4fcfc', 'shadow': {'color': '#000010', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}, 'aa': False}
MY = {'fill': '#fff060', 'shadow': {'color': '#201000', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}, 'aa': False}
CHIP = {'gradient': [[0, '#ffffff'], [0.55, '#f0f0f0'], [1, '#b8b8c0']], 'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}, 'aa': False}
E_CHIP = {'mode': 'mask', 'ink': [{'luma_gt': 150, 'sat_lt': 0.3}, {'luma_lt': 18}], 'dilate': 1, 'fill': 'diffuse'}
E_WK = {'mode': 'mask', 'ink': [{'luma_gt': 160}, {'luma_lt': 22}], 'dilate': 1, 'fill': 'diffuse'}


def _m(rect, text, **kw):
    d = dict(rect=rect, text=text, font=['arial-narrow-bold', 'arial-bold'], style=M, autostyle=False, shear=0.18, align='left', pad=1, min_sx=0.5, size=17)
    d.update(kw)
    return d


def _chip(col, row, text, **kw):
    x0 = (97, 209, 321)[col]
    y0 = 289 + 32 * row
    d = dict(rect=(x0 + 3, y0 + 3, 99, 21), text=text, font=['arial-narrow-bold', 'arial-bold'], style=CHIP, autostyle=False, shear=0.18, align='left',
             pad=0, min_sx=0.6, max_size=21, erase=E_CHIP, colfill=dict(rect=(x0 + 3, y0 + 2, 91, 28), src=x0 + 2), colfill2=dict(rect=(x0 + 94, y0 + 2, 11, 28), src=x0 + 106))
    d.update(kw)
    return d


S37285 = [
    # left strip
    _m((0, 194, 96, 29), 'Practice Orders'), _m((0, 227, 96, 29), 'Change Policy'), _m((0, 259, 95, 28), 'Run Practice'),
    _m((0, 290, 95, 29), 'View Teamwork'), _m((1, 323, 94, 27), 'Team Check'),
    # sub plates
    _m((104, 194, 95, 31), 'Team Practice'), _m((103, 226, 96, 28), 'Solo Practice'), _m((104, 258, 93, 28), 'Extra Rest'),
    # total panel (right)
    _m((394, 97, 96, 28), 'Overall Rating', size=19), _m((396, 132, 90, 27), 'Team Tactics', size=19), _m((393, 163, 93, 29), 'DF Type', size=19),
]
S37285 += [_chip(0, 0, 'Formation'), _chip(1, 0, 'Tactics'), _chip(2, 0, 'By Play Style'),
           _chip(0, 1, 'By Position'), _chip(1, 1, 'Strength'), _chip(2, 1, 'Skills'),
           _chip(0, 2, 'Endurance'), _chip(1, 2, 'Speed'), _chip(2, 2, 'Basic Fitness'),
           _chip(0, 3, 'Set Pieces'), _chip(1, 3, 'Scrimmage'), _chip(2, 3, 'Teamwork'),
           _chip(0, 4, 'Free Training'), _chip(1, 4, 'Rest'), _chip(2, 4, 'Free Training'),
           _chip(2, 5, 'Rest'),
           _chip(0, 6, 'Leave to Manager')]
S37285 += [dict(rect=(129, 452, 46, 20), text='1st Half', font=['arial-bold'], style=M, autostyle=False, align='center', pad=0, min_sx=0.6, max_size=19, erase=None, colfill=dict(rect=(100, 451, 100, 26), src=99)),
           dict(rect=(239, 451, 46, 20), text='2nd Half', font=['arial-bold'], style=M, autostyle=False, align='center', pad=0, min_sx=0.6, max_size=19, erase=None, colfill=dict(rect=(212, 451, 100, 26), src=211)),
           dict(rect=(215, 485, 44, 19), text='OK', font=['arial-black', 'arial-bold'], style=MY, autostyle=False, shear=0.05, align='left', pad=0, min_sx=0.6, max_size=20, erase=None, colfill=dict(rect=(212, 483, 70, 24), src=211)),
           dict(rect=(321, 484, 91, 25), text='Special Prep', font=['arial-narrow-bold', 'arial-bold'], style=M, autostyle=False, shear=0.18, align='left', pad=1, min_sx=0.6, max_size=21)]
for k in range(4):
    S37285.append(dict(rect=(4, 389 + 32 * k, 36, 21), text='Wk %d' % (k + 1), font=['arial-bold'], style=M, autostyle=False, align='center', pad=0,
                       min_sx=0.6, max_size=20, erase=None, colfill=dict(rect=(3, 387 + 32 * k, 40, 26), src=43)))
E_WIDE = {'mode': 'mask', 'ink': [{'luma_gt': 150}, {'luma_lt': 30}], 'dilate': 2, 'fill': 'diffuse'}
S37285 += [dict(rect=(210, 194, 168, 27), text='Team Practice Orders', font=['arial-bold-italic'], style=M, autostyle=False, shear=0.05, align='center', pad=0, min_sx=0.7, max_size=22, erase=E_WIDE),
           dict(rect=(226, 226, 150, 28), text='Solo Practice Plan', font=['arial-bold-italic'], style=M, autostyle=False, shear=0.05, align='center', pad=0, min_sx=0.7, max_size=22, erase=E_WIDE)]
SPECS['37285'] = {'items': S37285, 'base': 'installed'}

# ---------------------------------------------------------------- 37173 bfgame.tbd#2 (= 37286 TRAINING.TBD#1): pre-match menu text column, 256x256
L173 = ['Positions', 'Formation', 'Tactics', 'Mid Defence', 'DF Type', 'Set Takers', 'Special Prep']
R173 = [None, 'Start Match', 'Positions', 'Change Policy', 'View Teamwork', 'Win Bonus', 'Opponent Info']
S173 = []
for k in range(7):
    S173.append(_m((2, 32 * k, 92, 32), L173[k], size=18, pad=0, erase_grow=[3, 0, 4, 0]))
    if R173[k]:
        S173.append(_m((100, 32 * k, 91, 32), R173[k], size=18, pad=0, erase_grow=[3, 0, 3, 0]))
S173[0] = _m((3, 0, 92, 32), 'Positions', size=18, pad=0, erase_grow=[3, 0, 4, 0])
SPECS['37173'] = {'items': S173}
SPECS['37286'] = SPECS['37173']

# ---------------------------------------------------------------- 37172 bfgame.tbd#1 (pal8, palette bg_pcom3.pvp): tactics / position / training plates
def _p(col, row, text):
    x0 = (0, 112, 224)[col]
    y0 = 32 * row
    return dict(rect=(x0 + 3, y0 + 3, 104, 21), text=text, font=['arial-narrow-bold', 'arial-bold'], style=CHIP, autostyle=False, shear=0.18,
                align='left', pad=0, min_sx=0.6, max_size=21, erase=E_CHIP,
                colfill=dict(rect=(x0 + 3, y0 + 2, 91, 28), src=x0 + 2), colfill2=dict(rect=(x0 + 94, y0 + 2, 14, 28), src=x0 + 109))


def _pl(x, row, text):
    return dict(rect=(x, 32 * row + 1, 104, 30), text=text, font=['arial-narrow-bold', 'arial-bold'], style=CHIP, autostyle=False, shear=0.18,
                align='left', pad=0, min_sx=0.6, max_size=21, erase={'mode': 'clear'}, erase_grow=[8, 0, 2, 0])


C1 = ['Post Play', 'Attack Right', 'Attack Left', 'Central Break', 'Counter', 'Zonal Press', 'Offside Trap', 'Zonal Press', 'Normal', 'Shooting',
      'Dribbling', 'Pass Cut', 'GK Rush Out', 'PK']
C2 = ['Target Man', 'Dribbler', 'Holding Mid', 'Stopper', 'Goalkeeper', 'Heading', 'Passing', 'Tackling', 'GK Saving', 'Place Kick']
C3 = ['Striker', 'Playmaker', 'Full-back', 'Libero', 'Endurance', 'Speed', 'Strength', 'Line', 'Libero', 'Sweeper']
C4 = ['Post Play', 'Attack Right', 'Attack Left', 'Central Break', 'Counter', 'Line', 'Libero', 'Sweeper']
S172 = [_p(0, r, t) for r, t in enumerate(C1)] + [_p(1, 4 + r, t) for r, t in enumerate(C2)] + [_p(2, 4 + r, t) for r, t in enumerate(C3)]
for r in (1, 2, 6):
    S172[r]['colfill']['srcy'] = 2
S172 += [_pl(230, 14, 'Normal')] + [_pl(342, 8 + r, t) for r, t in enumerate(C4)]
SPECS['37172'] = {'items': S172, 'palette': 'bg_pcom3.pvp'}

# ---------------------------------------------------------------- 37171 bfgame.tbd#0 (pal8, palette bg_barx.pvp): pre-match menu
YEL = {'gradient': [[0, '#ffff80'], [0.55, '#ffee10'], [1, '#d8b800']], 'outline': {'color': '#302000', 'width': 1.0},
       'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}, 'aa': False}
SIL = {'gradient': [[0, '#ffffff'], [0.5, '#dfe8f0'], [1, '#8ea4b8']], 'outline': {'color': '#101820', 'width': 0.8},
       'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}, 'aa': False}
E_ANY = {'mode': 'mask', 'ink': [{'luma_gt': 150}, {'luma_lt': 18}], 'dilate': 2, 'fill': 'diffuse'}
S171 = []
for y, t in zip((198, 239, 278, 319, 359, 398, 438, 477),
                ('Opponent Info', 'Start Match', 'Change Policy', 'Win Bonus', 'Formation', 'Change Tactics', 'Mid Defence', 'DF Type')):
    S171.append(dict(rect=(28, y, 110, 24), text=t, font=['arial-black', 'arial-bold'], style=YEL, autostyle=False, shear=0.14, align='left', pad=0,
                     min_sx=0.55, size=20, erase=None, colfill=dict(rect=(24, y - 2, 114, 28), src=139)))
AMT = ['None', '100 man', '300 man', '600 man', '1000 man', '3000 man', '5000 man', '1 oku']
for k, t in enumerate(AMT):
    y0 = 96 + 32 * k
    S171.append(dict(rect=(150, y0 + 2, 87, 22), text=t, font=['arial-black', 'arial-bold'], style=SIL, autostyle=False, shear=0.14, align='right', pad=0,
                     min_sx=0.6, size=19, erase=None, colfill=dict(rect=(150, y0 + 3, 74, 23), src=148), colfill2=dict(rect=(224, y0 + 3, 14, 26), src=244)))
    S171.append(dict(rect=(264, y0 + 1, 92, 26), text=t, font=['arial-black', 'arial-bold'], style=SIL, autostyle=False, shear=0.14, align='left', pad=0,
                     min_sx=0.6, size=19, erase={'mode': 'clear'}, erase_grow=[2, 0, 2, 2]))
S171 += [dict(rect=(146, 358, 94, 26), text='Watch Match', font=['arial-black', 'arial-bold'], style=YEL, autostyle=False, shear=0.14, align='left', pad=0,
              min_sx=0.55, size=19, erase={'mode': 'clear'}, erase_grow=[0, 6, 0, 2]),
         dict(rect=(146, 386, 94, 28), text='See Result', font=['arial-black', 'arial-bold'], style=YEL, autostyle=False, shear=0.14, align='left', pad=0,
              min_sx=0.55, size=19, erase={'mode': 'clear'}, erase_grow=[0, 0, 0, 2]),
         dict(rect=(150, 423, 92, 22), text='Current Funds', font=['arial-bold-italic'], style=SIL, autostyle=False, shear=0.0, align='left', pad=0,
              min_sx=0.6, size=16, erase=None, colfill=dict(rect=(149, 422, 88, 25), src=147)),
         dict(rect=(383, 459, 63, 24), text='man', font=['arial-black', 'arial-bold'], style=YEL, autostyle=False, shear=0.14, align='right', pad=0,
              min_sx=0.6, size=22, erase={'mode': 'flat', 'color': [0, 85, 85, 255]}, erase_grow=[2, 1, 0, 1]),
         dict(rect=(459, 451, 31, 25), text='oku', font=['arial-black', 'arial-bold'], style=YEL, autostyle=False, shear=0.14, align='center', pad=0,
              min_sx=0.6, size=20, erase={'mode': 'flat', 'color': [0, 85, 85, 255]}, erase_grow=[1, 5, 1, 1])]
SPECS['37171'] = {'items': S171, 'palette': 'bg_barx.pvp'}

# ---------------------------------------------------------------- NEWS plates (colours sampled from the old ink by art7_lib.autostyle)
def _n(rect, text, **kw):
    x, y, w, h = rect
    d = dict(rect=(x, y - 2, w, h + 4), text=text, font=['arial-bold'], min_sx=0.5, max_size=20, align='left', pad=0, erase={'mode': 'clear'}, erase_grow=[1, 0, 2, 0])
    d.update(kw)
    return d


# NEWS_CHAR.TBD#0 (36912): table captions of the post-match news; HOME AWAY / PK / H / A are English already
SPECS['36912'] = {'items': [
    _n((5, 24, 118, 24), 'Last Rank', max_size=22), _n((133, 24, 118, 24), 'This Rank', max_size=22),
    _n((1, 56, 37, 17), 'Pos', max_size=17), _n((47, 55, 70, 18), 'Club', max_size=17), _n((126, 56, 36, 17), 'Pts', max_size=17),
    _n((174, 56, 16, 17), 'W', max_size=17), _n((200, 56, 18, 17), 'L', max_size=17), _n((225, 56, 19, 17), 'D', max_size=17),
    _n((6, 80, 36, 17), 'GF', max_size=17), _n((54, 80, 36, 17), 'GA', max_size=17), _n((100, 80, 54, 17), 'GD', max_size=17),
    _n((0, 104, 43, 17), '90 min', max_size=14), _n((44, 104, 42, 16), 'V-Goal', max_size=15),
    _n((7, 135, 47, 19), 'Assists', max_size=15), _n((58, 135, 56, 19), 'Total Ast', max_size=15),
    _n((5, 168, 54, 18), 'Player', max_size=16), _n((77, 168, 45, 16), 'Goals', max_size=16, erase_grow=[1, 0, 7, 0]), _n((130, 168, 72, 16), 'Total Goals', max_size=16),
    _n((77, 200, 49, 17), 'Rating', max_size=16), _n((131, 200, 66, 17), 'Total Rtg', max_size=16),
]}

# PARTS.TBD#2 (36926): headings of the news pages; strips are 32 px high, long phrases wrap at 256 px (ランキ|ング): kept as two pieces
def _s(rect, text, **kw):
    x, y, w, h = rect
    d = dict(rect=rect, text=text, font=['arial-black', 'arial-bold'], min_sx=0.55, max_size=26, align='left', pad=1, mode='shadow',
             erase={'mode': 'clear'}, erase_grow=[0, 2, 2, 2])
    d.update(kw)
    return d


SPECS['36926'] = {'items': [
    _s((1, 0, 255, 29), "Today's Results"), _s((1, 32, 113, 29), 'Standings'), _s((1, 64, 251, 29), 'Goal Ranking'),
    _s((1, 96, 255, 29), 'Player Ratings'), _s((0, 192, 76, 29), None),
    _s((82, 196, 28, 26), 'Rd', max_size=22), _s((147, 197, 25, 24), None),
    _s((42, 226, 44, 26), '(Rd', max_size=22), _s((112, 228, 120, 25), 'End)', max_size=22),
]}

# PARTS.TBD#7 (36931): the only Japanese is ゴール (goal) beside the digit strips
SPECS['36931'] = {'items': [
    _n((162, 98, 52, 27), 'Goal', max_size=22),
]}

# PARTS.TBD#8 (36932): 得点者 (scorers) / 負傷者 (injured) tags on opaque plates: plate bands are copied across the old text, then the new text is drawn
TAGW = {'fill': '#ffffff', 'shadow': {'color': '#06281a', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}}
TAGB = {'fill': '#ffffff', 'shadow': {'color': '#10083c', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}}


def _t(x, y, w, text, sty, srcx):
    return dict(rect=(x, y, w, 24), dy=2, text=text, font=['arial-black', 'arial-bold'], style=sty, autostyle=False, align='center', pad=0, min_sx=0.6,
                max_size=22, erase=None, colfill=dict(rect=(x - 4, y, w + 8, 28), src=srcx))


SPECS['36932'] = {'items': [
    _t(14, 3, 92, 'Scorers', TAGW, 8), _t(134, 35, 92, 'Injured', TAGB, 128),
    _t(14, 67, 92, 'Scorers', TAGW, 8), _t(134, 99, 92, 'Injured', TAGB, 128),
]}

# NEWS_P0.TBD#0 (36918): extra-time markers on black cells, and the "前試合" plate (strip A + cap strip B)
YP = {'fill': '#ffff00', 'outline': {'color': '#555500', 'width': 1.0}}
BLK = {'mode': 'flat', 'color': [0, 0, 0, 204]}
GP = {'gradient': [[0, '#ffffff'], [1, '#a8a8b0']], 'shadow': {'color': '#06202c', 'dx': 1, 'dy': 1, 'steps': 1, 'alpha': 1.0}}


def _y(cx, cy, text):
    return dict(rect=(cx - 18, cy - 11, 36, 22), text=text, font=['arial-bold'], style=YP, autostyle=False, align='center', pad=0,
                min_sx=0.7, max_size=18, erase=BLK)


SPECS['36918'] = {'items': [
    _y(32, 52, 'ET'), _y(32, 76, '1H'), _y(32, 100, '2H'),
    dict(rect=(70, 66, 57, 21), text='Last Match', font=['arial-bold'], style=GP, autostyle=False, align='left', pad=0, min_sx=0.6, max_size=13,
         erase=None, colfill=dict(rect=(70, 66, 58, 21), src=69)),
    dict(rect=(64, 90, 14, 19), text=None, font=['arial-bold'], style=GP, autostyle=False, pad=0, erase=None,
         colfill=dict(rect=(64, 90, 14, 19), src=69, srcy=66)),
]}

# NEWS_PANEL.TBD#0 (36921): same tags as PARTS#8 but on bevelled opaque plates, bright (rows 0-1) and dimmed (rows 2-3)
def _sty(top, bot, sh):
    return {'gradient': [[0, top], [1, bot]], 'shadow': {'color': sh, 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}}


def _p2(x, py, w, text, sty, srcx):
    return dict(rect=(x, py + 3, w, 24), dy=2, text=text, font=['arial-black', 'arial-bold'], style=sty, autostyle=False, align='center', pad=0,
                min_sx=0.6, max_size=22, erase=None, colfill=dict(rect=(x - 4, py + 3, w + 2, 26), src=srcx))


G_B = _sty('#ffffff', '#c8d0c8', '#104521')
B_B = _sty('#ffffff', '#c8c8d4', '#212439')
G_D = _sty('#7bb88f', '#4f9663', '#185931')
B_D = _sty('#9496ad', '#6c6e92', '#313449')
SPECS['36921'] = {'items': [
    _p2(16, 0, 92, 'Scorers', G_B, 8), _p2(137, 32, 92, 'Injured', B_B, 128),
    _p2(16, 64, 92, 'Scorers', G_D, 8), _p2(137, 96, 92, 'Injured', B_D, 128),
]}

# RSLTLOGO.TBD#0 (36937): result words on opaque blue plates (vertical gradient only: plate columns are copied across the old text)
RB = {'gradient': [[0, '#ffffff'], [0.55, '#d4ecff'], [1, '#7cb8f0']], 'shadow': {'color': '#082a68', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}}


def _r(rect, text, fill):
    x, y, w, h = rect
    return dict(rect=rect, dy=1, text=text, font=['arial-black', 'arial-bold'], style=RB, autostyle=False, align='center', pad=0, min_sx=0.6,
                max_size=26, erase=None, colfill=dict(rect=fill, src=2))


SPECS['36937'] = {'items': [
    _r((5, 6, 118, 30), 'Champions', (3, 4, 126, 34)), _r((130, 6, 124, 30), 'First Advance', (130, 4, 126, 34)),
    _r((5, 46, 118, 30), 'First Title', (3, 44, 126, 34)), _r((140, 46, 100, 30), 'Leaders', (136, 44, 120, 34)),
    _r((5, 86, 118, 30), 'Advanced', (3, 84, 124, 33)),
]}

# TUTO_TG.TBD#1 (37302): 連携表示 heading (flat blue on light blue, thin horizontal lines run behind it: hfill keeps them continuous); the red figures stay
TB = {'fill': '#2a6dc6', 'aa': False}
SPECS['37302'] = {'items': [
    dict(rect=(33, 5, 262, 59), valign='top', dy=8, text='Teamwork Display', font=['arial-black', 'arial-bold'], style=TB, autostyle=False, align='left', pad=0, min_sx=0.75,
         max_size=44, shear=0.0,
         erase={'mode': 'mask', 'ink': {'color': [41, 109, 198], 'tol': 40}, 'dilate': 2, 'fill': 'hfill', 'exclude': [[46, 58, 44, 64], [244, 58, 44, 64]]}),
]}
