"""hng: read a few files back out of a built trial disc and say which optional patch classes it really contains.

usage: hng_discprobe.py NAME [NAME ...]        (discs are build/trial/NAME/NAME.gdi)
Checks (all from the disc bytes, compared with extracted/):
  money   cave at 0x8c299a00 non-zero + the 12-byte hook at the money function of EVENT.BIN, and the style (cave length / first words)
  guard   the club-name composer of EVENT.BIN is NOT the original one (sha256 of the 232 bytes differs)
  prop    the proportional-font cave at 0x8c299800 is non-zero
  tex     which of E003.DAT, ETC_DATA/BAR.TBD, ETC_DATA/TV_EVENT.ZAR, FLOW_PRG/SEARCH.BIN (texture-bearing) differ from the original at the texture bytes
          (SEARCH.BIN also carries text, so it is compared at its two embedded texture slots only)
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discbuild as D            # noqa: E402
import moneypatch as MP          # noqa: E402
import layoutpatch as LP         # noqa: E402


def probe(name):
    src = D.Source(os.path.join(ROOT, 'build', 'trial', name), name)
    _p, _rl, _rs, recs = D.read_filesystem(src)
    files = {r.path.upper(): r for r in recs if not r.isdir}

    def rd(p):
        r = files['/' + p.upper()]
        return src.read(r.lba, r.size)

    out = {}
    k = rd('1ST_READ.BIN')
    o = MP.CAVE_ADDR - MP.IMG_BASE
    out['money cave'] = 'yes' if any(k[o:o + 64]) else 'no'
    out['prop cave'] = 'yes' if any(k[0x8c299800 - MP.IMG_BASE:0x8c299800 - MP.IMG_BASE + 64]) else 'no'
    ev = rd('FLOW_PRG/EVENT.BIN')
    ev0 = MP.read_extracted('FLOW_PRG/EVENT.BIN')
    site = MP.find_sites(ev0, 'EVENT')[0]['off']
    out['money hook'] = 'yes' if ev[site:site + 12] == MP.hook_bytes() else 'no'
    # money style: length of the cave tail is not stored; the first mova displacement differs (western 0x..)
    style = 'western' if b'\x59\xe0' in k[o:o + 0x1b0] else 'jp'       # western cave loads 'Y' (mov #89,r0)
    out['money style'] = style if out['money cave'] == 'yes' else '-'
    a = ev.find(LP.CLUB_SIG_A_NEW)
    comp = ev[a + LP.COMP_DELTA:a + LP.COMP_DELTA + LP.COMP_LEN] if a >= 0 else b''
    out['guard'] = 'no (original composer)' if hashlib.sha256(comp).hexdigest() == LP.COMP_SHA256 else 'yes (bounded composer)'
    out['town_short unbounded'] = 'yes' if a >= 0 else 'no (original signature)'
    tex = []
    for p in ('EVENT/E003.DAT', 'ETC_DATA/BAR.TBD', 'ETC_DATA/TV_EVENT.ZAR', 'ETC_DATA/PLATE.ZAR', 'FLOW_PRG/DRAFT.ZAR', 'GAME2/SS_EDIT.TBD'):
        d = rd(p)
        o2 = MP.read_extracted(p)
        tex.append('%s=%s' % (os.path.basename(p), 'changed' if d != o2 else 'orig'))
    for off in (0x2c58c, 0x2fcf0):
        s = rd('FLOW_PRG/SEARCH.BIN')
        s0 = MP.read_extracted('FLOW_PRG/SEARCH.BIN')
        tex.append('SEARCH@%x=%s' % (off, 'changed' if s[off:off + 0x400] != s0[off:off + 0x400] else 'orig'))
    out['textures'] = ' '.join(tex)
    src.close()
    return out


if __name__ == '__main__':
    for n in sys.argv[1:]:
        r = probe(n)
        print('%-6s money cave %s (%s) hook %s | prop cave %s | guard %s | textures: %s' % (
            n, r['money cave'], r['money style'], r['money hook'], r['prop cave'], r['guard'], r['textures']))
