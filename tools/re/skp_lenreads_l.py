"""skp (skeptic): list mov.l/mov.w/mov.b reads @(r0,rm) with r0 in the panel len-field offsets (64..144) in the panel block of an overlay."""
import os, struct, sys
name = sys.argv[1]
lo = int(sys.argv[2], 16); hi = int(sys.argv[3], 16)
d = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'extracted', 'FLOW_PRG', name + '.BIN'), 'rb').read()
ws = struct.unpack('<%dH' % (len(d) // 2), d[:len(d) // 2 * 2])
K = set(range(64, 148, 4))
for i in range(lo // 2, hi // 2):
    w = ws[i]
    if w & 0xF00F in (0x000C, 0x000D, 0x000E):
        for j in range(i - 1, max(i - 5, 0), -1):
            if ws[j] >> 8 == 0xE0 and (ws[j] & 0xFF) in K:
                print('%#x: %s @(r0=%d, r%d) -> r%d' % (i * 2, {0xC: 'mov.b', 0xD: 'mov.w', 0xE: 'mov.l'}[w & 15], ws[j] & 0xFF, (w >> 4) & 15, (w >> 8) & 15)); break
