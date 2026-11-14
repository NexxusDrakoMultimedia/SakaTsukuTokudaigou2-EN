"""Self-test of the Event income table crowd line patch (tools/layoutpatch.py patch_crowd / crowd_patches, docs/layout-issues.md section 13):
python -I -X utf8 tools/test_crowdfix.py   (a few seconds; reads extracted/ and translation/ only, builds no disc)

The crowd-row function of FLOW_PRG/G_INCOME.BIN (file 0x2d0) builds `<hi>万<lo>人` in a 32 byte stack buffer and copies the unit strings with the
libc strncpy and hard-coded counts of 2 bytes.  The REAL function of the REAL overlay bytes runs in the SH-4 simulator (tools/sh4sim.py; division,
strncpy, strlen and the text-object creator are hooked, the digit routines run natively) on the Japanese original with the English unit records
('man' 'ppl' '0') and the English digit table written in place, exactly the bytes the text repacker produces:
  1. unpatched: 10827 -> '1ma827pp', 7 -> '7pp', 0 -> '0' (the playtest screenshot);
  2. patched (patch A + B): '1man 827ppl', '1man 5000ppl', '1man ppl', '827ppl', '7ppl', '0ppl', '9man 9999ppl'; every value ends at the same
     right edge (x = 504 + (8 - len) * 12 plus its pixel width, the proportional font table of tools/pixelwidth.py);
  3. byte level: same size, exactly 6 halfwords, 2 pool words and 2 five byte strings (in the zero padding) change; the unit records, the code before
     0x326 and everything else stay; a second application, a foreign image, a non-empty zero area, the untranslated Japanese image and a moved
     function are refused; crowd_patches composes on the CURRENT bytes and touches no other file."""
import json
import os
import struct
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import layoutpatch as LP   # noqa: E402
import pixelwidth as PW    # noqa: E402
import sh4sim              # noqa: E402
import textdb              # noqa: E402

FAILS = []
BASE = 0x8C4D0000
RET = 0xDEAD0000
STACK = 0x8CFF0000


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        FAILS.append(msg)


def read_ext(rel):
    with open(os.path.join(ROOT, 'extracted', *rel.split('/')), 'rb') as f:
        return f.read()


class Mach(sh4sim.Machine):
    """sh4sim.Machine plus bsr and dt"""

    def exec_op(self, op, pc):
        if (op >> 12) == 0xB:
            disp = op & 0xFFF
            if disp & 0x800:
                disp -= 0x1000
            self.PR = pc + 4
            return ('call', pc + 4 + disp * 2)
        if (op & 0xF0FF) == 0x4010:
            n = (op >> 8) & 15
            self.R[n] = (self.R[n] - 1) & sh4sim.M
            self.T = int(self.R[n] == 0)
            return None
        return super().exec_op(op, pc)


def hooks(m, got):
    def div(m):
        a, b = sh4sim.s32(m.R[1]), sh4sim.s32(m.R[0])
        q = abs(a) // abs(b)
        m.R[0] = (-q if (a < 0) != (b < 0) else q) & sh4sim.M

    def mod(m):
        a, b = sh4sim.s32(m.R[1]), sh4sim.s32(m.R[0])
        r = abs(a) % abs(b)
        m.R[0] = (-r if a < 0 else r) & sh4sim.M

    def strncpy(m):
        dst, src, n = m.R[4], m.R[5], m.R[6]
        z = False
        for i in range(n):
            c = 0 if z else m.rb(src + i)
            z = z or c == 0
            m.wn(dst + i, c, 1)
        m.R[0] = dst

    def strlen(m):
        a, n = m.R[4], 0
        while m.rb(a + n):
            n += 1
        m.R[0] = n

    def textobj(m):                      # 0x8c4d43dc: the string pointer is the stack argument
        p = m.rn(m.R[15], 4)
        n = 0
        while m.rb(p + n):
            n += 1
        got['text'] = bytes(m.rb(p + k) for k in range(n))
        m.R[0] = 0x8CF00000
    m.ext_ret.update({0x8C012BF8: div, 0x8C013460: mod, 0x8C013294: strncpy, 0x8C014DE4: strlen, 0x8C4D43DC: textobj})


def english(orig):
    """the Japanese original with what the text repacker writes: the unit records 'man' / 'ppl' / '0' in place and the English digit table
    (pointer table 0x2679c..0x267c4 -> '0'..'9','-' strings of 2 bytes at 0x267db)"""
    d = bytearray(orig)
    d[0x26490:0x26494] = b'man\0'
    d[0x26494:0x26498] = b'ppl\0'
    d[0x26498:0x2649c] = b'0\0\0\0'
    for i, c in enumerate('0123456789-'):
        d[0x267db + 2 * i:0x267db + 2 * i + 2] = c.encode() + b'\0'
        struct.pack_into('<I', d, 0x2679c + 4 * i, BASE + 0x267db + 2 * i)
    return bytes(d)


