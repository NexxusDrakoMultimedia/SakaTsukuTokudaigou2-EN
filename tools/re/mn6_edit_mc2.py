"""mn6_edit_mc2.py: one-off, idempotent edit of tools/moneycheck.py for the numeric wrapper (libn) of mn6."""
import os
import sys

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'moneycheck.py')
s = open(P, encoding='utf-8').read()
if 'check_libn' in s:
    sys.exit('already applied')
EDITS = [
    ("    allowed = set(range(o, o + len(cave))) | (set(range(lo_, lo_ + len(libb))) if lo_ is not None else set())\n",
     "    allowed = set(range(o, o + len(cave))) | (set(range(lo_, lo_ + len(libb))) if lo_ is not None else set())\n"
     "    if lo_ is not None:\n"
     "        ln_ = MP.LIBN_ADDR - MP.IMG_BASE\n"
     "        allowed |= set(range(ln_, ln_ + len(MP.libn_bytes())))\n"),
    ("    check(len(k1) == len(k0) and set(diff) <= allowed and k1[o:o + len(cave)] == cave and (lo_ is None or k1[lo_:lo_ + len(libb)] == libb),\n"
     "          '1ST_READ.BIN differs only inside the cave (and the number-library wrapper)')",
     "    check(len(k1) == len(k0) and set(diff) <= allowed and k1[o:o + len(cave)] == cave and (lo_ is None or k1[lo_:lo_ + len(libb)] == libb),\n"
     "          '1ST_READ.BIN differs only inside the cave (and the number-library wrappers)')"),
    ("                for po, _ in MP.LIB_SITES[rel] + ([MP.LIB_ZERO[rel]] if rel in MP.LIB_ZERO else []):\n"
     "                    want |= set(range(po, po + 4))",
     "                for po, _ in MP.LIB_SITES[rel] + ([MP.LIB_ZERO[rel]] if rel in MP.LIB_ZERO else []):\n"
     "                    want |= set(range(po, po + 4))\n"
     "            if STYLE == 'jp' and rel in MP.LIBN_SITES:              # the numeric-format stub (money function + 32, 24 bytes), pool words, digit counter\n"
     "                want |= set(range(s['off'] + MP.LIBN_STUB_REL, s['off'] + MP.LIBN_STUB_REL + 24))\n"
     "                sp = MP.LIBN_SITES[rel]\n"
     "                for po, _ in sp['pools'] + ([sp['counter']] if 'counter' in sp else []):\n"
     "                    want |= set(range(po, po + 4))\n"
     "            if STYLE == 'jp' and rel in MP.LIBN_GAME:               # GAME's money text function: the 12 byte hook\n"
     "                want |= set(range(MP.LIBN_GAME[rel]['off'], MP.LIBN_GAME[rel]['off'] + MP.HOOK_LEN))"),
    ("    bad = LS.check_functions(quick)\n    check(bad == 0, 'library functions F1 / F2a through the wrapper (%d failures)' % bad)\n",
     "    bad = LS.check_functions(quick)\n    check(bad == 0, 'library functions F1 / F2a through the wrapper (%d failures)' % bad)\n"
     "    check_libn(LS, quick)\n"),
]
for old, new in EDITS:
    if s.count(old) != 1:
        sys.exit('edit not applicable (%d matches): %r' % (s.count(old), old[:70]))
    s = s.replace(old, new)
s = s.replace('def check_lib(quick):', '''def check_libn(LS, quick):
    """9b: the numeric-format wrapper (libn): G_INCOME / ABROAD FIRE PLNUMSET SELNAT / INVEST formats through the patched overlays, GAME's text function."""
    for rel in MP.LIBN_SITES:
        bad, L = LS.check_libn(rel, quick)
        check(bad == 0, '%s: numeric wrapper (%d failures)' % (rel, bad))
    bad = LS.check_game(quick)
    check(bad == 0, 'GAME money text function through n_gm (%d failures)' % bad)
    print('   %d numeric overlays + GAME' % len(MP.LIBN_SITES))


def check_lib(quick):''', 1)
open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
