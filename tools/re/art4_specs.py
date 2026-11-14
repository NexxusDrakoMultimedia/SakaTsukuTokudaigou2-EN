"""Spec registry for tools/re/art4_run.py (group 4: secretary, staff and recruiting menus)."""
JOBS = {}


def _btn(n, text):
    return {
        'file': 'ETC_DATA/SH_ICON.ZAR', 'tid': 'S3_SH_%d.TBD#1' % n,
        'spec': {
            'supersample': 4, 'quantize': 'rgb565',
            'styles': {'btn': {'font': ['tahoma-bold', 'arial-bold'], 'fill': '#000000', 'bold': 0.3}},
            'regions': [{
                'id': 'label', 'text': text, 'x': 5, 'y': 4, 'w': 118, 'h': 24, 'style': 'btn',
                'size': 'auto', 'max_size': 19, 'min_sx': 0.75, 'pad': 0,
                'erase': {'mode': 'flat', 'color': [165, 239, 239, 255]},
                'erase_rect': [5, 3, 118, 26]}]},
    }


for _n, _t in ((1, 'Schedule'), (2, 'Club Info'), (3, 'Record'), (4, 'Player Rankings'), (5, 'To Office')):
    JOBS['shicon%d' % _n] = _btn(_n, _t)


# ------------------------------------------------------------------ secretary profile plates (SS_PR1 #0..#8)
_PLATES = [
    # (record, name, name_x, birthday, hometown, hobby, white_luma_gt)
    (0, 'Yuko Takashima', 96, '19 Aug', 'Aichi', 'Ballet, Violin', 235),
    (1, 'Jennifer Scoll', 4, '24 Oct', 'England', 'Alchemy', 200),
    (2, 'Sari Yamaguchi', 96, '6 Sep', 'Kanagawa', 'Snowboarding, Marathon', 200),
    (3, 'Kyoko Mitsuya', 96, '3 Mar', 'Oita', 'Keeping Pets', 200),
    (4, 'Sayaka Shinohara', 96, '28 May', 'Hokkaido', 'Spas, Combat Sports', 200),
    (5, 'Eri Nagai', 96, '29 Sep', 'Okinawa', 'Marine Sports', 200),
    (6, 'Gloria Knowlton', 4, '1 Apr', 'USA', 'Hunting, Driving', 200),
    (7, 'Nanako Minami', 96, '14 Dec', 'Kyoto', 'Cooking, Ikebana', 200),
    (8, 'Masumi Yamasaki', 96, '2 Nov', 'Tokyo', 'Plush Toys, Shopping', 200),
]
_ROWS = [  # label, zone y, zone h
    ('Blood Type', 74, 24), ('Birthday', 102, 25), ('Hometown', 130, 25), ('Hobby', 159, 25)]
_BG = [0, 0, 0, 187]


def _dy(t):
    return 2 if any(c in t for c in 'gjpqy') else 0


BLOOD = ['AB', 'AB', 'A', 'O', None, 'B', 'AB', 'A', 'O']


