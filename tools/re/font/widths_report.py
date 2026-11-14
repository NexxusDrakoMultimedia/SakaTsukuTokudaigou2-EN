"""Writes tools/re/font/widths.json (+ widths_meta.json) and prints the statistics used in docs/font-widths.md.
python -I -X utf8 tools/re/font/widths_report.py"""
import sys, os, json, statistics as S
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), 'tools'))
import widths as W, font as F
ROOT = W.ROOT
G = 'H'
adv = {c: W.advance(c, G) for c in sorted(W.M)}
flat = {'0x%02X' % c: a for c, a in adv.items()}
json.dump(flat, open(os.path.join(HERE, 'widths.json'), 'w'), indent=0)
meta = {'rule': "advance = strong_ink_right_col_after_shift + 1 + G; G=1 if strong ink width>=8 else 2; blank glyphs=6 (space)",
        'units': 'pixels', 'fullwidth_advance': 24, 'line_budget_px_39_cells': 468, 'strong_threshold_coverage': W.STRONG,
        'glyphs': {'0x%02X' % c: ({'blank': True} if m['blank'] else
                  {k: m[k] for k in ('any_l', 'any_r', 'st_l', 'st_r', 'shift', 'faint_l', 'faint_r')} | {'advance': adv[c]})
                  for c, m in sorted(W.M.items())}}
json.dump(meta, open(os.path.join(HERE, 'widths_meta.json'), 'w'), indent=0)

asc = [c for c in range(0x21, 0x7f)]
print('ASCII glyph count', len(asc), 'blank:', [hex(c) for c in W.M if W.M[c]['blank']])
sh = [c for c in asc if W.M[c]['shift'] > 0]
print('ASCII glyphs with left blank cols (any ink):', len(sh), ' shift hist', sorted(__import__('collections').Counter(W.M[c]['shift'] for c in asc).items()))
print('needs shift >=2:', ''.join(chr(c) for c in asc if W.M[c]['shift'] >= 2))
print('right blank (any ink) hist', sorted(__import__('collections').Counter(W.M[c]['right_blank_any'] for c in asc).items()))
print('glyphs any-ink touching col 11:', ''.join(chr(c) for c in asc if W.M[c]['any_r'] == 11))
print('glyphs strong-ink touching col 11:', ''.join(chr(c) for c in asc if W.M[c]['st_r'] == 11), len([c for c in asc if W.M[c]['st_r'] == 11]))
print('glyphs any_l==0:', len([c for c in asc if W.M[c]['any_l'] == 0]))
print('faint_r max', max(W.M[c]['faint_r'] for c in asc), 'faint_l max', max(W.M[c]['faint_l'] for c in asc))
# pair safety: strong-to-strong blank gap, and fringe overlap
mn = 99; worst = []; fo = 0; tot = 0
for a in asc:
    for b in asc:
        ma, mb = W.M[a], W.M[b]
        gap = adv[a] - (ma['b'] + 1) + mb['a']       # blank px between strong ink
        # any-ink overlap: right any ink col of a (shifted) vs left any col of b (=0)
        ov = (ma['any_r'] - ma['shift'] + 1) - adv[a]
        tot += 1
        if ov > 0: fo += 1
        if gap < mn: mn = gap; worst = [(chr(a), chr(b))]
        elif gap == mn: worst.append((chr(a), chr(b)))
print('min strong blank gap', mn, 'pairs', len(worst), worst[:10], '| pairs w/ any-ink fringe overlap', fo, 'of', tot)
# widths
import collections
print('advance dist', sorted(collections.Counter(adv[c] for c in asc).items()))
print('over 12:', ''.join(chr(c) for c in asc if adv[c] > 12), len([c for c in asc if adv[c] > 12]))
print('<=8:', ''.join(chr(c) for c in asc if adv[c] <= 8))
# corpus
C = W.corpus()
txt = lambda r: W.clean(r['en_flat'].replace('|', ' '))
allc = ''.join(txt(r) for r in C)
prose = [r for r in C if r['cat'].startswith('prose') or r['cat'] == 'help']
pa = ''.join(txt(r) for r in prose)
def avg(s, g):
    return W.text_adv(s, g) / len(s)
print('corpus', len(C), 'strings', len(allc), 'chars; prose', len(pa), 'space share %.3f' % (allc.count(' ') / len(allc)))
for g in (0, 1, 2, 'H'):
    print('avg adv G=%s all %.3f prose %.3f' % (g, avg(allc, g), avg(pa, g)))
nar = lambda s: sum(W.narrow_glyph(ord(c))[1] if 0x20 <= ord(c) < 0x7f else 12 for c in s) / len(s)
print('avg adv narrow all %.3f prose %.3f' % (nar(allc), nar(pa)))
for g in (1, 2, 'H'):
    print('G', g, 'chars per 468 px (prose) %.1f' % (468 / avg(pa, g)), ' (all) %.1f' % (468 / avg(allc, g)))
print('nar chars per 468px prose %.1f' % (468 / nar(pa)))
# letter-frequency-weighted check
cnt = collections.Counter(allc)
print('fixed-12 reference: 39 chars/line')
# wrap simulation (greedy words, paragraphs by |)
def lines_for(fits):
    t = 0
    for r in prose:
        t += W.wrap_greedy(W.clean(r['en_flat']), fits)
    return t
lf = lines_for(lambda l: len(l) <= 39)
for g in (1, 2, 'H'):
    lp = lines_for(lambda l, g=g: W.text_adv(l, g) <= 468)
    print('wrap G', g, 'lines fixed39', lf, 'prop', lp, 'ratio %.3f' % (lp / lf))
lp_n = lines_for(lambda l: sum(W.narrow_glyph(ord(c))[1] for c in l) <= 468)
print('wrap narrow', lp_n, 'ratio %.3f' % (lp_n / lf))
# avg line fill of existing en lines (39-char wrapped samples)
ls = [l for r in prose for l in W.clean(r['en']).split('\n') if l]
print('existing en lines', len(ls), 'avg len %.1f' % S.mean(len(l) for l in ls), 'max', max(len(l) for l in ls),
      'avg px(H) %.0f' % S.mean(W.text_adv(l, 'H') for l in ls), 'max px(H)', max(W.text_adv(l, 'H') for l in ls),
      'lines >39:', sum(1 for l in ls if len(l) > 39), 'lines >468px(H):', sum(1 for l in ls if W.text_adv(l, 'H') > 468))
# longest word px
words = set(w for r in C for w in txt(r).split(' '))
print('longest word H px', max((W.text_adv(w, 'H'), w) for w in words))
print('full-width 24 px = 2 half cells; 39 half cells = 468 px; 20 full = 480 px')
# katakana widths
kat = [c for c in range(0xA1, 0xE0)]
print('katakana: blank', [hex(c) for c in kat if W.M[c]['blank']], 'adv range', min(adv[c] for c in kat), max(adv[c] for c in kat))
