"""s7e specs (End/Option owner, stage 7): items for tools/re/s7e_run.py (same item format as art7_lib.repaint)."""
SPECS = {}
ALLOW_RECENT = {'00586', '02281', '10470', '10474'}   # installed file only carries the lower-case oku header edit (mn6): paint on top of it
WHITE = {'fill': '#ffffff'}

# 03550 OPTION.DAT: value plates, letter-spaced white text like the existing ON / OFF / STEREO
def V(rect, text, **kw):
    d = dict(rect=rect, text=text, font='arial-bold', align='center', pad=0, erase_grow=1, min_sx=0.6, style=WHITE, autostyle=False,
             max_size=20, letter_spacing=2)
    d.update(kw)
    return d

SPECS['03550'] = {'items': [
    V((340, 30, 55, 22), 'Near'),
    V((340, 62, 55, 22), 'Mid'),
    V((340, 94, 55, 22), 'Far'),
    V((423, -1, 51, 21), '1 min', align='left', letter_spacing=1),
    V((423, 30, 51, 21), '3 min', align='left', letter_spacing=1),
    V((423, 62, 51, 21), '5 min', align='left', letter_spacing=1),
]}

# 03266 MEETING.ZAR pvr.tbd: strength meter end caps
ER_CAP = {'mode': 'mask', 'ink': [{'luma_gt': 215}, {'luma_lt': 45}], 'dilate': 2, 'fill': 'hfill'}
CAP = {'fill': '#ffffff', 'outline': {'color': '#000000', 'width': 1}}
SPECS['03266'] = {'items': [
    dict(rect=(194, 138, 29, 22), text='Weak', erase=ER_CAP, font='arial-narrow-bold', pad=0, style=CAP, autostyle=False,
         erase_grow=1, shear=0.2, min_sx=0.5, max_size=14),
    dict(rect=(226, 138, 29, 22), text='Strong', erase=ER_CAP, font='arial-narrow-bold', pad=0, style=CAP, autostyle=False,
         erase_grow=1, shear=0.2, min_sx=0.5, max_size=14),
]}

# 00344 DRMENU.ZAR dr_comm.tbd#0: bottom-right year plate (年目); the plate (grey dither + slanted blue band) is rebuilt first
def pre_00344(a):
    for x in range(444, 496):
        if x <= 456:
            T = 504
        elif x >= 472:
            T = 496
        else:
            T = int(round(504 - (x - 456) * 0.5))
        c = 400 + ((x - 444) % 40)
        for y in range(476, 504):
            if y < T:
                a[y, x] = a[y, c]
        a[T, x] = a[504, c]
        a[T + 1, x] = a[505, c]
        for y in range(T + 2, 510):
            a[y, x] = a[506 + ((y - T - 2) % 4), c]
        a[510, x] = a[510, c]
        a[511, x] = a[511, c]


SPECS['00344'] = {'pre': pre_00344, 'items': [
    dict(rect=(449, 484, 41, 21), text='Yr', erase=None, align='right', font='arial-bold', pad=0, autostyle=False, max_size=21, min_sx=0.7,
         style={'gradient': [[0, [255, 240, 170]], [1, [225, 185, 100]]], 'shadow': {'color': [34, 34, 51], 'dx': 1, 'dy': 1, 'blur': 0, 'alpha': 0.9}}),
]}


# 00803 ENDOPT.TBD#1: End/Option menu entries, gold on transparent (same look as the ar6 00805 column)
def _end(rect, text):
    return dict(rect=rect, text=text, mode='shadow', font=['arial-bold'], max_size=27, min_sx=0.6, align='left', erase_grow=[0, 2, 4, 6])


SPECS['00803'] = {'items': [
    _end((1, 0, 221, 36), 'Save and Quit'),
    _end((3, 48, 161, 37), 'Create Data'),
    _end((2, 95, 160, 36), 'Options'),
    _end((1, 143, 194, 36), 'Backup'),
]}


# 00586 DRSSRANK.TBD#1 / 02281 LOCAL.ZAR pvr.tbd#0: the four unit glyph cells beside the digit strip (億 円 / 万 人)
def _unit(rect, text, **kw):
    return dict(rect=rect, text=text, mode='shadow', font=['arial-narrow-bold', 'arial-bold'], max_size=27, min_sx=0.45, pad=1, erase_grow=2, **kw)


_UNITS = [_unit((377, 97, 23, 29), 'oku'), _unit((410, 97, 30, 29), 'Yen'), _unit((377, 130, 25, 29), 'man'), _unit((410, 130, 23, 29), 'ppl', dy=-3)]
SPECS['00586'] = {'items': _UNITS}
SPECS['02281'] = {'items': _UNITS}


