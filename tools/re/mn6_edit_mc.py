"""mn6_edit_mc.py: one-off, idempotent edit of tools/moneycheck.py for the number-library wrapper (mn6)."""
import os
import sys

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'moneycheck.py')
s = open(P, encoding='utf-8').read()
if 'check_lib' in s:
    sys.exit('already applied')

EDITS = [
    ("    check(len(k1) == len(k0) and k1[:o] == k0[:o] and k1[o + len(cave):] == k0[o + len(cave):] and k1[o:o + len(cave)] == cave,\n"
     "          '1ST_READ.BIN differs only inside the cave')",
     "    lo_ = MP.LIB_ADDR - MP.IMG_BASE if STYLE == 'jp' else None\n"
     "    libb = MP.lib_bytes() if STYLE == 'jp' else b''\n"
     "    diff = [i for i in range(o - 16, o + 0x200 + 16) if k1[i] != k0[i]] if lo_ is None else [i for i in range(len(k0)) if k1[i] != k0[i]]\n"
     "    allowed = set(range(o, o + len(cave))) | (set(range(lo_, lo_ + len(libb))) if lo_ is not None else set())\n"
     "    check(len(k1) == len(k0) and set(diff) <= allowed and k1[o:o + len(cave)] == cave and (lo_ is None or k1[lo_:lo_ + len(libb)] == libb),\n"
     "          '1ST_READ.BIN differs only inside the cave (and the number-library wrapper)')"),
    ("            for o in s.get('panel') or []:                          # the compact flag of the info panel call sites (jp, section 8)\n"
     "                want |= set(range(o, o + 2))",
     "            for o in s.get('panel') or []:                          # the compact flag of the info panel call sites (jp, section 8)\n"
     "                want |= set(range(o, o + 2))\n"
     "            if STYLE == 'jp' and rel in MP.LIB_SITES:               # the number-library stub (money function + 12, 16 bytes) and the pool words\n"
     "                want |= set(range(s['off'] + MP.LIB_STUB_REL, s['off'] + MP.LIB_STUB_REL + 16))\n"
     "                for po, _ in MP.LIB_SITES[rel] + ([MP.LIB_ZERO[rel]] if rel in MP.LIB_ZERO else []):\n"
     "                    want |= set(range(po, po + 4))"),
    ("        check_panel()\n        if '--e2e' in argv",
     "        check_panel()\n        check_lib(quick)\n        if '--e2e' in argv"),
]
for old, new in EDITS:
    if s.count(old) != 1:
        sys.exit('edit not applicable (%d matches): %r' % (s.count(old), old[:70]))
    s = s.replace(old, new)

SECTION = '''def check_lib(quick):
    """9: the number library (mn6): the wrapper behind the literal-pool word of `real`, executed through the REAL patched overlays (tools/re/mn6_libsim.py):
    synthetic calls (fmt, a1, a2) for every library overlay, and the real library functions F1 / F2a with real amounts (0, 58 man, 3 oku 9000 man, ...)."""
    print('--- 9: the number-library wrapper (9 overlays)')
    if STYLE != 'jp':
        print('   (jp style only)')
        return
    sys.path.insert(0, os.path.join(HERE, 're'))
    import mn6_libsim as LS
    LS.MC = sys.modules[__name__]
    for rel in MP.LIB_SITES:
        bad, L = LS.check_lib(rel, quick)
        check(bad == 0, '%s: wrapper calls (%d failures)' % (rel, bad))
    bad = LS.check_functions(quick)
    check(bad == 0, 'library functions F1 / F2a through the wrapper (%d failures)' % bad)
    print('   %d overlays, functions %s' % (len(MP.LIB_SITES), 'quick' if quick else 'all'))


def main(argv):'''
s = s.replace('def main(argv):', SECTION, 1)
open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
