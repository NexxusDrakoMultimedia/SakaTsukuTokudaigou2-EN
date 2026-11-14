"""s7p_plates - generate the club-name plate textures (package B/C/D of docs/art-sweep-v3.md, owner s7p).

One table drives everything:
  * GAME/ALLLOGOS.BIN [0..65]   66 plates, four 32 px lines per 128x128 VQ texture (J-League clubs, select teams, national
                                teams, foreign clubs, the schedule words, Stars/Legends teams); master = ALLLOGOS [k]
  * GAME/BINDLOGO.BIN [14+k]    the byte-identical copy of ALLLOGOS [k] used by the match module (own file per copy)
  * GAME/BINDLOGO.BIN [0..13]   the 54 club words (second half of a made-up club name, four per texture), taken from
                                translation/clubwords_art.tsv (column ascii_for_strings = the spelling of the ORIGINAL logo art)
  * GAME/BINDNAME.BIN [141]     the Sakatsuku Stars logo (job 'logo', hand style: white letters, blue rim, black outline)

Style of the original Latin plates (OFF / ???): white fill with a light grey lower edge, solid black drop shadow 2 px right/down,
cap height about 22 px, text centred in the 128x32 cell.  Long names switch to a condensed face and then squash.

usage (run from anywhere):
  python -I -X utf8 tools/re/s7p_plates.py [--only 0,5,59 | --words | --logo] [--write] [--verify] [--sheet]
    default        render everything to build/s7/p/out/<file>_<k>.png (+ before/after) and report fit warnings
    --write        encode into each texture's own VQ format and write translation/textures/GAME/<file>/[k].pvr (own files
                   only: a file that exists and is not recorded in build/s7/p_manifest.json is another owner's: skipped)
    --verify       replace_textures() the written set into extracted/ copies in memory, decode every texture back
    --sheet        contact sheets build/s7/p/sheet_*.png of the new plates on the game's blue
Pure Pillow + numpy; fonts come from tools/arttext.py (Arial Bold / Arial Narrow Bold).
"""
import os
import sys
import json
import hashlib
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import numpy as np                       # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
import arttext                           # noqa: E402
import pvr                               # noqa: E402
import texinject                         # noqa: E402

OUT = os.path.join(ROOT, 'build', 's7', 'p', 'out')
TEXDIR = os.path.join(ROOT, 'translation', 'textures')
MANIFEST = os.path.join(ROOT, 'build', 's7', 'p_manifest.json')
CLUBWORDS = os.path.join(ROOT, 'translation', 'clubwords_art.tsv')

