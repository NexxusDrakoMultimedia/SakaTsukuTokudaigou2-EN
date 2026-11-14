"""svfmt_xref.py OVERLAY HEXADDR... : pc-relative literal references (mov.l/mov.w/mova) to a value or to
the literal-pool slot holding that value; prints referencing instruction and guessed function entry.
Also accepts a 1ST_READ address via FR: prefix not needed (values are just 32-bit words)."""
import sys, os, struct
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASES = {'1ST_READ': 0x8c010000, 'AUTOSAVE': 0x8c8d0000, 'SONGSAVE': 0x8c8d0000, 'CSAVE': 0x8c4d0000, 'CSAVE3': 0x8c4d0000, 'CSAVE4': 0x8c4d0000, 'N_ENTRY': 0x8c8d0000, 'EVENT': 0x8c2d0000, 'HOMETOWN': 0x8c2d0000, 'NEWCON': 0x8c6d0000, 'SS_EDIT': 0x8c4d0000, 'GAME': 0x8c2d0000, 'SEARCH': 0x8c4d0000, 'SCDRF': 0x8c2d0000}
def load(n):
    p = os.path.join(ROOT, 'extracted', n + '.BIN') if n == '1ST_READ' else os.path.join(ROOT, 'extracted', 'FLOW_PRG', n + '.BIN')
    return open(p, 'rb').read(), BASES[n]
def entry_guess(d, off):
    i = off & ~1
    lo = max(0, i - 0x1200)
    j = i
    while j >= lo:
        w = struct.unpack_from('<H', d, j)[0]
        if w == 0x4F22:  # sts.l pr,@-r15
            k = j
            while k >= 2:
                p = struct.unpack_from('<H', d, k - 2)[0]
                if (p & 0xF0FF) == 0x2F06 or p in (0x4F02, 0x4F12) or (p & 0xFF0F) == 0xFF0B:  # push regs / sts.l mach/macl
                    k -= 2
                else: break
            return k
        j -= 2
    return None
def refs(d, base, targets):
    out = []
    n = len(d)
    for off in range(0, n - 1, 2):
        w = struct.unpack_from('<H', d, off)[0]
        t = w >> 12
        if t == 0xD:
            ea = ((base + off + 4) & ~3) + (w & 0xFF) * 4
            kind = 'mov.l'
        elif t == 0x9:
            ea = base + off + 4 + (w & 0xFF) * 2
            kind = 'mov.w'
        else: continue
        eo = ea - base
        if not (0 <= eo < n - 3): continue
        v = struct.unpack_from('<I', d, eo)[0] if kind == 'mov.l' else struct.unpack_from('<H', d, eo)[0]
        if v in targets:
            out.append((base + off, kind, 'r%d' % ((w >> 8) & 15), v, ea))
    return out
if __name__ == '__main__':
    d, base = load(sys.argv[1])
    tg = set(int(x, 16) for x in sys.argv[2:])
    for a, k, r, v, ea in refs(d, base, tg):
        e = entry_guess(d, a - base)
        print('%08x %s %s <- lit@%08x val %x  func~%s' % (a, k, r, ea, v, ('%08x' % (base + e)) if e is not None else '?'))
