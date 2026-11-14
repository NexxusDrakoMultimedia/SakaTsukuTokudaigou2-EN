"""mn6_discsim.py <disc dir> <disc name> [--quick]: run the number-library wrapper, the numeric wrapper, the real library functions and GAME's text function
on the overlays and 1ST_READ.BIN READ BACK FROM A BUILT DISC (tools/discbuild.Source): the English formats are the ones the text stage really wrote (relocated by
the repack), the stubs / pool words / caves the ones the build wrote.  Nothing is launched.

    python -I -X utf8 tools/re/mn6_discsim.py build/trial mn6_t1 [--quick]"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import discbuild as D        # noqa: E402
import moneypatch as MP      # noqa: E402
import mn6_libsim as LS      # noqa: E402


def main(argv):
    root, name = argv[1], argv[2]
    quick = '--quick' in argv
    src = D.Source(root, name)
    _pvd, _rl, _rs, recs = D.read_filesystem(src)
    files = {r.path.upper(): r for r in recs if not r.isdir}
    cache = {}

    def rd(p):
        key = p.upper()
        if key not in cache:
            r = files['/' + key]
            cache[key] = src.read(r.lba, r.size)
        return cache[key]
    LS.DISC = rd
    bad = 0
    for rel in MP.LIB_SITES:
        b, L = LS.check_lib(rel, quick)
        bad += b
        print('%-24s wrapper %s' % (rel, 'OK' if not b else '%d FAIL' % b))
    b = LS.check_functions(quick, modes=(True,))
    bad += b
    print('library functions F1 / F2a with the English formats of the disc: %s' % ('OK' if not b else '%d FAIL' % b))
    for rel in MP.LIBN_SITES:
        b, L = LS.check_libn(rel, quick)
        bad += b
        print('%-24s numeric %s' % (rel, 'OK' if not b else '%d FAIL' % b))
    b = LS.check_game(quick)
    bad += b
    print('GAME %s' % ('OK' if not b else '%d FAIL' % b))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
