"""Self test for tools/pvr.py (decode / encode of Dreamcast PVR textures) against the real disc files.

    python -I -X utf8 tools/test_pvr.py [--quick] [--per-format N] [--no-corpus]

What is proven (and printed with counts):
  1. unit: twiddle map is a bijection, every 16-bit word survives words->RGBA->words for ARGB1555/RGB565/ARGB4444,
     layout sizes, synthetic formats that do not occur on the disc (PAL4, YUV422, BUMP), GBIX/PVRT wrapper.
  2. corpus: EVERY texture found by pvr_scan (all carriers, duplicates counted but decoded once) decodes, and
       lossless data formats (twiddled, rectangle, stride, rect-twiddled, twiddled+mips):
           encode(decode(x), original=x) == x   bit exact      (real path, mips regenerated where applicable)
           encode(decode(x)) (no original)      == x   (non-mip)  /  top level identical (mips)
       VQ / small VQ (+mips):
           encode(decode(x), original=x)  == x  bit exact (codebook preserved)
           decode(encode(decode(x))) == decode(x) for the from-scratch quantiser and a second generation gives
           identical bytes (fixed point)
       PVR files: whole-file round trip including GBIX/PVRT header.
       paletted: decode(encode(decode(x), palette)) == decode(x)
  3. lossy: repainting real text textures (VQ, small VQ, twiddled, palette) keeps the exact byte length,
     unchanged blocks stay identical, PSNR inside the painted area is reported.
Exit code 0 only when everything passes.  A report is written to build/textures/test_report.txt.
"""
import os
import sys
import time
import hashlib
import collections
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
import pvr  # noqa: E402
import pvr_scan  # noqa: E402

OUT = os.path.join('build', 'textures')
FAILS = []
LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.append(s)


def check(cond, what):
    if not cond:
        FAILS.append(what)
        log('  FAIL:', what)
    return cond


