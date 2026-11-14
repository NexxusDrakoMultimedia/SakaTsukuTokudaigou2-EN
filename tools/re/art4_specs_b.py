"""More jobs for tools/re/art4_run.py (group 4).  Adds to art4_specs.JOBS."""
from art4_specs import JOBS, _blk, _clr, WHITE, WHITE_I

# ------------------------------------------------------------------ NEWCON (offer menu)
JOBS['newcon'] = _blk('FLOW_PRG/NEWCON.BIN', '@293f0#0',
                      [_clr('finish', 'Finish Offer', 0, 24, 128, 23, 'w', 20)], {'w': WHITE_I})

# ------------------------------------------------------------------ SHINJIN (rookie signing banner)
JOBS['shinjin'] = _blk('ETC_DATA/SHINJIN.TBD', '#3', [
    _clr('club', 'HollyHock', 2, 1, 124, 31, 'w', 26, align='center'),
    _clr('new', 'Rookie Signing', 2, 33, 124, 31, 'w', 22, align='center')], {'w': dict(WHITE, aa=False, shadow={'color': '#000000', 'dx': 2, 'dy': 2, 'steps': 1, 'alpha': 1.0})})

# ------------------------------------------------------------------ SELNAT (national team select)
_BTN = {'mode': 'mask', 'ink': [{'luma_gt': 170}, {'luma_lt': 12}], 'dilate': 2, 'fill': 'hfill'}
_YSTY = {'font': ['arial-bold', 'segoe-ui-bold'], 'fill': '#ffff00', 'outline': {'color': '#000000', 'width': 0.8},
         'shadow': {'color': '#000000', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}}
JOBS['selnat'] = _blk('ETC_DATA/SELNAT.TBD', '#0', [
    _clr('u22', 'Japan U22', 318, 3, 186, 28, 'w', 24, align='center'),
    _clr('u23', 'Japan U23', 318, 35, 186, 28, 'w', 24, align='center'),
    _clr('jpn', 'Japan', 340, 67, 150, 28, 'w', 24, align='center', erase={'mode': 'clear'}, erase_rect=[352, 67, 130, 28]),
    _clr('ovs', 'Top Overseas Players', 340, 96, 170, 31, 'w', 20, align='center', min_sx=0.6),
    {'id': 'kt1', 'text': 'Confirm', 'x': 110, 'y': 68, 'w': 74, 'h': 22, 'style': 'y', 'size': 18, 'align': 'center',
     'min_sx': 0.7, 'pad': 0, 'erase': _BTN, 'erase_rect': [108, 66, 76, 26]},
    {'id': 'kt2', 'text': 'Confirm', 'x': 198, 'y': 68, 'w': 74, 'h': 22, 'style': 'y', 'size': 18, 'align': 'center',
     'min_sx': 0.7, 'pad': 0, 'erase': _BTN, 'erase_rect': [196, 66, 76, 26]},
], {'w': WHITE, 'y': _YSTY})

# ------------------------------------------------------------------ E003 (scout report banner)
_SCOUT = {'mode': 'mask', 'ink': [{'color': [255, 255, 255], 'tol': 90}, {'color': [51, 51, 51], 'tol': 45},
                                  {'color': [0, 0, 0], 'tol': 45}], 'dilate': 2, 'fill': 'hfill'}
JOBS['scout'] = _blk('EVENT/E003.DAT', '003_2.tbd#0', [
    {'id': 'scout', 'text': 'Scout Report', 'x': 100, 'y': 3, 'w': 152, 'h': 27, 'style': 'sc', 'size': 22, 'min_sx': 0.7,
     'align': 'center', 'pad': 0, 'erase': _SCOUT, 'erase_rect': [96, 2, 158, 29]}],
    {'sc': {'font': ['arial-bold', 'segoe-ui-bold'], 'fill': '#ffffff', 'outline': {'color': '#333333', 'width': 1.0},
            'shadow': {'color': '#333333', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}}})

