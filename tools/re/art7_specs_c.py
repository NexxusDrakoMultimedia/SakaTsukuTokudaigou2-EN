"""art7 specs, part C: manual items for data-room / dream-club textures that the label matcher cannot do alone.
EXTRA[id] items are appended to the matcher items of art7_specs_b for the same id."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import art7_specs_b as B

SH = dict(mode='shadow')
WHT = {'fill': '#ffffff', 'outline': {'color': '#101030', 'width': 1}}
ER_WB = {'mode': 'mask', 'ink': [{'luma_gt': 215}, {'luma_lt': 45}], 'dilate': 1, 'fill': 'hfill'}


def S(rect, text, **kw):
    d = dict(rect=rect, text=text, mode='shadow', font='arial-bold', pad=1, erase_grow=[1, 1, 2, 2], min_sx=0.5, max_size=40)
    d.update(kw)
    return d


EXTRA = {}

# DRSSRANK: local investment trend (large + small), home history bar
EXTRA['00586'] = [
    S((1, 274, 286, 33), 'Local Investment Trend'),
    S((2, 372, 252, 26), 'Local Investment Trend', erase_grow=[0, 0, 1, 1]),
]
EXTRA['00587'] = [
    dict(rect=(7, 66, 145, 19), text='Home History', align='left', mode='shadow', font='arial-bold', pad=0,
         erase={'mode': 'mask', 'ink': [{'luma_gt': 225}, {'luma_lt': 120}], 'dilate': 1, 'fill': 'hfill'}),
]

# DRSUBR1: ranking table header
EXTRA['00621'] = [
    S((2, 323, 34, 19), 'Rank', max_size=16),
    S((40, 323, 39, 19), 'Goals', max_size=16),
    S((90, 323, 51, 19), 'Player', max_size=16),
    S((147, 323, 67, 19), 'Club', max_size=16),
    S((218, 323, 73, 19), 'Nationality', max_size=16),
    dict(rect=(57, 285, 42, 20), text='Year', mode='shadow', font='arial-bold', pad=0, align='center',
         erase={'mode': 'mask', 'ink': [{'luma_gt': 170, 'sat_gt': 0.25}, {'luma_lt': 70}], 'dilate': 1, 'fill': 'hfill'}),
]

# DRSUBS2: records page
EXTRA['00637'] = [
    S((128, 145, 97, 22), 'Losing Streak'),
    S((232, 145, 145, 22), 'Fewest Goals Scored'),
    S((128, 169, 144, 22), 'Most Goals Conceded'),
    S((128, 288, 144, 22), 'Consecutive Titles'),
    S((280, 288, 96, 22), 'Win Streak'),
    S((128, 312, 168, 22), 'Clean Sheet Streak'),
    S((304, 312, 145, 22), 'Highest Score'),
    S((128, 337, 140, 22), 'Fewest Conceded'),
    S((277, 337, 140, 22), 'Most Goals Scored'),
    S((128, 362, 144, 21), 'Scoring Streak'),
    S((281, 362, 184, 21), 'Most Hat-tricks'),
    S((2, 389, 68, 26), 'Titles', size=22),
    S((73, 389, 69, 26), 'Wins', size=22),
    S((146, 390, 69, 25), 'Matches', size=22),
    S((218, 390, 67, 25), 'Goals', size=22),
    S((291, 390, 66, 26), 'Conceded', size=22),
    S((1, 430, 69, 25), 'Losses', size=22),
    S((74, 430, 67, 26), 'Goals', size=22),
    S((147, 430, 66, 25), 'Conceded', size=22),
]

# DCEMAIN / DCE_TEX
R = dict(align='right', max_size=26)
EXTRA['00332'] = [
    S((100, 66, 285, 38), 'Password Players', **R),
    S((264, 108, 121, 36), 'Select Players', **R),
    S((40, 148, 345, 32), 'Save Dream Club Data', **R),
    S((41, 187, 344, 34), 'Load Dream Club Data', **R),
    S((155, 228, 230, 34), 'Confirm Members', **R),
    S((82, 270, 303, 32), 'Finish Member Selection', **R),
    dict(rect=(273, 317, 78, 20), text='Confirm', mode='outline', font='arial-bold', pad=0,
         erase={'mode': 'mask', 'ink': [{'color': [255, 235, 0], 'tol': 100}, {'color': [0, 0, 0], 'tol': 28}], 'dilate': 1, 'fill': 'hfill'},
         erase_grow=[10, 12, 10, 2], style={'fill': '#ffee00', 'outline': {'color': '#000000', 'width': 1}}),
    S((5, 445, 145, 31), 'Key Players', align='left', max_size=28),
    dict(rect=(402, 202, 94, 18), text='Domestic', mode='outline', font='arial-bold', pad=0, erase=ER_WB, erase_grow=0),
    dict(rect=(402, 353, 94, 18), text='Overseas', mode='outline', font='arial-bold', pad=0, erase=ER_WB, erase_grow=0),
]
EXTRA['00337'] = [
    S((180, 64, 206, 38), 'Free Player Select', **R),
    S((264, 107, 122, 34), 'Select Players', **R),
    S((40, 148, 346, 34), 'Save Dream Club Data', **R),
    S((41, 187, 341, 35), 'Load Dream Club Data', **R),
    S((155, 228, 231, 34), 'Confirm Members', **R),
    S((82, 268, 304, 34), 'Finish Member Selection', **R),
    S((2, 414, 88, 31), 'Confirm', align='left', max_size=28),
]

# DRMENU dr_comm #1 (00345): championship history page
EXTRA['00345'] = [
    dict(rect=(217, 64, 32, 18), text='Year', mode='outline', font='arial-bold', pad=0, erase=ER_WB, erase_grow=0, style=WHT),
    dict(rect=(217, 185, 32, 17), text='Year', mode='outline', font='arial-bold', pad=0, erase=ER_WB, erase_grow=0, style=WHT),
    dict(rect=(4, 76, 88, 18), text='Champion Club', mode='shadow', font='arial-bold', pad=0, align='left',
         erase={'mode': 'mask', 'ink': [{'color': [200, 185, 80], 'tol': 80}, {'color': [120, 100, 40], 'tol': 70}], 'dilate': 1, 'fill': 'hfill'}),
    dict(rect=(3, 126, 68, 15), text='Apps /', mode='outline', font='arial-bold', pad=0, align='left', erase=ER_WB, erase_grow=0, style=WHT),
    dict(rect=(121, 126, 13, 15), text='x', mode='outline', font='arial-bold', pad=0, erase=ER_WB, erase_grow=0, style=WHT),
    dict(rect=(144, 126, 41, 15), text='Titles /', mode='outline', font='arial-bold', pad=0, align='left', erase=ER_WB, erase_grow=0, style=WHT),
    dict(rect=(232, 126, 15, 15), text='x', mode='outline', font='arial-bold', pad=0, erase=ER_WB, erase_grow=0, style=WHT),
    dict(rect=(3, 214, 68, 15), text='Apps /', mode='outline', font='arial-bold', pad=0, align='left', erase=ER_WB, erase_grow=0, style=WHT),
    dict(rect=(121, 214, 13, 15), text='x', mode='outline', font='arial-bold', pad=0, erase=ER_WB, erase_grow=0, style=WHT),
    dict(rect=(144, 214, 41, 15), text='Titles /', mode='outline', font='arial-bold', pad=0, align='left', erase=ER_WB, erase_grow=0, style=WHT),
    dict(rect=(232, 214, 15, 15), text='x', mode='outline', font='arial-bold', pad=0, erase=ER_WB, erase_grow=0, style=WHT),
    dict(rect=(5, 163, 170, 46), text='Champions', mode='shadow', font='arial-black', pad=0, min_sx=0.6,
         erase={'mode': 'mask', 'ink': [{'color': [245, 245, 100], 'tol': 90}, {'color': [160, 160, 40], 'tol': 70}, {'luma_lt': 78}], 'dilate': 2, 'fill': 'diffuse'}),
    dict(rect=(2, 236, 24, 17), text='th', mode='outline', font='arial-bold', pad=0, erase={'mode': 'clear'}, erase_grow=[1, 1, 1, 1], style=WHT),
    dict(rect=(30, 236, 83, 17), text='Knocked Out', mode='outline', font='arial-bold', pad=0, align='left', erase={'mode': 'clear'}, erase_grow=[1, 1, 1, 1], style=WHT),
]

# skeptic pass: leftover kanji on dr_comm atlas #0 (00344)
EXTRA['00344'] = [
    dict(rect=(247, 139, 16, 14), text='th', mode='outline', font='arial-bold', pad=0, erase={'mode': 'clear'}, erase_grow=[3, 10, 3, 6], style=WHT),
    dict(rect=(306, 398, 26, 20), text='Yr', mode='outline', font='arial-bold', pad=0, erase={'mode': 'mask', 'ink': [{'color': [165, 175, 220], 'tol': 75}, {'color': [90, 90, 150], 'tol': 60}, {'luma_gt': 200}], 'dilate': 2, 'fill': 'hfill'}, erase_grow=0, style=WHT),
]
EXTRA['00628'] = list(EXTRA['00344'])

SPECS = {}
for _id, _items in EXTRA.items():
    SPECS[_id] = {'items': list(B.SPECS.get(_id, {}).get('items', [])) + _items}
