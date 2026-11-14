"""texsheets - decode EVERY texture on the disc to PNG and build labelled contact sheets for reading the art.

    python -I -X utf8 tools/texsheets.py [--phase scan|sheets|all] [--only SUBSTR ...] [--out build/tex]

Outputs (all under build/tex/):
    <container>/<id>.png        one RGBA PNG per texture RECORD (duplicates are written too, bit-identical copies).
                                container = top-level file under extracted/ with '/' -> '__' (e.g. GAME__BIND01.BIN,
                                ATFIRST__TITLE.DAT); id = '<serial5>_<member>_<rec>' (serial is global and stable
                                for a given disc because files are walked in sorted order).
    index.tsv                   id, source, member, offset, width, height, format, bytes, then extras:
                                kind, rec, dup_of, alpha, sheet, alpha_sheet, status
                                source = top-level file; member = path inside it (ZSARC member / @hexoffset / name);
                                offset = last '@hex' in the member path (embedded table / chunk) or ''; bytes = payload
                                size; dup_of = id of the first record with the same format+payload (+palette);
                                alpha = opaque | binary | partial | empty (all pixels transparent);
                                sheet = sheet_NNNN for the FIRST copy of a payload ('' for later copies: see dup_of).
    sheets/sheet_NNNN.png       contact sheets of the DISTINCT textures (first copy only), same container together,
                                about 24-40 per sheet, mid-grey background, labelled '#serial WxH', container captions.
    sheets/sheet_map.json       {"sheets": {name: {file, alpha, items:[{n,id,container,x,y,w,h,src_w,src_h}]}},
                                 "by_id": {id: sheet}, "dups": {id: dup_of_id}, "alpha_by_id": {id: alpha_sheet}}
    sheets_alpha/alpha_NNNN.png the same view for every distinct texture that has any transparent pixel, drawn on a
                                checkerboard so transparent areas are visible (the main sheets show them as grey).
    notes.txt                   counts and caveats.

Texture sources: tools/pvr_scan.py (PROVEN carriers: PVR files/members/chunks, TBD tables) plus the headerless raw members
of GAME/GMSPONTX.ZAR, GAME/JSPONTX.ZAR, GAME/HAIRBEAR.ZAR, NEWS/SUIT0TEX.ZAR whose format is INFERRED from size
(kind RAW-inferred).  GAME/ACCESSRY.ZAR and GAME/FACEPART.ZAR members have an UNKNOWN layout and are not decoded.
Paletted textures use DPTEX/BANKnn.PVP for DPTEX/WALLPAPERnn.PVR (pairing INFERRED from numbers); the two
TRAINING/BFGAME.ZAR/bfgame.tbd textures use bg_barx.pvp / bg_pcom3.pvp in order (GUESS); others would be grey.
extracted/ is only read.
"""
import os
import re
import sys
import json
import time
import hashlib
import shutil
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

import numpy as np                     # noqa: E402
from PIL import Image, ImageDraw, ImageFont   # noqa: E402
import bzlib                           # noqa: E402
import pvr                             # noqa: E402
import pvr_scan                        # noqa: E402

SRC = os.path.join(ROOT, 'extracted')

# headerless raw members: (file, {payload length: (pix, dat, w, h)})   -- INFERRED from sizes + rendering
RAW_FILES = {
    'GAME/GMSPONTX.ZAR': {2048: (1, 0x10, 64, 64)},
    'GAME/JSPONTX.ZAR': {2048: (1, 0x10, 64, 64)},
    'GAME/HAIRBEAR.ZAR': {6144: (1, 3, 128, 128), 2048: (1, 0x10, 64, 64)},
    'NEWS/SUIT0TEX.ZAR': {32768: (1, 1, 128, 128), 131072: (1, 1, 256, 256)},
}

MAXN = 40          # textures per sheet (max)
SHEET_W = 1600
SHEET_HMAX = 1500
GAP = 8
LABEL_H = 14
CAPTION_H = 18
BG = (128, 128, 128)


def safe(s, n):
    s = re.sub(r'[^A-Za-z0-9_.\-]+', '_', s).strip('_.')
    return s[:n] if s else 'x'


