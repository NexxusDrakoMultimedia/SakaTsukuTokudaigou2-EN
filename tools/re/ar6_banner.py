"""ar6_banner: repaint the EVENT title banners (256x32 textures: a coloured tag plate with white text, right aligned).

    python -I -X utf8 tools/re/ar6_banner.py [--write] [--sheet] [ID ...]     (default: every id of WORDS)

The plate width follows the text: the plate is rebuilt from scratch with the original left cap (curved edge, first CAP columns),
a body that blends the cap's last column into the right-hand reference columns (the plates have a light-to-dark sheen), and the
original right end (columns 251..255).  The English is rendered right aligned to x = 249 (the Japanese ended at 247 + shadow),
auto-fitted (size <= 21, squash >= 0.68) into the widest legal box, then the plate's left edge is placed 30 px left of the ink
(minimum plate as the originals: left edge at their own minimum x).
--write encodes every identical copy into translation/textures (art7_lib.encode_and_write).  Output PNGs: build/ar6/ban/ID.png."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
import art7_lib as L
import arttext

CAP = 26
RIGHT0 = 251
INK_R = 249           # right limit of the English ink box (the Japanese ink ended at about 247 + shadow)
MAXW = 219            # widest box (plate left edge >= 0)
OUT = os.path.join(L.ROOT, 'build', 'ar6', 'ban')

WORDS = {
    '04148': 'Scout Report', '04163': 'Player Leaves Club', '04205': 'Player Retires', '04206': 'New Signing Unveiled',
    '04208': 'Off to Study Abroad', '04241': 'Injury Report', '04262': 'Hall of Fame Entry', '04263': 'Supporter Request',
    '04264': 'Supporter Discontent', '04267': 'Local Speciality Launched', '04281': 'Merchandise Development',
    '04301': 'New Merchandise Out', '04338': 'Appears in TV Advert', '04341': 'Game Released', '04344': 'Website Launched',
    '04381': 'Bus Route Extended', '04384': 'Overseas VIP Visit', '04385': 'Second Training Pitch', '04388': 'Pitch Maintenance',
    '04391': 'Floodlights Installed', '04441': 'Slump', '04474': 'Slump Recovery', '04510': 'Stadium Expansion',
    '04511': 'Grass Pitch', '04512': 'Roof Installed', '04513': 'Honorary Citizen', '04514': 'Bid to Host',
    '04515': 'Inspection Trip', '04526': 'Bid Successful', '04527': 'Bid Unsuccessful', '04528': 'Clubhouse Expansion',
    '04529': 'Foreign Player Goes Home', '04530': 'Foreign Player Returns', '04533': 'National Squad Selected',
    '04534': 'National Team Departs', '04535': 'National Team Returns', '04536': 'Study Abroad Return',
    '04539': 'Domestic VIP Visit', '04583': 'Manager Retires', '04616': 'Injured Player Returns', '04652': 'Capable Executive',
    '04655': 'Station Building Construction', '04656': 'Station Building Completed', '04659': 'Airport Construction',
    '04660': 'Airport Completed', '04663': 'Club Building Construction', '04664': 'Club Building Completed',
    '04667': 'School Construction', '04668': 'School Completed', '04671': 'Club Tower Construction',
    '04672': 'Club Tower Completed', '04675': 'News From Abroad', '04678': 'Player Unearthed',
    '04679': 'Sister City Partnership', '04680': 'Ageing Facilities', '04683': 'Manager Seeks Job',
    '04686': 'Player Seeks Contract', '04689': 'Player Transfer Request', '04692': 'Local Festival Held',
    '04693': 'National Ground Construction', '04694': 'A Star Is Born', '04697': 'Local Youth Champions',
    '04700': 'Local Junior High Champions', '04701': 'Local High School Champions', '04704': 'Football School Opens',
    '04705': 'Coaching School Completed', '04706': 'Autograph Session', '04709': 'Merchandise Shop Opens',
    '04712': 'Hot Spring Discovered', '04713': 'Hot Spring Completed', '04740': 'Population Boom', '04761': '11 Hall of Famers',
    '04762': 'Japan Manager Selected', '04777': 'Injury Forces Exit', '04780': 'Sister City Park Construction',
    '04781': 'Sister City Park Completed', '04784': 'Outdoor Pool Construction', '04785': 'Outdoor Pool Completed',
    '04788': 'Library Construction', '04789': 'Library Completed', '04792': 'Nature Park Construction',
    '04793': 'Nature Park Completed', '04796': 'Police Station Construction', '04799': 'Zoo Construction',
    '04800': 'Zoo Completed', '04803': 'Hospital Construction', '04804': 'Hospital Completed', '04805': 'Scout Retires',
    '04808': 'Theme Park Construction', '04809': 'Theme Park Completed', '04812': 'Rail Line Opened',
    '04813': 'Special Stadium Construction', '04816': 'Baseball Ground Construction', '04817': 'Baseball Ground Completed',
    '04818': 'Baseball Ground Demolished', '04821': 'Factory Construction', '04822': 'Factory Completed',
    '04823': 'Factory Demolished', '04826': 'Game Centre Construction', '04829': 'Very Effective', '04832': 'Faulty Goods',
    '04845': 'Japan Manager Replaced', '04848': 'Sports Club Opens', '04852': 'Overseas Camp Departure',
    '04853': 'Overseas Camp Return', '04928': 'Injury Report',
}

TEXT_STYLE = {'gradient': [[0, '#ffffff'], [1, '#dde4f0']], 'outline': {'color': '#0a1a44', 'width': 1.1},
              'shadow': {'color': '#000010', 'dx': 2, 'dy': 2, 'alpha': 0.95}}


STYLE_LEVEL = [0]


def style_for(level):
    st = dict(TEXT_STYLE)
    if level >= 1:
        st['fill'] = '#ffffff'
        st.pop('gradient', None)
    if level >= 2:
        st['aa'] = False
    if level >= 3:
        st.pop('outline', None)
    return st


def plate_of(a):
    op = a[..., 3] > 128
    L0 = min(int(np.nonzero(op[y])[0].min()) for y in range(22, 31) if op[y].any())
    return L0


def render_text(img, text, fmt, boxx0, size='auto'):
    """render `text` right-aligned into x in [boxx0, INK_R]; returns (image, block_w)"""
    reg = dict(id='t', text=text, x=boxx0, y=5, w=INK_R - boxx0, h=26, erase=None, align='right', valign='middle',
               font=['arial-bold', 'arial-narrow-bold'], size=size, max_size=21, min_sx=0.68, pad=0, style=style_for(STYLE_LEVEL[0]))
    spec = {'supersample': 4, 'regions': [reg], 'defaults': {}, 'quantize': fmt}
    out, rep = arttext.render_spec(spec, img)
    return out, rep['regions'][0], rep['warnings']


_DON = {}


def donor(a):
    """clean left cap of the same colour class: blue 04706, red 04163, orange 04263 (their text starts well right of the cap)"""
    ref = np.median(a[20:30, 252:255, :3], axis=(0, 1))
    if ref[0] > 120 and ref[2] < 60:
        k = '04263' if ref[1] > 90 else '04163'
    elif ref[0] > ref[2] + 40:
        k = '04163'
    else:
        k = '04706'
    if k not in _DON:
        d = L.load(k)['arr'].astype(int)
        _DON[k] = (d, plate_of(d))
    return _DON[k]


def build(t, text):
    a = t['arr'].astype(int)
    H, W = a.shape[:2]
    fmt = {'ARGB1555': 'argb1555', 'RGB565': 'rgb565'}.get(t['info']['format'].split('/')[0], 'argb4444')
    L0 = plate_of(a)
    # pass 1: measure on a blank canvas
    blank = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for sz in [21 - 0.5 * k for k in range(0, 20)]:
        _, r1, w1 = render_text(blank, text, fmt, INK_R - 222, sz)
        if r1['block'][0] <= 224.5 and (r1.get('squash') or 1.0) >= 0.68:
            break
    bw = r1['block'][0]
    inkl = INK_R - bw
    L1 = max(0, min(124, int(round(inkl - 30))))
    n = np.zeros_like(a)
    da, dL0 = donor(a)
    for x in range(L1, L1 + CAP):
        n[:, x] = da[:, dL0 + (x - L1)]
    capl = da[:, dL0 + CAP - 1]
    ref = np.median(a[:, 252:255], axis=1)
    x0 = L1 + CAP
    for x in range(x0, RIGHT0):
        tt = (x - x0) / float(max(1, RIGHT0 - x0))
        col = capl * (1 - tt) + ref * tt
        col = np.rint(col).astype(int)
        al = np.where(ref[:, 3] > 128, 255, 0)
        n[:, x, :3] = col[:, :3]
        n[:, x, 3] = al
    n[:, RIGHT0:] = a[:, RIGHT0:]
    img = Image.fromarray(n.clip(0, 255).astype(np.uint8), 'RGBA')
    out, r2, w2 = render_text(img, text, fmt, INK_R - 222, sz)
    return out, dict(L0=L0, L1=L1, block=r1['block'], size=r2.get('size'), squash=r2.get('squash'), warn=w1 + w2)


def main():
    a = sys.argv[1:]
    write = '--write' in a
    ids = [x for x in a if not x.startswith('--')] or sorted(WORDS)
    os.makedirs(OUT, exist_ok=True)
    bad = 0
    for i in ids:
        try:
            t = L.load(i)
        except Exception as ex:
            print(i, 'LOAD FAILED', ex)
            bad += 1
            continue
        lvl = 0
        while True:
            STYLE_LEVEL[0] = lvl
            out, info = build(t, WORDS[i])
            msg = '%s %-30s L0=%3d L1=%3d w=%5.1f size=%s sx=%s lvl=%d' % (i, WORDS[i], info['L0'], info['L1'], info['block'][0], info['size'], info['squash'], lvl)
            if not write:
                break
            new = L.pvr.encode(np.asarray(out.convert('RGBA')), original=t['pvr'])
            fr = L.fit_report(new, t)
            if all(r[2] for r in fr):
                _, w = L.encode_and_write(t, out)
                msg += ' wrote %d' % len(w)
                break
            if lvl >= 3:
                msg += ' DOES NOT FIT: ' + str([r[3] for r in fr if not r[2]])[:100]
                bad += 1
                break
            lvl += 1
        out.save(os.path.join(OUT, i + '.png'))
        if info['warn']:
            msg += ' WARN ' + '; '.join(info['warn'])[:60]
        print(msg)
    print('done, problems:', bad)


main()
