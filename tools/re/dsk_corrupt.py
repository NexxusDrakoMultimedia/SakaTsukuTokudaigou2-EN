"""dsk_corrupt: skeptic's corrupt-disc battery for verify_disc (cases of my own; sectors are re-encoded so EDC/ECC stay valid
and only the STRUCTURE is damaged, except where stated).

    python -I -X utf8 tools/re/dsk_corrupt.py DUMP_DIR     (builds build/dsk_b, runs the cases, deletes it)
"""
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
os.chdir(ROOT)
import discbuild as D   # noqa: E402
import verify_disc as V   # noqa: E402

OUT = os.path.join(ROOT, 'build', 'dsk_b')
NAME = 'dsk'
GDI = []


def tracks():
    lines = open(os.path.join(OUT, NAME + '.gdi')).read().splitlines()
    res = []
    for ln in lines[1:1 + int(lines[0])]:
        p = ln.split('"')
        a = p[0].split()
        res.append((int(a[1]), int(a[2]), int(a[3]), os.path.join(OUT, p[1])))
    return res


def loc(lba):
    best = None
    for t in tracks():
        if t[0] <= lba and t[1] == 4:
            best = t
    return best[3], (lba - best[0]) * best[2]


def get_user(lba):
    p, off = loc(lba)
    with open(p, 'rb') as f:
        f.seek(off)
        return bytearray(f.read(2352)[16:2064])


def put_user(lba, user, reencode=True):
    p, off = loc(lba)
    raw = D.encode_sector(lba, bytes(user)) if reencode else None
    with open(p, 'r+b') as f:
        f.seek(off)
        if reencode:
            f.write(raw)
        else:
            old = bytearray(f.read(2352))
            old[16:2064] = user
            f.seek(off)
            f.write(old)


def read_range(lba, n):
    return b''.join(bytes(get_user(lba + i)) for i in range(n))


