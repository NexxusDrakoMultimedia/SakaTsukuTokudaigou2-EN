"""Summarise build/textures/inventory.tsv (output of pvr_scan.py) for docs/textures.md."""
import sys
import collections

PIX = {0: 'ARGB1555', 1: 'RGB565', 2: 'ARGB4444', 3: 'YUV422', 4: 'BUMP', 5: 'PAL4', 6: 'PAL8'}
DAT = {1: 'twid', 2: 'twid+mip', 3: 'VQ', 4: 'VQ+mip', 5: 'pal4', 6: 'pal4+mip', 7: 'pal8', 8: 'pal8+mip',
       9: 'rect', 0xA: 'rect+mip', 0xB: 'stride', 0xD: 'rect-twid', 0x10: 'smallVQ', 0x11: 'smallVQ+mip',
       0x12: 'twid+mip2'}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'build/textures/inventory.tsv'
    rows = [l.rstrip('\n').split('\t') for l in open(path, encoding='utf-8')]
    head = rows[0]
    rows = [dict(zip(head, r)) for r in rows[1:]]
    tex = [r for r in rows if r['kind'] != 'PVP']
    print('records', len(tex))
    c = collections.Counter((int(r['pix']), int(r['dat'])) for r in tex)
    for k, v in sorted(c.items()):
        print('| %s | %s | %d |' % (PIX[k[0]], DAT[k[1]], v))
    print()
    cc = collections.defaultdict(collections.Counter)
    for r in tex:
        top = r['path'].split('/')[0]
        cc[top][r['kind']] += 1
    for t, d in sorted(cc.items()):
        print('| %s | %d | %s |' % (t, sum(d.values()), ', '.join('%s %d' % kv for kv in sorted(d.items()))))
    print()
    print('sizes', collections.Counter((r['w'] + 'x' + r['h']) for r in tex).most_common(12))
    print('methods', collections.Counter(r['method'] for r in tex))
    nbytes = sum(int(r['dsize']) for r in tex)
    print('payload bytes (with duplicates)', nbytes)


main()
