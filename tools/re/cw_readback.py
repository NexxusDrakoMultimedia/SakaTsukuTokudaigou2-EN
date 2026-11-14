"""Read the club words back from a built dump: HOMETOWN pool and CLUBEDIT messages (table 0x1eb8c).  usage: cw_readback.py DUMPDIR"""
import csv, struct, sys, os
D = sys.argv[1]
art = {}
for row in csv.reader(open('translation/clubwords_art.tsv', encoding='utf8'), delimiter='\t'):
    if row[0].isdigit(): art[int(row[0])] = row[3]
def cs(d, o): return d[o:d.index(b'\0', o)].decode('cp932')
h = open(os.path.join(D, 'FLOW_PRG', 'HOMETOWN.BIN'), 'rb').read()
c = open(os.path.join(D, 'FLOW_PRG', 'CLUBEDIT.BIN'), 'rb').read()
bad = 0
for k in range(1, 55):
    pw = cs(h, struct.unpack_from('<I', h, 0x422c8 + 4 * k)[0] - 0x8c2d0000)
    msg = cs(c, struct.unpack_from('<I', c, 0x1eb8c + 4 * k)[0] - 0x8c2d0000)
    mw = msg.split('@Y/')[1].split('@')[0]
    ok = mw == art[k] and (pw == art[k] or art[k].startswith(pw[:-0 or None]) or len(art[k]) > 7)
    if mw != art[k] or (pw != art[k] and len(art[k]) <= 7): bad += 1; print('MISMATCH', k, art[k], pw, mw)
    lang = msg.split('@')[2].strip()[:28]
    print(k, '%-11s %-11s %-11s %s' % (art[k], pw, mw, lang.replace('\n', ' ')))
print('bad', bad)
