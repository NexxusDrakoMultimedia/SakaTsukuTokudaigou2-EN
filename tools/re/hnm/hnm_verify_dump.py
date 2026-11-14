"""Run the club-name composer on a PATCHED, translated HOMETOWN.BIN (build_patch --dump DIR) in the SH-4 simulator.

    python -I -X utf8 tools/re/hnm/hnm_verify_dump.py DUMP_DIR/FLOW_PRG/HOMETOWN.BIN
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hnm_sim_club as C  # noqa: E402


def cstr(img, off):
    e = img.index(b'\0', off)
    return img[off:e]


def main():
    img = open(sys.argv[1], 'rb').read()
    first = open(os.path.join(C.ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
    towns = {}
    for k in range(1, 1271):
        p = struct.unpack_from('<I', img, C.TOWN_TBL + 4 * k)[0] - C.BASE
        towns.setdefault(cstr(img, p).decode('cp932', 'replace'), k)
    prefs = {cstr(img, struct.unpack_from('<I', img, C.PREF_TBL + 4 * k)[0] - C.BASE).decode('cp932', 'replace'): k for k in range(50)}
    pool = {cstr(img, struct.unpack_from('<I', img, C.POOL_TBL + 4 * k)[0] - C.BASE).decode('cp932', 'replace'): k for k in range(55)}
    print('pointer table strings: %d towns, %d prefectures, %d pool words' % (len(towns), len(prefs), len(pool)))
    for t, pf, w in (('Yokohama', 'Kanagawa', 'Shadows'), ('Kagoshima', 'Kagoshima', 'Mythos'), ('Hiratsuka', 'Kanagawa', 'Salire'),
                     ('Fujisawa', 'Kanagawa', 'Shadows'), ('Miura', 'Kanagawa', 'Mythos'), ('Izu Is.', 'Izu Is.', 'Mythos')):
        ti = towns.get(t)
        pi = prefs.get(pf)
        wi = pool.get(w)
        if ti is None or pi is None or wi is None:
            print('missing', t, pf, w, ti, pi, wi)
            continue
        print('%-10s %-10s %-8s -> ' % (t, pf, w) + ' | '.join(C.compose(img, first, ti, pi, wi, m).decode('cp932', 'replace') for m in range(4)))


if __name__ == '__main__':
    main()