def fmt_name(pix, dat):
    return '%s/%s' % (pvr.PIX_NAMES.get(pix, str(pix)), pvr.DAT_NAMES.get(dat, hex(dat)))


def alpha_class(rgba):
    a = rgba[..., 3]
    if a.max() == 0:
        return 'empty'
    if a.min() == 255:
        return 'opaque'
    if np.isin(a, (0, 255)).all():
        return 'binary'
    return 'partial'


# ---------------------------------------------------------------- palettes
def load_palettes():
    pals = {}
    for nn in range(4):
        p = os.path.join(SRC, 'DPTEX', 'BANK%02d.PVP' % nn)
        if os.path.exists(p):
            with open(p, 'rb') as f:
                pals['DPTEX/WALLPAPER%02d.PVR' % nn] = ('BANK%02d' % nn, pvr.parse_pvp(f.read()))
    bf = os.path.join(SRC, 'TRAINING', 'BFGAME.ZAR')
    if os.path.exists(bf):
        got = []

        def cb(t):
            if t.kind == 'PVP':
                got.append((t.path, t.payload))
        sc = pvr_scan.Scanner(cb, keep_rows=False)
        with open(bf, 'rb') as f:
            sc.walk('TRAINING/BFGAME.ZAR', f.read())
        got.sort(key=lambda x: x[0])
        names = [g[0] for g in got]
        order = [n for n in ('bg_barx.pvp', 'bg_pcom3.pvp')]
        for i, want in enumerate(order):
            for path, data in got:
                if path.endswith(want):
                    pals['TRAINING/BFGAME.ZAR/bfgame.tbd#%d' % i] = (want, pvr.parse_pvp(data))
    return pals


def palette_for(t, pals):
    if t.dat not in pvr.PAL_FORMATS:
        return None, ''
    if t.path in pals:
        return pals[t.path][1], pals[t.path][0]
    k = '%s#%d' % (t.path, t.index)
    if k in pals:
        return pals[k][1], pals[k][0]
    return None, 'nopal'


# ---------------------------------------------------------------- phase 1: scan + decode + png
class Ctx:
    pass


