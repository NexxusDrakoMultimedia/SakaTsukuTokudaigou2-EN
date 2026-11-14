"""art5_pairs - two-tile plates: SPT_CLUB (03823 | 03822) and JSCEVENT (02233 | 02232); painted on the stitched 512x256 canvas."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art5_lib as L
from PIL import Image

INK = {'mode': 'mask', 'ink': [{'sat_lt': 0.45, 'luma_gt': 150, 'alpha_gt': 128}, {'luma_lt': 45, 'alpha_gt': 128}],
       'dilate': 2, 'fill': 'diffuse', 'relax': 160}
HG = {'mode': 'hgrad'}
# am2: unit sprites (oku / man): light glyph ink and its dark shadow only, the plate bevel (luma ~90) stays
UINK = {'mode': 'mask', 'ink': [{'luma_gt': 150}, {'luma_lt': 80}], 'dilate': 2, 'fill': 'diffuse', 'relax': 160}
MAIN = dict(font=['arial-bold'], gradient=[[0, '#ffffff'], [0.55, '#e8fbff'], [1, '#9fe4f6']],
            outline={'color': '#001018', 'width': 2.0}, shadow={'color': '#00203c', 'dx': 2, 'dy': 2, 'alpha': 0.9},
            size='auto', min_sx=0.8, valign='middle', pad=0, align='center')
UNIT = dict(font=['arial-black'], gradient=[[0, '#b8e4f8'], [1, '#78b4d8']], shadow={'color': '#08304c', 'dx': 1, 'dy': 1, 'alpha': 0.8},
            size='auto', min_sx=0.75, valign='middle', pad=0, align='center')


def stitch(a, b):
    o = Image.new('RGBA', (512, 256))
    o.paste(L.load(a), (0, 0)); o.paste(L.load(b), (256, 0))
    return o


JPF = 'C:/Windows/Fonts/BIZUDGothic-Bold.ttf'


def gate(name, lines, grow=3):
    """mask PNG: the old Japanese lines re-rendered (approximate) and grown, used to limit the erase mask"""
    from PIL import ImageFont, ImageDraw, ImageFilter
    m = Image.new('L', (512, 256), 0)
    d = ImageDraw.Draw(m)
    for text, x0, x1, y0, y1 in lines:
        n = len(text)
        adv = (x1 - x0) / float(n)
        f = ImageFont.truetype(JPF, int(round(min(adv * 0.95, (y1 - y0) * 0.95))))
        for i, ch in enumerate(text):
            d.text((x0 + i * adv + adv / 2, (y0 + y1) / 2), ch, font=f, fill=255, anchor='mm')
    m = m.filter(ImageFilter.MaxFilter(2 * grow + 1))
    m.save(os.path.join(L.ART, name))


def run(left, right, l1, l2, r1, r2, jp, free):
    img = stitch(left, right)
    gate('gate_%s.png' % left, jp)
    ink = {'mode': 'mask', 'ink': [{'mask_png': 'gate_%s.png' % left, 'sat_lt': 0.45, 'luma_gt': 150, 'alpha_gt': 128},
                                   {'mask_png': 'gate_%s.png' % left, 'luma_lt': 45, 'alpha_gt': 128}],
           'dilate': 2, 'fill': 'diffuse', 'relax': 160}
    freeink = {'mode': 'mask', 'ink': [{'sat_lt': 0.45, 'luma_gt': 150, 'alpha_gt': 128}, {'luma_lt': 50, 'alpha_gt': 128}],
               'dilate': 3, 'fill': 'diffuse', 'relax': 160}
    regs = [dict(id='free%d' % i, x=f[0], y=f[1], w=f[2], h=f[3], erase=freeink) for i, f in enumerate(free)]
    regs += [
        dict(MAIN, id='l1', align='left', text=l1, x=r1[0], y=r1[1], w=r1[2], h=r1[3], max_size=r1[4], erase_rect=r1[5], erase=ink),
        dict(MAIN, id='l2', text=l2, x=r2[0], y=r2[1], w=r2[2], h=r2[3], max_size=r2[4], erase_rect=r2[5], erase=ink),
        dict(UNIT, id='oku', text='oku', x=118, y=150, w=46, h=32, max_size=21, erase=UINK, erase_rect=[120, 147, 44, 36]),
        dict(UNIT, id='man', text='man', x=248, y=150, w=54, h=32, max_size=21, erase=UINK, erase_rect=[250, 147, 52, 36]),
    ]
    out = L.render(left, {'regions': regs}, img)
    L.finish(left, out.crop((0, 0, 256, 256)))
    L.finish(right, out.crop((256, 0, 512, 256)))


run('03823', '03822', "Supporters' Club", 'Operating Costs', (36, 50, 340, 52, 44, [30, 50, 340, 54]),
    (90, 98, 230, 40, 36, [98, 96, 200, 44]),
    [('サポーターズクラブ', 38, 360, 56, 100), ('運営費設定', 108, 290, 98, 138)],
    [(145, 50, 235, 54), (145, 96, 170, 48)])
run('02233', '02232', 'Local Football Tournament', 'Sponsorship', (40, 56, 330, 46, 34, [36, 54, 340, 50]),
    (150, 100, 110, 44, 32, [158, 98, 96, 46]),
    [('地元サッカー大会', 45, 360, 60, 100), ('出資', 165, 243, 100, 140)],
    [(150, 52, 230, 52), (150, 98, 110, 46)])
