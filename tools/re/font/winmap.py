"""Static window-class analysis of one overlay.

    from winmap import Overlay
    ov = Overlay('CAP_SLCT.BIN')
    ov.funcs            sorted function entries (call targets, jmp targets, prologue starts)
    ov.factories        {entry: [(site, cells, rows, adv, lineh)]}  functions that store a window geometry (+0x3c cells ...)
    ov.func_of(addr)    containing function entry
    ov.calls[f]         set of call targets (resolved jsr/bsr/jmp literals) of function f
    ov.loads_of(value_lo, value_hi) -> [(site_addr, value)]   instructions `mov.l @(pc),Rn` / `mova` loading a value in range

Everything is derived from the overlay code image only (extracted/ files are read-only)."""
import os, sys, struct, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from disov import load

PUSH = {0x2f86, 0x2f96, 0x2fa6, 0x2fb6, 0x2fc6, 0x2fd6, 0x2fe6, 0x4f22}


def s8(x):
    return x - 256 if x > 127 else x


class Overlay:
    def __init__(self, name):
        self.name = name
        img, row = load(name)
        self.img = img
        self.base = img.base
        d = img.d
        self.d = d
        n = len(d) // 2
        self.W = struct.unpack('<%dH' % n, d[:n * 2])
        self.end = self.base + n * 2
        self._scan_loads()
        self._scan_calls()
        self._scan_factories()

    # -- helpers
    def u32(self, a):
        o = a - self.base
        if 0 <= o <= len(self.d) - 4:
            return struct.unpack_from('<I', self.d, o)[0]
        return None

    def _scan_loads(self):
        """loads[i] = (reg, value) for `mov.l @(disp,pc),Rn`; mova gives ('A', addr)."""
        self.loads = {}
        W = self.W
        base = self.base
        for i, w in enumerate(W):
            t = w & 0xF000
            if t == 0xD000:
                pc = base + i * 2
                a = ((pc + 4) & ~3) + (w & 0xFF) * 4
                v = self.u32(a)
                if v is not None:
                    self.loads[i] = ((w >> 8) & 15, v, a)
            elif (w & 0xFF00) == 0xC700:
                pc = base + i * 2
                a = ((pc + 4) & ~3) + (w & 0xFF) * 4
                self.loads[i] = (0, a, a)

    def _scan_calls(self):
        W = self.W
        base = self.base
        self.callsites = []        # (site_index, target, kind)
        for i, w in enumerate(W):
            if (w & 0xF0FF) == 0x400B:                      # jsr @Rn
                n = (w >> 8) & 15
                for k in range(i - 1, max(i - 30, 0), -1):
                    u = W[k]
                    if k in self.loads and self.loads[k][0] == n and (u & 0xF000) == 0xD000:
                        self.callsites.append((i, self.loads[k][1], 'jsr'))
                        break
                    if (u & 0xF00F) == 0x6003 and ((u >> 8) & 15) == n:        # mov Rm,Rn: unresolved
                        break
                    if u == 0x000b:
                        break
            elif (w & 0xF000) == 0xB000:                    # bsr
                disp = w & 0xFFF
                if disp & 0x800:
                    disp -= 0x1000
                self.callsites.append((i, base + i * 2 + 4 + disp * 2, 'bsr'))
            elif (w & 0xF0FF) == 0x402B:                    # jmp @Rn (tail call)
                n = (w >> 8) & 15
                for k in range(i - 1, max(i - 12, 0), -1):
                    if k in self.loads and self.loads[k][0] == n and (W[k] & 0xF000) == 0xD000:
                        self.callsites.append((i, self.loads[k][1], 'jmp'))
                        break
        ent = set()
        for i, t, kind in self.callsites:
            if self.base <= t < self.end and t % 2 == 0:
                ent.add(t)
        def cont(w):
            return (w & 0xFF0F) == 0x2F06 or (w & 0xFF0F) == 0xFF0B or w == 0x4f22 or (w & 0xFF00) == 0x7F00

        def delay_owner(w):
            return (w & 0xF0FF) in (0x400B, 0x402B) or (w & 0xF000) == 0xB000 or (w & 0xF000) == 0xA000 or (w & 0xFF00) in (0x8D00, 0x8F00)
        for i in range(1, len(W)):
            if W[i] in PUSH and not cont(W[i - 1]) and not delay_owner(W[i - 1]):
                a = self.base + i * 2
                ent.add(a)
        self.ctargets = sorted(t for t in {t for i, t, k in self.callsites} if self.base <= t < self.end and t % 2 == 0)
        self.funcs = sorted(ent)

    def func_of(self, a):
        import bisect
        i = bisect.bisect_right(self.funcs, a) - 1
        return self.funcs[i] if i >= 0 else None

    def ctarget_of(self, a):
        import bisect
        i = bisect.bisect_right(self.ctargets, a) - 1
        return self.ctargets[i] if i >= 0 else None

    def func_range(self, f):
        import bisect
        i = bisect.bisect_right(self.funcs, f)
        return f, (self.funcs[i] if i < len(self.funcs) else self.end)

    def _scan_factories(self):
        W = self.W
        base = self.base
        self.factories = collections.defaultdict(list)
        for i, w in enumerate(W):
            if (w & 0xFF00) == 0xE000 and (w & 0xFF) == 0x3c:
                cells = None
                for j in range(i + 1, min(i + 4, len(W))):
                    v = W[j]
                    if (v & 0xF00F) == 0x0004:
                        m = (v >> 4) & 15
                        for k in range(j - 1, max(j - 14, 0), -1):
                            u = W[k]
                            if (u & 0xF000) == 0xE000 and ((u >> 8) & 15) == m:
                                cells = s8(u & 0xFF)
                                break
                        break
                else:
                    continue
                fields = {}
                for k in range(max(i - 12, 0), min(i + 60, len(W))):
                    if (W[k] & 0xFF00) == 0xE000 and (W[k] & 0xFF) in (0x3d, 0x3e, 0x3f, 0x45, 0x46):
                        f = W[k] & 0xFF
                        for j in range(k + 1, min(k + 4, len(W))):
                            v = W[j]
                            if (v & 0xF00F) == 0x0004:
                                m = (v >> 4) & 15
                                for q in range(j - 1, max(j - 14, 0), -1):
                                    u = W[q]
                                    if (u & 0xF000) == 0xE000 and ((u >> 8) & 15) == m:
                                        fields.setdefault(f, s8(u & 0xFF))
                                        break
                                break
                site = base + i * 2
                self.factories[self.ctarget_of(site)].append((site, cells, fields.get(0x3d), fields.get(0x3e), fields.get(0x3f)))

    def loads_of(self, lo, hi):
        out = []
        for i, (reg, v, a) in self.loads.items():
            if lo <= v <= hi:
                out.append((self.base + i * 2, v))
        return out

    def pool_loads_at(self, addr):
        """instructions whose literal pool word is at addr"""
        return [self.base + i * 2 for i, (reg, v, a) in self.loads.items() if a == addr]

    def calls_of(self, f):
        lo, hi = self.func_range(f)
        out = collections.Counter()
        for i, t, kind in self.callsites:
            a = self.base + i * 2
            if lo <= a < hi:
                out[t] += 1
        return out


if __name__ == '__main__':
    ov = Overlay(sys.argv[1])
    print('funcs', len(ov.funcs), 'callsites', len(ov.callsites))
    for f, lst in sorted(ov.factories.items()):
        print('factory func %08x' % f, lst)
