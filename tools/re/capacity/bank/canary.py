"""Soak-test helper for the in-file bank regions (no emulator needed here; the orchestrator runs the game).

    python -I -X utf8 tools/re/capacity/bank/canary.py make [--regions tail,gap1,gap2,gap3,font] [--out DIR]
        writes DIR/1ST_READ_canary.BIN and DIR/FONT_canary.BIN : every byte of the chosen regions replaced by a position-dependent
        pseudo-random pattern  pat(addr) = ((addr * 2654435761) >> 11) & 0xFF  (never all-zero, so "got zeroed" is detectable).
        Put them on the disc with discbuild:  /1ST_READ.BIN=DIR/1ST_READ_canary.BIN  /FONT.BIN=DIR/FONT_canary.BIN
    python -I -X utf8 tools/re/capacity/bank/canary.py check RAMDUMP [--base 0x8c000000] [--regions ...]
        RAMDUMP = full 16 MB dump (live.lua dump(0x8c000000, 0x1000000, 'x.bin')) or a partial dump with --base.
        Prints per region: bytes intact / changed, first changed address, and the changed byte ranges (max 5).
"""
import argparse, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, HERE)
import bankbuild as bb


def pat(addr):
    return ((addr * 2654435761) >> 11) & 0xFF or 0x5A


def regions(names):
    return bb.make_regions(names)


def make(a):
    fr = bytearray(open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read())
    font = bytearray(open(os.path.join(ROOT, 'extracted', 'FONT.BIN'), 'rb').read())
    for r in regions(a.regions.split(',')):
        data = bytes(pat(r.addr + i) for i in range(r.size))
        if r.target == '1ST_READ.BIN':
            fr[r.foff:r.foff + r.size] = data
        else:
            font.extend(b'\0' * (r.foff + r.size - len(font)))
            font[r.foff:r.foff + r.size] = data
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, '1ST_READ_canary.BIN'), 'wb').write(fr)
    open(os.path.join(a.out, 'FONT_canary.BIN'), 'wb').write(font)
    print('wrote', a.out, 'sizes', len(fr), len(font), '(FONT limit 679936)')


def check(a):
    d = open(a.dump, 'rb').read()
    for r in regions(a.regions.split(',')):
        o = r.addr - a.base
        seg = d[o:o + r.size]
        if len(seg) < r.size:
            print(r.name, 'not inside the dump'); continue
        bad = [i for i in range(r.size) if seg[i] != pat(r.addr + i)]
        runs, cur = [], None
        for i in bad:
            if cur and i == cur[1]:
                cur[1] = i + 1
            else:
                cur = [i, i + 1]; runs.append(cur)
        print('%-5s %08x-%08x intact %d / %d  changed %d  %s' % (r.name, r.addr, r.addr + r.size, r.size - len(bad), r.size, len(bad),
              ['%08x+%d' % (r.addr + x, y - x) for x, y in runs[:5]]))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['make', 'check'])
    ap.add_argument('dump', nargs='?')
    ap.add_argument('--regions', default='tail,gap1,gap2,gap3,font')
    ap.add_argument('--out', default=os.path.join(HERE, 'out'))
    ap.add_argument('--base', type=lambda x: int(x, 0), default=0x8C000000)
    a = ap.parse_args()
    make(a) if a.cmd == 'make' else check(a)
