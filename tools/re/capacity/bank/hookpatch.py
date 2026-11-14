"""Route (a): boot-time load of a donor file into RAM = a 1ST_READ.BIN patch.

Mechanism (docs/trans-bank.md s3): boot function FUN_8c15ffcc loads FONT.BIN/SHTEX0.ZAR/BAR.TBD/SECFTEX0.ZAR with
FUN_8c15eeb8(name, dir, dest) and then calls FUN_8c163984 through the literal at 0x8c160360 (`mov.l 0x8c160360,r3; jsr @r3; nop`
at 0x8c160288).  FUN_8c163984 is an empty function (`rts; nop`, Ghidra: 4 bytes) and has exactly one call site.  The patch
redirects that ONE literal to a cave that performs one more FUN_8c15eeb8(name, 0, dest) (dir 0 = root directory, like FONT.BIN) and
returns.  The cave lives in the zero padding of 1ST_READ (0x8c13bae0..0x8c159000, proven zero in the file and in 4 RAM dumps).

    python -I -X utf8 tools/re/capacity/bank/hookpatch.py [--dest 0x8c13c000] [--name NAMIHEI.DRV] [--out DIR]
writes patches.json + a patched copy of 1ST_READ.BIN (never into extracted/).
"""
import argparse
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sh4asm as A  # noqa: E402

BASE = 0x8C010000
LOADER = 0x8C15EEB8          # FUN_8c15eeb8(name, dir, dest) -> 0 ok / -1 fail  (wrapper of FUN_8c15eede)
HOOK_LIT = 0x8C160360        # literal holding &FUN_8c163984 (empty function), used only by the call at 0x8c160288
ORIG_TARGET = 0x8C163984
CAVE = 0x8C13BB00            # inside the zero gap 0x8c13bae0..0x8c159000
CAVE_RESERVED = 0x80         # bytes of the gap used by the cave (code 0x14 + literals 0xc + name)


def build(dest, name='NAMIHEI.DRV', cave=CAVE):
    nm = name.encode('ascii') + b'\0'
    lit = cave + 0x14
    nameaddr = cave + 0x20
    code = b''.join([
        A.sts_l_pr_push(),                              # +00 push PR
        A.mov_l_pc(4, cave + 2, lit + 0),               # +02 r4 = &name
        A.mov_l_pc(6, cave + 4, lit + 4),               # +04 r6 = dest
        A.mov_l_pc(3, cave + 6, lit + 8),               # +06 r3 = FUN_8c15eeb8
        A.jsr(3),                                       # +08 call
        A.mov_imm(5, 0),                                # +0a (delay) r5 = 0 -> root directory
        A.lds_l_pr_pop(),                               # +0c pop PR
        A.rts(),                                        # +0e
        A.nop(),                                        # +10 (delay)
        b'\0\0',                                        # +12 pad
    ])
    assert len(code) == 0x14
    pool = struct.pack('<III', nameaddr, dest, LOADER)  # +14..+1f
    blob = code + pool
    blob += b'\0' * (0x20 - len(blob)) + nm
    assert len(blob) <= CAVE_RESERVED
    blob += b'\0' * (CAVE_RESERVED - len(blob))
    return blob, cave


def patches(first_read, dest, name='NAMIHEI.DRV'):
    blob, cave = build(dest, name)
    out = []
    o = cave - BASE
    old = first_read[o:o + len(blob)]
    if old.strip(b'\0'):
        raise SystemExit('cave region is not zero in the file')
    out.append({'off': o, 'old': old.hex(), 'new': blob.hex(), 'note': 'cave code+literals+name at 0x%08x' % cave})
    o2 = HOOK_LIT - BASE
    old2 = first_read[o2:o2 + 4]
    if struct.unpack('<I', old2)[0] != ORIG_TARGET:
        raise SystemExit('hook literal does not hold FUN_8c163984')
    out.append({'off': o2, 'old': old2.hex(), 'new': struct.pack('<I', cave).hex(),
                'note': 'literal 0x%08x: 0x%08x -> cave 0x%08x' % (HOOK_LIT, ORIG_TARGET, cave)})
    return out


def apply(data, plist):
    b = bytearray(data)
    for p in plist:
        old = bytes.fromhex(p['old'])
        assert bytes(b[p['off']:p['off'] + len(old)]) == old, 'old bytes mismatch at %#x' % p['off']
        b[p['off']:p['off'] + len(old)] = bytes.fromhex(p['new'])
    return bytes(b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dest', type=lambda x: int(x, 0), default=0x8C13C000,
                    help='RAM destination of the donor file (default: inside the 1ST_READ text gap, for the dynamic hook test only)')
    ap.add_argument('--name', default='NAMIHEI.DRV')
    ap.add_argument('--out', default=os.path.join(HERE, 'out'))
    a = ap.parse_args()
    fr = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
    pl = patches(fr, a.dest, a.name)
    new = apply(fr, pl)
    os.makedirs(a.out, exist_ok=True)
    json.dump(pl, open(os.path.join(a.out, 'hook_patches.json'), 'w'), indent=1)
    open(os.path.join(a.out, '1ST_READ_hook.BIN'), 'wb').write(new)
    blob, cave = build(a.dest, a.name)
    print('patch list:')
    for p in pl:
        print('  file off 0x%06x (addr 0x%08x) len %d  %s' % (p['off'], BASE + p['off'], len(p['new']) // 2, p['note']))
    print('cave listing (own assembler):')
    for l in A.listing(blob[:0x12], cave):
        print('  ' + l)
    print('  %08x  literals: name=0x%08x dest=0x%08x fn=0x%08x' % ((cave + 0x14,) + struct.unpack('<III', blob[0x14:0x20])))
    print('  %08x  "%s"' % (cave + 0x20, a.name))
    print('size change of 1ST_READ.BIN: %d bytes' % (len(new) - len(fr)))


if __name__ == '__main__':
    main()
