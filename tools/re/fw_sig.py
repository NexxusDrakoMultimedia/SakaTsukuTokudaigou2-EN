"""fw_sig.py FILE START_HEX LEN_HEX [ROOT]: masked-instruction signature scan (read-only, field-width study).
Takes LEN bytes of code at START of FILE (an overlay), masks the 8-bit displacement of PC-relative loads (0x9nDD mov.w, 0xDnDD mov.l,
0xC7DD mova) and of bra/bsr (0xAxxx/0xBxxx), then scans every overlay under ROOT/FLOW_PRG and ROOT/ATFIRST for the same masked word
sequence at any even offset.  Prints file, hit count, first offsets."""
import os
import sys

f, s, n = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
root = sys.argv[4] if len(sys.argv) > 4 else 'extracted'


def mask(b):
    out = bytearray(b)
    for i in range(0, len(out) - 1, 2):
        w = out[i] | out[i + 1] << 8
        top = w >> 12
        if top in (0x9, 0xD):
            out[i] = 0
        elif top in (0xA, 0xB):
            out[i] = 0
            out[i + 1] &= 0xF0
        elif (w >> 8) == 0xC7:
            out[i] = 0
    return bytes(out)


sig = mask(open(f, 'rb').read()[s:s + n])
# anchor: first word whose top nibble is not a masked kind -> exact bytes
anchor = None
for i in range(0, len(sig) - 1, 2):
    w = sig[i] | sig[i + 1] << 8
    if (w >> 12) not in (0x9, 0xD, 0xA, 0xB) and (w >> 8) != 0xC7:
        anchor = (i, sig[i:i + 2])
        break
tot = 0
for sub in ('FLOW_PRG', 'ATFIRST'):
    base = os.path.join(root, sub)
    for name in sorted(os.listdir(base)):
        if not name.endswith('.BIN'):
            continue
        d = open(os.path.join(base, name), 'rb').read()
        hits = []
        pos = d.find(anchor[1], 0)
        while pos != -1:
            a = pos - anchor[0]
            if a >= 0 and a % 2 == 0 and a + n <= len(d) and mask(d[a:a + n]) == sig:
                hits.append(a)
            pos = d.find(anchor[1], pos + 1)
        if hits:
            tot += 1
            print('%s/%s' % (sub, name), len(hits), ['%x' % h for h in hits[:4]])
print('files', tot)
