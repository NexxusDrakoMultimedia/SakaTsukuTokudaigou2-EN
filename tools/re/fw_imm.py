"""fw_imm.py FILE BASE_HEX LO_HEX HI_HEX IMM [IMM..]: halfword scan for `mov #imm,Rn` (0xEnII, sign-extended imm8) and `add #imm,Rn` (0x7nII)
and for literal-pool words equal to imm, inside a code range (heuristic: data can mimic code).  Read-only helper (field-width study)."""
import struct, sys
f, base, lo, hi = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16), int(sys.argv[4], 16)
d = open(f, 'rb').read()
for v in sys.argv[5:]:
    v = int(v, 0)
    lit = v & 0xFF
    for kind, top in (('mov', 0xE), ('add', 0x7)):
        hits = []
        for a in range(lo & ~1, min(hi, len(d) - 1), 2):
            x = d[a] | d[a + 1] << 8
            if x >> 12 == top and (x & 0xFF) == lit:
                hits.append('%x(r%d)' % (base + a, (x >> 8) & 15))
        print('%s #%d: %d hits' % (kind, v, len(hits)), ' '.join(hits[:60]))