# ---------------------------------------------------------------- 1. unit tests
def unit_tests():
    log('== unit tests')
    # twiddle map bijection + known corner values
    for n in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024):
        m = pvr.twiddle_map(n)
        check(sorted(m.ravel().tolist()) == list(range(n * n)), 'twiddle bijection n=%d' % n)
    m = pvr.twiddle_map(4)
    check(m[0, 0] == 0 and m[0, 1] == 2 and m[1, 0] == 1 and m[1, 1] == 3, 'twiddle (x odd bits, y even bits)')
    # every word survives
    words = np.arange(65536, dtype=np.uint16)
    for pix in (0, 1, 2):
        rgba = pvr.words_to_rgba(words, pix)
        back = pvr.rgba_to_words(rgba, pix)
        check(np.array_equal(back, words), 'word->rgba->word identity pix=%d' % pix)
    check(np.array_equal(pvr.rgba_to_words(pvr.words_to_rgba(words, 4), 4), words), 'BUMP word identity')
    # layout sizes seen on the disc (PROVEN against all decoded payload lengths in the corpus test)
    exp = {(1, 1, 64, 64): 8192, (1, 2, 8, 8): 172, (2, 2, 128, 128): 43692, (1, 3, 128, 128): 6144,
           (1, 4, 64, 64): 3424, (1, 4, 128, 128): 7520, (1, 0x10, 16, 16): 192, (1, 0x10, 32, 32): 512,
           (1, 0x10, 64, 64): 2048, (1, 0x11, 16, 16): 224, (1, 0x11, 32, 32): 864, (6, 7, 256, 256): 65536,
           (2, 9, 256, 32): 16384, (2, 0xD, 512, 128): 131072}
    for k, v in exp.items():
        check(pvr.data_size(*k) == v, 'data_size%s == %d' % (k, v))
    # wrapper
    payload = bytes(range(256)) * 8
    f = pvr.build_file(1, 1, 32, 32, payload, gbix=0x1234)
    p = pvr.parse_file(f)
    check(p is not None and p.gbix == 0x1234 and (p.pix, p.dat, p.w, p.h) == (1, 1, 32, 32) and
          f[p.data_off:p.data_off + p.data_len] == payload, 'GBIX/PVRT build/parse')
    f2 = pvr.build_file(1, 1, 32, 32, payload, gbix=None)
    check(pvr.parse_file(f2).gbix is None, 'bare PVRT parse')
    # synthetic formats that are not on the disc
    rng = np.random.RandomState(1)
    pal = pvr.Palette(rng.randint(0, 256, (16, 4)).astype(np.uint8), 6)
    pal.rgba[:, 3] = 255
    pal.rgba = np.unique(pal.rgba, axis=0)[:16]
    pay = bytes(rng.randint(0, 256, 128).astype(np.uint8))       # 16x16 4bpp = 128 bytes
    pal.rgba = np.concatenate([pal.rgba, np.zeros((16 - len(pal.rgba), 4), np.uint8) + np.arange(16 - len(pal.rgba))[:, None] + 7])
    img = pvr.decode(pay, 5, 5, 16, 16, palette=pal)
    enc = pvr.encode(img, 5, 5, 16, 16, palette=pal)
    check(pvr.decode(enc, 5, 5, 16, 16, palette=pal).tobytes() == img.tobytes(), 'PAL4 decode(encode(decode)) stable')
    check(len(enc) == 128, 'PAL4 payload length')
    pay8 = bytes(rng.randint(0, 256, 32 * 32).astype(np.uint8))
    pal8 = pvr.Palette(np.array([[i, (i * 7) & 255, (i * 13) & 255, 255] for i in range(256)], np.uint8), 6)
    img8 = pvr.decode(pay8, 6, 7, 32, 32, palette=pal8)
    check(pvr.encode(img8, 6, 7, 32, 32, palette=pal8) == pay8, 'PAL8 bit exact with unique palette')
    bump = bytes(rng.randint(0, 256, 8 * 8 * 2).astype(np.uint8))
    ib = pvr.decode(bump, 4, 1, 8, 8)
    check(pvr.encode(ib, 4, 1, 8, 8) == bump, 'BUMP bit exact')
    yuv_src = np.zeros((16, 16, 4), np.uint8)
    yy, xx = np.mgrid[0:16, 0:16]
    yuv_src[..., 0] = xx * 12
    yuv_src[..., 1] = yy * 10
    yuv_src[..., 2] = 90
    yuv_src[..., 3] = 255
    ey = pvr.encode(yuv_src, 3, 1, 16, 16)
    dy = pvr.decode(ey, 3, 1, 16, 16)
    check(len(ey) == 512 and np.abs(dy.astype(int) - yuv_src.astype(int)).mean() < 6, 'YUV422 smooth image error small')
    ey2 = pvr.encode(dy, 3, 1, 16, 16)
    check(np.abs(pvr.decode(ey2, 3, 1, 16, 16).astype(int) - dy.astype(int)).max() <= 3, 'YUV422 second generation stable (+-3)')
    try:
        pvr.data_size(1, 8, 16, 16)
        check(False, 'pal8+mips must raise (not implemented)')
    except pvr.PVRError:
        pass
    # k-means palette sanity
    big = rng.randint(0, 256, (64, 64, 4)).astype(np.uint8)
    big[..., 3] = 255
    p16 = pvr.quantize_palette(big, 16, 6)
    ids = pvr._nearest_palette(big, p16)
    err = np.abs(p16[ids].astype(float) - big.astype(float)).mean()
    rnd = rng.randint(0, 256, (16, 4)).astype(np.uint8)
    err_r = np.abs(rnd[pvr._nearest_palette(big, rnd)].astype(float) - big.astype(float)).mean()
    check(len(p16) == 16 and err < err_r, 'k-means palette beats a random palette (%.1f < %.1f)' % (err, err_r))
    log('   unit tests done, failures so far: %d' % len(FAILS))


