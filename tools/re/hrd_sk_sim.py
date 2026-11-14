"""hrd skeptic: run the GAME's own ZSARC walker (1ST_READ jump table +0x3d4 = 0x8c15a87c -> FUN_8c15a45a mode 2) in
tools/sh4sim.py exactly as SCDRF's init calls it (r4 = 0, r5 = 0x8c2fff38, r6 = 0), on

  * the hung RAM image itself (code AND data taken from build/emu/hang_v1_ram.bin), and
  * the same RAM code with the SCDRF.BIN bytes of a trial disc laid over 0x8c2d0000 (bis_e, bis_v1, fix_v1, ...).

usage: hrd_sk_sim.py RAMDUMP [DISC ...]
Prints r0 (the member data pointer, or 0 = rejected) and the error strings handed to the logging wrapper 0x8c159f78's
target 0x8c011084.  No Python re-implementation of the CRC or of the header parser is involved.  Read-only.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sh4sim                    # noqa: E402
import discbuild as D            # noqa: E402

BASE = 0x8c000000
CODE = (0x8c010000, 0x8c240000)          # 1ST_READ code and data as found in RAM (walker, header parser, CRC, libc helpers)
STR = (0x8c160000, 0x8c170000)           # where the error strings live (already inside CODE)
OVL = 0x8c2d0000
MEM = (0x8c2fff00, 0x8c3329c0)           # the member and a little around it
ENTRY, STOP, STACK = 0x8c15a87c, 0x8c000000, 0x8cfff000


def cstr(ram, a):
    o = a - BASE
    e = ram.find(b'\0', o)
    return ram[o:e].decode('cp932', 'replace')


def run(ram, label, overlay=None):
    m = sh4sim.Machine()
    m.load(CODE[0], ram[CODE[0] - BASE:CODE[1] - BASE])
    m.load(STR[0], ram[STR[0] - BASE:STR[1] - BASE])
    if overlay is None:
        m.load(MEM[0], ram[MEM[0] - BASE:MEM[1] - BASE])
    else:
        m.load(MEM[0], overlay[MEM[0] - OVL:MEM[1] - OVL])
    m.native = [CODE]
    m.R[4], m.R[5], m.R[6], m.R[15] = 0, 0x8c2fff38, 0, STACK
    m.PR = STOP
    steps = m.run(ENTRY, STOP, max_steps=50_000_000)
    ext = [c for c in m.calls if not CODE[0] <= c[0] < CODE[1]]
    msgs = ['%#x(%r)' % (c[0], cstr(ram, c[1]) if STR[0] <= c[1] < STR[1] else '%#x' % c[1]) for c in ext]
    r0 = m.R[0]
    print('%-22s r0 = %08x  %s  (%d instructions)  external calls: %s' % (
        label, r0, 'member data pointer' if r0 == 0x8c2fff38 + 0x2c else ('NULL: member REJECTED' if r0 == 0 else '?'),
        steps, ', '.join(msgs) or 'none'))


def main(argv):
    ram = open(argv[1], 'rb').read()
    run(ram, 'RAM dump as is')
    for name in argv[2:]:
        src = D.Source(os.path.join(ROOT, 'build', 'trial', name), name)
        _p, _rl, _rs, recs = D.read_filesystem(src)
        r = [x for x in recs if x.path.upper().endswith('FLOW_PRG/SCDRF.BIN')][0]
        run(ram, 'RAM code + ' + name, src.read(r.lba, r.size))


main(sys.argv)
