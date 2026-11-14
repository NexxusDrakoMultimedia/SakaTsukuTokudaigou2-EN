"""tdl: compare plain vs LZMA-secondary delta sizes over every repainted texture, and cross-check xdelta3 on a few."""
import os
import subprocess
import sys
import shutil
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texdelta as T   # noqa: E402

out = os.path.join(ROOT, 'build', 'l10n_tdl_size')
os.makedirs(out, exist_ok=True)
orig = T.Originals(T.DEF_EXTRACTED)
plain = lz = 0
worst = []
n = 0
xd = shutil.which('xdelta3') or r'C:\ProgramData\chocolatey\bin\xdelta3.exe'
for full in T._walk(T.DEF_TEXTURES, '.pvr'):
    rel = T._rel(full, T.DEF_TEXTURES)
    cont, tid = T.split_container(rel.split('/'), T.DEF_EXTRACTED)
    src = orig.texture(cont, tid[:-4])
    tgt = open(full, 'rb').read()
    a = T.encode_delta(src, tgt)
    b = T.encode_delta(src, tgt, secondary=True)
    assert T.decode_delta(b, src) == tgt
    plain += len(a)
    lz += len(b)
    worst.append((len(b), rel))
    n += 1
    if n % 40 == 1:
        sp, dp, op = (os.path.join(out, x) for x in ('s.pvr', 'd.vcdiff', 'o.pvr'))
        open(sp, 'wb').write(src)
        open(dp, 'wb').write(b)
        if os.path.exists(op):
            os.remove(op)
        r = subprocess.run([xd, '-d', '-s', sp, dp, op], capture_output=True)
        ok = r.returncode == 0 and open(op, 'rb').read() == tgt
        print('xdelta3 -d on', rel, 'ok' if ok else 'FAIL %r' % r.stderr[:200])
        dp2 = os.path.join(out, 'd2.vcdiff')
        open(dp2, 'wb').write(a)
        if os.path.exists(op):
            os.remove(op)
        r = subprocess.run([xd, '-d', '-s', sp, dp2, op], capture_output=True)
        print('   plain', 'ok' if r.returncode == 0 and open(op, 'rb').read() == tgt else 'FAIL %r' % r.stderr[:200])
print('textures', n, 'plain', plain, 'lzma', lz)
worst.sort(reverse=True)
print(worst[:8])
