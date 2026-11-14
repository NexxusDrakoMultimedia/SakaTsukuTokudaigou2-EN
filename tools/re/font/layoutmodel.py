"""Executable model of the tsString layout loop (FUN_8c2de294, MEETING variant A) and of the proposed pixel-based replacement.
original(): transcribed from the disassembly (units counter; wrap on (units+1)>>1 vs cells-1).
hooked():   same loop with a per-char pixel width and a pixel wrap test.
Self-test: with uniform widths (half = a>>1, full = a) hooked() == original() for random strings -> the hook is a strict
generalisation (PROVEN by the randomized check below, not by running the game)."""
import random

def sra1(v):                       # cmp/gt r2,r3 ; addc r3,r2 ; shar r2   == (v + (v<0)) >> 1  (round toward zero)
    return (v + (1 if v < 0 else 0)) >> 1

def original(codes, cells, adv, flag45, x0=0, y0=0, lineh=24):
    """codes: list of u16.  returns list of (x, y, code) for drawn glyphs (0x2020 not drawn)"""
    out = []; x = x0; y = y0; u = 0
    for c in codes:
        if (c & 0x2000) == 0 or c == 0x2020:
            r4 = (u + 1 + (1 if (u + 1) < 0 else 0)) >> 1      # (u+1)>>1 with rounding as in the code
            r2 = cells - 1
            if r4 > r2:
                x = x0; y += lineh; u = 0
            elif r4 == r2 and flag45 == 0 and not (c & 0x4000):
                u = 0; y += lineh; x = x0
            if c != 0x2020:
                out.append((x, y, c))
            half = (c == 0x2020) or bool(c & 0x8000)
            if half:
                x += sra1(adv); u += 1
            else:
                x += adv; u += 2
        elif c == 0x200a:
            x = x0; y += lineh; u = 0
    return out

def hooked(codes, cells, adv, flag45, width, x0=0, y0=0, lineh=24):
    """width(code, adv) -> px advance of this glyph.  wrap iff the pen has reached the limit (same limit as the original for uniform widths)."""
    out = []; x = x0; y = y0
    lim = (2 * cells - 1) * adv // 2          # flag45==1 :  units >= 2W-1   <=> px >= (2W-1)*adv/2
    lim0 = (2 * cells - 3) * adv // 2         # flag45==0 :  units >= 2W-3 (non-hang) 
    for c in codes:
        if (c & 0x2000) == 0 or c == 0x2020:
            px = x - x0
            if px >= lim or (flag45 == 0 and px >= lim0 and not (c & 0x4000)):
                x = x0; y += lineh
            if c != 0x2020:
                out.append((x, y, c))
            x += width(0x8000 if c == 0x2020 else c, adv)
        elif c == 0x200a:
            x = x0; y += lineh
    return out

def uniform(c, adv):
    return sra1(adv) if (c & 0x8000) else adv

def selftest(n=20000, seed=1):
    rnd = random.Random(seed)
    pool = [0x8041, 0x8061, 0x8021 | 0x4000, 0x2020, 0x200a, 0x0000 | 0x0160, 0x0160 | 0x4000, 0x2010, 0x2030]
    bad = 0
    for _ in range(n):
        cells = rnd.choice([1, 2, 5, 8, 10, 17, 20, 25]); adv = rnd.choice([10, 16, 24, 32, 48]); fl = rnd.choice([0, 1])
        codes = [rnd.choice(pool) for _ in range(rnd.randint(1, 120))]
        if original(codes, cells, adv, fl) != hooked(codes, cells, adv, fl, uniform):
            bad += 1
    return bad

if __name__ == '__main__':
    print('mismatches in 20000 random cases:', selftest())
    # example: 40 'W' (half, 12 px) in the default window (20 cells, adv 24, flag 1): 39 per line
    w = original([0x8057] * 80, 20, 24, 1)
    import collections
    print('chars per line (default window):', sorted(collections.Counter(y for x, y, c in w).values()))
