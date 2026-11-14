"""Skeptic check of the proportional half-width font (typography side).

Independent of tools/re/font/widths.py: everything is rebuilt from
  * extracted/FONT.BIN (original half-width glyph block, via tools/font.py)
  * build/emu/t1_ram.bin (what the running game really holds at 0x8cdf851c)
  * the exact bytes the live test writes (parsed out of tools/emu/fonttest.lua: TABLE_HEX, GLYPH_NEW, GLYPH_OLD, HALF_IDX)

    python -I -X utf8 tools/re/font/skeptic_typo.py
Writes build/font/skeptic_*.png and prints the report (also saved to build/font/skeptic_typo_out.txt by the caller).
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import font as F  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

OUT = os.path.join(ROOT, 'build', 'font')
lua = open(os.path.join(ROOT, 'tools', 'emu', 'fonttest.lua'), encoding='utf8').read()


def grab(name):
    return re.search(r'local %s = "([0-9a-f]+)"' % name, lua).group(1)


TABLE = bytes.fromhex(grab('TABLE_HEX'))
FIXED = bytes.fromhex(grab('FIXED_HEX'))
i0 = lua.index('local GLYPH_NEW')
i1 = lua.index('local GLYPH_OLD')
i2 = lua.index('local VARIANTS')
NEW = {int(k): bytes.fromhex(v) for k, v in re.findall(r'\[(\d+)\]="([0-9a-f]+)"', lua[i0:i1])}
OLD = {int(k): bytes.fromhex(v) for k, v in re.findall(r'\[(\d+)\]="([0-9a-f]+)"', lua[i1:i2])}
HALF_IDX = {int(k): int(v) for k, v in re.findall(r'\[(\d+)\]=(\d+)', re.search(r'local HALF_IDX = \{(.*?)\}', lua).group(1))}
HALF_BASE = int(re.search(r'local HALF_BASE = (0x[0-9A-Fa-f]+)', lua).group(1), 16)
print('lua: table %d B, fixed %d B, glyphs NEW %d OLD %d, HALF_IDX %d, HALF_BASE %#x' % (len(TABLE), len(FIXED), len(NEW), len(OLD), len(HALF_IDX), HALF_BASE))

# ------------------------------------------------------------------ glyph sources
font = F.Font.load(os.path.join(ROOT, 'extracted', 'FONT.BIN'))
half = font.half()                       # original 160 glyphs
ram = open(os.path.join(ROOT, 'build', 'emu', 't1_ram.bin'), 'rb').read()
ramhalf = [ram[HALF_BASE - 0x8c000000 + i * 144: HALF_BASE - 0x8c000000 + (i + 1) * 144] for i in range(160)]
print('RAM(t1) half block == extracted/FONT.BIN half block for', sum(1 for a, b in zip(half, ramhalf) if a == b), '/ 160 glyphs')
hdr3 = int.from_bytes(open(os.path.join(ROOT, 'extracted', 'FONT.BIN'), 'rb').read()[12:16], 'little')
print('FONT.BIN header[3] = %#x -> RAM %#x (HALF_BASE in lua %#x) %s' % (hdr3, 0x8cd5c000 + hdr3, HALF_BASE, 'MATCH' if 0x8cd5c000 + hdr3 == HALF_BASE else 'MISMATCH'))


def grid(g):
    p = F.nibbles(g)
    return np.array(p, dtype=np.uint8).reshape(24, 12)


def cov_cols(g):
    c = 15 - grid(g)
    return c.max(axis=0)            # per column coverage 0..15


def inkspan(g, thr=1):
    c = cov_cols(g)
    nz = np.nonzero(c >= thr)[0]
    return (int(nz[0]), int(nz[-1])) if len(nz) else (None, None)


# which glyph does the live test really draw for code b
def glyph_for(b, mode):
    idx = F.half_index(b)
    if mode == 'new' and b in NEW:
        return NEW[b]
    return half[idx]


# ------------------------------------------------------------------ 1. lua glyph tables vs real data
bad = 0
for b, idx in HALF_IDX.items():
    if idx != F.half_index(b):
        print('HALF_IDX mismatch', b, idx)
        bad += 1
    if OLD[b] != half[idx]:
        print('GLYPH_OLD != extracted for', b)
        bad += 1
    # NEW must be OLD shifted left by its leading blank columns, paper (15) filled on the right
    g = grid(OLD[b])
    a0, a1 = inkspan(OLD[b])
    sh = a0
    exp = np.full((24, 12), 15, dtype=np.uint8)
    exp[:, :12 - sh] = g[:, sh:]
    if not np.array_equal(exp, grid(NEW[b])):
        print('NEW not equal to a pure left shift by', sh, 'for', b, chr(b))
        bad += 1
print('1) lua glyph tables: %d problems (NEW = lossless left shift of OLD, OLD = FONT.BIN, indices ok)' % bad)

shifted = set(NEW)
need = []
for b in range(0x21, 0x7F):
    a0, a1 = inkspan(half[F.half_index(b)])
    if a0 and a0 >= 1 and b not in shifted:
        need.append((chr(b), a0))
print('   glyphs with leading blank columns NOT shifted:', need)
print('   shifted glyphs not needing a shift:', [(chr(b), inkspan(OLD[b])[0]) for b in shifted if inkspan(OLD[b])[0] == 0])

# ------------------------------------------------------------------ 2. table vs widths.json
wj = json.load(open(os.path.join(ROOT, 'tools', 're', 'font', 'widths.json')))
diff = []
for b in range(0x20, 0x80):
    w = wj.get('0x%02X' % b)
    t = TABLE[b]
    if w != t:
        diff.append((chr(b), b, w, t))
print('2) cave table vs widths.json differences (0x20-0x7F):', diff)
print('   table entries outside 0x20-0x7F that are non-zero:', [(hex(i), TABLE[i]) for i in range(256) if TABLE[i] and not 0x20 <= i < 0x80])
print('   table[0x20]=%d table[0x7f]=%d, min/max over printable %d/%d' % (TABLE[0x20], TABLE[0x7F], min(TABLE[0x21:0x7F]), max(TABLE[0x21:0x7F])))
print('   mean over 94 printable: %.2f' % (sum(TABLE[0x21:0x7F]) / 94))

# ------------------------------------------------------------------ 3. per glyph clearance
rows = []
for b in range(0x21, 0x7F):
    g = glyph_for(b, 'new')
    a0, a1 = inkspan(g)
    s0, s1 = inkspan(g, 4)
    rows.append((b, a0, a1, s0, s1, TABLE[b]))
over = [(chr(b), a1, adv) for b, a0, a1, s0, s1, adv in rows if a1 + 1 > adv]
print('3) glyphs whose any-ink extends to or past the advance (would be covered by the next tile / touch it):', over)
touch = [(chr(b), a1 + 1, adv) for b, a0, a1, s0, s1, adv in rows if a1 + 1 == adv]
print('   glyphs whose ink ends exactly at the advance (0 px gap on the right):', [t[0] for t in touch])
print('   glyphs with first ink column > 0 after the shift:', [(chr(b), a0) for b, a0, a1, s0, s1, adv in rows if a0 and a0 > 0])
# pair gaps (any ink) at the real table pitch
gaps = {}
for (b1, a0, a1, s0, s1, adv) in rows:
    for (b2, c0, c1, t0, t1, adv2) in rows:
        gaps[(b1, b2)] = adv - (a1 + 1) + c0
mn = min(gaps.values())
print('   min blank-column gap between neighbouring any-ink over all 94x94 pairs: %d; pairs with gap 0: %d; gap 1: %d; of %d' % (
    mn, sum(1 for v in gaps.values() if v == 0), sum(1 for v in gaps.values() if v == 1), len(gaps)))
z = [(chr(a), chr(b)) for (a, b), v in gaps.items() if v == 0]
print('   gap-0 pairs (first 40):', z[:40])
# compare with the original fixed pitch (unshifted glyphs, advance 12)
gaps0 = {}
for b1 in range(0x21, 0x7F):
    a0, a1 = inkspan(half[F.half_index(b1)])
    for b2 in range(0x21, 0x7F):
        c0, c1 = inkspan(half[F.half_index(b2)])
        gaps0[(b1, b2)] = 12 - (a1 + 1) + c0
print('   ORIGINAL fixed 12 px: min gap %d, pairs gap 0: %d of 8836' % (min(gaps0.values()), sum(1 for v in gaps0.values() if v == 0)))
# letter pairs of a-z (lowercase text) only
lo = range(0x61, 0x7B)
g_new = [gaps[(a, b)] for a in lo for b in lo]
g_old = [gaps0[(a, b)] for a in lo for b in lo]
print('   lowercase pairs: NEW gap-0 %d / 676, mean gap %.2f ; ORIGINAL gap-0 %d / 676, mean gap %.2f' % (
    sum(1 for v in g_new if v == 0), np.mean(g_new), sum(1 for v in g_old if v == 0), np.mean(g_old)))

# ------------------------------------------------------------------ 4. rendering
SPACE_W = TABLE[0x20]


def render(text, mode, scale=2, opaque=False, width=None):
    """mode 'fixed' = original glyphs at 12 px; 'prop' = shifted glyphs at table advance.  Returns 2-D uint8 (255 paper)."""
    W = width or 480
    cv = np.full((24, W + 400), 255, dtype=np.int32)
    x = 0
    for ch in text:
        b = ord(ch)
        if ch == ' ':
            x += 12 if mode == 'fixed' else SPACE_W
            continue
        g = grid(glyph_for(b, 'old' if mode == 'fixed' else 'new'))
        gray = (g.astype(np.int32) * 17)
        if opaque:
            cv[:, x:x + 12] = gray
        else:
            cv[:, x:x + 12] = np.minimum(cv[:, x:x + 12], gray)
        x += 12 if mode == 'fixed' else (TABLE[b] if (b != 0x30 and not (0x30 <= b <= 0x39)) else 12)
    return cv[:, :W].astype(np.uint8), x


samples = [
    'The club manager signs a young striker.',
    'Illegal little will fill Willie Hill\'s pill.',
    'Hello, World! iiii WWWW mmmm wwww MMMM',
    'Next match: Vissel Kobe (Home) - Sat. 14:30',
    'You can change the player layout, and select',
    'Budget 1,250,000,000 yen; wages 3.5% up. Wow!',
    'The goalkeeper is injured. Tell the fans: "ok"!',
    'a quick jump: ij, il, li, ll, tt, ft, fi, rt, r.',
    'Estella is Spanish for \'starlike\'.',
    'Let\'s aim to be a shining club that',
]
strips = []
diffs = []
for s in samples:
    a, wa = render(s, 'fixed')
    b, wb = render(s, 'prop')
    b2, _ = render(s, 'prop', opaque=True)
    diffs.append(int((b != b2).sum()))
    strips.append((a, b, b2, s, wa, wb))
print('4) rendered %d sample lines; pixels that differ between opaque-paper and transparent-paper composition: %s (0 = overlap cannot matter)' % (len(samples), diffs))
for s, (a, b, b2, _, wa, wb) in zip(samples, [(x[0], x[1], x[2], 0, x[4], x[5]) for x in strips]):
    print('   %-50s fixed %3d px  prop %3d px  (%.0f%%)' % (s[:50], wa, wb, 100.0 * wb / wa))

SC = 2
pad = 6
H = len(samples) * (2 * 24 + pad) * SC
img = np.full((H, 480 * SC), 255, dtype=np.uint8)
y = 0
for a, b, b2, s, wa, wb in strips:
    for r in (a, b):
        big = np.kron(r, np.ones((SC, SC), dtype=np.uint8))
        img[y:y + 24 * SC] = big
        y += 24 * SC
    img[y:y + 1] = 160
    y += pad * SC
Image.fromarray(img).save(os.path.join(OUT, 'skeptic_strips.png'))

# digit columns: tabular?  right aligned numbers at the table pitch
cols = ['1111', '8888', '0000', '4444', '1,234', '10-0', '2:30', '1.5', '100%']
img2 = np.full((len(cols) * 28, 200), 255, dtype=np.uint8)
for i, s in enumerate(cols):
    r, w = render(s, 'prop', width=200)
    # tile of 24 rows at y = i*28
    img2[i * 28:i * 28 + 24] = r[:, :200]
Image.fromarray(np.kron(img2, np.ones((3, 3), dtype=np.uint8))).save(os.path.join(OUT, 'skeptic_digits.png'))
print('   digit table entries 0x30-0x39:', [TABLE[c] for c in range(0x30, 0x3A)], '(all 12 => tabular; the renderer uses the same rule)')
print('   but ink of digit 1 (any):', inkspan(half[F.half_index(0x31)]), ' of 0:', inkspan(half[F.half_index(0x30)]), ' of 4:', inkspan(half[F.half_index(0x34)]))

# ------------------------------------------------------------------ 5. line budget on the real sample
recs = [json.loads(l) for l in open(os.path.join(ROOT, 'tools', 're', 'capacity', 'ratio', 'sample.jsonl'), encoding='utf8')]


def adv_of(ch):
    b = ord(ch)
    if b < 0x20 or b > 0x7E:
        return 24
    if ch == ' ':
        return TABLE[0x20]
    if 0x30 <= b <= 0x39:
        return 12
    return TABLE[b]


tot_px = tot_ch = 0
cats = {}
wider = []
for r in recs:
    if r['skip']:
        continue
    t = r['en_flat']
    t = re.sub(r'@[A-Za-z]/|=[A-Za-z]/|@', '', t).replace('|', ' ')
    if not t:
        continue
    px = sum(adv_of(c) for c in t)
    tot_px += px
    tot_ch += len(t)
    c = cats.setdefault(r['cat'], [0, 0, 0, 0])
    c[0] += px
    c[1] += len(t)
    c[2] += 1
    if px > 12 * len(t):
        c[3] += 1
        wider.append((r['cat'], t, px, 12 * len(t)))
print('5) sample.jsonl: %d chars, mean advance %.2f px/char (digits 12), %.1f chars per 468 px' % (tot_ch, tot_px / tot_ch, 468 / (tot_px / tot_ch)))
for k, (px, ch, n, w) in sorted(cats.items()):
    print('   %-15s n=%3d mean %.2f px/char  strings WIDER than the same text at fixed 12 px: %d' % (k, n, px / ch, w))
print('   examples of strings wider than fixed 12:')
for w in wider[:12]:
    print('     ', w)
# letter-only text
freq = dict(zip('etaoinshrdlcumwfgypbvkjxqz', [12.7, 9.1, 8.2, 7.5, 7.0, 6.7, 6.3, 6.1, 6.0, 4.3, 4.0, 2.8, 2.8, 2.4, 2.4, 2.2, 2.0, 2.0, 1.9, 1.5, 1.0, 0.8, 0.15, 0.15, 0.1, 0.07]))
mean_letter = sum(freq[c] * TABLE[ord(c)] for c in freq) / sum(freq.values())
print('   English-frequency mean advance of a lower-case LETTER (no spaces): %.2f px (fixed font: 12)' % mean_letter)
print('   advance 13 letters:', ''.join(chr(b) for b in range(0x61, 0x7B) if TABLE[b] == 13), ' upper-case at 13:', ''.join(chr(b) for b in range(0x41, 0x5B) if TABLE[b] == 13))

# wrap simulation with the rule the cave implements (pen - x0 > 24*(W-1)) for W=20, flag=1
L = 24 * 19


def chars_on_line(text):
    x = 0
    n = 0
    for c in text:
        if x > L:
            break
        x += adv_of(c)
        n += 1
    return n


for name, t in (('all W', 'W' * 100), ('all i', 'i' * 200), ('lower mix', 'the quick brown fox jumps over the lazy dog ' * 4), ('caps words', 'MANCHESTER UNITED AND LIVERPOOL ' * 4), ('digits', '1234567890' * 8)):
    n = chars_on_line(t)
    px = sum(adv_of(c) for c in t[:n])
    print('   wrap sim W=20: %-10s -> %3d chars on the line (original 39), ink right edge <= %d px (limit 468)' % (name, n, px - adv_of(t[n - 1]) + 12))
