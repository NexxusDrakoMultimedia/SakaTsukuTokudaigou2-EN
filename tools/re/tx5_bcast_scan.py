"""tx5: scan /BCAST/BCAST.BIN (the 630 MB voice archive, not in extracted/) for 'PCM FILE START' headers and list the transcripts.

    python -I -X utf8 tools/re/tx5_bcast_scan.py [--out build/tx5/bcast_headers.tsv] [--disc DIR]

Read-only.  Reads the ORIGINAL disc tracks through tools/gdrom.py.  Writes a TSV: idx, sector (relative to the file start), name,
size, tag1, tag2, text (cp932 at header +0x80), and the offsets of any other non-zero header bytes.
"""
import os, sys, re, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import gdrom

BCAST_LBA = 68002
BCAST_SECTORS = 307326
MAGIC = b'PCM FILE START  '


def cstr(b):
    i = b.find(b'\0')
    return b if i < 0 else b[:i]


def main():
    out = os.path.join(ROOT, 'build', 'tx5', 'bcast_headers.tsv')
    disc_dir = ROOT
    a = sys.argv[1:]
    if '--out' in a:
        out = a[a.index('--out') + 1]
    if '--disc' in a:
        disc_dir = a[a.index('--disc') + 1]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    d = gdrom.Disc(disc_dir)
    rows = []
    CH = 512
    for base in range(0, BCAST_SECTORS, CH):
        n = min(CH, BCAST_SECTORS - base)
        buf = d.read(BCAST_LBA + base, n * 2048)
        pos = 0
        while True:
            i = buf.find(MAGIC, pos)
            if i < 0:
                break
            pos = i + 1
            if i % 2048:
                continue
            if i + 2048 > len(buf):
                hdr = d.read(BCAST_LBA + base + i // 2048, 2048)
            else:
                hdr = buf[i:i + 2048]
            rows.append((base + i // 2048, hdr))
    print('headers', len(rows))
    stats = collections.Counter()
    with open(out, 'w', encoding='utf8') as f:
        f.write('idx\tsector\tname\tsize\ttag\ttext\textra_nonzero\n')
        for k, (sec, h) in enumerate(rows):
            name = cstr(h[0x10:0x40]).decode('ascii', 'replace')
            size = cstr(h[0x40:0x50]).decode('ascii', 'replace')
            tag = cstr(h[0x50:0x60]).decode('ascii', 'replace')
            raw = cstr(h[0x80:0x800])
            try:
                text = raw.decode('cp932')
            except UnicodeDecodeError:
                text = raw.decode('cp932', 'replace')
            nz = [j for j in range(0x60, 0x800) if h[j] and not (0x80 <= j < 0x80 + len(raw))]
            nz = [j for j in nz if j not in (0x60,)]
            stats[len(raw)] += 1
            f.write('%d\t%d\t%s\t%s\t%s\t%s\t%s\n' % (k, sec, name, size, tag, text.replace('\t', ' '), ','.join('%x' % j for j in nz[:12])))
    print('text length histogram (bytes):', sorted(stats.items())[:40], '... max', max(stats))
    print('wrote', out)


if __name__ == '__main__':
    main()
