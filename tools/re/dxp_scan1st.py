"""Read-only: scan images for GD-ROM/ISO related constants. usage: dxp_scan1st.py FILE [BASE]"""
import sys, struct
fn = sys.argv[1]; base = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x8c010000
d = open(fn, 'rb').read()
for pat in (b'CD001', b'SEGA SEGAKATANA', b'GDFS', b'gdfs', b'GDROM', b'GD-ROM', b'IP.BIN', b'1ST_READ', b'TOC', b'ISO', b'.BIN'):
    i = -1; hits = []
    while True:
        i = d.find(pat, i + 1)
        if i < 0: break
        hits.append(i)
    print(pat, len(hits), [hex(base + h) for h in hits[:8]])
# words equal to interesting constants
words = {0xB05E: 'HD start FAD 45150', 45000: 'HD base 45000', 45150: '45150', 549150: 'end', 549300: 'end+150', 0x0861B4: 'lead-out FAD', 0x8c0000bc: 'GDROM syscall vec',
         0x8c0000b0: 'syscall b0', 0x8c0000b4: 'syscall b4', 0x8c0000b8: 'syscall b8', 0x8c0000c0: 'c0', 2048: '2048', 150: '150', 0xAFC8: '45000hex', 0x1b8a: 'x'}
n = len(d) // 4
w = struct.unpack('<%dI' % n, d[:n * 4])
for v, name in words.items():
    h = [k for k in range(n) if w[k] == v]
    print('%-22s %#x count=%d first=%s' % (name, v, len(h), [hex(base + 4 * k) for k in h[:6]]))
