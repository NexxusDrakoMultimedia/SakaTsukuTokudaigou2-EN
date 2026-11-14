"""skp (skeptic): run the shirt-number row layout on the PATCHED overlay + cave bytes read back from a built trial disc
(independent of make_patches: what the disc really contains).

    python -I -X utf8 tools/re/skp_discsim.py DISC_DIR DISC_NAME
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import discbuild as D
import fontpatch as FP
import test_alignfix as T

src = D.Source(sys.argv[1], sys.argv[2])
_p, _rl, _rs, recs = D.read_filesystem(src)
files = {r.path.upper(): r for r in recs if not r.isdir}
rd = lambda p: src.read(files['/' + p.upper()].lba, files['/' + p.upper()].size)
k = rd('1ST_READ.BIN')
ct = FP.placement()
a0 = T.ALIGN - FP.IMG_BASE
c0 = ct[0] - FP.IMG_BASE
t0 = ct[1] - FP.IMG_BASE
tbl = k[t0:t0 + 256]
cave = k[c0:c0 + 0x100]
align = k[a0:a0 + 0x100]
print('align cave == align_bytes:', align[:FP.align_size() if hasattr(FP, 'align_size') else 224] == FP.align_bytes(T.ALIGN, ct[1])[:224] if True else '')
img = rd('FLOW_PRG/PLNUMSET.BIN')
_, h1 = T.h1_of('FLOW_PRG/PLNUMSET.BIN')
ex = [(ct[0], cave), (ct[1], tbl), (T.ALIGN, align)]
nat = [(ct[0], ct[0] + 0x100), (T.ALIGN, T.ALIGN + 0x100)]
names = ['Ito', 'Kenji', 'Takahashi', 'Nakagawa', 'Isao Nakagak', 'Wanyama Wang', 'Li', 'Okamoto', 'WWWWWWWWWWWW', 'iiiiiiiiiiii', 'Mwamba Njoroge'[:14], 'Hiroshi Wakui']
for nm in names:
    for num in (3, 5, 12, 68):
        s = (nm + ' ' * 14)[:14] if len(nm) <= 12 else nm
        s = s + ('%2d' % num)
        snaps = T.run_layout(img, h1, T.codes_of(s), W=20, A=24, flag=1, x0=100, extra=ex, native=nat)
        # position where the first digit's glyph is drawn = pen after the code before it
        idx = len(s) - len('%2d' % num)
        idx = idx + ('%2d' % num).index(str(num)[0])
        print('%-16s %3d  digit x0+%d  (pen end x0+%d)' % (nm, num, snaps[idx - 1][0] - 100, snaps[-1][0] - 100))