# --------------------------------------------------------------------------------------------- the table
# ALLLOGOS index -> four lines (None = unused row).  Names: J-League/select rows follow the spelling of the original logo art
# (translation/clubwords_art.tsv F/S rows), national teams are plain country names, foreign clubs are "<City> FC".
PLATES = {
    0: ['Antlers', 'Red Diamonds', 'JEF United', 'Reysol'],
    1: ['Verdy', 'F Marinos', 'Bellmare', 'S-Pulse'],   # skeptic: the Japanese plate itself abbreviates (F･マリノス); the full name was squashed to 0.68 at 22 px
    2: ['Júbilo', 'Grampus', 'Purple Sanga', 'Gamba'],
    3: ['Cerezo', 'Vissel Kobe', 'Sanfrecce', 'Avispa'],
    4: ['Consadole', 'Vegalta', 'Montedio', 'Ardija'],
    5: ['F.C.TOKYO', 'Frontale', 'Ventforet', 'Albirex'],
    6: ['Sagan Tosu', 'Trinita', 'East', 'West'],
    7: ['Dream', 'Dream', 'European XI', 'World XI'],
    8: ['Hollyhock', 'Yokohama FC', None, None],
    9: ['Japan', 'South Korea', 'Saudi Arabia', 'Iran'],
    10: ['Thailand', 'China', 'Kuwait', 'UAE'],
    11: ['Uzbekistan', 'Iraq', 'Kazakhstan', 'Turkmenistan'],
    12: ['North Korea', 'Qatar', 'Indonesia', 'Singapore'],
    13: ['Malaysia', 'Oman', 'Tajikistan', 'Hong Kong'],
    14: ['Kyrgyzstan', 'Taiwan', 'Macau', 'Nepal'],
    15: ['Australia', 'Nigeria', 'Morocco', 'Cameroon'],
    16: ['Tunisia', 'South Africa', 'Egypt', 'Zambia'],
    17: ['Ghana', 'Liberia', 'Zimbabwe', 'France'],
    18: ['Germany', 'Netherlands', 'Italy', 'England'],
    19: ['Spain', 'Croatia', 'Czech Republic', 'Yugoslavia'],
    20: ['Norway', 'Romania', 'Denmark', 'Russia'],
    21: ['Sweden', 'Belgium', 'Bulgaria', 'Scotland'],
    22: ['Portugal', 'Austria', 'Slovakia', 'Poland'],
    23: ['Greece', 'Switzerland', 'Israel', 'Ireland'],
    24: ['Turkey', 'Hungary', 'Finland', 'Ukraine'],
    25: ['Northern Ireland', 'Brazil', 'Argentina', 'Chile'],
    26: ['Colombia', 'Paraguay', 'Uruguay', 'Peru'],
    27: ['Bolivia', 'Venezuela', 'Ecuador', 'Mexico'],
    28: ['USA', 'Jamaica', 'Costa Rica', 'El Salvador'],
    29: ['Canada', 'Japan U-23', None, None],
    30: ['Incheon FC', 'Seoul FC', 'Daegu FC', 'Daejeon FC'],
    31: ['Busan FC', 'Riyadh FC', 'Tehran FC', 'Bangkok FC'],
    32: ['Qingdao FC', 'Shanghai FC', 'Dalian FC', 'Beijing FC'],
    33: ['Kuwait FC', 'Abu Dhabi FC', 'Bukhara FC', 'Baghdad FC'],
    34: ['Astana FC', 'Krasnovodsk FC', 'Pyongyang FC', 'Doha FC'],
    35: ['Jakarta FC', 'Singapore FC', 'Kuala Lumpur FC', 'Muscat FC'],
    36: ['Dushanbe FC', 'Hong Kong FC', 'Frunze FC', 'Taipei FC'],
    37: ['Kaohsiung FC', 'Macau FC', 'Kathmandu FC', 'Canberra FC'],
    38: ['Lagos FC', 'Casablanca FC', 'Yaounde FC', 'Carthage FC'],
    39: ['Johannesburg FC', 'Cairo FC', 'Lusaka FC', 'Accra FC'],
    40: ['Monrovia FC', 'Salisbury FC', 'Paris FC', 'Monaco FC'],
    41: ['Marseille FC', 'Dortmund FC', 'Munich FC', 'Bremen FC'],
    42: ['Amsterdam FC', 'Eindhoven FC', 'Rotterdam FC', 'Turin FC'],
    43: ['Milan FC', 'Rome FC', 'Lazio FC', 'Manchester FC'],
    44: ['London FC', 'Liverpool FC', 'Stamford FC', 'Barcelona FC'],
    45: ['Madrid FC', 'Valencia FC', 'Valladolid FC', 'Zagreb FC'],
    46: ['Prague FC', 'Belgrade FC', 'Oslo FC', 'Bucharest FC'],
    47: ['Copenhagen FC', 'Moscow FC', 'Stockholm FC', 'Brussels FC'],
    48: ['Sofia FC', 'Glasgow FC', 'Porto FC', 'Lisbon FC'],
    49: ['Coimbra FC', 'Vienna FC', 'Bratislava FC', 'Warsaw FC'],
    50: ['Athens FC', 'Bern FC', 'Israel FC', 'Dublin FC'],
    51: ['Ankara FC', 'Budapest FC', 'Helsinki FC', 'Kiev FC'],
    52: ['Sao Paulo FC', 'Rio de Janeiro FC', 'Belo Horizonte FC', 'Porto Alegre FC'],
    53: ['Santos FC', 'Buenos Aires FC', 'Boca FC', 'Santiago FC'],
    54: ['Medellin FC', 'Bogota FC', 'Asuncion FC', 'Montevideo FC'],
    55: ['Lima FC', 'La Paz FC', 'Caracas FC', 'Quito FC'],
    56: ['Acapulco FC', 'Mexico City FC', 'New York FC', 'Los Angeles FC'],
    57: ['Washington FC', 'Kingston FC', 'San Jose FC', 'San Salvador FC'],
    58: ['Ottawa FC', None, None, None],
    59: ['OFF', '???', 'TBD', 'Overseas Camp'],   # 10817: stage 6 installed the same wording first; its files are not in the manifest, so write_tex skips them
    60: ['Japanese Stars', 'Asian Stars', 'African Stars', 'N.Euro Stars'],
    61: ['Balkan Stars', 'Sakatsuku Stars', 'Spanish Legends', 'French Legends'],
    62: ['English Legends', 'Hollander Legends', 'Argentine Legends', 'Italian Legends'],
    63: ['German Legends', 'Brazilian Legends', 'Euro Super Stars', 'S.Am. Super Stars'],
    64: ['Euro Old Stars', 'S.Am. Old Stars', 'The World Stars', 'Dream Stars'],
    65: ['Wing Farms', None, None, None],
}
ALL_FILE, BIND_FILE, NAME_FILE = 'GAME/ALLLOGOS.BIN', 'GAME/BINDLOGO.BIN', 'GAME/BINDNAME.BIN'
BIND_COPY_OFFSET = 14            # BINDLOGO [14 + k] is the copy of ALLLOGOS [k]


