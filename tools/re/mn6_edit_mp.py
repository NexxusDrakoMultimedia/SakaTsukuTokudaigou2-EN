"""mn6_edit_mp.py: one-off, idempotent source edit of tools/moneypatch.py (wires the number-library wrapper into overlay_edits / patch_1st_read /
make_patches).  Checks every old text exactly once; refuses when already applied."""
import os
import sys

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'moneypatch.py')
s = open(P, encoding='utf-8').read()

EDITS = [
    ("def overlay_edits(es, d, name='', addr=CAVE_ADDR, variants='A', decimal_d=True, style=DEFAULT_STYLE, compact_token=False, panel_compact=True):",
     "def overlay_edits(es, d, name='', addr=CAVE_ADDR, variants='A', decimal_d=True, style=DEFAULT_STYLE, compact_token=False, panel_compact=True,\n"
     "                  lib=True):"),
    ("    compact_token (jp only): `%M` in the expander.  panel_compact (jp only): the 12 byte scout info panel field passes the compact flag.\"\"\"",
     "    compact_token (jp only): `%M` in the expander.  panel_compact (jp only): the 12 byte scout info panel field passes the compact flag.\n"
     "    lib (jp only, default cave address only): the number-library wrapper of LIB_SITES overlays (stub + literal-pool word).\"\"\""),
    ("            if compact_token:\n                expander_edits(es, d, r[0], name)\n    return sites\n",
     "            if compact_token:\n                expander_edits(es, d, r[0], name)\n"
     "    if lib and style == 'jp' and addr == CAVE_ADDR and name in LIB_SITES:\n"
     "        lib_edits(es, d, name, sites)\n    return sites\n"),
    ("def patch_overlay(d, name='', addr=CAVE_ADDR, variants='A', decimal_d=True, style=DEFAULT_STYLE, compact_token=False, panel_compact=True):",
     "def patch_overlay(d, name='', addr=CAVE_ADDR, variants='A', decimal_d=True, style=DEFAULT_STYLE, compact_token=False, panel_compact=True,\n"
     "                  lib=True):"),
    ("    sites = overlay_edits(es, d, name, addr, variants, decimal_d, style, compact_token, panel_compact)\n    if not sites:",
     "    sites = overlay_edits(es, d, name, addr, variants, decimal_d, style, compact_token, panel_compact, lib)\n    if not sites:"),
    ("def patch_1st_read(k, addr=CAVE_ADDR, style=DEFAULT_STYLE):\n    \"\"\"write the cave into the zero reserve of 1ST_READ.BIN; refuses unless the whole reserve is zero.\"\"\"",
     "def patch_1st_read(k, addr=CAVE_ADDR, style=DEFAULT_STYLE, lib=True):\n"
     "    \"\"\"write the cave (and, jp style at the default address, the number-library wrapper) into the zero reserve of 1ST_READ.BIN; refuses unless the\n"
     "    whole reserve is zero.\"\"\""),
    ("    es.add('money.cave', PE.IMG_NAME, addr - IMG_BASE, cave + bytes(RESERVE - len(cave)), expect=PE.ZERO)\n    try:\n        return es.apply({PE.IMG_NAME: k})[PE.IMG_NAME]",
     "    es.add('money.cave', PE.IMG_NAME, addr - IMG_BASE, cave + bytes(RESERVE - len(cave)), expect=PE.ZERO)\n"
     "    if lib and style == 'jp' and addr == CAVE_ADDR:\n"
     "        es.add('money.lib', PE.IMG_NAME, LIB_ADDR - IMG_BASE, lib_bytes(LIB_ADDR, addr) + bytes(LIB_RESERVE - len(lib_bytes(LIB_ADDR, addr))), expect=PE.ZERO)\n"
     "    try:\n        return es.apply({PE.IMG_NAME: k})[PE.IMG_NAME]"),
    ("                 compact_token=False, panel_compact=True):\n    \"\"\"The whole feature as a function.",
     "                 compact_token=False, panel_compact=True, lib=True):\n    \"\"\"The whole feature as a function."),
    ("    out['/1ST_READ.BIN'] = patch_1st_read(cur('1ST_READ.BIN'), addr, style)",
     "    out['/1ST_READ.BIN'] = patch_1st_read(cur('1ST_READ.BIN'), addr, style, lib)"),
    ("        nd, sites = patch_overlay(d, rel, addr, variants, decimal_d, style, compact_token, panel_compact)",
     "        nd, sites = patch_overlay(d, rel, addr, variants, decimal_d, style, compact_token, panel_compact, lib)"),
]
for old, new in EDITS:
    if s.count(old) != 1:
        sys.exit('edit not applicable (%d matches): %r' % (s.count(old), old[:70]))
    s = s.replace(old, new)

TABLE = '''

# the library overlays: file -> [(file offset of the literal-pool word holding `real`, value)] (mn6_libscan.py; every pool word is used only by the
# money library functions or by callers whose formats pass through unchanged).  `real` is the same code in all of them (mn6_realcmp.py).
LIB_SITES = {
    'FLOW_PRG/CHALMODE.BIN': [(0x78AC, 0x8C4D3CD4)],
    'FLOW_PRG/DRSHRANK.BIN': [(0x8B74, 0x8C4D63A4)],
    'FLOW_PRG/DRSISEKI.BIN': [(0x464C, 0x8C4D3740)],
    'FLOW_PRG/DRSJAPAN.BIN': [(0x3ADC, 0x8C4D2BD0)],
    'FLOW_PRG/DRSLIST.BIN': [(0xAE8C, 0x8C4D9418)],
    'FLOW_PRG/DRSSRANK.BIN': [(0x9C94, 0x8C4D74C4)],
    'FLOW_PRG/GETREP.BIN': [(0x94C0, 0x8C2E1130), (0x14468, 0x8C2E1130)],
    'FLOW_PRG/PL_EDIT.BIN': [(0x1175C, 0x8C4DE424)],
    'FLOW_PRG/SELNAT.BIN': [(0xB59C, 0x8C2D9B28)],
}


def lib_edits(es, d, name, sites):
    """stub (in the dead body of the money function copy) + the literal-pool words of `real`"""
    if not sites or sites[0].get('base') is None:
        raise MoneyPatchError('%s: number library: no money function / load address to host the stub' % name)
    x = sites[0]
    stub_va = x['base'] + x['off'] + LIB_STUB_REL
    real = LIB_SITES[name][0][1]
    lo = x['off'] + LIB_STUB_REL
    es.add('money.libstub', name, lo, lib_stub(real), expect=d[lo:lo + 20])
    for off, val in LIB_SITES[name]:
        if struct.unpack_from('<I', d, off)[0] != val:
            raise MoneyPatchError('%s: number library pool word at %#x is %#x, expected %#x' % (name, off, struct.unpack_from('<I', d, off)[0], val))
        es.add('money.lib', name, off, struct.pack('<I', stub_va), expect=struct.pack('<I', val))
'''
anchor = "\n\ndef overlay_edits(es, d, name=''"
assert s.count(anchor) == 1
s = s.replace(anchor, TABLE + anchor)
open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
