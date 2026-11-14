"""mn6_peek.py: print what the wrappers make of a few real amounts (through the patched overlays in the interpreter).  Read only."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mn6_libsim as LS      # noqa: E402

L = LS.Libn('FLOW_PRG/G_INCOME.BIN')
for y in (390000000, 243000000, 146420000, 58000000, 5000, 0, -390000000):
    seen, ok, r0, dst = L.call('%d Yen', [y])
    print('G_INCOME %12d yen -> %r (ok %s)' % (y, seen[0][1], ok))
L = LS.Libn('FLOW_PRG/ABROAD.BIN')
for fmt, args in (('%2d oku %02d00m', (13, 15)), ('%2d oku %02d00m', (1, 3)), ('%6d00 man', (26,)), ('%6d00 man', (0,))):
    seen, ok, r0, dst = L.call(fmt, list(args))
    print('ABROAD %r %r -> %r' % (fmt, args, LS.cstr(L.m, dst)))
L = LS.Libn('FLOW_PRG/INVEST.BIN')
for fmt, args in (('    %4d oku %02d00m', (1234, 56)), ('          %4d man', (4500,)), ('%d cho%04d oku%02d00m', (1, 1123, 5))):
    seen, ok, r0, dst = L.call(fmt, list(args))
    print('INVEST %r %r -> %r' % (fmt, args, LS.cstr(L.m, dst)))
