"""svfmt_ncpy.py : in every overlay, literal loads of strncpy (0x8c013294) followed by a call, with an immediate r6 count in 1..20 near it.
Histogram of counts (per overlay and total) -> where fixed-size name copies are."""
import sys, os, struct, glob, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TARGET = 0x8c013294
tot = collections.Counter(); per = {}
for f in sorted(glob.glob(os.path.join(ROOT, 'extracted', 'FLOW_PRG', '*.BIN'))):
    d = open(f, 'rb').read(); n = len(d)
    base = 0x8c2d0000  # slot base is irrelevant for literal counting except pc-relative alignment; use file-offset based alignment
    # literal pools are 4-aligned in file offset == vaddr alignment as long as base is 4-aligned (all bases are)
    c = collections.Counter()
    for off in range(0, n - 1, 2):
        w = struct.unpack_from('<H', d, off)[0]
        if (w >> 12) != 0xD: continue
        eo = ((off + 4) & ~3) + (w & 0xFF) * 4
        if eo + 4 > n or struct.unpack_from('<I', d, eo)[0] != TARGET: continue
        reg = (w >> 8) & 15
        # find jsr @reg within next 12 instructions, and mov #imm,r6 within 12 instructions before/after
        found = None
        for k in range(-12, 13):
            o2 = off + 2 * k
            if o2 < 0 or o2 + 2 > n: continue
            w2 = struct.unpack_from('<H', d, o2)[0]
            if (w2 & 0xFF00) == 0xE600:  # mov #imm,r6
                imm = w2 & 0xFF
                found = imm
        if found is not None and 1 <= found <= 40: c[found] += 1
    per[os.path.basename(f)[:-4]] = c
    tot.update(c)
print('total', sorted(tot.items()))
for k in (8, 10, 11, 12, 13, 14, 15, 16):
    print('count', k, 'in', sum(1 for v in per.values() if v[k]), 'overlays; sites', tot[k])
for name in ('EVENT', 'AUTOSAVE', 'MEETING', 'HELP', 'GAME'):
    print(name, sorted(per.get(name, {}).items()))
print('overlays with n=12:', ' '.join('%s:%d' % (k, v[12]) for k, v in per.items() if v[12]))
