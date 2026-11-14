"""Self-test of the scout panel fix (tools/layoutpatch.py patch_scout / scout_patches, docs/layout-issues.md section 11):
python -I -X utf8 tools/test_scoutfix.py   (about 1 minute; reads extracted/ only, builds no disc)

The scout info panel of SCDRF and SEARCH (two builders each: 0x7598-style = current player with '%4d/%d yrs', 0x76d8-style = candidate with
'Wants %2d yrs') fills a 12 wide row buffer b[37..87]: money | newline b[49] | row 2 | newline b[62] | age row b[63..74] | newline b[75] |
club b[76..87] | NUL b[88].  The two REAL builders of the REAL overlay bytes run in the SH-4 simulator (tools/sh4sim.py) with the English
formats put in the format table (the same pointers the text repacker writes):
  1. the unpatched code with 'Age %2d' (6 characters + NUL at b+71) overwrites its own digits: the Age number is blank;
  2. the patched code (`add #71,r4` -> `add #69,r4` in the delay slot of the two sprintf calls) gives 'Age 25' right aligned in 12 on both
     builders of both overlays;
  3. the row 2 format '%4d/%d yrs' (10 characters) lets the sprintf NUL stay at b[60] and rows 3 and 4 disappear; the 12 character
     '%4d/%d yrs  ' of the translation DB fixes that (the DB records are checked too);
  4. only b[37..88] is written and the newlines / NUL stay at b[49] b[62] b[75] b[88]; on the JAPANESE original the 4 byte '25歳' field
     ends at b[74] exactly as the English 'Age 25' now does;
  5. byte level: exactly 2 bytes per overlay change (0x47 -> 0x45), same size; a second application, a foreign image, a single site and
     moved sites are refused; earlier changes of the current image are kept."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import layoutpatch as LP   # noqa: E402
import moneypatch as MP    # noqa: E402
import sh4sim              # noqa: E402
import textdb              # noqa: E402

FAILS = []
B = 0x8CF00000
ENT = 0x8CF20000
REC = 0x8CF30000
ENG = 0x8CF40000
STACK = 0x8CFF0000
RET = 0xDEAD0000
SPRINTF = 0x8C014D80
TBL = {'SCDRF': 0x7880, 'SEARCH': 0x8b30}
DELTA = {'SCDRF': 0, 'SEARCH': 0x12b0}


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


def hooks(m):
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
    m.ext_ret.update({0x8C012BF8: div, 0x8C013460: mod, 0x8C013294: strncpy, 0x8C014DE4: strlen})


def cstr(m, a):
    n = 0
    while m.rb(a + n):
        n += 1
    return bytes(m.rb(a + k) for k in range(n))


def fmt(m, f, args):
    out, i, ai = [], 0, 0
    while i < len(f):
        c = f[i]
        if c != '%':
            out.append(c)
            i += 1
            continue
        mm = re.match(r'%(-?)(\d*)([ds%])', f[i:])
        left, w, t = mm.groups()
        i += mm.end()
        if t == '%':
            out.append('%')
            continue
        v = args[ai]
        ai += 1
        s = str(sh4sim.s32(v)) if t == 'd' else cstr(m, v).decode('cp932', 'replace')
        if w:
            s = s.ljust(int(w)) if left else s.rjust(int(w))
        out.append(s)
    return ''.join(out)


def machine(name, ov, english):
    """the overlay bytes `ov` at their base plus the original 1ST_READ helpers; english = (row 2, wants, age) formats put in the table"""
    base = textdb.load_image('FLOW_PRG/%s.BIN' % name).base
    k = read_ext('1ST_READ.BIN')
    m = Mach()
    m.load(base, bytes(ov))
    lo, hi = 0x8c299000, 0x8c29d000
    m.load(lo, k[lo - MP.IMG_BASE:hi - MP.IMG_BASE])
    m.native = [(base, base + len(ov)), (lo, hi)]
    hooks(m)

    def sprintf(m):
        sp = m.R[15]
        f = cstr(m, m.rn(sp, 4)).decode('cp932')
        nargs = f.count('%') - 2 * f.count('%%')
        args = [m.rn(sp + 4 + 4 * i, 4) for i in range(nargs)]
        s = fmt(m, f, args).encode('cp932')
        for i, c in enumerate(s + b'\0'):
            m.wn(m.R[4] + i, c, 1)
        m.R[0] = len(s)
    m.ext_ret[SPRINTF] = sprintf
    if english:
        a = ENG
        for i, s in enumerate(english):
            m.wn(a, int.from_bytes(s.encode('ascii') + b'\0', 'little'), len(s) + 1)
            m.wn(base + TBL[name] + 4 * i, a, 4)
            a += 32
    ws = []
    orig_wn = m.wn

    def wn(addr, val, n):
        if B <= addr < B + 120:
            ws.extend(range(addr - B, addr - B + n))
        return orig_wn(addr, val, n)
    m.wn = wn
    m.rec = ws
    return m, base


def run(m, fn, args):
    for i in range(120):
        m.wn(B + i, 0x41, 1)
    m.wn(B + 34, 0, 1)
    m.wn(B + 35, 0, 1)
    m.R = [0] * 16
    m.R[15] = STACK
    m.R[4], m.R[5], m.R[6] = args
    m.PR = RET
    m.rec.clear()
    m.run(fn, RET)
    return bytes(m.rb(B + i) for i in range(120)), sorted(set(m.rec))


def rows(raw):
    """b[37..88] split at the newlines: money, row 2, age row, club (fewer rows when a NUL cuts the text short)"""
    return [r.decode('cp932', 'replace') for r in raw[37:89].split(b'\0')[0].split(b'\n')]


def current_player(m, base, name, age):
    """0x7598 style builder: scout record in r5"""
    for i in range(56):
        m.wn(REC + i, 0, 1)
    m.wn(REC + 14, 50, 1)
    m.wn(REC + 15, 7, 1)
    m.wn(REC + 16, 3585, 2)
    m.wn(REC + 22, 1, 2)
    m.wn(REC + 24, 3, 1)
    m.wn(REC + 25, 5, 1)
    m.wn(REC + 26, age, 1)
    return run(m, base + 0x7598 + DELTA[name], (B, REC, 0))


def candidate(m, base, name, age, yrs):
    """0x76d8 style builder: candidate entry in r5, amount in r6"""
    m.wn(ENT, 2, 2)
    m.wn(ENT + 2, age, 1)
    m.wn(ENT + 3, yrs, 1)
    return run(m, base + 0x76d8 + DELTA[name], (B, ENT, 358500))


def main():
    print('== byte level')
    dbtext = {}
    for n in ('SCDRF', 'SEARCH'):
        with open(os.path.join(ROOT, 'translation', 'FLOW_PRG__%s.BIN.jsonl' % n), encoding='utf-8') as f:
            for line in f:
                r = json.loads(line)
                if r['id'] in LP.SCOUT_TEXT:
                    dbtext[r['id']] = r
    for rid, want in LP.SCOUT_TEXT.items():
        r = dbtext.get(rid)
        check(r is not None and r['en'] == want and len(want) == 12 and r['ja'] == '%4d/%d年契約' and len(want.encode()) < r['max_bytes'],
              'DB record %s: en %r is the 12 character row format (max_bytes %s)' % (rid, want, r and r['max_bytes']))
    origs, news = {}, {}
    for n in ('SCDRF', 'SEARCH'):
        d = read_ext('FLOW_PRG/%s.BIN' % n)
        origs[n] = d
        sites = LP.scout_scan(d, n)
        check(tuple(sites) == LP.SCOUT_SITES[n], '%s: the two sprintf delay slots are found by signature at %s' % (n, [hex(s) for s in sites]))
        p = LP.patch_scout(d, n)
        news[n] = p
        diff = [i for i in range(len(d)) if d[i] != p[i]]
        check(len(p) == len(d) and diff == sorted(sites) and all(d[i] == 0x47 and p[i] == 0x45 for i in diff),
              '%s: same size, exactly 2 bytes change (0x47 -> 0x45 at %s)' % (n, [hex(i) for i in diff]))
        last = LP.SCOUT_SITES[n][1]
        for bad, why in ((p, 'already patched'), (b'\0' * len(d), 'foreign (zero) image'),
                         (d[:last] + b'\0\0' + d[last + 2:], 'one site only'), (d[:100] + b'\0' * 4 + d[100:], 'moved sites')):
            try:
                LP.patch_scout(bad, n)
                check(False, '%s: %s is refused' % (n, why))
            except LP.LayoutPatchError:
                check(True, '%s: %s is refused' % (n, why))
        check(LP.patch_scout(d) == p, '%s: located by signature alone (no name) gives the same bytes' % n)
    out = LP.scout_patches(read_ext)
    check(sorted(out) == ['/FLOW_PRG/SCDRF.BIN', '/FLOW_PRG/SEARCH.BIN'] and out['/FLOW_PRG/SCDRF.BIN'] == news['SCDRF'],
          'scout_patches: 2 overlays, composed on the extracted bytes')
    try:
        LP.scout_patches(read_ext, out)
        check(False, 'scout_patches on its own output is refused (idempotence guard)')
    except LP.LayoutPatchError:
        check(True, 'scout_patches on its own output is refused (idempotence guard)')
    mark = bytearray(origs['SCDRF'])
    mark[0x100] ^= 0xFF
    kept = LP.scout_patches(read_ext, {'/FLOW_PRG/SCDRF.BIN': bytes(mark)})['/FLOW_PRG/SCDRF.BIN']
    check(kept[0x100] == mark[0x100] and kept[0x7684] == 0x45, 'earlier changes of the current image are kept')

    print('== simulator: the real builders')
    EN_OLD = ('%4d/%d yrs', 'Wants %2d yrs', 'Age %2d')
    EN_NEW = ('%4d/%d yrs  ', 'Wants %2d yrs', 'Age %2d')
    for n in ('SCDRF', 'SEARCH'):
        mj, base = machine(n, origs[n], None)
        for age in (25, 7, 40):
            a, _ = candidate(mj, base, n, age, 2)
            check(len(rows(a)) == 4 and rows(a)[2].strip() == '%d歳' % age and a[75] == 10 and a[88] == 0,
                  '%s ORIGINAL Japanese candidate age %d: the 4 byte field ends at b[74]: %r' % (n, age, rows(a)[2]))
        me, base = machine(n, origs[n], EN_NEW)
        mp, _ = machine(n, news[n], EN_NEW)
        for age in (25, 7, 40, 19):
            ru, wu = candidate(me, base, n, age, 2)
            check(rows(ru)[2].strip() == 'Age' and rows(ru)[1].strip() == 'Wants  2 yrs',
                  '%s UNPATCHED candidate age %d: the number is lost: %r' % (n, age, rows(ru)[2]))
            r, w = candidate(mp, base, n, age, 2)
            rr = rows(r)
            check(len(rr) == 4 and rr[1].strip() == 'Wants  2 yrs' and rr[2] == ('Age %2d' % age).rjust(12) and rr[3].strip() != '',
                  '%s PATCHED candidate age %d: %r' % (n, age, rr))
            check(r[75] == 10 and r[88] == 0 and r[49] == 10 and r[62] == 10, '%s PATCHED newlines at b[49] b[62] b[75] and NUL at b[88]' % n)
            diff = [i for i in range(120) if r[i] != ru[i]]
            check(w == wu and diff and all(63 <= i <= 77 for i in diff),
                  '%s PATCHED vs UNPATCHED: same set of written bytes, the buffers differ only at b%s (the age row)' % (n, [min(diff), max(diff)] if diff else diff))
            check(r[:34] == b'A' * 34 and r[36] == 0x41 and all(i <= 91 for i in w), '%s PATCHED: b[0..33] and b[36] untouched (b[34] b[35] belong to the harness), nothing written past b[91]' % n)
        for label, mach, code in (('UNPATCHED code + 10 character format', machine(n, origs[n], EN_OLD)[0], False),
                                  ('PATCHED code + 10 character format', machine(n, news[n], EN_OLD)[0], False),
                                  ('UNPATCHED code + 12 character format', me, False)):
            r, _ = current_player(mach, base, n, 25)
            check(len(rows(r)) == 2 if label.endswith('10 character format') else rows(r)[2].strip() == 'Age',
                  '%s, current player: %r' % (label, rows(r)))
        mu, _ = machine(n, origs[n], EN_NEW)
        for age in (25, 33, 7):
            ru, wu = current_player(mu, base, n, age)
            r, w = current_player(mp, base, n, age)
            rr = rows(r)
            check(len(rr) == 4 and rr[1].strip() == '5/3 yrs' and rr[2] == ('Age %2d' % age).rjust(12) and rr[3].strip() != '',
                  '%s PATCHED code + 12 character yrs row, current player age %d: %r' % (n, age, rr))
            diff = [i for i in range(120) if r[i] != ru[i]]
            check(r[75] == 10 and r[88] == 0 and r[:34] == b'A' * 34 and r[36] == 0x41 and w == wu and diff and all(63 <= i <= 77 for i in diff),
                  '%s current player: frame intact, differs from the unpatched run only in the age row' % n)
    print()
    if FAILS:
        print('%d FAILED' % len(FAILS))
        return 1
    print('ALL PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
