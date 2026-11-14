"""art7 specs, part H (ar6): EVENT economy pictures and the schedule screen leftovers."""
SPECS = {}

# E024 / E025 tex.tbd: the graph pictures of the economy events: 好況 -> Boom, 不況 -> Slump
ER_BRIGHT = {'mode': 'mask', 'ink': [{'luma_gt': 110}], 'dilate': 3, 'fill': 'diffuse'}
SPECS['04361'] = {'items': [
    dict(rect=(18, 13, 98, 50), text='Boom', style={'outline': {'color': '#e06a10', 'width': 1.6}}, erase=ER_BRIGHT, font=['arial-black', 'arial-bold'], pad=2, min_sx=0.7, max_size=44),
]}
SPECS['04378'] = {'items': [
    dict(rect=(24, 102, 98, 50), text='Slump', style={'outline': {'color': '#10c0d8', 'width': 1.6}}, erase=ER_BRIGHT, font=['arial-black', 'arial-bold'], pad=2, min_sx=0.7, max_size=40),
]}

# FLOW_PRG TWND*.ZAR selb.tbd#0: the town menu labels (two variants: 08663 yellow, 08805 white), eight rows of 32 px + 代表グラウンド
def _selb(rows, texts, last2):
    items = []
    for y, t in zip(rows, texts):
        items.append(dict(rect=(2, y, 94, 28), text=t, font=['arial-narrow-bold', 'arial-bold'], pad=1, min_sx=0.5, max_size=24,
                          shear=0.18, align='left', erase={'mode': 'clear'}, erase_grow=[0, 2, 0, 2]))
    items.append(dict(rect=(97, rows[-1], 94, 28), text=last2, font=['arial-narrow-bold', 'arial-bold'], pad=1, min_sx=0.5, max_size=24,
                      shear=0.18, align='left', erase={'mode': 'clear'}, erase_grow=[0, 2, 0, 2]))
    return {'items': items}


SPECS['08663'] = _selb([3, 35, 66, 98, 132, 162, 194, 226],
                       ['Next Day', 'Office', 'Training', 'Meeting Room', 'Youth', 'Supporters', 'Local Groups', 'End/Setup'], 'National Ground')
SPECS['08805'] = _selb([2, 34, 66, 98, 130, 162, 194, 226],
                       ['Next Day', 'Office', 'Training', 'Meeting Room', 'Sub Ground', 'Supporters', 'Local Info', 'End/Setup'], 'National Ground')

# ---- single plates and small lists found by the ar6 inventory ----
ER_LIGHT_DARK = {'mode': 'mask', 'ink': [{'luma_gt': 165}, {'luma_lt': 40}], 'dilate': 2, 'fill': 'hfill'}
ER_DARK = {'mode': 'mask', 'ink': [{'luma_lt': 110}], 'dilate': 2, 'fill': 'hfill'}
# ALLJINI.ZAR jini11.tbd: cyan plates with dark text (07009 07018 07021)
for _i, _t in (('07009', 'Sign Player'), ('07018', 'Change Manager'), ('07021', 'Change Scout')):
    SPECS[_i] = {'items': [dict(rect=(8, 6, 112, 21), text=_t, erase={'mode': 'flat'}, dark=True, font=['arial-bold'], pad=1, min_sx=0.6, max_size=19,
                                style={'fill': '#101828'})]}
