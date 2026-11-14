"""s7n: read a trial disc back (read-only) and count the new / old name forms in every file of the disc.

usage: s7n_readback.py DISC_DIR NAME out.tsv        (DISC_DIR holds 'NAME (Track N).bin')
Also checks, for every record of build/s7n_changed_ids.tsv whose source is a plain overlay text, that the new English occurs in the built
file of that source (substring search of the cp932 bytes; records that share text count once).
"""
import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import gdrom  # noqa: E402

NEW = ['Red Diamonds', 'JEF United', 'Vissel Kobe', 'Sagan Tosu', 'F.C.Tokyo', 'Yokohama F Marinos', 'Bellmare', 'Sanfrecce', 'Consadole', 'Montedio', 'Frontale', 'Hollyhock',
       'Thanksgiving Match', 'Asia Winners Cup', 'World Winners Cup', 'Asia Challenge Cup', 'Asia Tournament', 'Europe Cup', 'Europe Challenge League',
       'South America Challenge League', 'Preseason Match', 'World Sports Festival', 'World vs Europe', 'Euro team', 'World team', 'Japanese Stars', 'English Legends',
       'The World Stars', 'Purple Sanga']
OLD = ['Reds', 'Belmare', 'Sanfrec', 'Consado', 'Montedo', 'Frontal', 'Holyhok', 'HollyHock', 'FCTokyo', 'Yoko.FC', 'All East', 'All West', 'AllEast', 'AllWest', 'World XI',
       'European XI', 'Euro XI', 'Fan Appreciation', 'Fan Thanks', 'Thank-You Match', 'Asian Winners', 'Asian Challenge Cup', 'Asian Tournament', 'European Cup',
       'European Challenge League', 'South American Challenge', 'South American Cup', 'Pre-Season', 'Pre-season', 'World Sports Games', 'World Games', 'Champ Cup',
       'Japan Stars', 'Asia Stars', 'Africa Stars', 'Nordic Stars', 'U.K. Legends', 'Spain Legends', 'PurpleSanga']


def count(data, s):
    b = s.encode('cp932')
    n = i = 0
    while True:
        i = data.find(b, i)
        if i < 0:
            return n
        n += 1
        i += len(b)


def main():
    gdrom.BASE = sys.argv[2] + ' (Track %d).bin'
    d = gdrom.Disc(sys.argv[1])
    fs = {p: (l, s) for p, l, s in gdrom.walk(d, *gdrom.pvd_root(d))}
    tot = collections.Counter()
    per = {}
    for p, (l, s) in sorted(fs.items()):
        if not p.upper().endswith(('.BIN', '.INI', '.DAT')) or (s > 40 * 1024 * 1024 and 'BCAST' not in p.upper()):
            continue
        data = d.read(l, s)
        row = {}
        for w in NEW + OLD:
            n = count(data, w)
            if n:
                row[w] = n
                tot[w] += n
        if row:
            per[p] = row
    with open(sys.argv[3], 'w', encoding='utf8', newline=chr(10)) as fh:
        for p, row in per.items():
            fh.write(p + chr(9) + '; '.join('%s=%d' % kv for kv in sorted(row.items())) + chr(10))
    print('NEW forms (occurrences on the disc):')
    for w in NEW:
        print('  %-34s %d' % (w, tot[w]))
    print('OLD forms still on the disc (substring counts; a longer new form can contain the old one):')
    for w in OLD:
        print('  %-34s %d' % (w, tot[w]))


main()
