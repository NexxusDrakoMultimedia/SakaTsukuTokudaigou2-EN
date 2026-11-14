"""hng: compare the money cave bytes of a built disc with moneypatch.cave_bytes (and print the first differing offsets).
usage: hng_cavecmp.py DISCDIR NAME [jp|western]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import discbuild as D, moneypatch as MP
root, name = sys.argv[1], sys.argv[2]; style = sys.argv[3] if len(sys.argv) > 3 else 'jp'
src = D.Source(root, name)
_p, _rl, _rs, recs = D.read_filesystem(src)
files = {r.path.upper(): r for r in recs if not r.isdir}
r = files['/1ST_READ.BIN']; k = src.read(r.lba, r.size)
want = MP.cave_bytes(MP.CAVE_ADDR, style)
o = MP.CAVE_ADDR - MP.IMG_BASE
got = k[o:o + 0x200]
print('cave len', len(want), 'disc has', len(got), 'equal prefix', got[:len(want)] == want, 'tail zero', not any(got[len(want):]))
diff = [i for i in range(len(want)) if got[i] != want[i]]
print('first diffs', diff[:20], len(diff))
print('disc  ', got[:0x40].hex()); print('model ', want[:0x40].hex())