# 10470 YOUTH.ZAR youth.tbd#0: labels under the player icons and on the orange tags
ER_GREY = {'mode': 'mask', 'ink': [{'luma_gt': 150}, {'luma_lt': 90}], 'dilate': 3, 'fill': 'hfill'}
ER_TAG = {'mode': 'mask', 'ink': [{'luma_gt': 200}, {'luma_lt': 90}], 'dilate': 3, 'fill': 'hfill'}
_GREYSTY = {'fill': '#d8dcd0', 'shadow': {'color': [20, 20, 30], 'dx': 1, 'dy': 1, 'blur': 0, 'alpha': 0.9}}
_TAGSTY = {'fill': '#fff4dc', 'shadow': {'color': [60, 30, 10], 'dx': 1, 'dy': 1, 'blur': 0, 'alpha': 0.9}}
SPECS['10470'] = {'items': [
    dict(rect=(132, 144, 85, 24), text='Trainee', erase=ER_GREY, font=['arial-bold'], max_size=19, min_sx=0.6, autostyle=False, style=_GREYSTY, pad=0, erase_grow=1),
    dict(rect=(222, 146, 72, 20), text='Successor', erase=ER_GREY, font=['arial-bold'], max_size=19, min_sx=0.55, autostyle=False, style=_GREYSTY, pad=0, erase_grow=1),
    dict(rect=(322, 143, 138, 26), text='Pick Coach', erase=ER_TAG, font=['arial-bold'], max_size=20, min_sx=0.6, shear=0.2, autostyle=False, style=_TAGSTY, pad=0, erase_grow=1),
    dict(rect=(281, 183, 132, 26), text='Coach Check', erase=ER_TAG, font=['arial-bold'], max_size=20, min_sx=0.6, shear=0.2, autostyle=False, style=_TAGSTY, pad=0, erase_grow=1),
]}


# 10474 YOUTH.ZAR youth.tbd#4: orange tag 選手入れ替え and the small blue tag サテライト
SPECS['10474'] = {'items': [
    dict(rect=(316, 95, 138, 27), text='Swap Players', erase=ER_TAG, font=['arial-bold'], max_size=20, min_sx=0.6, shear=0.2, autostyle=False, style=_TAGSTY, pad=0, erase_grow=1),
    dict(rect=(10, 229, 53, 20), text='Satellite', erase={'mode': 'mask', 'ink': [{'luma_gt': 190}, {'luma_lt': 40}], 'dilate': 2, 'fill': 'hfill'}, font=['arial-narrow-bold', 'arial-bold'],
         max_size=17, min_sx=0.5, shear=0.2, autostyle=False, pad=0, erase_grow=1,
         style={'fill': '#e4ffff', 'shadow': {'color': [0, 20, 60], 'dx': 1, 'dy': 1, 'blur': 0, 'alpha': 0.9}}),
]}


# 速報 -> FLASH (red-orange gradient, dark outline).  03344 NEWSOPED studio0.tbd#2 (128x128 VQ); 03342 is its blurred shadow (s7e_flash.py)
SPECS['03344'] = {'items': [
    dict(rect=(5, 42, 122, 52), text='FLASH', font=['arial-black', 'arial-bold'], size=42, max_size=42, dx=-2, min_sx=0.5, shear=0.2, pad=0, erase_grow=2),
]}

# 04082 TV_EVENT.ZAR TV_E1.TBD#0: the red 速報 above the Soccer TV logo sits on the opaque sunburst picture
ER_FLASH = {'mode': 'mask', 'ink': [{'sat_gt': 0.5, 'luma_lt': 235}, {'luma_lt': 70}], 'dilate': 2, 'fill': 'diffuse'}
_FLASHSTY = {'gradient': [[0, [255, 215, 40]], [0.5, [255, 120, 20]], [1, [215, 30, 10]]], 'outline': {'color': '#2a0a00', 'width': 1.4}}
SPECS['04082'] = {'items': [
    dict(rect=(70, 3, 84, 36), text='FLASH', erase=ER_FLASH, font=['arial-black', 'arial-bold'], max_size=34, min_sx=0.6, shear=0.2, autostyle=False,
         style=_FLASHSTY, pad=0, erase_grow=1),
]}

# 04104 YEAR.TBD#3: the same small logo inside the 256x256 atlas (glyphs only 31x11)
SPECS['04104'] = {'items': [
    dict(rect=(120, 66, 34, 14), text='FLASH', erase=ER_FLASH, font=['arial-black', 'arial-bold'], max_size=11, min_sx=0.6, shear=0.15, autostyle=False,
         style={'gradient': [[0, [255, 215, 40]], [0.5, [255, 120, 20]], [1, [215, 30, 10]]], 'outline': {'color': '#2a0a00', 'width': 0.7}}, pad=0, erase_grow=1),
]}

# 02235 JSCEVENT.TBD#3 (RGB565 VQ picture): the blue banner 地元サッカー大会; the small sideline board stays (advert signage, ~5 px)
SPECS['02235'] = {'items': [
    dict(rect=(166, 210, 196, 27), text='Local Soccer Tournament', erase={'mode': 'mask', 'ink': [{'luma_gt': 165, 'sat_lt': 0.3}, {'luma_lt': 60, 'sat_lt': 0.5}], 'dilate': 2, 'fill': 'diffuse'},
         font=['arial-bold'], max_size=19, min_sx=0.6, autostyle=False, pad=0, erase_grow=0,
         style={'fill': '#ffffff', 'shadow': {'color': [10, 20, 70], 'dx': 1, 'dy': 1, 'blur': 0, 'alpha': 0.9}}),
]}


# skeptic fix: the first Trainee render left hfill smear lines (rows 148-160) across the whole word; the area is
# transparent in the original, so clear it before re-rendering.
def _clear_trainee(base):
    base[144:167, 128:221] = (0x11, 0x33, 0x88, 0)


SPECS['10470']['pre'] = _clear_trainee
