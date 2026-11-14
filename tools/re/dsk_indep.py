"""dsk_indep: skeptic's independent check of a built disc (own gdi parser, own ISO9660 walker, no verify_disc / gdrom code).

    python -I -X utf8 tools/re/dsk_indep.py DUMP_DIR [--dedupe] [--add]   (builds build/dsk_a, checks, deletes it)

Builds the standard patch set (DUMP_DIR from build_patch --dump), then walks the ISO9660 tree of the result by itself, reads every
file and compares with the patched bytes (patched files) or the original disc's bytes (unpatched), and checks extent overlaps."""
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
os.chdir(ROOT)
import discbuild as D   # noqa: E402


class Disc:
    def __init__(self, base, name, gdi=None):
        self.tr = []
        text = open(os.path.join(base, name + '.gdi')).read() if gdi is None else gdi
        lines = text.splitlines()
        for ln in lines[1:1 + int(lines[0])]:
            p = ln.split('"')
            a = p[0].split()
            self.tr.append((int(a[1]), int(a[2]), int(a[3]), p[1]))
        self.base = base
        self.files = {}

    def sector(self, lba):
        # last track whose start <= lba
        best = None
        for (start, typ, ss, fn) in self.tr:
            if start <= lba:
                best = (start, typ, ss, fn)
        start, typ, ss, fn = best
        if typ != 4:
            raise ValueError('lba %d not in data track' % lba)
        path = os.path.join(self.base, fn)
        fh = self.files.get(path)
        if fh is None:
            fh = self.files[path] = open(path, 'rb')
        fh.seek((lba - start) * ss)
        raw = fh.read(ss)
        assert raw[:12] == b'\x00' + b'\xff' * 10 + b'\x00' and raw[15] == 1, 'not a mode 1 sector %d' % lba
        return raw[16:16 + 2048]

    def read(self, lba, size):
        out = bytearray()
        for i in range((size + 2047) // 2048):
            out += self.sector(lba + i)
        return bytes(out[:size])


def walk(d):
    pvd = d.sector(45016)
    assert pvd[1:6] == b'CD001' and pvd[0] == 1
    root = pvd[156:190]
    res = {}
    stack = [('', struct.unpack('<I', root[2:6])[0], struct.unpack('<I', root[10:14])[0])]
    seen = set()
    dirs = []
    while stack:
        path, lba, size = stack.pop()
        if lba in seen:
            raise ValueError('directory loop/alias %s' % path)
        seen.add(lba)
        dirs.append((path, lba, size))
        data = d.read(lba, size)
        pos = 0
        while pos < len(data):
            ln = data[pos]
            if ln == 0:
                pos = (pos // 2048 + 1) * 2048
                continue
            rec = data[pos:pos + ln]
            pos += ln
            nl = rec[32]
            name = rec[33:33 + nl]
            if name in (b'\x00', b'\x01'):
                continue
            nm = name.decode('ascii').split(';')[0]
            l2 = struct.unpack('<I', rec[2:6])[0]
            s2 = struct.unpack('<I', rec[10:14])[0]
            if rec[25] & 2:
                stack.append((path + '/' + nm, l2, s2))
            else:
                res[path + '/' + nm] = (l2, s2)
    return res, dirs


def main():
    dump = sys.argv[1]
    patches = {}
    for dp, _dn, fns in os.walk(dump):
        for fn in fns:
            full = os.path.join(dp, fn)
            with open(full, 'rb') as f:
                patches['/' + os.path.relpath(full, dump).replace(os.sep, '/')] = f.read()
    spec = D.DiscSpec(patches, dedupe='--dedupe' in sys.argv)
    if '--add' in sys.argv:
        spec.add_file('/DSKNEW.TXT', b'hello\n' * 700)
        patches['/DSKNEW.TXT'] = b'hello\n' * 700
    out = os.path.join(ROOT, 'build', 'dsk_a')
    shutil.rmtree(out, ignore_errors=True)
    try:
        D.build_disc(spec, out, 'dsk', ROOT)
        new = Disc(out, 'dsk')
        oname = 'Sakatsuku Tokudaigou 2 - J.League Pro Soccer Club o Tsukurou! (Japan)'
        gtxt = open(os.path.join(out, 'dsk.gdi')).read().replace('dsk (Track', oname + ' (Track')
        orig = Disc(ROOT, oname, gtxt)
        nf, nd = walk(new)
        of, od = walk(orig)
        print('files new %d orig %d ; dirs new %d orig %d' % (len(nf), len(of), len(nd), len(od)))
        missing = set(of) - set(nf)
        extra = set(nf) - set(of)
        print('missing', sorted(missing)[:5], 'extra', sorted(extra)[:5])
        bad = 0
        for p, (l, s) in sorted(nf.items()):
            data = new.read(l, s)
            if p in patches:
                exp = patches[p]
            else:
                ol, os_ = of[p]
                exp = orig.read(ol, os_)
            if data != exp:
                bad += 1
                print('MISMATCH', p)
        print('content mismatches:', bad)
        # overlap check among non-identical extents
        ext = {}
        for p, (l, s) in nf.items():
            n = max(1, (s + 2047) // 2048)
            ext.setdefault((l, n), []).append(p)
        iv = sorted(ext)
        ov = 0
        for i in range(1, len(iv)):
            if iv[i][0] < iv[i - 1][0] + iv[i - 1][1]:
                ov += 1
                print('OVERLAP', iv[i - 1], ext[iv[i - 1]][:2], iv[i], ext[iv[i]][:2])
        print('overlaps', ov, 'shared groups', sum(1 for v in ext.values() if len(v) > 1))
        for h in list(new.files.values()) + list(orig.files.values()):
            h.close()
        return 1 if (bad or ov or missing) else 0
    finally:
        shutil.rmtree(out, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