def ids_of(k):
    """groups_v3 ids: ALLLOGOS [k] = 10758 + k (10817 = [59])."""
    return 10758 + k


# the original art draws these accents (clubwords_art.tsv art_spelling GLÜCK, MÉGÈRE, VALENTÍA); a texture is not limited to ASCII
ACCENTS = {'Gluck': 'Glück', 'Megere': 'Mégère', 'Valentia': 'Valentía'}


def club_words():
    """54 art spellings (ascii_for_strings) from clubwords_art.tsv rows 1..54 -> BINDLOGO [0..13] four per texture."""
    rows = []
    with open(CLUBWORDS, encoding='utf8') as f:
        hdr = next(f).rstrip('\n').split('\t')
        ci = hdr.index('ascii_for_strings')
        for line in f:
            p = line.rstrip('\n').split('\t')
            if p[0].isdigit():
                rows.append(p[ci])
    assert len(rows) == 54, len(rows)
    rows = [ACCENTS.get(r, r) for r in rows]
    return {t: [rows[t * 4 + i] if t * 4 + i < 54 else None for i in range(4)] for t in range(14)}


# --------------------------------------------------------------------------------------------- rendering
W, H = 128, 32
S = 4                         # supersample
BASE = 24                     # baseline y inside the 32 px cell
FSIZE = 29                    # em size in px (cap height about 21)
AVAIL = 123                   # text width budget (shadow adds 2)
MIN_SX = 0.62
GOOD_SX = 0.78                # squash accepted before the size is reduced
MIN_SIZE = 22
FACES = [('arial-bold', 1.0), ('arial-narrow-bold', 1.0)]
FILL_TOP, FILL_MID, FILL_BOT = (255, 255, 255), (238, 238, 238), (221, 221, 221)
_fc = {}


def _font(alias, px):
    path, _ = arttext.resolve_font(alias)
    if path is None:
        raise SystemExit('font %s not found' % alias)
    key = (path, px)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(path, px)
    return _fc[key]


def _mask(text, alias, size, sx):
    """Antialiased L mask of the text at S x, baseline at BASE*S, plus its ink x-extent (supersampled px)."""
    font = _font(alias, int(round(size * S)))
    bb = font.getbbox(text, anchor='ls')
    wpx = bb[2] - bb[0]
    pad = 8 * S
    im = Image.new('L', (wpx + 2 * pad, H * S), 0)
    ImageDraw.Draw(im).text((pad - bb[0], BASE * S), text, font=font, fill=255, anchor='ls')
    if sx != 1.0:
        nw = max(1, int(round(im.size[0] * sx)))
        im = im.resize((nw, im.size[1]), Image.LANCZOS)
    a = np.asarray(im)
    xs = np.where(a.max(0) > 8)[0]
    return a, int(xs[0]), int(xs[-1]) + 1


