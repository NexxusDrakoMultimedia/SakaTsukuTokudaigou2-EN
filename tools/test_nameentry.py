#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the SakaTsuku Tokudaigou 2 English patch contributors
"""Self-test of the Name Entry keyboard page order (tools/layoutpatch.py patch_name_entry / name_entry_patches / ne_pages, build flag --name-entry-order,
docs/layout-issues.md section 20):  python -I -X utf8 tools/test_nameentry.py   (a few seconds; reads extracted/ when present, builds no disc)

The ABC/123 tab of FLOW_PRG/N_ENTRY.BIN reaches its four keyboard pages (full-width 1-l, full-width m-z, half-width 1-l, half-width m-z) only through a NULL
terminated pointer table; the patch swaps the two pairs of pointer words so the tab opens on the half-width pages.  What is checked (nothing is booted):
  1. the page generator reproduces the four strings of the real image byte for byte, and the real table is in the documented original order;
  2. swap result: only the 8 changed bytes (low halves of the four words), same size, the exact bytes of the study (05e08d8c 82e08d8c 56df8d8c d3df8d8c);
  3. 'original' leaves the bytes identical (also on an already swapped image: it restores the original), a second application changes nothing, composition on
     the CURRENT bytes keeps earlier edits;
  4. refusals with a clear message: foreign image, a changed page, a duplicated page, an extra reference to a page pointer, a table that is not NULL bounded, a mixed order,
     an unknown order name;
  5. the assumptions the swap rests on, pinned on the real image: the table base word and the page-number variable are loaded by exactly the known instructions, every page
     pointer is referenced only by the table;
  6. build wiring: build_patch.apply_name_entry_order composes on the CURRENT bytes, 'original' touches nothing, a foreign image stops the build."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import layoutpatch as LP   # noqa: E402

FAILS = []
REAL = os.path.join(ROOT, 'extracted', 'FLOW_PRG', 'N_ENTRY.BIN')
TABLE = 0xE0D4
ORIG_WORDS = bytes.fromhex('56df8d8cd3df8d8c05e08d8c82e08d8c')
SWAP_WORDS = bytes.fromhex('05e08d8c82e08d8c56df8d8cd3df8d8c')


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        FAILS.append(msg)


def raises(fn, text=''):
    try:
        fn()
    except LP.LayoutPatchError as e:
        return text in str(e)
    return False


def synthetic():
    """a small image with the four pages, the NULL bounded table and unrelated words, laid out like the real one (base 0x8c8d0000)"""
    d = bytearray(0x400)
    pages = LP.ne_pages()
    offs, o = [], 0x100
    for p in pages:
        offs.append(o)
        d[o:o + len(p)] = p + b'\0'
        o += (len(p) + 1 + 3) & ~3
    t = 0x300
    for k, w in enumerate(offs):
        struct.pack_into('<I', d, t + 4 * k, LP.NE_BASE + w)
    struct.pack_into('<I', d, t - 4, 0)
    struct.pack_into('<I', d, t + 16, 0)
    struct.pack_into('<I', d, 0x40, 0x8C8D0300)     # an unrelated word pointing at the table (not at a page): allowed
    return bytes(d), t


def swapped_synth(d, t):
    return d[:t] + d[t + 8:t + 16] + d[t:t + 8] + d[t + 16:]


def real_tests(real):
    print('== 1. the real image')
    pages = LP.ne_pages()
    for k, (p, o) in enumerate(zip(pages, (0xDF56, 0xDFD3, 0xE005, 0xE082))):
        check(real[o:o + len(p) + 1] == p + b'\0', 'generated page %d (%d bytes) equals the image at %#x' % (k + 1, len(p), o))
    check([len(p) for p in pages] == [124, 49, 124, 49], 'page sizes 124 / 49 / 124 / 49 (5 rows and 2 rows of 12 two-byte cells, rows joined by LF)')
    check(real[TABLE:TABLE + 16] == ORIG_WORDS and real[TABLE - 4:TABLE] == bytes(4) and real[TABLE + 16:TABLE + 20] == bytes(4),
          'the ABC/123 table at %#x is in the original order, NULL before and after' % TABLE)
    first, order, words = LP._ne_locate(real, 'N_ENTRY')
    check(first == TABLE and order == 'original', '_ne_locate finds the table by content: %#x, order %s' % (first, order))

    print('== 2. the swap')
    new = LP.patch_name_entry(real)
    diff = [i for i in range(len(real)) if real[i] != new[i]]
    check(len(new) == len(real), 'same size (%d)' % len(new))
    check(new[TABLE:TABLE + 16] == SWAP_WORDS, 'the table now reads half-width pages first: %s' % new[TABLE:TABLE + 16].hex())
    check(diff == [0xE0D4, 0xE0D5, 0xE0D8, 0xE0D9, 0xE0DC, 0xE0DD, 0xE0E0, 0xE0E1], 'only the low two bytes of the four words change: %s' % [hex(i) for i in diff])
    check(LP.name_entry_patches(lambda p: real, None, 'half-first') == {LP.NE_ISO: new}, 'name_entry_patches returns the file under its disc path')

    print('== 3. original / idempotence / composition')
    check(LP.patch_name_entry(real, 'original') == real, "'original' on the original image is byte-identical")
    check(LP.name_entry_patches(lambda p: real, None, 'original') == {}, "name_entry_patches('original') on the original image reports no change")
    check(LP.patch_name_entry(new) == new, 'a second application changes nothing (idempotent)')
    check(LP.patch_name_entry(new, 'original') == real, "'original' on the swapped image restores the original bytes")
    check(LP.name_entry_patches(lambda p: real, {LP.NE_ISO: new}, 'half-first') == {}, 'an image that already is in order is reported unchanged')
    cur = bytearray(real)
    cur[0x1000] ^= 0x5A
    cur = bytes(cur)
    out = LP.name_entry_patches(lambda p: real, {LP.NE_ISO: cur}, 'half-first')[LP.NE_ISO]
    check(out[0x1000] == cur[0x1000] and out[TABLE:TABLE + 16] == SWAP_WORDS, 'composed on the CURRENT bytes (an earlier edit survives), not on extracted/')

    print('== 4. refusals')
    d = bytearray(real)
    check(raises(lambda: LP.patch_name_entry(bytes(len(real))), 'found 0 times'), 'a foreign (all zero) image of the same size is refused')
    d[0xE005 + 4] ^= 1
    check(raises(lambda: LP.patch_name_entry(bytes(d)), 'found 0 times'), 'a changed half-width page is refused (page not found)')
    d = bytearray(real) + real[0xDF56:0xDF56 + 125]
    check(raises(lambda: LP.patch_name_entry(bytes(d)), 'found 2 times'), 'a duplicated page is refused (not unique)')
    d = bytearray(real)
    struct.pack_into('<I', d, 0x2000, LP.NE_BASE + 0xE005)
    check(raises(lambda: LP.patch_name_entry(bytes(d)), 'referenced 2 time'), 'a second aligned reference to a page pointer is refused (the swap would not be safe)')
    d = bytearray(real)
    struct.pack_into('<I', d, TABLE + 16, LP.NE_BASE + 0xE005)
    check(raises(lambda: LP.patch_name_entry(bytes(d)), 'referenced 2 time'), 'a fifth page pointer in the table is refused (the pointer of half-width 1-l occurs twice)')
    d = bytearray(real)
    struct.pack_into('<I', d, TABLE + 16, 0x8C8D1234)
    check(raises(lambda: LP.patch_name_entry(bytes(d)), 'NULL terminated'), 'a table that is not NULL terminated is refused')
    d = bytearray(real)
    struct.pack_into('<I', d, TABLE - 4, 0x8C8D1234)
    check(raises(lambda: LP.patch_name_entry(bytes(d)), 'NULL preceded') or raises(lambda: LP.patch_name_entry(bytes(d)), 'NULL terminated'), 'a table that is not NULL preceded is refused')
    d = bytearray(real)
    d[TABLE:TABLE + 8] = real[TABLE + 4:TABLE + 8] + real[TABLE:TABLE + 4]
    check(raises(lambda: LP.patch_name_entry(bytes(d)), 'not consecutive'), 'a mixed order (first two words exchanged) is refused')
    check(raises(lambda: LP.patch_name_entry(real, 'half'), 'unknown name entry order'), 'an unknown order name is refused')


def synthetic_tests():
    print('== synthetic image (no extracted/ needed)')
    d, t = synthetic()
    s = swapped_synth(d, t)
    check(LP.patch_name_entry(d) == s and LP.patch_name_entry(s) == s and LP.patch_name_entry(s, 'original') == d and LP.patch_name_entry(d, 'original') == d,
          'swap, idempotence and restore on a synthetic overlay')
    nd = [i for i in range(len(d)) if d[i] != s[i]]
    check(0 < len(nd) <= 8 and all(t <= i < t + 16 for i in nd), 'only bytes of the four pointer words differ (%d)' % len(nd))
    check(raises(lambda: LP.patch_name_entry(bytes(len(d))), 'found 0 times'), 'foreign synthetic image refused')
    x = bytearray(d)
    struct.pack_into('<I', x, t + 16, 0x8C8D0100)
    check(raises(lambda: LP.patch_name_entry(bytes(x)), 'referenced 2 time'), 'synthetic: a fifth pointer to a page is refused')


def pinned_assumptions(real):
    print('== 5. assumptions pinned on the real image')
    base = LP.NE_BASE

    def loads(target):
        out = []
        for o in range(0, len(real) - 1, 2):
            w = struct.unpack_from('<H', real, o)[0]
            if (w & 0xF000) == 0xD000:
                t = ((o + 4) & ~3) + (w & 0xFF) * 4
                if t + 4 <= len(real) and struct.unpack_from('<I', real, t)[0] == base + target:
                    out.append(o)
        return out
    check(loads(0xE0D4) == [0x62C, 0x8A6, 0x3720, 0x3798], 'the ABC/123 table base 0xe0d4 is loaded by exactly 4 pc-relative loads: %s' % [hex(x) for x in loads(0xE0D4)])
    check(loads(0xE0EC) == [0x200, 0x628, 0x8A2, 0x356E], 'the page number 0xe0ec is loaded by exactly 4 pc-relative loads (init, 2 tab entries, page flip): %s' % [hex(x) for x in loads(0xE0EC)])
    check(real[0xE0EC] == 0 and real[0xE0F6:0xE0F8] == b'\0\0', 'page number and cursor index of the tab start at 0 in the image (and are zeroed at init 0x200 / 0x218)')
    for o in (0xDF56, 0xDFD3, 0xE005, 0xE082):
        n = sum(1 for p in range(0, len(real) - 3, 4) if struct.unpack_from('<I', real, p)[0] == base + o)
        check(n == 1, 'the pointer to page %#x occurs once (the table only)' % o)
    # the tab group tables of the other tabs are not touched by the patch
    check(LP.patch_name_entry(real)[0xE0B4:0xE0D4] == real[0xE0B4:0xE0D4], 'the hiragana (0xe0b4) and katakana (0xe0c0) page tables are untouched')


def wiring(real):
    print('== 6. build wiring (build_patch.apply_name_entry_order)')
    import build_patch as BP
    res = BP.Result()
    cur = bytearray(real)
    cur[0x1000] ^= 0x5A
    res.patches[LP.NE_ISO] = bytes(cur)
    BP.apply_name_entry_order(res, 'half-first')
    got = res.patches[LP.NE_ISO]
    check(got[TABLE:TABLE + 16] == SWAP_WORDS and got[0x1000] == cur[0x1000] and len(got) == len(real)
          and any('name entry order' in x for x in res.notes) and any(f.iso == LP.NE_ISO and f.kind == 'layout' for f in res.files),
          'apply_name_entry_order patches the CURRENT bytes, adds a layout report and a note')
    res2 = BP.Result()
    BP.apply_name_entry_order(res2, 'original')
    check(res2.patches == {} and res2.files == [] and res2.notes == [], "'original' touches nothing (no patch, report or note: the default output stays byte-identical)")
    res3 = BP.Result()
    BP.apply_name_entry_order(res3, 'half-first')
    check(res3.patches[LP.NE_ISO] == LP.patch_name_entry(real), 'with no earlier patch it reads extracted/ and swaps')
    res4 = BP.Result()
    res4.patches[LP.NE_ISO] = bytes(len(real))
    try:
        BP.apply_name_entry_order(res4, 'half-first')
        check(False, 'a foreign image stops the build')
    except BP.PipelineError as e:
        check('name entry order' in str(e) and 'found 0 times' in str(e), 'a foreign image stops the build (PipelineError: %s)' % str(e)[:90])
    try:
        BP.build_patches(name_entry_order='sideways')
        check(False, 'an unknown order stops build_patches')
    except BP.PipelineError as e:
        check('--name-entry-order' in str(e), 'an unknown order stops build_patches (%s)' % str(e)[:70])


def main():
    synthetic_tests()
    if os.path.exists(REAL):
        with open(REAL, 'rb') as f:
            real = f.read()
        real_tests(real)
        pinned_assumptions(real)
        wiring(real)
    else:
        print('NOTE extracted/FLOW_PRG/N_ENTRY.BIN is missing (fresh clone): the real-image checks 1-6 were NOT run')
    print()
    if FAILS:
        print('%d FAILED' % len(FAILS))
        return 1
    print('all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