def phase_scan(out, only, log):
    t0 = time.time()
    pals = load_palettes()
    rows = []
    seen = {}          # key -> id of first
    counters = {'serial': 0, 'err': 0, 'distinct': 0}
    cur = {'top': None, 'dir': None}

    def emit(top, member, kind, rec, pix, dat, w, h, payload, stored, palette=None, palname=''):
        counters['serial'] += 1
        n = counters['serial']
        cont = safe(top.replace('/', '__'), 60)
        d = os.path.join(out, cont)
        if cur['dir'] != d:
            os.makedirs(d, exist_ok=True)
            cur['dir'] = d
        parts = [p for p in member.split('/') if p]
        stem = safe('_'.join(parts[-2:]) if parts else os.path.basename(top), 48)
        tid = '%05d_%s_%d' % (n, stem, rec)
        png = os.path.join(d, tid + '.png')
        m = re.findall(r'@([0-9a-fA-F]+)', member)
        offset = m[-1] if m else ''
        row = dict(id=tid, n=n, source=top, member=member, offset=offset, w=w, h=h, fmt=fmt_name(pix, dat),
                   bytes=(len(payload) if payload is not None else -1), kind=kind, rec=rec, dup_of='', alpha='',
                   sheet='', alpha_sheet='', status='ok', png=os.path.relpath(png, out).replace('\\', '/'),
                   pal=palname)
        key = (pix, dat, w, h, hashlib.md5(payload).hexdigest() if payload is not None else '', palname)
        if payload is None:
            row['status'] = 'ERR:no payload'
            counters['err'] += 1
        elif key in seen:
            first = seen[key]
            row['dup_of'] = first['id']
            row['alpha'] = first['alpha']
            if first['status'] == 'ok':
                shutil.copyfile(os.path.join(out, first['png']), png)
            else:
                row['status'] = first['status']
        else:
            try:
                img = pvr.decode(payload, pix, dat, w, h, palette=palette)
                row['alpha'] = alpha_class(img)
                Image.fromarray(img, 'RGBA').save(png, optimize=False, compress_level=3)
                counters['distinct'] += 1
            except Exception as e:   # noqa
                row['status'] = 'ERR:%s' % str(e)[:80]
                counters['err'] += 1
            seen[key] = row
        rows.append(row)

    def walk_top(rel, p):
        with open(p, 'rb') as f:
            data = f.read()

        def cb(t):
            if t.kind == 'PVP':
                return
            member = t.path[len(rel):].lstrip('/')
            pal, pn = palette_for(t, pals)
            emit(rel, member, t.kind, t.index, t.pix, t.dat, t.w, t.h, t.payload, t.stored, pal, pn)
        sc = pvr_scan.Scanner(cb, keep_rows=False)
        sc.walk(rel, data)
        if rel in RAW_FILES:
            members, tail = bzlib.parse_archive(data)
            tab = RAW_FILES[rel]
            for m in members:
                try:
                    pl = m.extract()
                except Exception:   # noqa
                    continue
                if len(pl) in tab and pl[:4] not in (b'GBIX', b'PVRT'):
                    pix, dat, w, h = tab[len(pl)]
                    emit(rel, m.name, 'RAW-inferred', 0, pix, dat, w, h, pl, len(pl))

    files = list(pvr_scan.iter_files(SRC))
    for i, (rel, p) in enumerate(files):
        if only and not any(s in rel for s in only):
            continue
        n0 = len(rows)
        walk_top(rel, p)
        if len(rows) != n0 and (i % 20 == 0 or len(rows) - n0 > 500):
            log('  [%4d/%d] %-40s +%d  total %d  distinct %d  err %d  %.0fs' % (
                i, len(files), rel[:40], len(rows) - n0, len(rows), counters['distinct'], counters['err'],
                time.time() - t0))
    write_index(out, rows)
    log('scan done: %d records, %d distinct decoded, %d errors, %.0fs' % (
        len(rows), counters['distinct'], counters['err'], time.time() - t0))
    return rows


COLS = ['id', 'source', 'member', 'offset', 'width', 'height', 'format', 'bytes', 'kind', 'rec', 'dup_of',
        'alpha', 'sheet', 'alpha_sheet', 'status', 'palette']


def write_index(out, rows):
    with open(os.path.join(out, 'index.tsv'), 'w', encoding='utf-8', newline='') as f:
        f.write('\t'.join(COLS) + '\n')
        for r in rows:
            vals = [r['id'], r['source'], r['member'], r['offset'], r['w'], r['h'], r['fmt'], r['bytes'], r['kind'],
                    r['rec'], r['dup_of'], r['alpha'], r['sheet'], r['alpha_sheet'], r['status'], r.get('pal', '')]
            f.write('\t'.join(str(v).replace('\t', ' ').replace('\n', ' ') for v in vals) + '\n')


def read_index(out):
    rows = []
    with open(os.path.join(out, 'index.tsv'), encoding='utf-8') as f:
        head = f.readline().rstrip('\n').split('\t')
        for line in f:
            v = line.rstrip('\n').split('\t')
            d = dict(zip(head, v))
            n = int(d['id'].split('_')[0])
            cont = safe(d['source'].replace('/', '__'), 60)
            rows.append(dict(id=d['id'], n=n, source=d['source'], member=d['member'], offset=d['offset'],
                             w=int(d['width']), h=int(d['height']), fmt=d['format'], bytes=int(d['bytes']),
                             kind=d['kind'], rec=int(d['rec']), dup_of=d['dup_of'], alpha=d['alpha'],
                             sheet=d['sheet'], alpha_sheet=d['alpha_sheet'], status=d['status'],
                             pal=d.get('palette', ''), png=cont + '/' + d['id'] + '.png'))
    return rows


