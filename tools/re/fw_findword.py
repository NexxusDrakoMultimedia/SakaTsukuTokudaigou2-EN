"""fw_findword.py FILE BASE_HEX VALUE_HEX [VALUE_HEX..]: aligned little-endian u32 words equal to a value (or within value..value+0x3) and the
mov.l @(disp,PC) sites that load them (read-only helper of the field-width study)."""
import struct, sys
f, base = sys.argv[1], int(sys.argv[2], 16)
d = open(f, 'rb').read()
n = len(d) // 4
words = struct.unpack('<%dI' % n, d[:n * 4])
for v in sys.argv[3:]:
    v = int(v, 16)
    for i, w in enumerate(words):
        if w == v:
            L = i * 4
            users = []
            for A in range(max(0, L - 1024 - 8), L, 2):
                x = d[A] | d[A + 1] << 8
                if x >> 12 == 0xD and (A & ~3) + 4 + 4 * (x & 0xFF) == L:
                    users.append(hex(base + A))
            print('%#x: word @%#x (addr %#x) loaded at %s' % (v, L, base + L, users))
