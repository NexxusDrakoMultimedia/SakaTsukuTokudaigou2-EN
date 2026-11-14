#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 the SakaTsuku Tokudaigou 2 English patch contributors
"""Self-test of the in-match OPTIONS highlight windows (tools/layoutpatch.py patch_options / options_patches / opt_cells, build flag --options-fix,
docs/layout-issues.md section 18):  python -I -X utf8 tools/test_optionsfix.py   (a second; reads extracted/ and translation/ only, builds no disc)

The OPTIONS panel of FLOW_PRG/GAME.BIN (copy in ENDING.BIN) draws the value of every option row dim, in 12 px character cells, and brightens the CURRENT
option with a sprite that re-draws a fixed window (a cell range) of the same text; the 11 window records are data (20 byte records 0x82..0x8c).  What is
checked (nothing starts an emulator or a disc build; the sprite engine itself is not simulated, see the notes in docs/layout-issues.md s18):
  1. the model: the windows computed from the JAPANESE value strings (full-width glyphs = 2 cells, middle dot separators) reproduce the 220 original record
     bytes of both overlays exactly (w = 2 (u1 - u0), x = 182 - 2 u0, u = 96 + 6 cell);
  2. why the English text broke: the ORIGINAL windows over the English strings light `ON/O` / nothing, `A/` / nothing, `ar` / `id` / `ar` (so a Far camera
     lit only `ar`, the playtest screenshot);
  3. the fix: with the English strings of the translation DB written in place (the bytes the text repacker produces) every window covers exactly the cells of
     its option word, for every row and both overlays; only the 220 byte block changes, h / y / v / type are kept; a Japanese image is returned unchanged;
     the windows follow a changed string (moved pointer, other indent); a second application, foreign bytes, a string that does not fit 14 cells or lacks its
     '/' are refused;
  4. build wiring: build_patch.apply_options_fix composes on the CURRENT bytes of both files, adds layout reports and a note, stops on a second application."""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import layoutpatch as LP   # noqa: E402

FAILS = []


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        FAILS.append(msg)


def read_ext(rel):
    with open(os.path.join(ROOT, 'extracted', *rel.split('/')), 'rb') as f:
        return f.read()


def raises(fn, text=''):
    try:
        fn()
    except LP.LayoutPatchError as e:
        return text in str(e)
    return False


def db_records(name):
    """the translation records of the OPTIONS pointer table of an overlay: {file offset: (en, max_bytes)}"""
    out = {}
    with open(os.path.join(ROOT, 'translation', 'FLOW_PRG__%s.BIN.jsonl' % name), encoding='utf8') as f:
        for line in f:
            if '"ctx":"tbl@%x[' % LP.OPT_SITES[name][0] in line:
                r = json.loads(line)
                out[int(r['id'].split('#')[1], 16)] = (r['en'], r['max_bytes'])
    return out


def english_image(name):
    """the extracted overlay with the DB English written in place into the table's string slots (what the repacker produces for these 10 strings)"""
    d = bytearray(read_ext('FLOW_PRG/%s.BIN' % name))
    for off, (en, mx) in db_records(name).items():
        b = en.encode('ascii')
        assert len(b) < mx, (name, hex(off), en)
        d[off:off + mx] = b + b'\0' * (mx - len(b))
    return bytes(d)


def lit(value, win):
    """the text under a window (first cell, end cell)"""
    return value[win[0]:win[1]].decode('ascii')


def cells_of(r):
    """the (first cell, end cell) of a sprite record"""
    return (r[4] - LP.OPT_U0) // 6, (r[6] - LP.OPT_U0) // 6


def records(d, name):
    rec0 = LP.OPT_SITES[name][1]
    return [struct.unpack_from('<10h', d, rec0 + 20 * i) for i in range(11)]


def sjis_cells(v, parts):
    """independent reference for the Japanese strings: full-width glyph = 2 cells, the 2 byte middle dot (0x8145) separates the options"""
    out, i, n = [], 0, len(v)
    while i < n and v[i] == 0x20:
        i += 1
    start = i
    while i < n:
        if v[i:i + 2] == b'\x81\x45':
            out.append((start, i))
            i += 2
            start = i
        else:
            i += 2 if v[i] >= 0x80 else 1
    out.append((start, n))
    assert len(out) == parts, (v, out)
    return out