# ENDOPT.TBD#3 (00805): menu entries, gold on transparent
SPECS['00805'] = {'items': [
    dict(rect=(3, 2, 154, 32), text='Free Players', mode='shadow', font=['arial-bold'], max_size=27, min_sx=0.6, align='left', erase_grow=[0, 2, 4, 6]),
    dict(rect=(1, 49, 158, 33), text='Opponent Clubs', mode='shadow', font=['arial-bold'], max_size=27, min_sx=0.6, align='left', erase_grow=[0, 2, 4, 6]),
    dict(rect=(2, 97, 249, 33), text='Legend Clubs', mode='shadow', font=['arial-bold'], max_size=27, min_sx=0.6, align='left', erase_grow=[0, 2, 4, 6]),
]}
# CLUBHOUS.DAT#22 / STADIUM.DAT (00281): facility status tags
SPECS['00281'] = {'items': [
    dict(rect=(3, 6, 106, 21), text='Can Expand', erase=ER_LIGHT_DARK, font=['arial-black', 'arial-bold'], min_sx=0.6, max_size=19, style={'fill': '#ffffff', 'outline': {'color': '#000000', 'width': 1}}),
    dict(rect=(3, 37, 106, 21), text='To Be Removed', erase=ER_LIGHT_DARK, font=['arial-black', 'arial-bold'], min_sx=0.6, max_size=19, style={'fill': '#ffffff', 'outline': {'color': '#000000', 'width': 1}}),
    dict(rect=(3, 68, 106, 22), text='Can Rebuild', erase={'mode': 'mask', 'ink': [{'luma_gt': 110, 'sat_gt': 0.5}, {'luma_lt': 35}], 'dilate': 2, 'fill': 'hfill'},
         font=['arial-black', 'arial-bold'], min_sx=0.6, max_size=19, style={'fill': '#e8e800', 'outline': {'color': '#000000', 'width': 1}}),
]}
# DCE_TEX.ZAR (00339): the two player-pool cards
ER_CAP = {'mode': 'mask', 'ink': [{'luma_gt': 135, 'sat_lt': 0.35}, {'luma_lt': 40}], 'dilate': 2, 'fill': 'hfill'}
SPECS['00339'] = {'items': [
    dict(rect=(14, 111, 94, 27), text='Domestic', erase=ER_CAP, font=['arial-bold'], min_sx=0.6, max_size=22,
         style={'gradient': [[0, '#ffffff'], [1, '#9aa0a8']], 'outline': {'color': '#0a2a14', 'width': 1.2}}),
    dict(rect=(142, 111, 94, 27), text='Overseas', erase=ER_CAP, font=['arial-bold'], min_sx=0.6, max_size=22,
         style={'gradient': [[0, '#ffffff'], [1, '#9aa0a8']], 'outline': {'color': '#0a2a3a', 'width': 1.2}}),
]}
# TITLEM.DAT#7 (00109): the tagline under the title logo; only the Japanese part is replaced (J.LEAGUE stays)
SPECS['00109'] = {'items': [
    dict(rect=(142, 3, 366, 24), text="Make a Pro Football Club!", mode='outline', font=['arial-black', 'arial-bold'], min_sx=0.6, max_size=24, align='left',
         erase={'mode': 'clear'}, erase_grow=[2, 2, 2, 2], style={'fill': '#ffffff', 'outline': {'color': '#000000', 'width': 1.6}}),
]}
# 08688 TWND1.ZAR economy gauge labels
_EC = {'fill': '#e8e8f0', 'outline': {'color': '#202030', 'width': 1}}
SPECS['08688'] = {'items': [
    dict(rect=(1, 17, 49, 13), text='Big Boom', erase={'mode': 'clear'}, font=['arial-bold'], min_sx=0.6, max_size=13, align='left', style=_EC, erase_grow=[0, 1, 2, 1]),
    dict(rect=(1, 33, 33, 13), text='Boom', erase={'mode': 'clear'}, font=['arial-bold'], min_sx=0.6, max_size=13, align='left', style=_EC, erase_grow=[0, 1, 2, 1]),
    dict(rect=(1, 49, 48, 13), text='Flat', erase={'mode': 'clear'}, font=['arial-bold'], min_sx=0.6, max_size=13, align='left', style=_EC, erase_grow=[0, 1, 2, 1]),
    dict(rect=(1, 65, 33, 13), text='Slump', erase={'mode': 'clear'}, font=['arial-bold'], min_sx=0.6, max_size=13, align='left', style=_EC, erase_grow=[0, 1, 2, 1]),
    dict(rect=(1, 81, 49, 13), text='Crash', erase={'mode': 'clear'}, font=['arial-bold'], min_sx=0.6, max_size=13, align='left', style=_EC, erase_grow=[0, 1, 2, 1]),
]}
# 07023 (ALLJINI.ZAR scsitei): position list
SPECS['07023'] = {'items': [
    dict(rect=(2, 26, 140, 21), text='Goalkeeper', mode='shadow', font=['arial-bold'], max_size=19, min_sx=0.6, align='left', shear=0.18, erase_grow=[0, 1, 3, 4]),
    dict(rect=(1, 49, 141, 22), text='Defender', mode='shadow', font=['arial-bold'], max_size=19, min_sx=0.6, align='left', shear=0.18, erase_grow=[0, 1, 3, 4]),
    dict(rect=(1, 73, 148, 21), text='Midfielder', mode='shadow', font=['arial-bold'], max_size=19, min_sx=0.6, align='left', shear=0.18, erase_grow=[0, 1, 3, 4]),
    dict(rect=(3, 98, 101, 21), text='Forward', mode='shadow', font=['arial-bold'], max_size=19, min_sx=0.6, align='left', shear=0.18, erase_grow=[0, 1, 3, 4]),
    dict(rect=(1, 121, 160, 22), text='Captain Candidate', mode='shadow', font=['arial-bold'], max_size=19, min_sx=0.6, align='left', shear=0.18, erase_grow=[0, 1, 3, 4]),
    dict(rect=(2, 146, 92, 21), text='Unspecified', mode='shadow', font=['arial-bold'], max_size=19, min_sx=0.6, align='left', shear=0.18, erase_grow=[0, 1, 3, 4]),
]}

# NEWS/PARTS.TBD#3 (36927): standings table captions of the TV sports news (white) and the round names (green)
def _pt(rect, text, **kw):
    d = dict(rect=rect, text=text, font=['arial-bold'], min_sx=0.5, max_size=18, align='left', pad=1, erase={'mode': 'clear'}, erase_grow=[1, 1, 2, 2])
    d.update(kw)
    return d


SPECS['36927'] = {'items': [
    _pt((2, 34, 106, 19), 'Last Rank'), _pt((114, 34, 105, 19), 'This Rank'),
    _pt((2, 65, 42, 21), 'Pos'), _pt((50, 65, 78, 21), 'Club'), _pt((146, 65, 59, 21), 'Player'),
    _pt((3, 97, 39, 20), 'GF'), _pt((50, 97, 39, 20), 'GA'), _pt((98, 97, 61, 20), 'GD'),
    _pt((3, 130, 40, 20), 'Pts'), _pt((61, 130, 20, 20), 'W'), _pt((110, 130, 19, 20), 'L'), _pt((158, 130, 19, 20), 'D'),
    _pt((194, 130, 49, 26), 'Rd'),
    _pt((2, 161, 81, 22), 'Total GF'), _pt((98, 161, 77, 22), 'GF This Rd'),
    _pt((186, 161, 23, 26), 'Rd'), _pt((230, 161, 25, 26), None),
    _pt((2, 193, 60, 20), 'Total Rtg'), _pt((83, 193, 80, 20), 'This Rating'),
    _pt((1, 229, 72, 24), 'Semi-Final'), _pt((81, 229, 96, 24), 'Quarter-Final'), _pt((194, 229, 47, 24), 'Final'),
]}
