"""s7m_selb [--write] [08663|08805] : Hometown / Office town menu plates (TWND*.ZAR selb.tbd#0, 256x256 ARGB4444 twiddled).
8 cells of 32 px; text zone x 0..94 (bars start at x 96); last row also has the national team ground label at x 97..191."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7m_lib as L
import art7_lib

ROWS_A = ['Advance\nSchedule', 'Office', 'Training\nGround', 'Meeting\nRoom', 'Youth', "Supporters'\nClub", 'Local\nGroups', 'Quit /\nOptions']
ROWS_B = ['Advance\nSchedule', 'Office', 'Training\nGround', 'Meeting\nRoom', 'Sub\nGround', "Supporters'\nClub", 'Local\nInfo', 'Quit /\nOptions']
JOBS = {'08663': ('FLOW_PRG/TWND1.ZAR', ROWS_A), '08805': ('FLOW_PRG/TWND1F.ZAR', ROWS_B)}
SIZE1, SIZE2 = 22, 14


def items(rows):
    its = []
    for k, text in enumerate(rows):
        y0 = 32 * k
        two = '\n' in text
        its.append(dict(rect=(0, y0, 96, 32), text=text, font='arial-narrow-bold', pad=0, align='center', valign='middle',
                        size=SIZE2 if two else SIZE1, min_sx=0.7, shear=0.2, wrap=False, line_spacing=0.84,
                        erase={'mode': 'clear'}))
    # national team ground label right of the last row
    its.append(dict(rect=(97, 224, 95, 32), text='National Team\nGround', font='arial-narrow-bold', pad=0, align='center',
                    valign='middle', size=SIZE2, min_sx=0.7, shear=0.2, line_spacing=0.84, erase={'mode': 'clear'},
                    style_from=(0, 225, 94, 30)))
    return its


def run(sid, write):
    src, rows = JOBS[sid]
    t = L.load(src, 'selb.tbd#0')
    its = items(rows)
    # autostyle of the national team label comes from the last row's old ink
    out, rep = art7_lib.repaint(t, [{k: v for k, v in i.items() if k != 'style_from'} for i in its], 'argb4444')
    for w in rep['warnings']:
        print(sid, 'WARN', w)
    for r in rep['regions']:
        print(sid, repr(r['text']), r['font'], r['size'], r['squash'], r['block'])
    L.sheet(t['arr'], out, os.path.join(L.OUT, sid + '_ba.png'), 3, rect=(0, 0, 200, 256))
    if write:
        new, paths, bad = L.write(t, out)
        print(sid, 'wrote', len(paths), 'bad', bad)


if __name__ == '__main__':
    write = '--write' in sys.argv
    ids = [a for a in sys.argv[1:] if not a.startswith('--')] or sorted(JOBS)
    for i in ids:
        run(i, write)
