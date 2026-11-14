"""mn6_discfmt.py <disc dir> <disc name>: print the format strings the money code reads, as they really are in the BUILT disc (pool words -> strings).  Read only."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import discbuild as D        # noqa: E402
import textdb                # noqa: E402

POOLS = {
    'FLOW_PRG/ABROAD.BIN': (0x7E68, 0x7E6C), 'FLOW_PRG/FIRE.BIN': (0x6BFC, 0x6C00), 'FLOW_PRG/PLNUMSET.BIN': (0x9890, 0x9894), 'FLOW_PRG/SELNAT.BIN': (0xDE18, 0xDE1C, 0xB5AC),
    'FLOW_PRG/INVEST.BIN': (0x1CE4, 0x1CE8, 0x1CEC), 'FLOW_PRG/G_INCOME.BIN': (0x1A50,), 'FLOW_PRG/GETREP.BIN': (0x94C8, 0x94D0, 0x9560, 0x14470, 0x14474, 0x1457C),
    'FLOW_PRG/CHALMODE.BIN': (), 'FLOW_PRG/GAME.BIN': (0xF7C10, 0xF7C18, 0xF7C7C, 0xF7C88),
}


def main(argv):
    src = D.Source(argv[1], argv[2])
    _pvd, _rl, _rs, recs = D.read_filesystem(src)
    files = {r.path.upper(): r for r in recs if not r.isdir}
    for rel, pools in POOLS.items():
        r = files['/' + rel.upper()]
        d = src.read(r.lba, r.size)
        base = textdb.load_image(rel).base
        for p in pools:
            va = struct.unpack_from('<I', d, p)[0]
            o = va - base
            e = d.find(b'\0', o)
            print('%-24s pool %#06x -> %#x  %r' % (rel.split('/')[-1], p, o, d[o:e].decode('cp932', 'replace')))


if __name__ == '__main__':
    main(sys.argv)
