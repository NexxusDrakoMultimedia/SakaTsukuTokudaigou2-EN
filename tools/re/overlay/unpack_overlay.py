"""FLOW_PRG overlay loader/"unpacker".

FINDING: FLOW_PRG/*.BIN overlays are NOT compressed.  They are flat SH-4 memory
images (word 0 = entry stub) that are read verbatim into RAM at a fixed base.
The base is not in a header field; it is one of the 0x8cXX0000 literals in the
entry stub (passed as r5 to the cache-flush helper at 0x8c159144 in 1ST_READ),
and is proven by the image's own absolute pointers (pointer tables that land on
the starts of NUL-terminated Shift-JIS strings).

unpack_overlay(data) -> dict(load_addr, entry, image, ...)
Run as script:  python -I -X utf8 unpack_overlay.py [glob]
"""
import struct, sys, glob, os

RAM_LO, RAM_HI = 0x8C000000, 0x8D000000


def _is_lead(b):
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEA


def string_ptr_score(data, base):
    """# of aligned words whose target is the start of a NUL-preceded SJIS string"""
    n = len(data) // 4
    c = 0
    for w in struct.unpack('<%dI' % n, data[:n * 4]):
        o = w - base
        if 0x100 <= o < len(data) - 2 and data[o - 1] == 0 and _is_lead(data[o]):
            c += 1
    return c


def ptr_score(data, base):
    n = len(data) // 4
    lo, hi = base, base + len(data)
    return sum(1 for w in struct.unpack('<%dI' % n, data[:n * 4]) if lo <= w < hi)


def is_sh4_overlay(data):
    # entry stubs all start with a PC-relative mov.l (0xDnnn) / sts.l pr / push (0x2f..)
    return len(data) > 0x100 and data[1] in (0xD0, 0xD1, 0xD2, 0xD3, 0x4F, 0x2F) and \
        any(RAM_LO <= w < RAM_HI for w in struct.unpack('<64I', data[:0x100]))


def candidate_bases(data):
    c = set()
    for w in struct.unpack('<%dI' % (0x100 // 4), data[:0x100]):
        if RAM_LO <= w < RAM_HI:
            c.add(w & ~0xFFFF)          # 64K-aligned literal, or the 64K page of a literal
            if (w & 0xFFFF) == 0:
                c.add(w)
    return sorted(c)


def unpack_overlay(data: bytes) -> dict:
    if not is_sh4_overlay(data):
        raise ValueError('not a flat SH-4 overlay (no entry stub)')
    cands = candidate_bases(data)
    scored = sorted(((string_ptr_score(data, b), ptr_score(data, b), b) for b in cands), reverse=True)
    s, p, base = scored[0]
    return dict(load_addr=base, entry=base, image=bytes(data), end_addr=base + len(data),
                string_ptr_score=s, ptr_score=p, candidates=[hex(b) for b in cands],
                text_proven=s >= 10)


if __name__ == '__main__':
    files = sorted(glob.glob(sys.argv[1] if len(sys.argv) > 1 else 'extracted/FLOW_PRG/*.BIN'))
    bases = {}; ok = 0; proven = 0; bad = []
    for p in files:
        d = open(p, 'rb').read()
        try:
            r = unpack_overlay(d)
        except ValueError as e:
            bad.append(os.path.basename(p)); print('%-16s size=%8d  NOT-OVERLAY (%s)' % (os.path.basename(p), len(d), e)); continue
        ok += 1; proven += r['text_proven']
        bases.setdefault(r['load_addr'], []).append(os.path.basename(p))
        print('%-16s size=%8d base=%08x entry=%08x ptrs=%6d strptrs=%5d %s' % (
            os.path.basename(p), len(d), r['load_addr'], r['entry'], r['ptr_score'], r['string_ptr_score'],
            'TEXT-PROVEN' if r['text_proven'] else 'stub-only'))
    print(len(files), 'files; overlays parsed:', ok, ' base proven via SJIS string pointers:', proven, ' not overlays:', bad)
    for b, l in sorted(bases.items()): print(hex(b), len(l))
