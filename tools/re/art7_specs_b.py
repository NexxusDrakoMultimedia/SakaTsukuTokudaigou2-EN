"""art7 specs, part B: Data Room / Dream Club books.  Labels are defined once (ref texture + rough rect + English) and found by
alpha-mask matching in every other texture of the family (art7_match.find), then repainted with autosampled colours."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import art7_lib as L
import art7_match as M

SH = dict(mode='shadow')
IT = dict(mode='shadow', shear=0.18)
PLATE_ER = {'mode': 'mask', 'ink': [{'luma_gt': 175}, {'luma_lt': 40}], 'dilate': 1, 'fill': 'hfill'}

# (ref id, rect (tight or rough), English, extra item keys)
VOCAB = [
    # --- 00347 DRSDENDO (report book)
    ('00347', (130, 97, 166, 31), 'Player List', SH),
    ('00347', (131, 139, 259, 34), 'Hall of Fame', SH),
    ('00347', (1, 194, 208, 30), 'Terms & Goals', SH),
    ('00347', (250, 194, 249, 29), 'Schedule', SH),
    ('00347', (3, 231, 298, 40), 'J.League Other Clubs', SH),
    ('00347', (2, 272, 249, 32), 'Transfer Info', SH),
    ('00347', (3, 348, 66, 17), 'Contract', dict(font='arial-narrow-bold')),
    ('00347', (75, 347, 42, 17), 'Injury', dict(font='arial-narrow-bold')),
    ('00347', (123, 348, 42, 18), 'Salary', dict(font='arial-narrow-bold')),
    ('00347', (171, 348, 43, 17), 'Age', dict(font='arial-narrow-bold')),
    ('00347', (220, 348, 42, 17), 'Goals', dict(font='arial-narrow-bold')),
    ('00347', (267, 347, 51, 18), 'Apps', dict(font='arial-narrow-bold')),
    ('00347', (323, 347, 51, 17), 'Cards', dict(font='arial-narrow-bold')),
    ('00347', (379, 347, 43, 17), 'Abroad', dict(font='arial-narrow-bold')),
    ('00347', (166, 370, 192, 26), 'Unavailable', SH),
    ('00347', (166, 396, 200, 24), 'Poor Club Finances', SH),
    ('00347', (169, 418, 51, 21), 'Bankrupt', SH),
    ('00347', (0, 448, 240, 26), 'Japan Manager Goals', dict(mode='outline', shear=0.15, inner=(4, 5, 224, 17), erase=PLATE_ER, font='arial-bold', erase_grow=0, pad=0, rgb=30)),
    ('00347', (0, 472, 240, 24), 'Game Over Conditions', dict(mode='outline', shear=0.15, inner=(4, 4, 206, 17), erase=PLATE_ER, font='arial-bold', erase_grow=0, pad=0, rgb=30)),
    ('00596', (123, 348, 43, 17), 'Salary', dict(font='arial-narrow-bold')),
    ('00596', (162, 371, 162, 22), 'Unavailable', SH),
    ('00596', (162, 394, 115, 21), 'Poor Results', SH),
    ('00362', (303, 88, 81, 27), 'Achieved', dict(mode='outline', inner=(4, 4, 73, 19), erase=PLATE_ER, erase_grow=0, pad=0, rgb=30)),
    ('00362', (302, 113, 84, 22), 'Current', dict(mode='outline', inner=(4, 3, 76, 16), erase=PLATE_ER, erase_grow=0, pad=0, rgb=30)),
    # --- 00344 dr_comm atlas
    ('00344', (0, 194, 137, 34), 'J.League', SH),
    ('00344', (137, 194, 230, 34), 'By Season', SH),
    ('00344', (2, 236, 176, 28), 'National Team', dict(mode='shadow', size=24)),
    ('00344', (186, 236, 181, 28), 'Tournament Results', dict(mode='shadow', size=24)),
    ('00344', (3, 272, 122, 32), 'Club', dict(mode='shadow', size=24)),
    ('00344', (128, 272, 163, 32), 'World Results', dict(mode='shadow', size=24)),
    ('00344', (2, 464, 135, 34), 'J.League', SH),
    ('00344', (140, 464, 181, 34), 'Current Table', SH),
    ('00344', (322, 101, 40, 19), 'Rank', SH),
    ('00344', (321, 127, 45, 17), 'Year', SH),
    # --- 00340 / 00341 / 00342 / 00343 menu atlases
    ('00340', (4, 2, 218, 31), 'Own Club Info', SH),
    ('00340', (0, 42, 223, 31), 'Other Clubs', SH),
    ('00340', (1, 82, 229, 31), 'Transfer Status', SH),
    ('00340', (0, 122, 260, 30), 'Great Players', SH),
    ('00340', (3, 162, 150, 31), 'National Team Info', SH),
    ('00340', (264, 5, 119, 24), 'Player List', IT),
    ('00340', (266, 37, 174, 24), 'Hall of Fame', IT),
    ('00340', (265, 69, 203, 23), 'Club Rep Terms', IT),
    ('00340', (266, 102, 167, 29), 'National Squad List', IT),
    ('00340', (266, 133, 218, 25), 'Japan Manager Goals', IT),
    ('00341', (1, 1, 253, 28), 'J1 Goal Rankings', SH),
    ('00341', (1, 41, 253, 28), 'J2 Goal Rankings', SH),
    ('00341', (1, 80, 262, 34), 'Rankings by Position', SH),
    ('00341', (265, 4, 219, 23), 'J1 Goal Rankings', IT),
    ('00341', (266, 35, 217, 23), 'J1 Assist Rankings', IT),
    ('00341', (265, 68, 219, 23), 'J2 Goal Rankings', IT),
    ('00341', (266, 99, 217, 23), 'J2 Assist Rankings', IT),
    ('00342', (39, 5, 143, 23), 'Ranking', IT),
    ('00342', (39, 37, 143, 23), 'Ranking', IT),
    ('00342', (39, 69, 143, 23), 'Ranking', IT),
    ('00342', (39, 101, 143, 23), 'Ranking', IT),
    ('00343', (1, 1, 201, 31), 'J.League History', SH),
    ('00343', (2, 42, 150, 30), 'Japan Team History', SH),
    ('00343', (1, 83, 150, 30), 'Tournament Results', SH),
    ('00343', (1, 121, 253, 30), 'J.League Records', SH),
    ('00343', (1, 163, 246, 28), 'Club World Results', SH),
    ('00343', (257, 163, 208, 22), 'Personal Records', IT),
    ('00343', (2, 196, 189, 23), 'Current J.League Table', IT),
    ('00343', (227, 196, 179, 22), 'Best Records', IT),
    ('00343', (1, 228, 215, 21), 'J.League By Season', IT),
    ('00343', (228, 228, 198, 22), 'Worst Records', IT),
    # --- 02281 LOCAL pvr.tbd / 00586 DRSSRANK
    ('02281', (0, 190, 209, 38), 'Finance Trend', dict(mode='shadow', thr=0.75)),
    ('02281', (0, 232, 294, 40), 'Home Development', dict(mode='shadow', thr=0.75)),
    ('02281', (296, 286, 114, 18), 'People (10k)', dict(mode='shadow', font='arial-narrow-bold')),
    ('02281', (209, 126, 140, 20), 'Amount (oku Yen)  Year', dict(mode='shadow', font='arial-narrow-bold')),
    ('02281', (3, 340, 188, 26), 'Finance Trend', dict(mode='shadow', thr=0.75)),
    ('02281', (0, 402, 256, 30), 'Home Development', dict(mode='shadow', thr=0.75)),
    ('02281', (0, 434, 256, 32), 'Sponsor Status', dict(mode='shadow', thr=0.7)),
    ('02281', (60, 464, 46, 17), 'Index', dict(mode='shadow', font='arial-narrow-bold')),
    ('02281', (258, 392, 57, 19), 'Income', SH),
    ('02281', (323, 392, 54, 19), 'Expenses', SH),
    ('02281', (386, 392, 53, 20), 'Population', SH),
    ('02281', (259, 422, 119, 22), 'Attendance', SH),
    ('02281', (386, 422, 56, 22), 'Land Price', SH),
    ('02281', (259, 454, 56, 22), 'Transport', SH),
    ('02281', (322, 454, 123, 22), 'Soccer Popularity', SH),
    ('02281', (259, 486, 118, 21), 'Club Popularity', SH),
    ('02281', (386, 486, 123, 22), 'Home History', SH),
    # --- 00362 DRSGP
    ('00362', (5, 5, 324, 33), 'Club Rep Terms', SH),
    ('00362', (2, 48, 392, 32), 'Japan Manager Goals', SH),
    ('00362', (5, 145, 182, 32), 'National Team Info', SH),
]

TARGETS = ['00340', '00341', '00342', '00343', '00344', '00347', '00362', '00586', '00587', '00596', '00603', '00616',
           '00621', '00628', '00637', '02281']

_cache = {}


def _ov(r, q):
    w = min(r[0] + r[2], q[0] + q[2]) - max(r[0], q[0])
    h = min(r[1] + r[3], q[1] + q[3]) - max(r[1], q[1])
    if w <= 0 or h <= 0:
        return False
    return w * h > 0.3 * min(r[2] * r[3], q[2] * q[3])


def _arr(i):
    if i not in _cache:
        _cache[i] = L.load(i)['arr']
    return _cache[i]


def build(targets=None, thr=0.9, report=False):
    refs = []
    for rid, rect, text, kw in VOCAB:
        a = _arr(rid)
        tb = M.tight(a, rect)
        x, y, w, h = tb
        refs.append((rid, tb, (a[y:y + h, x:x + w, 3] >= 128), text, kw, a[y:y + h, x:x + w, :3].astype(int)))
    out = {}
    for tid in (targets or TARGETS):
        a = _arr(tid)
        tg = M.Target(a)
        cand = []
        for rid, tb, mask, text, kw, rgb in refs:
            for (x, y, v) in M.find(tg, mask, kw.get('thr', thr)):
                if kw.get('rgb'):
                    win = a[y:y + tb[3], x:x + tb[2], :3].astype(int)
                    dd = np.abs(win - rgb).max(-1)[mask]
                    if np.median(dd) > kw['rgb']:
                        continue
                cand.append((v, (x, y, tb[2], tb[3]), text, kw))
        cand.sort(key=lambda c: -c[0])
        items, taken = [], []
        for v, r, text, kw in cand:
            if any(_ov(r, q) for q in taken):
                continue
            taken.append(r)
            d = dict(rect=r, text=text, font='arial-bold', pad=1, erase_grow=[1, 1, 2, 2], min_sx=0.5, max_size=40)
            d.update(kw)
            d.pop('rgb', None)
            d.pop('thr', None)
            if 'inner' in d:
                ix, iy, iw, ih = d.pop('inner')
                d['rect'] = (r[0] + ix, r[1] + iy, iw, ih)
            items.append(d)
            if report:
                print(tid, 'match', text, r, round(v, 3))
        if items:
            out[tid] = {'items': items}
    return out


SPECS = {}
_CACHE = os.path.join(L.OUT, 'specs_b.json')


def _load_cache():
    import json
    try:
        if os.path.getmtime(_CACHE) < os.path.getmtime(__file__):
            return None
        d = json.load(open(_CACHE, encoding='utf8'))
        for v in d.values():
            for it in v['items']:
                it['rect'] = tuple(it['rect'])
        return d
    except Exception:
        return None


_c = _load_cache()
if _c is None:
    _c = build()
    import json
    os.makedirs(L.OUT, exist_ok=True)
    json.dump(_c, open(_CACHE, 'w', encoding='utf8'))
SPECS.update(_c)
