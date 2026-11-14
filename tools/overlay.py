"""FLOW_PRG overlay (flat SH-4 memory image) helpers.

Finding (see docs/formats.md): FLOW_PRG/*.BIN overlays are NOT compressed.  The
file is a verbatim memory image whose first word is an entry stub; it is read
into RAM at a fixed base address (one of the 0x8cXX0000 literals in the stub,
the r5 argument of the helper at 0x8c159144).  Pointers inside the image are
absolute: file_offset = pointer - load_addr.

unpack_overlay(data) -> dict(load_addr, entry, image, end_addr, string_ptr_score,
                             ptr_score, candidates, text_proven, stub_literals)
pack_overlay(info_or_image, size_limit=None) -> bytes   (identity + checks)
va_to_off / off_to_va / read_cstr / patch_bytes helpers.

Run as a script for a survey:  python -I -X utf8 tools/overlay.py [glob]
"""
import glob
import os
import struct
import sys

RAM_LO, RAM_HI = 0x8C000000, 0x8D000000
STUB_SIZE = 0x40            # entry stub region (0x38..0xff is zero padding)


def _is_lead(b):
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEA


def string_ptr_score(data, base):
    """Number of aligned words that point at the start of a NUL-preceded
    Shift-JIS string inside the image."""
    n = len(data) // 4
    c = 0
    ln = len(data)
    for w in struct.unpack('<%dI' % n, data[:n * 4]):
        o = w - base
        if 0x100 <= o < ln - 2 and data[o - 1] == 0 and _is_lead(data[o]):
            c += 1
    return c


def ptr_score(data, base):
    n = len(data) // 4
    lo, hi = base, base + len(data)
    return sum(1 for w in struct.unpack('<%dI' % n, data[:n * 4]) if lo <= w < hi)


def is_sh4_overlay(data):
    return len(data) > 0x100 and data[1] in (0xD0, 0xD1, 0xD2, 0xD3, 0x4F, 0x2F) and \
        any(RAM_LO <= w < RAM_HI for w in struct.unpack('<64I', data[:0x100]))


def candidate_bases(data):
    c = set()
    for w in struct.unpack('<%dI' % (0x100 // 4), data[:0x100]):
        if RAM_LO <= w < RAM_HI:
            c.add(w & ~0xFFFF)
            if (w & 0xFFFF) == 0:
                c.add(w)
    return sorted(c)


def unpack_overlay(data):
    """Return the overlay image and its inferred load address.  There is no
    compression, so `image` is `data` unchanged."""
    data = bytes(data)
    if not is_sh4_overlay(data):
        raise ValueError('not a flat SH-4 overlay (no entry stub)')
    cands = candidate_bases(data)
    scored = sorted(((string_ptr_score(data, b), ptr_score(data, b), b) for b in cands), reverse=True)
    s, p, base = scored[0]
    return dict(load_addr=base, entry=base, image=data, end_addr=base + len(data),
                string_ptr_score=s, ptr_score=p, candidates=[hex(b) for b in cands],
                text_proven=s >= 10,
                stub_literals=[hex(w) for w in struct.unpack('<%dI' % (0x100 // 4), data[:0x100])
                               if RAM_LO <= w < RAM_HI])


def pack_overlay(info, size_limit=None):
    """Inverse of unpack_overlay.  Accepts the dict (possibly with a modified
    'image') or raw image bytes.  The stub must still look like an overlay
    entry.  `size_limit` (bytes) can be given to guard against growing a file
    past its on-disc slot / the memory span the game reserves."""
    img = bytes(info['image'] if isinstance(info, dict) else info)
    if not is_sh4_overlay(img):
        raise ValueError('image no longer starts with an overlay entry stub')
    if size_limit is not None and len(img) > size_limit:
        raise ValueError('image %d bytes exceeds limit %d' % (len(img), size_limit))
    return img


def va_to_off(info, va):
    o = va - info['load_addr']
    if not 0 <= o < len(info['image']):
        raise ValueError('address %#x outside image' % va)
    return o


def off_to_va(info, off):
    return info['load_addr'] + off


def read_cstr(info, va_or_off, is_offset=False):
    off = va_or_off if is_offset else va_to_off(info, va_or_off)
    img = info['image']
    e = img.index(b'\0', off)
    return img[off:e]


def patch_bytes(info, off, new, pad=b'\0'):
    """Overwrite image[off:off+len(new)] in place of a same-length region;
    returns a new info dict.  Refuses to change the image length."""
    img = bytearray(info['image'])
    img[off:off + len(new)] = new
    r = dict(info)
    r['image'] = bytes(img)
    return r


def main(argv):
    files = sorted(glob.glob(argv[0] if argv else 'extracted/FLOW_PRG/*.BIN'))
    ok = proven = rt = 0
    bad = []
    for p in files:
        d = open(p, 'rb').read()
        try:
            r = unpack_overlay(d)
        except ValueError:
            bad.append(os.path.basename(p))
            continue
        ok += 1
        proven += r['text_proven']
        rt += pack_overlay(r) == d
        print('%-16s size=%8d base=%08x strptrs=%5d %s' % (os.path.basename(p), len(d), r['load_addr'],
                                                          r['string_ptr_score'],
                                                          'TEXT-PROVEN' if r['text_proven'] else 'stub-only'))
    print('%d files, %d parsed as overlays, %d text-proven, %d round-trip identical, not overlays: %s'
          % (len(files), ok, proven, rt, bad))


if __name__ == '__main__':
    main(sys.argv[1:])
