"""art7 specs, part D: Challenge Mode kanji, rank plates, team banners, tournament name banners."""
SPECS = {}

GOLD = {'gradient': [[0, [255, 244, 130]], [0.55, [255, 215, 20]], [1, [215, 150, 0]]],
        'outline': {'color': '#fff6d8', 'width': 3},
        'shadow': {'color': '#000000', 'dx': 4, 'dy': 4, 'alpha': 1.0, 'blur': 0}}
GOLD_SM = {'gradient': [[0, [255, 244, 130]], [0.55, [255, 215, 20]], [1, [215, 150, 0]]],
           'outline': {'color': '#fff6d8', 'width': 1},
           'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'alpha': 1.0, 'blur': 0}}


def full(text, font='arial-black', size='auto', **kw):
    d = dict(rect=(0, 0, 128, 128), text=text, font=font, autostyle=False, style=GOLD, pad=6, erase={'mode': 'clear'},
             size=size, max_size=110, min_sx=0.5)
    d.update(kw)
    return {'items': [d]}


# 128x128 single glyph sprites: numerals one..ten, 初 (first), 級 (kyu), 段 (dan)
for _i, _t in zip(range(209, 219), ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']):
    SPECS['%05d' % _i] = full(_t, size=104 if len(_t) == 1 else 'auto')
SPECS['00219'] = full('1st', size='auto')
SPECS['00220'] = full('Kyu', size='auto')
SPECS['00221'] = full('Dan', size='auto')

# 00222: Defeat / Clean Sweep ; 00208: Master
SPECS['00222'] = {'items': [
    dict(rect=(0, 1, 270, 127), text='Defeat', font='arial-black', autostyle=False, style=GOLD, pad=4,
         erase={'mode': 'clear'}, erase_grow=[2, 2, 4, 4], min_sx=0.6, max_size=100),
    dict(rect=(3, 131, 327, 98), text='Clean Sweep', font='arial-black', autostyle=False, style=GOLD, pad=4,
         erase={'mode': 'clear'}, erase_grow=[2, 2, 4, 4], min_sx=0.6, max_size=88),
]}
SPECS['00208'] = {'items': [
    dict(rect=(2, 424, 337, 86), text='Master', font='arial-black', autostyle=False, style=GOLD, pad=4,
         erase={'mode': 'clear'}, erase_grow=[2, 2, 4, 4], min_sx=0.6, max_size=88),
]}

# CHALMODE.TBD 3..5: team name lists (256x256 VQ), 8 / 8 / 5 rows
W_OUT = {'gradient': [[0, [255, 240, 80]], [1, [255, 200, 0]]],
         'outline': {'color': '#000000', 'width': 1},
         'shadow': {'color': '#000000', 'dx': 1, 'dy': 1, 'alpha': 1.0, 'blur': 0}}


def team_rows(names, y0=0, pitch=32, h=32):
    return {'items': [dict(rect=(0, y0 + k * pitch, 256, h), text=n, font='arial-narrow-bold', autostyle=False, style=W_OUT,
                           pad=0, erase={'mode': 'clear'}, erase_grow=[0, 0, 0, 0], min_sx=0.6, max_size=26) for k, n in enumerate(names)]}


SPECS['00227'] = team_rows(['European Old Stars', 'European Superstars', 'S. America Old Stars', 'S. America Superstars',
                            'Asia Stars', 'Japan Stars', 'Nordic Stars', 'Balkan Stars'])
SPECS['00228'] = team_rows(['Sakatsuku Stars', 'World Stars', 'Africa Stars', 'Spain Legends', 'France Legends',
                            'U.K. Legends', 'German Legends', 'Dutch Legends'])
SPECS['00229'] = team_rows(['Italy Legends', 'Brazil Legends', 'Argentina Legends', 'Wing Farms', 'Dream Stars'])

# CPNAMEB: tournament name banners (128x128, four rows)
CPW = {'fill': '#ffffff', 'outline': {'color': '#000000', 'width': 1}, 'shadow': {'color': '#000000', 'dx': 1, 'dy': 1, 'alpha': 1.0, 'blur': 0}}


def cp(rows):
    items = []
    for (y, h), t in rows:
        if t:
            items.append(dict(rect=(15, y, 112, h), text=t, font='arial-narrow-bold', autostyle=False, style=CPW, pad=0,
                              erase={'mode': 'clear'}, erase_grow=[1, 1, 1, 2], min_sx=0.4, max_size=20))
    return {'items': items}


R4 = [(4, 26), (35, 26), (67, 26), (99, 26)]
SPECS['00290'] = cp(list(zip(R4, ['Pre-season Match', 'Fan Thanks Match', 'World XI vs Euro XI', 'Asia Winners Cup'])))
SPECS['00291'] = cp(list(zip(R4, ['World Winners Cup', 'Platinum League', None, 'Asia Tournament'])))
SPECS['00292'] = cp(list(zip(R4, ['World Club Tournament', 'European Cup', 'South America Cup', 'World Challenge Cup'])))
SPECS['00293'] = cp(list(zip(R4, ['World Champions League', 'Golden Cup', 'Asia Challenge Cup', 'Euro Challenge League'])))
SPECS['00294'] = cp(list(zip(R4, ['S. America Challenge League', 'International Champions Cup', None, 'U22 Asia Tournament'])))
SPECS['00295'] = cp(list(zip(R4, ['U23 Inter League', 'U22 Super Youth Cup', 'Overseas Camp', 'Friendly Match'])))

# CH_DANI / CHL_DANI rank plates (128x64 RGB565 marble)
PLATE_INK = {'mode': 'mask', 'ink': [{'sat_gt': 0.32, 'luma_gt': 90}, {'luma_lt': 52}, {'color': [250, 235, 205], 'tol': 45}], 'dilate': 2, 'fill': 'diffuse'}
ORG = {'gradient': [[0, [255, 215, 150]], [1, [235, 140, 55]]], 'outline': {'color': '#3a1c08', 'width': 1},
       'shadow': {'color': '#000000', 'dx': 1, 'dy': 1, 'alpha': 0.8, 'blur': 0}}
PLATES = {'00235': '1st Dan', '00238': '10th Kyu', '00239': '9th Kyu', '00240': '8th Kyu', '00241': '7th Kyu', '00242': '6th Kyu',
          '00243': '5th Kyu', '00244': '4th Kyu', '00245': '3rd Kyu', '00246': '2nd Kyu', '00247': '1st Kyu', '00248': '1st Dan',
          '00249': '2nd Dan', '00250': '3rd Dan', '00251': '4th Dan', '00252': '5th Dan', '00253': '6th Dan', '00254': '7th Dan',
          '00255': '8th Dan', '00256': '9th Dan', '00257': 'Master', '00258': 'Special Match'}
for _i, _t in PLATES.items():
    st = dict(ORG)
    if _i == '00257' or _i == '00258':
        st = dict(ORG, gradient=[[0, [250, 245, 160]], [1, [215, 205, 100]]])
    SPECS[_i] = {'items': [dict(rect=(24, 12, 82, 40), text=_t, font='arial-black', autostyle=False, style=st, pad=0,
                                erase=PLATE_INK, erase_grow=[4, 2, 4, 2], min_sx=0.55, max_size=30)]}
