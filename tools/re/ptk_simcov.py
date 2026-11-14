"""Read-only analysis: which SH-4 opcodes does tools/sh4sim.py execute, and which mnemonics do real overlays use?

    python -I -X utf8 tools/re/ptk_simcov.py

Prints (1) mnemonics (capstone) for which sh4sim raises SimError on some encoding, (2) the mnemonic histogram of the
half-words in the layout function range of MEETING.BIN and in the whole 1ST_READ .text range (halfword-wise decode, so data
words add noise).  Used by docs/expansion/patch-toolkit.md; writes nothing.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import capstone as cs      # noqa: E402
import sh4sim              # noqa: E402

MD = cs.Cs(cs.CS_ARCH_SH, cs.CS_MODE_SH4 | cs.CS_MODE_LITTLE_ENDIAN)
_CACHE = {}


def mnem(op):
    if op in _CACHE:
        return _CACHE[op]
    r = None
    for i in MD.disasm(op.to_bytes(2, 'little'), 0x8c000000):
        r = i.mnemonic
        break
    _CACHE[op] = r
    return r


def coverage():
    ok = collections.Counter()
    bad = collections.Counter()
    for op in range(65536):
        m = mnem(op)
        if m is None:
            continue
        mach = sh4sim.Machine()
        mach.R = [0x8c100000 + 4 * i for i in range(16)]
        try:
            mach.exec_op(op, 0x8c000000)
            ok[m] += 1
        except sh4sim.SimError:
            bad[m] += 1
        except Exception:
            ok[m] += 1
    return ok, bad


def histogram(path, lo, hi):
    d = open(path, 'rb').read()[lo:hi]
    h = collections.Counter()
    for i in range(0, len(d) - 1, 2):
        m = mnem(d[i] | d[i + 1] << 8)
        if m:
            h[m] += 1
    return h


def main():
    ok, bad = coverage()
    print('distinct mnemonics seen by capstone:', len(set(ok) | set(bad)))
    print('fully implemented in sh4sim        :', len([m for m in ok if m not in bad]))
    print('some encoding unsupported          :', len(bad))
    print('   ', ' '.join(sorted(bad)))
    p = os.path.join(ROOT, 'extracted', 'FLOW_PRG', 'MEETING.BIN')
    h = histogram(p, 0xe294, 0xe4d4)
    print('layout function MEETING 0xe294..0xe4d4: %d halfwords decode, %d distinct mnemonics' % (sum(h.values()), len(h)))
    print('   lacking in sim:', {m: n for m, n in h.items() if m in bad})
    k = os.path.join(ROOT, 'extracted', '1ST_READ.BIN')
    big = histogram(k, 0, 0x12bb00)
    tot = sum(big.values())
    lack = sum(n for m, n in big.items() if m in bad)
    print('1ST_READ .text (0..0x12bb00): %d decodable halfwords, %.1f %% carry a mnemonic that sim lacks some encoding of' % (tot, 100.0 * lack / tot))
    print('   most used lacking:', sorted(((m, n) for m, n in big.items() if m in bad), key=lambda x: -x[1])[:20])


if __name__ == '__main__':
    main()