# ------------------------------------------------------------------ YOUTH menu (10471)
_MINT = {'font': ['arial-bold-italic', 'segoe-ui-bold-italic'], 'gradient': [[0, '#ccffff'], [1, '#aaf0e8']],
         'outline': {'color': '#000000', 'width': 1.0}, 'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}}
_BARTXT = {'font': ['arial-bold-italic', 'segoe-ui-bold-italic'], 'fill': '#ffffff', 'outline': {'color': '#000000', 'width': 1.0},
           'shadow': {'color': '#000000', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}}
_yr = []
for _y, _lab, _age, _h, _ay in ((35, 'Policy', 19, 30, 42), (68, 'Pick Coach', 18, 30, 74), (97, 'Coach Check', 17, 32, 104)):
    _yr.append(_clr('c_' + _lab, _lab, 95, _y, 99, _h, 'm', 21))
    _yr.append(_clr('a%d' % _age, '%d yrs' % _age, 194, _ay, 44, 22, 'm', 14, min_sx=0.6))
_yr.append(_clr('swap', 'Swap', 98, 131, 94, 32, 'm', 21))
_yr.append(_clr('a16', '16 yrs', 194, 136, 44, 22, 'm', 14, min_sx=0.6))
_yr += [_clr('system', 'System', 3, 1, 100, 32, 'm', 23), _clr('tactics', 'Tactics', 1, 34, 94, 31, 'm', 22),
        _clr('midd', 'MF Defence', 2, 67, 94, 31, 'm', 22), _clr('dft', 'DF Type', 2, 96, 94, 33, 'm', 22)]
_yr += [{'id': 'yp', 'text': 'Youth Policy', 'x': 22, 'y': 162, 'w': 140, 'h': 24, 'style': 'b', 'size': 18, 'align': 'center',
         'min_sx': 0.7, 'pad': 0, 'erase': None},
        {'id': 'sp', 'text': 'Satellite Policy', 'x': 22, 'y': 208, 'w': 140, 'h': 24, 'style': 'b', 'size': 18, 'align': 'center',
         'min_sx': 0.7, 'pad': 0, 'erase': None}]
_pre = [{'rect': [18, 160, 148, 30], 'ink': [{'luma_gt': 225, 'sat_lt': 0.25}, {'luma_lt': 14}], 'dilate': 2},
        {'rect': [18, 205, 148, 30], 'ink': [{'luma_gt': 225, 'sat_lt': 0.25}, {'luma_lt': 14}], 'dilate': 2}]
JOBS['youth1'] = _blk('FLOW_PRG/YOUTH.ZAR', 'youth.tbd#1', _yr, {'m': _MINT, 'b': _BARTXT}, pre=_pre)

# ------------------------------------------------------------------ YOUTH tactics atlas (10472, 512x512 VQ)
_SILVER = {'font': ['arial-narrow-bold', 'arial-bold'], 'shear': 0.2,
           'gradient': [[0, '#ffffff'], [0.55, '#e4eaff'], [1, '#a8b8f0']],
           'outline': {'color': '#101030', 'width': 0.9}, 'shadow': {'color': '#000000', 'dx': 1.5, 'dy': 1.5, 'steps': 2, 'alpha': 1.0}}
_PILL_INK = [{'alpha_gt': 200, 'luma_gt': 140}, {'alpha_gt': 200, 'luma_lt': 14}]
_COLS = {'A': (0, 112), 'B': (112, 114), 'C': (226, 114)}
_PILLS = [
    ('A', 0, 'Post Play'), ('A', 1, 'Left Wing Attack'), ('A', 2, 'Right Wing Attack'), ('A', 3, 'Centre Break'),
    ('A', 4, 'Counter'), ('A', 5, 'Zone Press'), ('A', 6, 'Offside Trap'), ('A', 7, 'Normal'), ('A', 8, 'Zone Press'),
    ('A', 9, 'Shooting'), ('A', 10, 'Dribbling'), ('A', 11, 'Interception'), ('A', 12, 'GK Rush Out'),
    ('B', 4, 'Post Player'), ('B', 5, 'Dribbler'), ('B', 6, 'Holding Mid'), ('B', 7, 'Stopper'), ('B', 8, 'Goalkeeper'),
    ('B', 9, 'Heading'), ('B', 10, 'Passing'), ('B', 11, 'Tackling'), ('B', 12, 'GK Saving'), ('B', 13, 'Place Kick'),
    ('C', 4, 'Striker'), ('C', 5, 'Playmaker'), ('C', 6, 'Full-Back'), ('C', 7, 'Libero'), ('C', 8, 'Stamina Boost'),
    ('C', 9, 'Burst Boost'), ('C', 10, 'Strength Boost'), ('C', 11, 'Line'), ('C', 12, 'Libero'), ('C', 13, 'Sweeper'),
]
_yreg, _ypre = [], []
for _c, _r, _t in _PILLS:
    _x0, _w = _COLS[_c]
    _y = 32 * _r
    _ypre.append({'rect': [_x0 + 2, _y + 3, _w - 4, 26], 'ink': _PILL_INK, 'dilate': 2, 'rad': -1})
    _yreg.append({'id': '%s%d' % (_c, _r), 'text': _t, 'x': _x0 + 4, 'y': _y + 3, 'w': _w - 9, 'h': 24, 'style': 's', 'size': 17,
                  'min_sx': 0.7, 'align': 'center', 'pad': 0, 'erase': None})
_D = [(6, 'Post Play'), (38 + 223, 'Post Play'), (292, 'Left Wing Attack'), (325, 'Right Wing Attack'), (358, 'Centre Break'),
      (389, 'Counter'), (421, 'Line'), (453, 'Libero'), (485, 'Sweeper')]
for _i, (_y, _t) in enumerate(_D[1:]):
    _yreg.append(_clr('D%d' % _i, _t, 340, _y - 5, 120, 29, 's', 18, min_sx=0.7))
_yreg.append(_clr('Cnormal', 'Normal', 226, 449, 120, 30, 's', 18, min_sx=0.7))
JOBS['youth2'] = _blk('FLOW_PRG/YOUTH.ZAR', 'youth.tbd#2', _yreg, {'s': _SILVER}, pre=_ypre)