def find_record(path_wanted):
    """(sector lba, offset in sector) of the directory record of an ISO path (root dir only for simplicity)."""
    pvd = get_user(45016)
    root_lba = struct.unpack('<I', pvd[158:162])[0]
    root_size = struct.unpack('<I', pvd[166:170])[0]
    parts = path_wanted.strip('/').split('/')
    lba, size = root_lba, root_size
    for i, part in enumerate(parts):
        found = None
        for s in range(size // 2048):
            sec = get_user(lba + s)
            pos = 0
            while pos < 2048 and sec[pos]:
                ln = sec[pos]
                nm = bytes(sec[pos + 33:pos + 33 + sec[pos + 32]]).decode('ascii', 'replace').split(';')[0]
                if nm == part:
                    found = (lba + s, pos, struct.unpack('<I', sec[pos + 2:pos + 6])[0], struct.unpack('<I', sec[pos + 10:pos + 14])[0])
                pos += ln
            if found:
                break
        assert found, path_wanted
        if i < len(parts) - 1:
            lba, size = found[2], found[3]
    return found


def run(label, mutate, restore, expect_fail=True, **kw):
    mutate()
    try:
        rep = V.verify_disc(OUT, NAME, kw.pop('source', None), rewritten=None, sectors=kw.pop('sectors', 'auto'), **kw)
    except Exception as e:   # a crash is a defect of the checker
        print('%-46s CRASH %r' % (label, e))
        restore()
        return False
    ok = (not rep.ok) if expect_fail else rep.ok
    print('%-46s %s  (%s)' % (label, 'detected' if not rep.ok else 'PASSED(!)', (rep.errors[0][:90] if rep.errors else '-')))
    restore()
    return ok


def main():
    dump = sys.argv[1]
    patches = {}
    for dp, _dn, fns in os.walk(dump):
        for fn in fns:
            full = os.path.join(dp, fn)
            with open(full, 'rb') as f:
                patches['/' + os.path.relpath(full, dump).replace(os.sep, '/')] = f.read()
    shutil.rmtree(OUT, ignore_errors=True)
    try:
        D.build_disc(patches, OUT, NAME, ROOT)
        base = V.verify_disc(OUT, NAME, ROOT, sectors='auto')
        print('baseline ok=%s errors=%s' % (base.ok, base.errors))
        results = []
        # a file record (root: 1ST_READ.BIN, 2_DP.BIN) and a deeper one
        l1, o1, ext1, sz1 = find_record('/2_DP.BIN')
        l2, o2, ext2, sz2 = find_record('/1ST_READ.BIN')
        print('2_DP.BIN rec at', l1, o1, 'ext', ext1, sz1, '; 1ST_READ.BIN ext', ext2, sz2)

        def snap(lba):
            s = bytes(get_user(lba))
            return lambda: put_user(lba, s)

        # 1 overlap: 2_DP.BIN extent -> inside 1ST_READ.BIN
        r = snap(l1)

        def m1():
            u = get_user(l1)
            u[o1 + 2:o1 + 6] = struct.pack('<I', ext2 + 3)
            u[o1 + 6:o1 + 10] = struct.pack('>I', ext2 + 3)
            put_user(l1, u)
        results.append(run('extent overlaps another file', m1, r))

        def m2():
            u = get_user(l1)
            u[o1 + 10:o1 + 14] = struct.pack('<I', sz1 + 4096)   # LE only
            put_user(l1, u)
        results.append(run('size LE/BE mismatch', m2, r))

        def m3():
            u = get_user(l1)
            u[o1 + 2:o1 + 6] = struct.pack('<I', 560000)
            u[o1 + 6:o1 + 10] = struct.pack('>I', 560000)
            put_user(l1, u)
        results.append(run('extent beyond GD-ROM ceiling', m3, r))

        def m4():
            u = get_user(l1)
            u[o1 + 2:o1 + 6] = struct.pack('<I', 100)
            u[o1 + 6:o1 + 10] = struct.pack('>I', 100)
            put_user(l1, u)
        results.append(run('extent in low-density area (LBA 100)', m4, r))

        def m5():
            u = get_user(l1)
            u[o1 + 10:o1 + 14] = struct.pack('<I', 0)
            u[o1 + 14:o1 + 18] = struct.pack('>I', 0)
            put_user(l1, u)
        results.append(run('size set to 0 (file silently empty)', m5, r))

        def m6():
            u = get_user(l1)
            u[o1 + 33] = ord('0')   # name now sorts first / breaks order
            put_user(l1, u)
        results.append(run('name changed breaks sort/ordering', m6, r))

        rp = snap(45016)

        def m7():
            u = get_user(45016)
            u[80:84] = struct.pack('<I', 500000)
            u[84:88] = struct.pack('>I', 500000)
            put_user(45016, u)
        results.append(run('PVD volume size wrong', m7, rp))

        def m8():
            u = get_user(45016)
            u[1:6] = b'CD002'
            put_user(45016, u)
        results.append(run('PVD id broken', m8, rp))

        pvd = get_user(45016)
        pt = struct.unpack('<I', pvd[140:144])[0]
        ptm = struct.unpack('>I', pvd[148:152])[0]
        rpt = snap(ptm)

        def m9():
            u = get_user(ptm)
            u[6:8] = struct.pack('>H', 5)   # root's parent number on the M table
            put_user(ptm, u)
        results.append(run('path table M differs from L', m9, rpt))

        rip = snap(45000)

        def m10():
            u = get_user(45000)
            u[0x10] ^= 0xFF   # inside the CRC-protected area 0x40.. is device info; hit 0x40
            u[0x40] ^= 0x55
            put_user(45000, u)
        results.append(run('IP.BIN CRC field region altered', m10, rip))

        # EDC flipped without re-encoding in a patched sector (source compare)
        lp = ext1
        rl = snap(lp)

        def m11():
            u = get_user(lp)
            u[5] ^= 1
            put_user(lp, u, reencode=False)
        results.append(run('EDC bad in a file sector (auto+source)', m11, rl, source=ROOT))
        results.append(run('EDC bad in a file sector (all)', m11, rl, sectors='all'))

        # file data changed but sector re-encoded: only detectable via expect
        def m12():
            u = get_user(lp)
            u[5] ^= 1
            put_user(lp, u)
        mutate_then = []
        m12()
        rep = V.verify_disc(OUT, NAME, ROOT, expect={'/2_DP.BIN': patches.get('/2_DP.BIN', b'')}, sectors='auto') if '/2_DP.BIN' in patches else None
        print('%-46s %s' % ('valid-EDC data change vs expect=', 'n/a (2_DP.BIN not patched)' if rep is None else ('detected' if not rep.ok else 'PASSED(!)')))
        rl()

        # truncated track 5
        t5 = tracks()[-1][3]
        size = os.path.getsize(t5)
        with open(t5, 'rb') as f:
            f.seek(size - 2352)
            tail = f.read(2352)

        def m13():
            with open(t5, 'r+b') as f:
                f.truncate(size - 2352)

        def r13():
            with open(t5, 'r+b') as f:
                f.seek(size - 2352)
                f.write(tail)
        results.append(run('track 5 truncated by one sector', m13, r13))

        def m14():
            with open(t5, 'r+b') as f:
                f.truncate(size - 1000)

        results.append(run('track 5 truncated mid-sector', m14, r13))

        # gdi: wrong LBA of track 5
        gp = os.path.join(OUT, NAME + '.gdi')
        gold = open(gp).read()

        def m15():
            ls = gold.splitlines()
            a = ls[5].split(' ', 2)
            ls[5] = a[0] + ' ' + str(int(a[1]) + 1) + ' ' + a[2]
            open(gp, 'w', newline='').write('\r\n'.join(ls) + '\r\n')

        def r15():
            open(gp, 'w', newline='').write(gold)
        results.append(run('gdi track-5 LBA off by one', m15, r15))
        cp = os.path.join(OUT, NAME + '.cue')
        cold = open(cp).read()

        def m16():
            open(cp, 'w', newline='').write(cold.replace('INDEX 01 00:02:00', 'INDEX 01 00:03:00', 1))

        def r16():
            open(cp, 'w', newline='').write(cold)
        results.append(run('cue index changed', m16, r16))

        def m17():
            os.remove(cp)

        results.append(run('cue missing', m17, r16))

        print('RESULT: %d/%d corruptions detected; baseline recheck: %s' % (
            sum(results), len(results), V.verify_disc(OUT, NAME, ROOT, sectors='auto').ok))
    finally:
        shutil.rmtree(OUT, ignore_errors=True)


if __name__ == '__main__':
    main()
