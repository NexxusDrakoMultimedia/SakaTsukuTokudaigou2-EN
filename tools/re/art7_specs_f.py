"""art7 specs, part F: SUPPORT.ZAR pvr.tbd #0 (supporter screen)."""
SPECS = {}
ER = {'mode': 'mask', 'ink': [{'luma_gt': 205}, {'luma_lt': 38}], 'dilate': 1, 'fill': 'hfill'}
ER2 = {'mode': 'mask', 'ink': [{'luma_gt': 190}, {'luma_lt': 24}], 'dilate': 2, 'fill': 'hfill'}
WHT = {'fill': '#ffffff', 'outline': {'color': '#0a1448', 'width': 1}, 'shadow': {'color': '#0a1448', 'dx': 1, 'dy': 1, 'alpha': 0.9, 'blur': 0}}


def b(x, y, w, text, h=22):
    return dict(rect=(x, y - 2, w, h), text=text, erase=ER, autostyle=False, style=WHT, font='arial-bold', pad=0, min_sx=0.55,
                max_size=17, erase_grow=0)


L = [(42, 108), (214, 112)]
SPECS['03869'] = {'items': [
    b(42, 198, 108, 'Popularity'), b(42, 238, 108, 'Scoring'), b(42, 277, 108, 'Roughness'), b(42, 318, 108, 'Set Pieces'),
    b(42, 357, 108, 'Mental'), b(42, 397, 108, 'Good Connections'), b(42, 437, 108, 'Strong Late'),
    b(214, 198, 112, 'Speed'), b(214, 240, 112, 'Defensive Key'), b(214, 277, 112, 'Leadership'), b(214, 318, 112, 'Discontent'),
    b(214, 357, 112, 'Stamina'), b(214, 397, 112, 'Coaching Talent'), b(214, 437, 112, 'Future Star'),
    dict(rect=(12, 145, 140, 42), text='Chant Edit', wrap=True, erase=ER2, autostyle=False, style=WHT, font='arial-bold', pad=0,
         min_sx=0.55, max_size=18, erase_grow=0, line_spacing=0.9),
    dict(rect=(153, 145, 152, 42), text='Club Chant Assign', wrap=True, erase=ER2, autostyle=False, style=WHT, font='arial-bold', pad=0,
         min_sx=0.55, max_size=18, erase_grow=0, line_spacing=0.9),
    dict(rect=(307, 145, 148, 42), text='Japan Chant Assign', wrap=True, erase=ER2, autostyle=False, style=WHT, font='arial-bold', pad=0,
         min_sx=0.55, max_size=18, erase_grow=0, line_spacing=0.9),
]}