def fit_line(text):
    """Choose face / size / squash so the ink is at most AVAIL px wide.  Order of preference: regular face at full size;
    condensed face at full size; condensed face squashed down to GOOD_SX; then smaller sizes (down to MIN_SIZE) with that
    squash; finally squash down to MIN_SX.  Returns (mask array, x0, x1, info)."""
    for alias, _ in FACES:
        a, x0, x1 = _mask(text, alias, FSIZE, 1.0)
        if (x1 - x0) / S <= AVAIL:
            return a, x0, x1, (alias, FSIZE, 1.0)
    alias = FACES[-1][0]
    for size in range(FSIZE, MIN_SIZE - 1, -1):
        a, x0, x1 = _mask(text, alias, size, 1.0)
        w = (x1 - x0) / S
        sx = AVAIL / w
        if sx >= GOOD_SX:
            a, x0, x1 = _mask(text, alias, size, sx)
            return a, x0, x1, (alias, size, round(sx, 2))
    size = MIN_SIZE
    a, x0, x1 = _mask(text, alias, size, 1.0)
    sx = max(AVAIL / ((x1 - x0) / S), MIN_SX)
    a, x0, x1 = _mask(text, alias, size, sx)
    return a, x0, x1, (alias, size, round(sx, 2))


def render_line(text):
    """-> RGBA uint8 (32, 128, 4) and info."""
    a, x0, x1, info = fit_line(text)
    w = (x1 - x0) / S
    left = (1 + (AVAIL - w) / 2.0)             # ink left edge in px (the shadow takes the right side)
    off = int(round(left * S)) - x0
    m = np.zeros((H * S, W * S), np.uint8)
    ys = slice(0, H * S)
    for xd in range(max(0, off), min(W * S, off + a.shape[1])):
        m[:, xd] = a[:, xd - off]
    # fill: three grey bands over the cap height (the originals use ff / ee / dd), cheap for the VQ codebook
    yy = np.arange(H * S, dtype=np.float64) / S
    t = np.clip((yy - (BASE - 22)) / 22.0, 0, 1)
    rgb = np.empty((H * S, 3))
    for c in range(3):
        rgb[:, c] = np.where(t < 0.45, FILL_TOP[c], np.where(t < 0.8, FILL_MID[c], FILL_BOT[c]))
    fill = np.zeros((H * S, W * S, 4), np.float64)
    fill[..., :3] = rgb[:, None, :]
    fill[..., 3] = m / 255.0
    sh = np.zeros_like(m, dtype=np.float64)
    for d in range(1, 3):
        o = d * S
        shifted = np.zeros_like(m, dtype=np.float64)
        shifted[o:, o:] = m[:-o, :-o]
        sh = np.maximum(sh, shifted)
    sh /= 255.0
    # composite fill over shadow (premultiplied), then box-filter down
    fa = fill[..., 3]
    out_a = fa + sh * (1 - fa)
    out_rgb_pm = fill[..., :3] * fa[..., None]            # shadow colour is black: adds nothing
    pm = np.concatenate([out_rgb_pm, out_a[..., None]], -1)
    small = pm.reshape(H, S, W, S, 4).mean((1, 3))
    al = small[..., 3]
    rgb_o = np.where(al[..., None] > 1e-6, small[..., :3] / np.maximum(al[..., None], 1e-6), 0)
    res = np.concatenate([rgb_o, al[..., None] * 255.0], -1)
    return np.clip(np.rint(res), 0, 255).astype(np.uint8), info


