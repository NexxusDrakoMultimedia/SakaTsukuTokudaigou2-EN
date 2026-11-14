"""hng: run the GAME's own LZ decoders (1ST_READ.BIN FUN_8c15a9f4 = bz, FUN_8c15aae4 = bzw) in tools/sh4sim.py on every
repainted texture stream of the built texture patches, and compare with the intended pixel data.

This answers one question for the hang investigation: can the real decoder read what the art installer wrote (right length, ends
at its end token, same bytes as the Python port)?  Nothing is written; the texture patches are rebuilt in memory with
texinject.make_patches on the ORIGINAL extracted files (the same call the build makes) and, with --disc DIR NAME, the built disc
files are compared with them first.

usage: hng_texdec.py [--only SUBSTRING] [--limit N] [--sample K]
       --only: only container paths containing the substring (e.g. EVENT, ETC_DATA/BAR)
Output: one line per texture stream: OK / MISMATCH / ERROR, the number of simulator instructions and seconds.
"""
import os
import sys
import time
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sh4sim                                   # noqa: E402
import texinject as TI                          # noqa: E402
import bzlib                                    # noqa: E402

BZ, BZW = 0x8C15A9F4, 0x8C15AAE4
LO, HI = 0x8C15A9F0, 0x8C15AC00
SRC, DST, STACK, STOP = 0x8D000000, 0x8D400000, 0x8CFFF000, 0x8C000000

_k = open(os.path.join(ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
CODE = _k[LO - 0x8C010000:HI - 0x8C010000]


def sim_decode(method, packed, max_steps=400_000_000):
    """the game's decoder on `packed`; returns (bytes, instruction count)"""
    m = sh4sim.Machine()
    m.load(LO, CODE)
    m.load(SRC, bytes(packed) + bytes(16))
    m.R[4], m.R[5], m.R[15] = DST, SRC, STACK
    m.PR = STOP
    m.native = [(LO, HI)]
    entry = {'-bz--': BZ, '-bzw-': BZW}[method]
    steps = m.run(entry, STOP, max_steps=max_steps)
    n = m.R[0]
    return bytes(m.rb(DST + i) for i in range(n)), steps


def streams(d, tid):
    """[(label, method, packed bytes, expected plain by the python port)] of the stream(s) that hold texture `tid` of file bytes d"""
    r = TI.resolve(d, tid)
    out = []
    if r['type'] == 'tbd':
        tab, i = r['table'], r['index']
        start, end = TI._rec_slot(d, tab, i)
        comp = tab.recs[i]['comp']
        if comp in (1, 2):
            meth = '-bzw-' if comp == 1 else '-bz--'
            blk = bytes(d[start:end])
            out.append(('record', meth, blk, TI.tbd_plain(d, tab, i)))
    elif r['type'] == 'zs-pvr':
        m = r['ms'][r['mi']]
        if m.method in ('-bz--', '-bzw-'):
            out.append(('member', m.method, bytes(d[m.data_offset:m.end_offset]), r['plain']))
    elif r['type'] == 'zs-tbd':
        m = r['ms'][r['mi']]
        if m.method in ('-bz--', '-bzw-'):
            out.append(('member', m.method, bytes(d[m.data_offset:m.end_offset]), r['plain']))
        tab, i = r['table'], r['index']
        comp = tab.recs[i]['comp']
        if comp in (1, 2):
            pl = r['plain']
            start, end = TI._rec_slot(pl, tab, i)
            out.append(('record', '-bzw-' if comp == 1 else '-bz--', bytes(pl[start:end]), TI.tbd_plain(pl, tab, i)))
    return out


def main(argv):
    only = argv[argv.index('--only') + 1] if '--only' in argv else ''
    limit = int(argv[argv.index('--limit') + 1]) if '--limit' in argv else 10 ** 9
    groups = TI.load_textures_dir(os.path.join(ROOT, 'translation', 'textures'), TI.EXTRACTED)
    n_ok = n_bad = n_streams = 0
    t_all = time.time()
    for rel in sorted(groups):
        if only and only not in rel:
            continue
        repl = groups[rel]
        base = TI._as_bytes(rel)
        new, _ = TI.replace_textures(base, repl, 'exact')
        for tid in sorted(repl):
            try:
                ss = streams(new, tid)
            except Exception as e:                    # noqa: BLE001
                print('ERROR  %s %s: %s' % (rel, tid, e))
                n_bad += 1
                continue
            if not ss:
                print('STORED %s %s (no compressed stream)' % (rel, tid))
                continue
            for label, meth, packed, plain in ss:
                if n_streams >= limit:
                    break
                n_streams += 1
                t0 = time.time()
                try:
                    got, steps = sim_decode(meth, packed)
                except Exception as e:                # noqa: BLE001
                    print('ERROR  %s %s %s %s: %s' % (rel, tid, label, meth, e))
                    n_bad += 1
                    continue
                ok = got == plain
                n_ok += ok
                n_bad += (not ok)
                print('%s %s %s %s %s: packed %d plain %d game %d, %d instr, %.1fs' % (
                    'OK     ' if ok else 'MISMATCH', rel, tid, label, meth, len(packed), len(plain), len(got), steps, time.time() - t0), flush=True)
    print('streams run %d: OK %d, bad %d, %.0fs' % (n_streams, n_ok, n_bad, time.time() - t_all))
    return 1 if n_bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