# ---------------------------------------------------------------- 2. corpus
class Corpus:
    def __init__(self, per_format=0):
        self.per_format = per_format
        self.seen = set()
        self.rows = collections.Counter()
        self.uniq = collections.Counter()
        self.ok = collections.Counter()
        self.bitexact = collections.Counter()
        self.fixed = collections.Counter()
        self.filert = collections.Counter()
        self.filert_n = collections.Counter()
        self.hdr_rebuild = collections.Counter()
        self.pal_jobs = []
        self.pvps = {}
        self.errors = []
        self.oob = []
        self.skipped = collections.Counter()
        self.mipdiff = collections.defaultdict(list)
        self.t_dec = 0.0
        self.t_enc = 0.0

    def on(self, t):
        if t.kind == 'PVP':
            self.pvps[t.path] = t.payload
            return
        if t.payload is None:
            self.errors.append((t.path, t.index, 'no payload: ' + t.note))
            return
        k = (t.pix, t.dat)
        self.rows[k] += 1
        if t.dat in (7, 8, 5, 6):
            self.pal_jobs.append(t)
            return
        key = hashlib.md5(bytes([t.pix, t.dat]) + t.w.to_bytes(2, 'little') + t.h.to_bytes(2, 'little') + t.payload).digest()
        fkey = None
        if t.blob is not None:
            fkey = hashlib.md5(t.blob).digest()
        new_payload = key not in self.seen
        new_file = fkey is not None and fkey not in self.seen
        if not new_payload and not new_file:
            return
        self.seen.add(key)
        if fkey:
            self.seen.add(fkey)
        if self.per_format and self.uniq[k] >= self.per_format and not new_file:
            self.skipped[k] += 1
            return
        try:
            if new_payload:
                self.uniq[k] += 1
                self.one(t)
            if new_file:
                self.file_roundtrip(t)
        except Exception:  # noqa
            self.errors.append((t.path, t.index, traceback.format_exc(limit=3)))

    def one(self, t):
        k = (t.pix, t.dat)
        p = t.payload
        t0 = time.time()
        dec = pvr.decode_ex(p, t.pix, t.dat, t.w, t.h)
        self.t_dec += time.time() - t0
        img = dec.image
        self.ok[k] += 1
        t0 = time.time()
        what = '%s %d %s' % (t.path, t.index, k)
        good = True
        if getattr(dec, 'oob_indices', False):
            self.oob.append((t.path, t.index, k))
        if t.dat in (1, 9, 0xB, 0xD):
            e1 = pvr.encode(img, original=None, pix=t.pix, dat=t.dat, w=t.w, h=t.h)
            e2 = pvr.encode(img, t.pix, t.dat, t.w, t.h, original=p)
            good = e1 == p and e2 == p
            if good:
                self.bitexact[k] += 1
            self.fixed[k] += good
            if not good:
                check(False, 'lossless round trip ' + what)
        elif t.dat in (2, 0x12):
            e_orig = pvr.encode(img, t.pix, t.dat, t.w, t.h, original=p)
            e_reg = pvr.encode(img, t.pix, t.dat, t.w, t.h, original=p, mips='regen')
            e_new = pvr.encode(img, t.pix, t.dat, t.w, t.h)
            lay = pvr.Layout(t.pix, t.dat, t.w, t.h)
            top_off = lay.levels[0][2]
            same_top = e_reg[top_off:] == p[top_off:] and e_reg[:lay.levels[-1][2]] == p[:lay.levels[-1][2]]
            same_top_new = e_new[top_off:] == p[top_off:]
            d2 = pvr.decode(e_new, t.pix, t.dat, t.w, t.h)
            e_new2 = pvr.encode(d2, t.pix, t.dat, t.w, t.h)
            good = e_orig == p and same_top and same_top_new and np.array_equal(d2, img) and e_new2 == e_new
            if good:
                self.bitexact[k] += 1
            self.fixed[k] += good
            if not good:
                check(False, 'mip round trip %s (orig=%s top=%s topnew=%s dec=%s fixedpt=%s)' % (
                    what, e_orig == p, same_top, same_top_new, np.array_equal(d2, img), e_new2 == e_new))
            # fidelity of the stored lower level vs a box-filtered top (INFO, validates the mip layout)
            if t.w >= 8 and t.pix != 3:
                lvl1 = dec.levels[1].astype(float)
                ref = pvr.box_down(img).astype(float)
                self.mipdiff[k].append(float(np.abs(lvl1 - ref).mean()))
        else:                                    # VQ family
            e_orig = pvr.encode(img, t.pix, t.dat, t.w, t.h, original=p)
            e_reg = pvr.encode(img, t.pix, t.dat, t.w, t.h, original=p, mips='regen')
            e_new = pvr.encode(img, t.pix, t.dat, t.w, t.h, retrain=True)
            lay = pvr.Layout(t.pix, t.dat, t.w, t.h)
            d_new = pvr.decode(e_new, t.pix, t.dat, t.w, t.h)
            e_new2 = pvr.encode(d_new, t.pix, t.dat, t.w, t.h, retrain=True)
            if t.dat in (3, 0x10):
                reg_ok = e_reg == p
            else:    # mips are regenerated: the codebook + full level must be identical
                reg_ok = e_reg[:lay.head] == p[:lay.head] and e_reg[lay.levels[0][2]:lay.levels[0][2] + lay.levels[0][3]] == \
                    p[lay.levels[0][2]:lay.levels[0][2] + lay.levels[0][3]]
            good = e_orig == p and reg_ok and np.array_equal(d_new, img) and e_new2 == e_new and len(e_new) == len(p)
            if getattr(dec, 'oob_indices', False):
                # codebook-overrun textures: only the exact (unchanged) path is promised
                good = e_orig == p and len(e_new) == len(p)
            if good:
                self.bitexact[k] += 1
            self.fixed[k] += good
            if not good:
                check(False, 'VQ round trip %s (orig=%s reg=%s scratch_dec=%s fixedpt=%s)' % (
                    what, e_orig == p, reg_ok, np.array_equal(d_new, img), e_new2 == e_new))
        self.t_enc += time.time() - t0

    def file_roundtrip(self, t):
        k = (t.pix, t.dat)
        if t.dat in (5, 6, 7, 8):
            return
        self.filert_n[k] += 1
        img = pvr.decode(t.blob)
        enc = pvr.encode(img, original=t.blob, mips='regen') if t.dat not in (2, 0x12, 4, 0x11) else \
            pvr.encode(img, original=t.blob)
        good = enc == t.blob
        self.filert[k] += good
        if not good:
            check(False, 'PVR file round trip %s %s' % (t.path, k))
        f = pvr.parse_file(t.blob)
        rebuilt = pvr.build_file(f.pix, f.dat, f.w, f.h, t.blob[f.data_off:f.data_off + f.data_len], f.gbix)
        self.hdr_rebuild[rebuilt == t.blob] += 1