def render_plate(lines):
    img = np.zeros((128, 128, 4), np.uint8)
    infos = []
    for r, t in enumerate(lines):
        if not t:
            infos.append(None)
            continue
        row, info = render_line(t)
        img[r * 32:(r + 1) * 32] = row
        infos.append(info)
    return img, infos


# --------------------------------------------------------------------------------------------- VQ encode that fits the slot
_SRC = {}


def src_bytes(file_rel):
    if file_rel not in _SRC:
        with open(os.path.join(ROOT, 'extracted', *file_rel.split('/')), 'rb') as f:
            _SRC[file_rel] = f.read()
    return _SRC[file_rel]


KS = (256, 192, 160, 128, 112, 96, 80, 72, 64, 56, 48, 40, 32)


def encode_fit(img, orig, file_rel, tid):
    """VQ-encode `img` into the format of `orig` (GBIX+PVRT file) with the largest codebook (k-means) whose packed size fits
    the container slot (policy 'exact').  Unused codebook entries stay zero so they pack to nothing.
    Returns (pvr bytes, K used, over bytes of the last try)."""
    payload, pix, dat, w, h, f = pvr._resolve(bytes(orig), None, None, None, None)
    assert dat == 3 and (w, h) == (128, 128), (dat, w, h)
    words = pvr.rgba_to_words(img, pix)
    blocks = pvr._vq_words_to_blocks(words)
    last = None
    for K in KS:
        cb, idx, info = pvr.vq_quantize(blocks, K, pix, seed=0)
        full = np.zeros((256, 4), np.uint16)
        full[:K] = cb
        # most used codes first: zero runs of the index stream and a compact used range
        use = np.bincount(idx, minlength=256)
        order = np.argsort(-use[:K], kind='stable')
        remap = np.zeros(K, np.int64)
        remap[order] = np.arange(K)
        full[:K] = cb[order]
        grid = remap[idx].reshape(64, 64)
        pl = full.astype('<u2').tobytes() + pvr._write_indices(grid)
        out = bytes(orig[:f.data_off]) + pl + bytes(orig[f.data_off + f.data_len:])
        if len(out) != len(orig):
            raise SystemExit('encode_fit: length changed %d vs %d' % (len(out), len(orig)))
        r = texinject.fit_check(src_bytes(file_rel), tid, out)
        last = r.get('over', 0)
        if r['fits']:
            return out, K, 0
    return out, K, last


# --------------------------------------------------------------------------------------------- IO helpers
def load_orig(file_rel, tid):
    with open(os.path.join(ROOT, 'extracted', *file_rel.split('/')), 'rb') as f:
        d = f.read()
    return texinject.extract_pvr(d, tid)


def on_blue(a, bg=(70, 90, 140)):
    al = a[..., 3:4].astype(float) / 255
    return Image.fromarray((a[..., :3] * al + np.array(bg) * (1 - al)).astype('uint8'))


