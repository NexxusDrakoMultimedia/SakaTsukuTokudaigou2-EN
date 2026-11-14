"""art7 specs, part E: REPORT result ribbons (256x64 ARGB4444 sprites)."""
SPECS = {}

CHROME = {'gradient': [[0, [255, 255, 255]], [0.45, [200, 205, 215]], [0.55, [120, 125, 140]], [1, [235, 238, 245]]],
          'outline': {'color': '#2a2d3a', 'width': 1},
          'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'alpha': 0.7, 'blur': 0}}
GOLDR = {'gradient': [[0, [255, 248, 210]], [0.5, [226, 196, 110]], [1, [150, 112, 40]]],
         'outline': {'color': '#5a3c10', 'width': 1},
         'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'alpha': 0.7, 'blur': 0}}
YEL = {'gradient': [[0, [255, 255, 180]], [1, [245, 215, 90]]],
       'outline': {'color': '#6a2a08', 'width': 1},
       'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'alpha': 0.8, 'blur': 0}}
WHT = {'gradient': [[0, [255, 255, 255]], [1, [205, 210, 235]]],
       'outline': {'color': '#3a1c78', 'width': 1},
       'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'alpha': 0.7, 'blur': 0}}
ORGN = {'gradient': [[0, [255, 245, 0]], [1, [255, 150, 0]]], 'outline': {'color': '#000000', 'width': 1},
        'shadow': {'color': '#000000', 'dx': 2, 'dy': 2, 'alpha': 1.0, 'blur': 0}}
DARKER = {'mode': 'mask', 'ink': [{'sat_gt': 0.45, 'luma_gt': 90}, {'luma_lt': 30}], 'dilate': 1, 'fill': 'hfill'}


def rib(rect, text, style, rf=None, xr=None, tol=40, erase=None, **kw):
    d = dict(rect=rect, text=text, autostyle=False, style=style, font='arial-black', pad=0, min_sx=0.5, erase=erase, max_size=60)
    if rf:
        d['rowfill'] = dict(rect=rf, tol=tol, dil=1, xr=xr)
    d.update(kw)
    return {'items': [d]}


SPECS['06484'] = rib((12, 8, 236, 48), 'Champions', GOLDR, rf=(6, 4, 244, 56), xr=(30, 226), tol=45)
SPECS['06485'] = rib((14, 8, 232, 48), 'Qualified', CHROME, rf=(6, 4, 244, 56), xr=(30, 226), tol=45)
SPECS['06486'] = rib((16, 6, 226, 52), 'Out  in  Qualifiers', CHROME, rf=(6, 4, 244, 56), xr=(30, 226), tol=45)
SPECS['06489'] = rib((14, 8, 232, 48), 'Runners-up', CHROME, rf=(6, 4, 244, 56), xr=(30, 226), tol=45)
SPECS['06487'] = rib((102, 10, 146, 44), 'Promoted', YEL, rf=(98, 6, 154, 52), xr=(100, 232), tol=50)
SPECS['06488'] = rib((104, 10, 142, 44), 'Relegated', WHT, erase={'mode': 'mask', 'ink': [{'luma_gt': 178}, {'luma_lt': 30}], 'dilate': 1, 'fill': 'hfill'}, erase_grow=[0, 2, 6, 2])
SPECS['06483'] = rib((124, 10, 56, 48), 'Pos.', ORGN, erase=DARKER, erase_grow=[2, 2, 4, 2], max_size=40)
SPECS['06490'] = rib((90, 28, 130, 26), 'Knocked Out', ORGN, erase=DARKER, erase_grow=[2, 2, 4, 2], max_size=24)