def corpus_tests(per_format):
    log('== corpus (decode every texture on the disc, re-encode)')
    c = Corpus(per_format)
    t0 = time.time()
    sc = pvr_scan.scan_all('extracted', on_texture=c.on, keep_rows=False)[0]
    log('   scan+test time %.0fs (decode %.0fs, encode %.0fs)' % (time.time() - t0, c.t_dec, c.t_enc))
    log('   texture records: %d  unique decoded: %d  carriers: %s' % (sum(c.rows.values()), sum(c.uniq.values()),
                                                                       dict(sc.carriers)))
    log('   %-10s %-14s %9s %8s %8s %10s' % ('pixfmt', 'datafmt', 'records', 'unique', 'decoded', 'bit-exact/fixed'))
    for k in sorted(c.rows):
        if k[1] in (5, 6, 7, 8):
            continue
        log('   %-10s %-14s %9d %8d %8d %10d' % (pvr.PIX_NAMES.get(k[0]), pvr.DAT_NAMES.get(k[1]), c.rows[k], c.uniq[k],
                                                  c.ok[k], c.fixed[k]))
        check(c.uniq[k] == c.ok[k] or c.skipped[k] > 0 or c.per_format, 'all unique decoded %s' % (k,))
    if c.skipped:
        log('   (sampling: skipped %d unique textures)' % sum(c.skipped.values()))
    for e in c.errors[:10]:
        check(False, 'corpus error %s' % (e,))
    log('   errors: %d' % len(c.errors))
    if c.oob:
        log('   textures whose indices run past the codebook (decoded as the GPU would): %d, e.g. %s' % (len(c.oob), c.oob[:3]))
    log('   PVR files whose header rebuilds byte-identically with build_file: %s' % dict(c.hdr_rebuild))
    log('   PVR-file round trips: %d / %d' % (sum(c.filert.values()), sum(c.filert_n.values())))
    for k, v in sorted(c.mipdiff.items()):
        log('   mip layout check %s: stored level 1 vs box-filtered top, mean abs diff %.2f (n=%d)' %
            (k, float(np.mean(v)), len(v)))
    paletted_tests(c)
    return c


