"""Contact sheet: decode every texture of the given files and tile them into one PNG.
usage: python -I -X utf8 tools/re/datatext/sheet.py <out.png> <file> [<file>...] [--max N] [--cell 128]
Files may be TBD/DAT bundles or PVR files.  Undecodable textures get a grey cell.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pvr


def textures(path):
    d = open(path, 'rb').read()
    if d[:4] in (b'GBIX', b'PVRT'):
        t = pvr.parse_pvr(d)
        if t:
            yield path, t['fmt'], t['dt'], t['w'], t['h'], t['data']
        return
    recs = pvr.parse_tbd(d)
    for i, r in enumerate(recs or []):
        try:
            plain = pvr.tbd_plain(r)
        except Exception:
            plain = None
        yield '%s[%d]' % (path, i), r['fmt'], r['dt'], r['w'], r['h'], plain


def thumb(rgba, w, h, cell):
    """nearest-neighbour downscale to fit cell x cell on a white background, return cell*cell*4 bytes"""
    s = max(w, h) / cell if max(w, h) > cell else 1.0
    tw, th = max(1, int(w / s)), max(1, int(h / s))
    out = bytearray(b'\xff\xff\xff\xff' * (cell * cell))
    for y in range(th):
        sy = min(h - 1, int(y * s))
        for x in range(tw):
            sx = min(w - 1, int(x * s))
            o = (sy * w + sx) * 4
            a = rgba[o + 3]
            r, g, b = rgba[o], rgba[o + 1], rgba[o + 2]
            # composite over mid-grey checker-less light background so alpha text stays visible
            bg = 200
            r, g, b = (r * a + bg * (255 - a)) // 255, (g * a + bg * (255 - a)) // 255, (b * a + bg * (255 - a)) // 255
            p = (y * cell + x) * 4
            out[p:p + 4] = bytes((r, g, b, 255))
    return out


def main(argv):
    out = argv[0]
    cell = 128
    mx = 48
    files = []
    i = 1
    while i < len(argv):
        if argv[i] == '--max':
            mx = int(argv[i + 1])
            i += 2
        elif argv[i] == '--cell':
            cell = int(argv[i + 1])
            i += 2
        else:
            files.append(argv[i])
            i += 1
    cells = []
    bad = 0
    for f in files:
        for name, fmt, dt, w, h, data in textures(f):
            if len(cells) >= mx:
                break
            rgba = pvr.decode(data, fmt, dt, w, h) if data is not None else None
            if rgba is None:
                bad += 1
                cells.append(bytes(b'\x80\x80\x80\xff' * (cell * cell)))
            else:
                cells.append(bytes(thumb(rgba, w, h, cell)))
    cols = min(8, max(1, len(cells)))
    rows = (len(cells) + cols - 1) // cols
    W, H = cols * cell, rows * cell
    img = bytearray(b'\xff' * (W * H * 4))
    for n, c in enumerate(cells):
        cx, cy = (n % cols) * cell, (n // cols) * cell
        for y in range(cell):
            img[((cy + y) * W + cx) * 4:((cy + y) * W + cx + cell) * 4] = c[y * cell * 4:(y + 1) * cell * 4]
    pvr.png(W, H, bytes(img), out)
    print(out, len(cells), 'cells', bad, 'undecodable')


if __name__ == '__main__':
    main(sys.argv[1:])
