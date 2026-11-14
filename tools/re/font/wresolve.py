"""Resolve text tables / pointer slots of every overlay to the window classes (factories) reachable from the function that loads them.

python -I -X utf8 wresolve.py OVERLAY.BIN        -> prints per table the referencing functions and class sets
Library use: resolve_overlay(name, tables) -> {table_key: info}
"""
import os, sys, re, bisect, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), '..', 'tools'))
from winmap import Overlay


def cls_name(c):
    cells, rows, adv, lineh = c
    return '%s/%s/%s/%s' % (cells, rows, adv, lineh)


class Resolver:
    def __init__(self, name):
        self.ov = ov = Overlay(name)
        W = ov.W
        self.rts = [ov.base + i * 2 for i, w in enumerate(W) if w == 0x000b]
        self.union = sorted(set(ov.funcs) | set(ov.ctargets))
        # factories: site -> class ; start of the factory function (first union entry after the previous rts)
        self.fac = []          # (start, site, class)
        for key, lst in ov.factories.items():
            for site, cells, rows, adv, lineh in lst:
                st = self.start_of(site)
                self.fac.append((st, site, (cells, rows, adv, lineh)))
        self.fac.sort()
        # call index: function (union entry) -> list of (callsite addr, target)
        self.calls_by_func = collections.defaultdict(list)
        for i, t, kind in ov.callsites:
            a = ov.base + i * 2
            self.calls_by_func[self.func_of(a)].append((a, t, kind))
        self._direct = {}
        self._closure = {}

    def start_of(self, a):
        ov = self.ov
        j = bisect.bisect_left(self.rts, a) - 1
        lo = self.rts[j] + 4 if j >= 0 else ov.base
        k = bisect.bisect_left(self.union, lo)
        if k < len(self.union) and self.union[k] <= a:
            return self.union[k]
        return self.func_of(a)

    def func_of(self, a):
        k = bisect.bisect_right(self.union, a) - 1
        return self.union[k] if k >= 0 else None

    def fac_called_by(self, t):
        """classes of the factories a call to target t creates"""
        out = []
        for st, site, c in self.fac:
            if st <= t <= site:
                out.append(c)
        return out

    def direct(self, f):
        if f in self._direct:
            return self._direct[f]
        s = set()
        for a, t, kind in self.calls_by_func.get(f, ()):
            for c in self.fac_called_by(t):
                if c[0] is not None:
                    s.add(c)
        self._direct[f] = s
        return s

    def closure(self, f, depth=2, seen=None):
        key = (f, depth)
        if key in self._closure:
            return self._closure[key]
        s = set(self.direct(f))
        if depth > 0:
            for a, t, kind in self.calls_by_func.get(f, ()):
                tf = self.func_of(t) if t is not None else None
                if tf is not None and tf != f and self.ov.base <= t < self.ov.end:
                    s |= self.closure(self.func_of(t), depth - 1)
        self._closure[key] = s
        return s


if __name__ == '__main__':
    r = Resolver(sys.argv[1])
    print('factories:')
    for st, site, c in r.fac:
        print('  start %08x site %08x class %s' % (st, site, cls_name(c)))
    if len(sys.argv) > 2:
        lo = int(sys.argv[2], 16)
        hi = int(sys.argv[3], 16) if len(sys.argv) > 3 else lo + 3
        for site, v in r.ov.loads_of(lo, hi):
            f = r.func_of(site)
            print('load at %08x value %08x func %08x direct %s closure %s' % (site, v, f, sorted(map(cls_name, r.direct(f))), sorted(map(cls_name, r.closure(f)))))
