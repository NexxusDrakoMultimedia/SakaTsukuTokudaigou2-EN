"""art7 specs, part G (ar5): textures that the group inventory listed but nobody repainted."""
SPECS = {}

# SCHE1.TBD / SHINJIN.TBD month strip: the single kanji 月 in front of the 1..12 numerals becomes 'Mo' (as the header bar).
SPECS['03587'] = {'items': [
    dict(rect=(3, 409, 33, 37), text='Mo', font=['arial-black', 'arial-bold'], pad=1, size='auto', max_size=26, min_sx=0.6,
         erase={'mode': 'clear'}),
]}