def run(img, value):
    got = {}
    k = read_ext('1ST_READ.BIN')
    m = Mach()
    m.load(BASE, img)
    m.load(0x8C010000, k)
    m.native = [(BASE, BASE + len(img)), (0x8C013814, 0x8C013860)]
    hooks(m, got)

    def at_len(m):
        got['len'] = (m.R[14] - m.R[3]) & 0xFFFF
        raise StopIteration
    m.R = [0] * 16
    m.R[15] = STACK
    m.R[4] = value
    m.PR = RET
    try:
        m.run(BASE + 0x2D0, RET, watch={BASE + 0x37C: at_len})
    except StopIteration:
        pass
    return got


def model(n):
    """what the patched game must print"""
    if n == 0:
        return '0ppl'
    hi, lo = divmod(n, 10000)
    return (('%dman ' % hi) if hi else '') + (str(lo) if lo else '') + 'ppl'


def show(img, v):
    g = run(img, v)
    t = g['text']
    s = unicodedata.normalize('NFKC', t.decode('cp932', 'replace'))
    ln = g['len']
    px = PW.line_px(s)[0]
    x = 504 + (8 - ln) * 12
    return s, ln, x, px, x + px


def main():
    print('== the DB records the patch relies on')
    recs = {}
    with open(os.path.join(ROOT, 'translation', 'FLOW_PRG__G_INCOME.BIN.jsonl'), encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            recs[r['id']] = r
    for rid, ja, en in (('FLOW_PRG/G_INCOME.BIN#26490', '万', 'man'), ('FLOW_PRG/G_INCOME.BIN#26494', '人', 'ppl'), ('FLOW_PRG/G_INCOME.BIN#26498', '0人', '0')):
        r = recs.get(rid)
        check(r is not None and r['ja'] == ja and r['en'] == en and r['max_bytes'] == 4, 'DB record %s: %r -> %r (max_bytes 4)' % (rid, ja, en))
    check(recs['FLOW_PRG/G_INCOME.BIN#2003c']['en'] == '@B/Earn@' and recs['FLOW_PRG/G_INCOME.BIN#20045']['en'] == '@Y/Cost@',
          "tab records read '@B/Earn@' and '@Y/Cost@' (user decision)")

    print('== byte level')
    jp = read_ext('FLOW_PRG/G_INCOME.BIN')
    check(textdb.load_image('FLOW_PRG/G_INCOME.BIN').base == LP.CROWD_BASE == BASE, 'G_INCOME load address is 0x8c4d0000')
    check(jp[LP.CROWD_CODE:LP.CROWD_CODE + LP.CROWD_LEN] == LP.CROWD_SIG and LP.CROWD_LEN == 232, 'the 232 byte signature is the original code at 0x2d0')
    en = english(jp)
    new = LP.patch_crowd(en)
    diff = [i for i in range(len(en)) if en[i] != new[i]]
    check(len(new) == len(en), 'same size (%d bytes)' % len(new))
    sites = set()
    for off, old, nw in LP.CROWD_EDITS:
        check(struct.unpack_from('<H', en, off)[0] == old and struct.unpack_from('<H', new, off)[0] == nw, 'halfword %#x: %04x -> %04x' % (off, old, nw))
        sites.update((off, off + 1))
    for pool, off in LP.CROWD_POOL.items():
        check(struct.unpack_from('<I', new, pool)[0] == BASE + off, 'pool word %#x -> %#x' % (pool, BASE + off))
        sites.update(range(pool, pool + 4))
    for off, s in LP.CROWD_NEW.items():
        check(new[off:off + len(s)] == s and not any(en[off:off + len(s)]), 'string %r at %#x (the bytes were zero)' % (s, off))
        sites.update(range(off, off + len(s)))
    # the pool word of the 'man' unit may already hold the right value (0x3d8 -> 0x264a0 differs from 0x26490, so it changes); only listed sites differ
    check(set(diff) <= sites and len(diff) == 16, 'only the listed sites change (%d bytes: 6 code, 2 pool, 8 string bytes)' % len(diff))
    check(new[0x26490:0x2649c] == en[0x26490:0x2649c], 'the three unit records man / ppl / 0 are untouched (ppl is still read in place)')

    print('== simulation (the real function)')
    values = (0, 7, 827, 5000, 10000, 10827, 15000, 20000, 62345, 99999)
    want_old = {10827: '1ma827pp', 7: '7pp', 0: '0', 10000: '1mapp'}
    for v, w in want_old.items():
        s = show(en, v)[0]
        check(s == w, 'UNPATCHED %d -> %r (expected the screenshot form %r)' % (v, s, w))
    edges = {}
    for v in values:
        s, ln, x, px, edge = show(new, v)
        edges[v] = edge
        check(s == model(v), 'PATCHED %d -> %r (x=%d, %d px, right edge %d)' % (v, s, x, px, edge))
    check(show(new, 10827)[0] == '1man 827ppl' and show(new, 827)[0] == '827ppl' and show(new, 0)[0] == '0ppl', "'1man 827ppl' / '827ppl' / '0ppl'")
    lo, hi = min(edges.values()), max(edges.values())
    check(hi - lo <= 1 and 592 <= lo and hi <= 594, 'every value ends at the same right edge (%d..%d, the money rows end at 600)' % (lo, hi))
    check(show(new, 99999)[2] >= 456, 'the longest value (9man 9999ppl) starts at x=%d, clear of the Crowd label column (x 104..163)' % show(new, 99999)[2])
    # patch A alone (the zero case keeps the old lone '0')
    only_a = bytearray(en)
    for off, old, nw in LP.CROWD_EDITS[:4]:
        struct.pack_into('<H', only_a, off, nw)
    only_a[0x264A0:0x264A5] = b'man \0'
    struct.pack_into('<I', only_a, 0x3D8, BASE + 0x264A0)
    check(show(bytes(only_a), 10827)[0] == '1man 827ppl' and show(bytes(only_a), 0)[0] == '0', 'patch A alone gives 1man 827ppl and keeps a lone 0 (patch B is the zero case)')

    print('== refusals')
    for bad, why in ((new, 'already patched'), (b'\0' * len(en), 'foreign (zero) image'), (jp, 'untranslated Japanese units'),
                     (en[:0x1000], 'truncated image'), (en[:0x100] + b'\0' * 2 + en[0x100:], 'moved function'),
                     (en[:0x264A8] + b'x' + en[0x264A9:], 'zero area in use'),
                     (en[:0x326] + struct.pack('<H', 0xE603) + en[0x328:], 'a changed copy count')):
        try:
            LP.patch_crowd(bad)
            check(False, '%s is refused' % why)
        except LP.LayoutPatchError:
            check(True, '%s is refused' % why)
    try:
        LP.patch_crowd(jp)
    except LP.CrowdUntranslated:
        check(True, 'the untranslated image raises CrowdUntranslated (the build skips the fix with a note)')
    else:
        check(False, 'the untranslated image raises CrowdUntranslated')
    pp = bytearray(en)
    struct.pack_into('<I', pp, 0x3E0, BASE + 0x2649C)           # 'ppl' pointer to something else
    try:
        LP.patch_crowd(bytes(pp))
        check(False, 'a unit pointer that does not read ppl is refused')
    except LP.LayoutPatchError:
        check(True, 'a unit pointer that does not read ppl is refused')

    print('== crowd_patches')
    out = LP.crowd_patches(lambda p: jp, {LP.CROWD_ISO: en})
    check(list(out) == [LP.CROWD_ISO] and out[LP.CROWD_ISO] == new, 'composes on the CURRENT bytes and returns only G_INCOME.BIN')
    cur = bytearray(en)
    cur[0x100:0x104] = b'KEEP'                                   # an earlier stage's change elsewhere is kept
    out = LP.crowd_patches(lambda p: jp, {LP.CROWD_ISO: bytes(cur)})
    check(out[LP.CROWD_ISO][0x100:0x104] == b'KEEP', 'earlier changes of the current image are kept')
    try:
        LP.crowd_patches(lambda p: jp, None)
        check(False, 'the untranslated extracted image is refused when nothing was built')
    except LP.LayoutPatchError:
        check(True, 'the untranslated extracted image is refused when nothing was built')

    print('== build wiring (build_patch.apply_crowd_fix)')
    import build_patch as BP
    res = BP.Result()
    res.patches[LP.CROWD_ISO] = en
    BP.apply_crowd_fix(res)
    check(res.patches[LP.CROWD_ISO] == new and any('crowd fix' in n for n in res.notes) and len(res.files) == 1 and res.files[0].kind == 'layout',
          'apply_crowd_fix patches the CURRENT G_INCOME bytes, adds a layout report and a note')
    try:
        BP.apply_crowd_fix(res)
        check(False, 'apply_crowd_fix twice stops the build')
    except BP.PipelineError as e:
        check('crowd fix' in str(e), 'apply_crowd_fix twice stops the build (PipelineError: %s)' % str(e)[:60])
    res = BP.Result()
    BP.apply_crowd_fix(res)
    check(not res.patches and any('skipped' in n for n in res.notes), 'a build whose G_INCOME text is still Japanese (partial database) skips the fix with a note')

    print('\n%d checks failed' % len(FAILS) if FAILS else '\nall checks passed')
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