def paletted_tests(c):
    log('-- paletted textures (%d records)' % len(c.pal_jobs))
    pal_for = {}
    for path, blob in c.pvps.items():
        pal_for[path] = pvr.parse_pvp(blob)
        rt = pvr.build_pvp(pal_for[path], original=blob)
        check(rt == blob, 'PVP byte-exact round trip ' + path)
    log('   %d PVP palette files parsed and rebuilt byte-exact' % len(c.pvps))
    os.makedirs(os.path.join(OUT, 'test'), exist_ok=True)
    for t in c.pal_jobs:
        pal = None
        if t.path.startswith('DPTEX/WALLPAPER'):
            n = t.path[len('DPTEX/WALLPAPER'):len('DPTEX/WALLPAPER') + 2]
            pal = pal_for.get('DPTEX/BANK%s.PVP' % n)
        elif t.path.startswith('TRAINING/BFGAME'):
            pal = pal_for.get('TRAINING/BFGAME.ZAR/bg_barx.pvp')
        if pal is None:
            check(False, 'no palette for ' + t.path)
            continue
        dec = pvr.decode_ex(t.payload, t.pix, t.dat, t.w, t.h, palette=pal)
        enc = pvr.encode(dec.image, t.pix, t.dat, t.w, t.h, palette=pal)
        dec2 = pvr.decode(enc, t.pix, t.dat, t.w, t.h, palette=pal)
        exact = enc == t.payload
        check(np.array_equal(dec2, dec.image), 'paletted decode(encode(decode)) stable ' + t.path)
        nuniq = len(np.unique(pal.rgba, axis=0))
        log('   %-44s %dx%d palette entries %d (distinct colours %d): bit exact=%s, decode stable=%s' % (
            t.path + '#%d' % t.index, t.w, t.h, len(pal), nuniq, exact, np.array_equal(dec2, dec.image)))
        if nuniq == len(pal):
            check(exact, 'paletted bit exact (unique palette) ' + t.path)
        if t.path.startswith('DPTEX/WALLPAPER00'):
            pvr.to_png(dec.image, os.path.join(OUT, 'test', 'wallpaper00_decoded.png'))
        # free palette: k-means palette from the decoded image reproduces it almost exactly
        r = pvr.encode_ex(dec.image, t.pix, t.dat, t.w, t.h, original=t.payload, palette=pal, new_palette=True)
        d3 = pvr.decode(r.data, t.pix, t.dat, t.w, t.h, palette=r.palette)
        mae = float(np.abs(d3.astype(int) - dec.image.astype(int)).mean())
        log('   %-44s k-means palette re-quantisation MAE %.2f, length %d == %d' % (t.path + '#%d' % t.index, mae, len(r.data), len(t.payload)))
        check(len(r.data) == len(t.payload), 'new palette length ' + t.path)


# ---------------------------------------------------------------- 3. lossy repaint tests
def paint(img, box, text, size=14, fill=(255, 255, 255), bg=(20, 40, 120)):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.fromarray(img.copy(), 'RGBA')
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=bg + (255,))
    try:
        font = ImageFont.load_default(size=size)
    except TypeError:
        font = ImageFont.load_default()
    d.text((x0 + 2, y0 + 1), text, fill=fill + (255,), font=font)
    return np.asarray(im).copy()


def region_psnr(a, b, box):
    x0, y0, x1, y1 = box
    d = a[y0:y1, x0:x1].astype(float) - b[y0:y1, x0:x1].astype(float)
    mse = (d ** 2).mean()
    return 99.0 if mse == 0 else 10 * np.log10(255.0 ** 2 / mse)