def sha1(p):
    with open(p, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()


def load_manifest():
    try:
        with open(MANIFEST, encoding='utf8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_manifest(m):
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    tmp = MANIFEST + '.tmp'
    with open(tmp, 'w', encoding='utf8') as f:
        json.dump(m, f, indent=1, sort_keys=True)
    os.replace(tmp, MANIFEST)


def jobs(args):
    """list of (key, [(file, tid)...], lines)"""
    only = None
    if '--only' in args:
        only = set(int(x) for x in args[args.index('--only') + 1].split(','))
    j = []
    sel_words = '--words' in args
    sel_all = only is None and not sel_words and '--logo' not in args
    if sel_all or (only is not None):
        for k in sorted(PLATES):
            if only is not None and k not in only:
                continue
            j.append(('all%02d' % k, [(ALL_FILE, '[%d]' % k), (BIND_FILE, '[%d]' % (k + BIND_COPY_OFFSET))], PLATES[k]))
    if sel_all or sel_words:
        for t, lines in sorted(club_words().items()):
            j.append(('word%02d' % t, [(BIND_FILE, '[%d]' % t)], lines))
    return j


def write_tex(file_rel, tid, data, manifest, report):
    p = os.path.join(TEXDIR, *file_rel.split('/'), tid + '.pvr')
    rel = os.path.relpath(p, ROOT).replace(os.sep, '/')
    if os.path.exists(p):
        if rel not in manifest or manifest[rel] != sha1(p):
            report.append('SKIP (exists, not ours / changed): ' + rel)
            return False
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, p)
    manifest[rel] = sha1(p)
    return True


def main(argv):
    args = argv[1:]
    write = '--write' in args
    os.makedirs(OUT, exist_ok=True)
    manifest = load_manifest()
    report, warn = [], []
    tiles = []
    kinfo = []
    for key, targets, lines in jobs(args):
        img, infos = render_plate(lines)
        for r, inf in enumerate(infos):
            if inf and (inf[2] < 0.8 or inf[1] < FSIZE):
                warn.append('%s row %d %r: %s' % (key, r, lines[r], inf))
        Image.fromarray(img, 'RGBA').save(os.path.join(OUT, key + '.png'))
        encoded = None
        cache = {}
        for file_rel, tid in targets:
            orig = load_orig(file_rel, tid)
            ck = (orig, file_rel)
            got = cache.get(orig)               # byte-identical originals (ALLLOGOS [k] / BINDLOGO [k+14]) share the encoding...
            if got is not None and got[3] == texinject.fit_check(src_bytes(file_rel), tid, got[0]).get('fits'):
                enc, K, over, _ = got           # ...when it also fits this copy's slot
            else:
                enc, K, over = encode_fit(img, orig, file_rel, tid)
                cache[orig] = (enc, K, over, over == 0)
            kinfo.append((key, file_rel, tid, K, over))
            if over:
                warn.append('%s %s %s does not fit: K=%d over %d bytes' % (key, file_rel, tid, K, over))
            dec = np.asarray(pvr.decode(enc))
            if dec.shape != img.shape:
                raise SystemExit('%s: decode shape %s' % (key, dec.shape))
            if encoded is None:
                encoded = dec
            if write and not over:
                write_tex(file_rel, tid, enc, manifest, report)
        diff = np.abs(encoded.astype(int) - img.astype(int))
        tiles.append((key, encoded, float(diff[..., 3].mean()), float(diff[..., :3].max())))
        # before / after (original of the first target)
        ob = np.asarray(pvr.decode(load_orig(*targets[0])))
        pair = Image.new('RGB', (128 * 2 + 4, 128), (30, 30, 30))
        pair.paste(on_blue(ob), (0, 0))
        pair.paste(on_blue(encoded), (132, 0))
        pair.resize((pair.size[0] * 2, 256), Image.NEAREST).save(os.path.join(OUT, key + '_ba.png'))
        if write:
            save_manifest(manifest)
    if '--sheet' in args or True:
        cols = 4
        per = 12
        for s0 in range(0, len(tiles), per):
            chunk = tiles[s0:s0 + per]
            rows = (len(chunk) + cols - 1) // cols
            sheet = Image.new('RGB', (cols * 260, rows * 260), (20, 20, 20))
            d = ImageDraw.Draw(sheet)
            for i, (key, dec, e_a, e_c) in enumerate(chunk):
                tile = on_blue(dec).resize((256, 256), Image.NEAREST)
                sheet.paste(tile, ((i % cols) * 260, (i // cols) * 260))
                d.text(((i % cols) * 260 + 3, (i // cols) * 260 + 2), key, fill=(255, 255, 0))
            sheet.save(os.path.join(OUT, 'sheet_%02d.png' % (s0 // per)))
    for w in warn:
        print('FIT', w)
    print('codebook sizes used (min/median/max):', min(k[3] for k in kinfo), sorted(k[3] for k in kinfo)[len(kinfo) // 2], max(k[3] for k in kinfo))
    for r in report:
        print(r)
    print('rendered %d plates%s' % (len(tiles), ', written' if write else ''))
    worst = sorted(tiles, key=lambda t: -t[2])[:5]
    print('VQ alpha error (mean abs, worst 5):', [(k, round(a, 2)) for k, _, a, _ in worst])


if __name__ == '__main__':
    main(sys.argv)
