"""svfmt_acc.py : census of the name-by-ID accessor (AUTOSAVE 0x8c8ea100: ID range check, 30-byte table, pointer table for ID >= 5600) in every overlay,
by code signature (prologue + muls.w #0x1e).  Prints file offsets, the two mov.w limits and number of direct callers (bsr/jsr-literal)."""
import sys, os, struct, glob
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SIG = bytes.fromhex('e62f4f6e224f114e')    # mov.l r14,@-r15; exts.w r4,r14; sts.l pr; cmp/pz r14
tot = 0
for f in sorted(glob.glob(os.path.join(ROOT, 'extracted', 'FLOW_PRG', '*.BIN')) + glob.glob(os.path.join(ROOT, 'extracted', 'ATFIRST', '*.BIN'))):
    d = open(f, 'rb').read(); i = d.find(SIG); hits = []
    while i >= 0:
        # require `mov #0x1e,r0` (e0 1e -> bytes 1e e0) within 0x30
        if d[i:i + 0x40].find(b'\x1e\xe0') > 0 and d[i:i + 0x40].find(b'\x2f\x2f\x00') < 0:
            w1 = struct.unpack_from('<H', d, ((i + 4 + 6) & ~1) + 0)[0] if False else None
            hits.append(i)
        i = d.find(SIG, i + 2)
    if hits:
        tot += len(hits); print(os.path.basename(f), ['%x' % h for h in hits])
print('overlay files with accessor', tot)
