"""Spec registry for tools/re/s7g_run.py (in-match tag textures of GAME/GAMEETC.ZAR, FACEMDUL tiles)."""
JOBS = {}
GE = 'GAME/GAMEETC.ZAR'

WHITE = {'font': ['arial-narrow-bold', 'arial-bold'], 'fill': '#f2f2fa', 'aa': False, 'bold': 0.8, 'outline': {'color': '#181820', 'width': 1.0}, 'shadow': {'color': '#000000', 'dx': 1, 'dy': 1, 'alpha': 1.0}}
GOLD = {'font': ['arial-black'], 'gradient': [[0, '#fff060'], [0.5, '#ffb800'], [1, '#e87000']],
        'outline': {'color': '#6a3000', 'width': 1.0}, 'shadow': {'color': '#202040', 'dx': 1.5, 'dy': 1.5, 'alpha': 0.85}}

JOBS['ktss03'] = dict(file=GE, tid='@110/ktss03.pvr', spec={
    'supersample': 4, 'quantize': 'argb4444', 'styles': {'w': WHITE},
    'regions': [{'id': 'head', 'text': 'Change Tactics', 'x': 1, 'y': 93, 'w': 105, 'h': 32, 'style': 'w', 'size': 23, 'min_sx': 0.6,
                 'erase': {'mode': 'flat', 'color': [255, 255, 255, 0]}, 'erase_rect': [0, 92, 110, 36]}]})

JOBS['skparts2'] = dict(file=GE, tid='@110/sk_parts2.pvr', spec={
    'supersample': 4, 'quantize': 'argb4444', 'styles': {'g': GOLD},
    'regions': [{'id': 'th', 'text': 'th', 'x': 62, 'y': 84, 'w': 38, 'h': 34, 'style': 'g', 'size': 34,
                 'min_sx': 0.7, 'erase': {'mode': 'flat', 'color': [0, 0, 0, 0]}, 'erase_rect': [60, 82, 42, 40]}]})


YEL = {'font': ['arial-black'], 'gradient': [[0, '#fff49a'], [0.45, '#ffdd33'], [1, '#e0a800']],
       'outline': {'color': '#3a2200', 'width': 1.0}, 'shadow': {'color': '#000000', 'dx': 1.5, 'dy': 1.5, 'alpha': 0.55}}


def _cell(i, text, x, y, w, h, size=22, **kw):
    d = {'id': i, 'text': text, 'x': x, 'y': y, 'w': w, 'h': h, 'style': 'y', 'size': size, 'min_sx': 0.5,
         'erase': {'mode': 'flat', 'color': [0, 0, 0, 0]}}
    d.update(kw)
    return d


JOBS['taisen'] = dict(file=GE, tid='@110/taisenhyoji.pvr', spec={
    'supersample': 4, 'quantize': 'argb4444', 'styles': {'y': YEL},
    'regions': [
        _cell('dai', 'No.', 60, 28, 35, 36),
        _cell('setsu', 'MD', 96, 28, 31, 36),
        _cell('kaisen', 'Round', 127, 28, 62, 36),
        _cell('kessho', 'Final', 192, 28, 62, 36, size=24),
        _cell('jun', 'Semi-final', 1, 64, 91, 36, size=22),
        _cell('i', 'th', 62, 126, 34, 34, size=30, erase_rect=[60, 123, 37, 40]),
    ]})


def _grad(bottom):
    return {'font': ['arial-narrow-bold', 'arial-bold'], 'gradient': [[0, '#ffffff'], [0.45, '#f4f4f4'], [1, bottom]], 'bold': 0.6,
            'outline': {'color': '#000000', 'width': 1.0}, 'shadow': {'color': '#000000', 'dx': 1, 'dy': 1, 'alpha': 0.7}}


def _sak(i, text, y, h, bottom):
    return {'id': i, 'text': text, 'x': 0, 'y': y, 'w': 128, 'h': h, 'style': 's_' + i, 'size': 23, 'min_sx': 0.6, 'align': 'left', 'dx': 1,
            'erase': {'mode': 'flat', 'color': [0, 0, 0, 0]}, 'erase_rect': [0, y - 1, 128, h + 2]}


JOBS['sakusen'] = dict(file=GE, tid='@110/sakusen.pvr', spec={
    'supersample': 4, 'quantize': 'argb4444',
    'styles': {'s_a': _grad('#eeee11'), 's_b': _grad('#77dddd'), 's_c': _grad('#aa33bb'), 's_d': _grad('#dd2255')},
    'regions': [_sak('a', 'Attack/Defend', 0, 28, ''), _sak('b', 'Hold', 31, 28, ''), _sak('c', 'All Defend', 63, 28, ''),
                _sak('d', 'All Attack', 95, 28, '')]})


_INK = [{'luma_lt': 75}, {'luma_gt': 205}]
JOBS['pkparts1'] = dict(file=GE, tid='@110/pk_parts1.pvr', spec={
    'supersample': 4, 'quantize': 'rgb565',
    'styles': {
        'auto': {'font': ['arial-narrow-bold', 'arial-bold'], 'fill': '#a5fbff', 'bold': 0.4,
                 'outline': {'color': '#001821', 'width': 1.0}, 'shadow': {'color': '#001821', 'dx': 1, 'dy': 1, 'alpha': 1.0}},
        'ok': {'font': ['arial-black'], 'fill': '#ffe4e4', 'outline': {'color': '#380000', 'width': 1.0},
               'shadow': {'color': '#380000', 'dx': 1, 'dy': 1, 'alpha': 1.0}}},
    'regions': [
        {'id': 'auto', 'text': 'Auto Select', 'x': 8, 'y': 55, 'w': 112, 'h': 28, 'style': 'auto', 'size': 24, 'min_sx': 0.6,
         'erase': {'mode': 'mask', 'ink': _INK, 'dilate': 2, 'fill': 'hfill'}, 'erase_rect': [7, 54, 114, 30]},
        {'id': 'ok', 'text': 'Confirm', 'x': 14, 'y': 92, 'w': 100, 'h': 28, 'style': 'ok', 'size': 24, 'min_sx': 0.6,
         'erase': {'mode': 'mask', 'ink': _INK, 'dilate': 2, 'fill': 'hfill'}, 'erase_rect': [12, 91, 104, 30]}]})


def _face(file, tid, text, size=50):
    return dict(file=file, tid=tid, spec={
        'supersample': 4, 'quantize': 'rgb565',
        'styles': {'f': {'font': ['impact', 'arial-black'], 'fill': '#ffffff', 'aa': False, 'outline': {'color': '#6a0000', 'width': 1.2},
                         'shadow': {'color': '#500000', 'dx': 2, 'dy': 2, 'alpha': 0.9}}},
        'regions': [{'id': 'w', 'text': text, 'x': 6, 'y': 20, 'w': 116, 'h': 88, 'style': 'f', 'size': size, 'min_sx': 0.5,
                     'erase': {'mode': 'mask', 'ink': {'sat_lt': 0.45}, 'dilate': 2, 'fill': 'diffuse'}, 'erase_rect': [0, 0, 128, 128]}]})


FM = 'ATFIRST/FACEMDUL.DAT'
JOBS['face_dai'] = _face(FM, '@cb7e0/kao_g_dai.pvr', 'Big')
JOBS['face_toku'] = _face(FM, '@cb7e0/kao_r_toku.pvr', 'Special')
JOBS['face_gou'] = _face(FM, '@cb7e0/kao_y_gou.pvr', 'Issue')