def _plate(rec, name, nx, bday, home, hobby, wl):
    lab = {'font': ['segoe-ui-semibold', 'arial-bold'], 'fill': '#ffffff',
           'outline': {'color': '#000000', 'width': 0.8}, 'shadow': {'color': '#000000', 'dx': 1, 'dy': 1, 'alpha': 0.9}}
    nm = {'font': ['arial-bold-italic', 'segoe-ui-bold-italic'], 'fill': '#ffffff', 'shear': 0.0,
          'outline': {'color': '#10102a', 'width': 1.2}, 'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'alpha': 0.85, 'blur': 0.8}}
    regs = [{
        'id': 'name', 'text': name, 'x': nx, 'y': 3, 'w': 250 - nx, 'h': 31, 'style': 'nm', 'size': 22, 'dy': _dy(name),
        'min_sx': 0.6, 'align': 'right', 'pad': 1,
        'erase': {'mode': 'mask', 'ink': ([{'sat_lt': 50, 'luma_gt': wl}, {'luma_lt': 24}] if rec == 1 else {'sat_lt': 50, 'luma_gt': wl}), 'dilate': 3, 'fill': 'hfill', 'exclude': [[251, 0, 6, 40]]},
        'erase_rect': [nx, 3, 253 - nx, 31]}]
    vals = [BLOOD[rec], bday, home, hobby]
    for i, (lt, zy, zh) in enumerate(_ROWS):
        regs.append({'id': 'lab%d' % i, 'text': lt, 'x': 6, 'y': zy + 1, 'w': 90, 'h': zh - 2, 'style': 'lab', 'size': 16, 'dy': _dy(lt),
                     'min_sx': 0.6, 'align': 'left', 'pad': 0,
                     'erase': {'mode': 'flat', 'color': _BG}, 'erase_rect': [3, zy, 93, zh]})
        if vals[i]:
            regs.append({'id': 'val%d' % i, 'text': vals[i], 'x': 100, 'y': zy + 1, 'w': 152, 'h': zh - 2, 'style': 'lab',
                         'size': 16, 'dy': _dy(vals[i]), 'min_sx': 0.55, 'align': 'left', 'pad': 0,
                         'erase': {'mode': 'flat', 'color': _BG}, 'erase_rect': [96, zy, 156, zh]})
    if rec == 7:
        regs.append({'id': 'hidden', 'text': '???·W ???·H ???', 'x': 117, 'y': 46, 'w': 138, 'h': 22, 'style': 'lab', 'size': 'auto',
                     'max_size': 20, 'min_sx': 0.7, 'align': 'left', 'pad': 0,
                     'erase': {'mode': 'flat', 'color': _BG}, 'erase_rect': [112, 45, 140, 24]})
    return {'file': 'ETC_DATA/SS_TEX.ZAR', 'tid': 'SS_PR1.TBD#%d' % rec,
            'spec': {'supersample': 4, 'quantize': 'argb4444', 'styles': {'lab': lab, 'nm': nm}, 'regions': regs}}


for _p in _PLATES:
    JOBS['pr%d' % _p[0]] = _plate(*_p)


# ------------------------------------------------------------------ secretary select banner
JOBS['title'] = {
    'file': 'ETC_DATA/SS_TEX.ZAR', 'tid': 'SS_TITLE.TBD#0',
    'spec': {'supersample': 4, 'quantize': 'argb4444',
             'styles': {'glass': {
                 'font': ['impact', 'arial-black'],
                 'gradient': [[0, '#e6fafa'], [0.5, '#cceeee'], [1, '#aadadf']],
                 'outline': {'color': '#4499bb', 'width': 2.5},
                 'shadow': {'color': '#1c5a78', 'dx': 2, 'dy': 3, 'alpha': 0.75, 'blur': 1.0}}},
             'regions': [{'id': 'title', 'text': 'Secretary Select', 'x': 2, 'y': 301, 'w': 300, 'h': 74, 'style': 'glass',
                          'size': 'auto', 'max_size': 54, 'min_sx': 0.8, 'align': 'center', 'pad': 3,
                          'erase': {'mode': 'clear'}}]},
}


# ------------------------------------------------------------------ helpers
def _blk(f, t, regions, styles, q='argb4444', pre=None, dups=(), ss=4):
    j = {'file': f, 'tid': t, 'dups': list(dups),
         'spec': {'supersample': ss, 'quantize': q, 'styles': styles, 'regions': regions}}
    if pre:
        j['pre'] = pre
    return j


def _clr(i, text, x, y, w, h, style, size=20, align='left', min_sx=0.7, **kw):
    r = {'id': i, 'text': text, 'x': x, 'y': y, 'w': w, 'h': h, 'style': style, 'size': size, 'min_sx': min_sx,
         'align': align, 'pad': 1, 'erase': {'mode': 'clear'}}
    r.update(kw)
    return r


METAL = {'font': ['segoe-ui-bold', 'arial-bold'], 'gradient': [[0, '#d6e6f4'], [0.5, '#c0d0e4'], [1, '#8898bb']],
         'outline': {'color': '#000000', 'width': 1.0}, 'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}}
WHITE_I = {'font': ['arial-bold-italic', 'segoe-ui-bold-italic'], 'fill': '#ffffff',
           'outline': {'color': '#000000', 'width': 1.3}, 'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}}
WHITE = {'font': ['arial-bold', 'segoe-ui-bold'], 'fill': '#ffffff',
         'outline': {'color': '#000000', 'width': 1.3}, 'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'steps': 2, 'alpha': 1.0}}
PALE = {'font': ['arial-bold', 'segoe-ui-bold'], 'gradient': [[0, '#d6eeee'], [1, '#98b8c8']],
        'outline': {'color': '#000000', 'width': 1.0}, 'shadow': {'color': '#000000', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}}
YLW = {'font': ['arial-bold-italic', 'segoe-ui-bold-italic'], 'gradient': [[0, '#fff0a0'], [1, '#e0c830']],
       'outline': {'color': '#0a0a30', 'width': 1.2}, 'shadow': {'color': '#000020', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}}
NAVY_I = {'font': ['arial-bold-italic', 'segoe-ui-bold-italic'], 'fill': '#ffffff',
          'outline': {'color': '#000029', 'width': 1.2}, 'shadow': {'color': '#000029', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}}

# ------------------------------------------------------------------ RECON (negotiation menu)
JOBS['recon'] = _blk('FLOW_PRG/RECON.BIN', '@25758#0', [
    _clr('negotiate', 'Negotiate', 2, 36, 140, 26, 'm', 21),
    _clr('leave', 'Leave to Secretary', 2, 68, 170, 28, 'm', 21),
    _clr('dontrenew', 'Do Not Renew', 2, 100, 142, 27, 'm', 21),
    _clr('finish', 'Finish Renewals', 146, 100, 109, 27, 'm', 19),
], {'m': METAL})

# ------------------------------------------------------------------ SCDRF (scout / draft category cells)
_CELL = {'mode': 'mask', 'ink': [{'luma_gt': 165}, {'luma_lt': 40}], 'dilate': 1, 'fill': 'diffuse', 'relax': 120}


def _cell(i, text, x, y, w, h, size, **kw):
    r = {'id': i, 'text': text, 'x': x, 'y': y, 'w': w, 'h': h, 'style': 'c', 'size': size, 'min_sx': 0.6, 'align': 'center',
         'valign': 'middle', 'pad': 0, 'erase': _CELL}
    r.update(kw)
    return r


JOBS['scdrf'] = _blk('FLOW_PRG/SCDRF.BIN', '@2ff64#0', [
    _cell('dom', 'Domestic', 2, 2, 44, 20, 12),
    _cell('ovs', 'Overseas', 50, 2, 44, 20, 12),
    _cell('jprk', 'Japan\nRookies', 2, 26, 44, 20, 10, wrap=True, line_spacing=0.9),
    _cell('osrk', 'Overseas\nRookies', 50, 26, 44, 20, 10, wrap=True, line_spacing=0.9),
    _cell('style', 'Style', 51, 50, 74, 19, 15, erase_rect=[50, 50, 76, 21]),
], {'c': {'font': ['arial-bold-italic', 'segoe-ui-bold-italic'], 'gradient': [[0, '#e6fafa'], [1, '#a8d8d8']],
          'outline': {'color': '#000000', 'width': 0.8}, 'shadow': {'color': '#000000', 'dx': 1, 'dy': 1, 'alpha': 1.0}}},
    q='argb1555', dups=[('FLOW_PRG/SEARCH.BIN', '@2fcf0#0')])

# ------------------------------------------------------------------ DRAFT (07304: sign menu + filter labels)
_L = [(36, 'Sign Domestic Player'), (68, 'Sign Foreign Player'), (100, 'By Position'), (132, 'Pick a Player'), (164, 'Sign Free Agent')]
_dr = [_clr('l%d' % k, t, 0, y, 174, 27, 'w', 22) for k, (y, t) in enumerate(_L)]
_dr += [_clr('spec', 'Specified', 360, 9, 110, 23, 'p', 17),
        _clr('cap', 'CAP Candidate', 364, 56, 140, 24, 'p', 16),
        _clr('none', 'No Preference', 364, 82, 140, 22, 'p', 17)]
JOBS['draft0'] = _blk('FLOW_PRG/DRAFT.ZAR', 'draft.tbd#0', _dr, {'w': WHITE_I, 'p': PALE})

# ------------------------------------------------------------------ DRAFT (07305: position bars)
_BARS = [(0, 25, 'Goalkeeper'), (25, 24, 'Defender'), (49, 24, 'Midfielder'), (73, 24, 'Forward'), (97, 24, 'Captain Candidate'),
         (121, 26, 'No Preference')]
_pre = [{'rect': [42, y, 102, h], 'ink': [{'luma_gt': 185}, {'luma_lt': 14}], 'dilate': 2} for y, h, _ in _BARS]
_reg = [{'id': 'b%d' % k, 'text': t, 'x': 42, 'y': y + 1, 'w': 102, 'h': h - 2, 'style': 'y', 'size': 17, 'min_sx': 0.6,
         'align': 'left', 'pad': 0, 'erase': None} for k, (y, h, t) in enumerate(_BARS)]
_TEAL = {'font': ['arial-bold-italic', 'segoe-ui-bold-italic'], 'gradient': [[0, '#e6fffa'], [1, '#96e6e1']], 'aa': False,
         'outline': {'color': '#083139', 'width': 1.0}, 'shadow': {'color': '#083139', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}}
_TINK = [{'bg': [24, 148, 165], 'bg_dist_gt': 28}]
_pre += [{'rect': [24, 214, 52, 23], 'ink': _TINK, 'dilate': 1, 'rad': -1}, {'rect': [79, 214, 100, 23], 'ink': _TINK, 'dilate': 1, 'rad': -1}]
_reg += [{'id': 'age', 'text': 'Age', 'x': 24, 'y': 214, 'w': 50, 'h': 22, 'style': 't', 'size': 17, 'align': 'center', 'pad': 0, 'erase': None},
         {'id': 'club', 'text': 'Club', 'x': 79, 'y': 214, 'w': 130, 'h': 22, 'style': 't', 'size': 17, 'align': 'center', 'pad': 0, 'erase': None}]
JOBS['draft1'] = _blk('FLOW_PRG/DRAFT.ZAR', 'draft.tbd#1', _reg, {'y': dict(YLW, aa=False), 't': _TEAL}, q='argb1555', pre=_pre,
                      dups=[('FLOW_PRG/YOUTH.ZAR', 'youth.tbd#3')])

# ------------------------------------------------------------------ DRAFTK (07306: list labels)
_K = [(25, 24, 'Goalkeeper'), (48, 24, 'Defender'), (72, 24, 'Midfielder'), (97, 24, 'Forward'), (120, 24, 'Captain Candidate'),
      (145, 26, 'No Preference')]
JOBS['draftk'] = _blk('FLOW_PRG/DRAFTK.ZAR', 'draftk.tbd#0',
                      [_clr('k%d' % i, t, 0, y, 172, h, 'n', 20, aa=False) for i, (y, h, t) in enumerate(_K)],
                      {'n': dict(NAVY_I, aa=False)}, q='argb1555')