# ---------------------------------------------------------------- phase 2: contact sheets
def display_size(w, h):
    L = max(w, h)
    if L < 128:
        k = -(-128 // L)
        k = min(k, 16)
        return w * k, h * k, Image.NEAREST
    if L == 128:
        return int(w * 1.5), int(h * 1.5), Image.BICUBIC
    if L <= 256:
        return w, h, Image.NEAREST
    f = 384.0 / L
    return max(1, round(w * f)), max(1, round(h * f)), Image.LANCZOS


_font = None


def font(sz=11):
    global _font
    if _font is None:
        try:
            _font = ImageFont.load_default(size=sz)
        except TypeError:
            _font = ImageFont.load_default()
    return _font


def checker(w, h, s=8):
    yy, xx = np.mgrid[0:h, 0:w]
    c = ((xx // s + yy // s) % 2).astype(np.uint8)
    v = np.where(c == 0, 190, 120).astype(np.uint8)
    return Image.fromarray(np.stack([v, v, v], -1), 'RGB')


class SheetBuilder:
    def __init__(self, outdir, prefix, use_checker, out_root):
        self.outdir, self.prefix, self.checker, self.root = outdir, prefix, use_checker, out_root
        os.makedirs(outdir, exist_ok=True)
        self.sheets = {}
        self.k = 0
        self._reset()

    def _reset(self):
        self.items = []      # (row, x, y, dw, dh, resample)
        self.conts = []
        self.x = 0
        self.y = CAPTION_H
        self.rowh = 0
        self.count = 0

    def finish(self):
        if not self.items:
            self._reset()
            return
        self.k += 1
        name = '%s_%04d' % (self.prefix, self.k)
        H = self.y + self.rowh + GAP
        sheet = Image.new('RGB', (SHEET_W, H), BG)
        dr = ImageDraw.Draw(sheet)
        f = font(11)
        dr.rectangle([0, 0, SHEET_W, CAPTION_H - 2], fill=(60, 60, 90))
        dr.text((4, 1), name + ':  ' + ',  '.join(self.conts), fill=(255, 255, 255), font=f)
        meta = []
        for row, x, y, dw, dh, rs in self.items:
            im = Image.open(os.path.join(self.root, row['png'])).convert('RGBA')
            im = im.resize((dw, dh), rs)
            if self.checker:
                bgc = checker(dw, dh).convert('RGBA')
                bgc.alpha_composite(im)
                sheet.paste(bgc.convert('RGB'), (x, y + LABEL_H))
            else:
                bgc = Image.new('RGBA', (dw, dh), BG + (255,))
                bgc.alpha_composite(im)
                sheet.paste(bgc.convert('RGB'), (x, y + LABEL_H))
            dr.rectangle([x - 1, y + LABEL_H - 1, x + dw, y + LABEL_H + dh], outline=(200, 80, 80))
            lab = '#%d %dx%d' % (row['n'], row['w'], row['h'])
            room = max(0, (max(dw, 96) - 8 * len(lab)) // 6)
            if room > 6:
                lab += ' ' + os.path.basename(row['source'])[:room]
            dr.text((x, y), lab, fill=(255, 255, 0), font=f)
            meta.append(dict(n=row['n'], id=row['id'], container=row['source'], x=x, y=y + LABEL_H, w=dw, h=dh,
                             src_w=row['w'], src_h=row['h'], alpha=row['alpha']))
        fn = os.path.join(self.outdir, name + '.png')
        sheet.save(fn, optimize=False, compress_level=3)
        self.sheets[name] = dict(file=os.path.relpath(fn, self.root).replace('\\', '/'), width=SHEET_W, height=H,
                                 alpha=self.checker, items=meta)
        self._reset()

    def add_group(self, cont, rows):
        """All rows belong to one container; keep them together if they fit."""
        if self.count and self.count + min(len(rows), MAXN) > MAXN:
            self.finish()
        for row in rows:
            dw, dh, rs = display_size(row['w'], row['h'])
            cw = max(dw, 96)
            ch = dh + LABEL_H
            if self.x + cw > SHEET_W and self.x > 0:
                self._newrow()
            if self.count >= MAXN or (self.y + max(self.rowh, ch) > SHEET_HMAX and self.count > 0):
                self.finish()
            if cont not in self.conts:
                self.conts.append(cont)
            self.items.append((row, self.x, self.y, dw, dh, rs))
            self.x += cw + GAP
            self.rowh = max(self.rowh, ch)
            self.count += 1

    def _newrow(self):
        self.y += self.rowh + GAP
        self.x, self.rowh = 0, 0


def phase_sheets(out, rows, log):
    t0 = time.time()
    by_id = {r['id']: r for r in rows}
    firsts = [r for r in rows if not r['dup_of'] and r['status'] == 'ok']

    def group(rs):
        g = []
        for r in rs:
            if g and g[-1][0] == r['source']:
                g[-1][1].append(r)
            else:
                g.append((r['source'], [r]))
        return g

    main = SheetBuilder(os.path.join(out, 'sheets'), 'sheet', False, out)
    for cont, rs in group(firsts):
        main.add_group(cont, rs)
    main.finish()
    log('main sheets: %d (%d distinct textures) %.0fs' % (len(main.sheets), len(firsts), time.time() - t0))

    alpha_rows = [r for r in firsts if r['alpha'] in ('binary', 'partial', 'empty')]
    al = SheetBuilder(os.path.join(out, 'sheets_alpha'), 'alpha', True, out)
    for cont, rs in group(alpha_rows):
        al.add_group(cont, rs)
    al.finish()
    log('alpha (checkerboard) sheets: %d (%d textures with transparent pixels) %.0fs' % (
        len(al.sheets), len(alpha_rows), time.time() - t0))

    sheet_of, asheet_of = {}, {}
    for name, s in main.sheets.items():
        for it in s['items']:
            sheet_of[it['id']] = name
    for name, s in al.sheets.items():
        for it in s['items']:
            asheet_of[it['id']] = name
    for r in rows:
        src = r['dup_of'] or r['id']
        r['sheet'] = sheet_of.get(src, '')
        r['alpha_sheet'] = asheet_of.get(src, '')
    write_index(out, rows)
    mp = dict(sheets=main.sheets, alpha_sheets=al.sheets,
              by_id={i: s for i, s in sheet_of.items()},
              dups={r['id']: r['dup_of'] for r in rows if r['dup_of']},
              alpha_by_id=asheet_of)
    with open(os.path.join(out, 'sheets', 'sheet_map.json'), 'w', encoding='utf-8') as f:
        json.dump(mp, f)
    counts = [len(s['items']) for s in main.sheets.values()]
    log('items per sheet: min %d  median %d  max %d' % (min(counts), sorted(counts)[len(counts) // 2], max(counts)))
    return main, al, firsts, alpha_rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--phase', default='all', choices=['scan', 'sheets', 'all'])
    ap.add_argument('--only', nargs='*', default=None, help='only top-level files whose path contains one of these')
    ap.add_argument('--out', default=os.path.join(ROOT, 'build', 'tex'))
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    logf = open(os.path.join(out, 'texsheets.log'), 'a', encoding='utf-8')

    def log(s):
        print(s, flush=True)
        logf.write(s + '\n')
        logf.flush()
    rows = None
    if a.phase in ('scan', 'all'):
        rows = phase_scan(out, a.only, log)
    if a.phase in ('sheets', 'all'):
        if rows is None:
            rows = read_index(out)
        main_b, al_b, firsts, alpha_rows = phase_sheets(out, rows, log)
        bad = [r for r in rows if r['status'] != 'ok']
        cls = {}
        for r in rows:
            cls[r['alpha']] = cls.get(r['alpha'], 0) + 1
        with open(os.path.join(out, 'notes.txt'), 'w', encoding='utf-8') as f:
            f.write('records %d, distinct %d, errors %d\n' % (len(rows), len(firsts), len(bad)))
            f.write('main sheets %d, alpha sheets %d\n' % (len(main_b.sheets), len(al_b.sheets)))
            f.write('alpha classes (records): %s\n' % cls)
            for r in bad[:50]:
                f.write('ERR %s %s %s\n' % (r['id'], r['source'], r['status']))
        log('records %d  distinct %d  errors %d  alpha classes %s' % (len(rows), len(firsts), len(bad), cls))
    return 0


if __name__ == '__main__':
    sys.exit(main())