def repaint_job(label, find, box, text, palette=None):
    """find: predicate(Tex) -> bool, first match is used."""
    got = []

    class Stop(Exception):
        pass

    def cb(t):
        if t.kind != 'PVP' and t.payload is not None and find(t):
            got.append(t)
            raise Stop

    sc = pvr_scan.Scanner(on_texture=cb, keep_rows=False)
    try:
        for rel, p in pvr_scan.iter_files('extracted'):
            if label['file'] not in rel:
                continue
            sc.walk(rel, open(p, 'rb').read())
    except Stop:
        pass
    if not got:
        check(False, 'repaint: texture not found for ' + label['name'])
        return
    t = got[0]
    orig = t.blob if t.blob is not None else t.payload
    raw = dict(pix=t.pix, dat=t.dat, w=t.w, h=t.h) if t.blob is None else {}
    dec = pvr.decode_ex(orig, palette=palette, **raw)
    before = dec.image
    after_target = paint(before, box, text)
    t0 = time.time()
    r = pvr.encode_ex(after_target, original=orig, palette=palette, **raw)
    dt = time.time() - t0
    out = r.data
    check(len(out) == len(orig), 'repaint length preserved ' + label['name'])
    final = pvr.decode(out, palette=palette, **raw)
    target_q = pvr.words_to_rgba(pvr.rgba_to_words(after_target, t.pix), t.pix) if t.pix in (0, 1, 2) and t.dat not in (7,) \
        else after_target
    x0, y0, x1, y1 = box
    mask = np.ones(before.shape[:2], bool)
    mask[y0:y1, x0:x1] = False
    same = float((final[mask] == before[mask]).all(1).mean())
    ps = region_psnr(final, target_q, box)
    log('   %-34s %s/%s %dx%d  %.2fs  mode=%s merged=%s new=%s  outside-area identical %.1f%%  painted-area PSNR %.1f dB' % (
        label['name'], pvr.PIX_NAMES.get(t.pix), pvr.DAT_NAMES.get(t.dat), t.w, t.h, dt, r.info.get('mode'),
        r.info.get('merged_codes'), r.info.get('new_codes'), same * 100, ps))
    from PIL import Image
    side = np.concatenate([before, after_target, final], 1)
    bg = Image.new('RGBA', (side.shape[1], side.shape[0]), (255, 0, 255, 255))
    bg.alpha_composite(Image.fromarray(side, 'RGBA'))
    bg.convert('RGB').save(os.path.join(OUT, 'test', 'repaint_%s.png' % label['name']))
    check(ps > 14.0, 'repaint PSNR in painted area > 14 dB for ' + label['name'])
    check(same > 0.6 or t.dat not in (3, 4, 0x10, 0x11), 'repaint keeps most unchanged blocks for ' + label['name'])
    # retrain mode on the same input must also fit
    if t.dat in (3, 4, 0x10, 0x11):
        r2 = pvr.encode_ex(after_target, original=orig, retrain=True, **raw)
        check(len(r2.data) == len(orig), 'retrain length ' + label['name'])
        f2 = pvr.decode(r2.data, **raw)
        log('   %-34s   full retrain: painted-area PSNR %.1f dB, overall MAE %.2f' % (
            '', region_psnr(f2, target_q, box), float(np.abs(f2.astype(int) - target_q.astype(int)).mean())))


def lossy_tests():
    log('== repaint (lossy VQ / palette quantiser) tests; pictures in build/textures/test/')
    os.makedirs(os.path.join(OUT, 'test'), exist_ok=True)
    jobs = [
        (dict(name='VQ4444_helpdat', file='ETC_DATA/HELP.DAT'),
         lambda t: t.dat == 3 and t.pix == 2 and t.w >= 256, (4, 4, 140, 24), 'Coach Guide'),
        (dict(name='VQ4444_option02', file='DPTEX/OPTION02.PVR'),
         lambda t: t.dat == 3, (8, 8, 200, 40), 'Phone number 1'),
        (dict(name='smallVQ565_skin', file='GAME/'),
         lambda t: t.dat == 0x10 and t.pix == 1 and t.w == 64 and t.path.upper().endswith('.PVR'), (4, 4, 40, 18), 'ABC'),
        (dict(name='twid4444', file='ETC_DATA/'),
         lambda t: t.dat == 1 and t.pix == 2 and t.w == 128 and t.kind == 'TBD', (4, 4, 90, 24), 'Test Text'),
        (dict(name='VQmip565', file='ETC_DATA/MCH01A.TBD'),
         lambda t: t.dat == 4 and t.pix == 1 and t.w == 128, (4, 4, 80, 24), 'Mip'),
        (dict(name='rect4444', file='ETC_DATA/'),
         lambda t: t.dat == 9 and t.pix == 2 and t.w == 256 and t.h == 32, (2, 2, 120, 20), 'Rect text'),
    ]
    for label, find, box, text in jobs:
        try:
            repaint_job(label, find, box, text)
        except Exception:  # noqa
            check(False, 'repaint job %s raised %s' % (label['name'], traceback.format_exc(limit=4)))
    # palette wallpaper
    try:
        pal = pvr.parse_pvp(open('extracted/DPTEX/BANK00.PVP', 'rb').read())
        repaint_job(dict(name='PAL8_wallpaper', file='DPTEX/WALLPAPER00.PVR'), lambda t: True, (8, 8, 120, 30), 'English', palette=pal)
    except Exception:  # noqa
        check(False, 'repaint job pal8 raised %s' % traceback.format_exc(limit=4))


def main(argv):
    quick = '--quick' in argv
    per = 0
    if '--per-format' in argv:
        per = int(argv[argv.index('--per-format') + 1])
    elif quick:
        per = 25
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    unit_tests()
    if '--no-corpus' not in argv:
        corpus_tests(per)
    lossy_tests()
    log('== %d failure(s) in %.0fs' % (len(FAILS), time.time() - t0))
    for f in FAILS[:50]:
        log('   ', f)
    with open(os.path.join(OUT, 'test_report.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(LOG) + '\n')
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
