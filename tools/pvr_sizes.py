"""Print the set of decoded data sizes per (data format, w, h) from the inventory."""
import sys
import collections


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'build/textures/inventory.tsv'
    rows = [l.rstrip('\n').split('\t') for l in open(path, encoding='utf-8')]
    head = rows[0]
    rows = [dict(zip(head, r)) for r in rows[1:]]
    g = collections.defaultdict(collections.Counter)
    for r in rows:
        if r['kind'] in ('PVP',):
            continue
        g[(int(r['dat']), int(r['pix']), int(r['w']), int(r['h']))][int(r['dsize'])] += 1
    for k in sorted(g):
        print('dat=%#04x pix=%d %4dx%-4d : %s' % (k[0], k[1], k[2], k[3], dict(g[k])))


main()
