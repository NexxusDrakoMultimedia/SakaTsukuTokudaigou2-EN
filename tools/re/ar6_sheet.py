"""ar6_sheet: labelled contact sheets from build/tex PNGs.
ar6_sheet.py OUTPREFIX [--source SUBSTR] [--member SUBSTR] [--not-member SUBSTR] [--ids a,b,c] [--tsv scan.tsv --top N]
            [--thumb 160] [--cols 6] [--rows 5] [--all]   (--all includes duplicate records)
Writes OUTPREFIX_NN.png and prints the id list per sheet."""
import os, sys
from PIL import Image, ImageDraw
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
IDX = os.path.join(ROOT, 'build', 'tex', 'index.tsv')


def arg(a, k, d=None):
    return a[a.index(k) + 1] if k in a else d


def main():
    a = sys.argv[1:]
    out = a[0]
    src = arg(a, '--source')
    mem = arg(a, '--member')
    nmem = arg(a, '--not-member')
    ids = arg(a, '--ids')
    thumb = int(arg(a, '--thumb', 160))
    cols = int(arg(a, '--cols', 6))
    rows_ = int(arg(a, '--rows', 5))
    allrec = '--all' in a
    rows = []
    with open(IDX, encoding='utf8') as f:
        hdr = f.readline().rstrip('\n').split('\t')
        for l in f:
            d = dict(zip(hdr, l.rstrip('\n').split('\t')))
            if d['dup_of'] and not allrec:
                continue
            if src and src not in d['source']:
                continue
            if mem and mem not in d['member']:
                continue
            if nmem and nmem in d['member']:
                continue
            rows.append(d)
    if ids:
        want = ids.split(',')
        rows = [d for d in rows if d['id'][:5] in want]
    if '--tsv' in a:
        tsv = [l.split('\t') for l in open(arg(a, '--tsv'), encoding='utf8').read().splitlines()[1:]]
        top = int(arg(a, '--top', 60))
        order = [t[3][:5] for t in tsv[:top]]
        m = {d['id'][:5]: d for d in rows}
        rows = [m[i] for i in order if i in m]
    per = cols * rows_
    cw = thumb + 4
    chh = thumb + 16
    n = 0
    for s in range(0, len(rows), per):
        chunk = rows[s:s + per]
        R = (len(chunk) + cols - 1) // cols
        sh = Image.new('RGB', (cols * cw, R * chh), (90, 90, 110))
        dr = ImageDraw.Draw(sh)
        for k, d in enumerate(chunk):
            p = os.path.join(ROOT, 'build', 'tex', d['source'].replace('/', '__'), d['id'] + '.png')
            try:
                im = Image.open(p).convert('RGBA')
            except Exception:
                continue
            bg = Image.new('RGBA', im.size, (110, 110, 130, 255))
            bg.alpha_composite(im)
            sc = min(thumb / bg.width, thumb / bg.height, 1.0 if '--noup' in a else 8)
            t = bg.convert('RGB').resize((max(1, int(bg.width * sc)), max(1, int(bg.height * sc))), Image.LANCZOS)
            x = (k % cols) * cw + 2
            y = (k // cols) * chh + 14
            sh.paste(t, (x, y))
            dr.text((x, y - 12), '%s %dx%d' % (d['id'][:5], bg.width, bg.height), fill=(255, 255, 0))
        fn = '%s_%02d.png' % (out, n)
        sh.save(fn)
        print(fn, ' '.join(d['id'][:5] for d in chunk))
        n += 1


main()