EXPECT_EN = {   # sprite id -> (first cell, end cell, text) for the CURRENT DB strings
    0x82: (2, 4, 'ON'), 0x83: (5, 8, 'OFF'), 0x84: (2, 4, 'ON'), 0x85: (5, 8, 'OFF'), 0x86: (2, 4, 'ON'), 0x87: (5, 8, 'OFF'),
    0x88: (8, 9, 'A'), 0x89: (10, 11, 'B'),
    0x8A: (2, 6, 'Near'), 0x8B: (7, 10, 'Mid'), 0x8C: (11, 14, 'Far'),
}


def main():
    names = sorted(LP.OPT_SITES)
    jp = {n: read_ext('FLOW_PRG/%s.BIN' % n) for n in names}
    en = {n: english_image(n) for n in names}

    print('== 1. the model reproduces the original records from the Japanese strings')
    for n in names:
        tbl, rec0 = LP.OPT_SITES[n]
        check(jp[n][rec0:rec0 + 220] == LP.OPT_ORIG, '%s: the 220 original record bytes are the OPT_ORIG block at %#x' % (n, rec0))
        block = bytearray(LP.OPT_ORIG)
        for pair, ids in enumerate(LP.OPT_ROWS):
            v = LP._opt_value(jp[n], tbl, pair)
            for sid, cells in zip(ids, sjis_cells(v, len(ids))):
                o = (sid - 0x82) * 20
                block[o:o + 20] = LP.opt_window(bytes(block[o:o + 20]), cells)
        check(bytes(block) == LP.OPT_ORIG, '%s: windows computed from the Japanese values give the original records back (w, x, u0, u1)' % n)
        check(LP.options_windows(jp[n], n) is None and LP.patch_options(jp[n], n) == jp[n],
              '%s: the Japanese image is left unchanged (its original windows are right)' % n)
        cells = {sid: c for pair, ids in enumerate(LP.OPT_ROWS) for sid, c in zip(ids, sjis_cells(LP._opt_value(jp[n], tbl, pair), len(ids)))}
        check(cells[0x82] == (2, 6) and cells[0x83] == (8, 14) and cells[0x88] == (8, 10) and cells[0x89] == (12, 14) and cells[0x8A] == (4, 6)
              and cells[0x8B] == (8, 10) and cells[0x8C] == (12, 14), '%s: Japanese windows ON 2..5 OFF 8..13, A 8..9 B 12..13, Near 4..5 Mid 8..9 Far 12..13' % n)

    print('== 2. why the English text broke (original windows over the English strings)')
    for n in names:
        tbl, rec0 = LP.OPT_SITES[n]
        vals = [LP._opt_value(en[n], tbl, p) for p in range(5)]
        check(vals[0] == b'  ON/OFF' and vals[3] == b'        A/B' and vals[4] == b'  Near/Mid/Far', '%s: DB values are %r' % (n, vals))
        orig = {sid: ((r[4] - LP.OPT_U0) // 6, (r[6] - LP.OPT_U0) // 6) for sid, r in zip(range(0x82, 0x8D), records(jp[n], n))}
        got = {sid: lit(vals[p], orig[sid]) for p, ids in enumerate(LP.OPT_ROWS) for sid in ids}
        check(got[0x82] == 'ON/O' and got[0x83] == '' and got[0x88] == 'A/' and got[0x89] == '' and got[0x8A] == 'ar' and got[0x8B] == 'id' and got[0x8C] == 'ar',
              '%s: original windows light ON -> %r OFF -> %r  A -> %r B -> %r  Near -> %r Mid -> %r Far -> %r' % (
                  n, got[0x82], got[0x83], got[0x88], got[0x89], got[0x8A], got[0x8B], got[0x8C]))

    print('== 3. the fix')
    for n in names:
        tbl, rec0 = LP.OPT_SITES[n]
        new = LP.patch_options(en[n], n)
        check(len(new) == len(en[n]), '%s: same size' % n)
        diff = [i for i in range(len(new)) if new[i] != en[n][i]]
        check(diff and rec0 <= diff[0] and diff[-1] < rec0 + 220, '%s: only bytes inside the 220 byte record block change (%d bytes)' % (n, len(diff)))
        win = LP.options_windows(en[n], n)
        check({k: v for k, v in win.items()} == {k: (v[0], v[1]) for k, v in EXPECT_EN.items()}, '%s: windows are the cells of the option words %s' % (n, win))
        vals = [LP._opt_value(new, tbl, p) for p in range(5)]
        recs = records(new, n)
        old = records(en[n], n)
        for p, ids in enumerate(LP.OPT_ROWS):
            for sid in ids:
                r, o = recs[sid - 0x82], old[sid - 0x82]
                w, h, x, y, u0, v0, u1, v1, typ, z = r
                first, end = (u0 - LP.OPT_U0) // 6, (u1 - LP.OPT_U0) // 6
                ok = (u0 - LP.OPT_U0) % 6 == 0 and (u1 - LP.OPT_U0) % 6 == 0
                ok = ok and lit(vals[p], (first, end)) == EXPECT_EN[sid][2] and (first, end) == EXPECT_EN[sid][:2]
                ok = ok and w == 2 * (u1 - u0) == 12 * (end - first) and x == 182 - 2 * u0 and (h, y, v0, v1, typ, z) == (o[1], o[3], o[5], o[7], o[8], o[9])
                check(ok, '%s: record %#x (row %d): cells %d..%d = %r, w %d, x %d, h / y / v / type kept' % (n, sid, p, first, end - 1, lit(vals[p], (first, end)), w, x))
        # exactly the option word is lit, none of the other words and no blank: the lit text of every state
        for p, ids in enumerate(LP.OPT_ROWS):
            words = [lit(vals[p], cells_of(recs[s - 0x82])) for s in ids]
            check(words == [EXPECT_EN[s][2] for s in ids] and all(w.strip() == w and w for w in words),
                  '%s: row %d lights exactly %s' % (n, p, ' / '.join(words)))
        # the windows never overlap each other inside a row and stay inside the 14 cell value area
        for p, ids in enumerate(LP.OPT_ROWS):
            cs = [cells_of(recs[s - 0x82]) for s in ids]
            check(all(a[1] <= b[0] for a, b in zip(cs, cs[1:])) and cs[0][0] >= 0 and cs[-1][1] <= 14, '%s: row %d windows are ordered, disjoint and inside 14 cells' % (n, p))
        check(LP.patch_options(en[n], n) == new, '%s: deterministic' % n)
        # follow a changed string: other indent, other pointer (string copied to a new place and the table pointer moved)
        d = bytearray(en[n])
        slot = len(d) - 32                                   # a scratch string slot in the tail of this test copy
        for text, what in ((b'      Near/Mid/Far', None), (b'Near/Mid/Far', 'moved'), (b'Near Mid/Far', 'sep')):
            d[slot:slot + 32] = text + b'\0' * (32 - len(text))
            struct.pack_into('<I', d, tbl + 4 * 9, LP.OPT_BASE + slot)
            if what is None:
                check(raises(lambda: LP.patch_options(bytes(d), n), 'value area'), '%s: a value that runs past 14 cells is refused (6 blanks + Near/Mid/Far)' % n)
            elif what == 'moved':
                w2 = LP.options_windows(bytes(d), n)
                check(w2[0x8A] == (0, 4) and w2[0x8B] == (5, 8) and w2[0x8C] == (9, 12),
                      '%s: windows follow a moved / re-indented string (no indent: Near 0..3, Mid 5..7, Far 9..11)' % n)
            else:
                check(raises(lambda: LP.patch_options(bytes(d), n), "no '/'"), '%s: a value without its separator is refused' % n)
        check(raises(lambda: LP.patch_options(new, n), 'already patched'), '%s: a second application is refused' % n)
        f = bytearray(en[n])
        f[rec0 + 7] ^= 1
        check(raises(lambda: LP.patch_options(bytes(f), n), 'was found') or raises(lambda: LP.patch_options(bytes(f), n), 'original'), '%s: foreign records are refused' % n)

    print('== 4. build wiring (build_patch.apply_options_fix)')
    import build_patch as BP
    res = BP.Result()
    for n in names:
        res.patches['/FLOW_PRG/%s.BIN' % n] = en[n] + b''
    BP.apply_options_fix(res)
    ok = all(res.patches['/FLOW_PRG/%s.BIN' % n] == LP.patch_options(en[n], n) for n in names)
    check(ok and any('options fix' in x for x in res.notes) and sum(1 for f in res.files if f.iso.endswith('GAME.BIN') or f.iso.endswith('ENDING.BIN')) >= 2,
          'apply_options_fix patches the CURRENT bytes of GAME.BIN and ENDING.BIN, adds layout reports and a note')
    try:
        BP.apply_options_fix(res)
        check(False, 'apply_options_fix twice stops the build')
    except BP.PipelineError as e:
        check('options fix' in str(e), 'apply_options_fix twice stops the build (PipelineError: %s)' % str(e)[:70])
    res2 = BP.Result()
    BP.apply_options_fix(res2)
    check(res2.patches == {} and any('0 overlays' in x for x in res2.notes), 'on the Japanese originals nothing changes')

    print()
    if FAILS:
        print('%d FAILED' % len(FAILS))
        return 1
    print('all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
