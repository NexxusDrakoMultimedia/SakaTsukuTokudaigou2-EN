"""mn6_edit_mp3.py: one-off, idempotent splice of the numeric-format wrapper (tools/re/mn6_libn_src.txt, mn6_libn_py.txt) into tools/moneypatch.py and its
wiring into overlay_edits / patch_1st_read."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(os.path.dirname(HERE), 'moneypatch.py')
s = open(P, encoding='utf-8').read()
if 'LIBN_SRC' in s:
    sys.exit('already applied')
src = open(os.path.join(HERE, 'mn6_libn_src.txt'), encoding='utf-8').read().rstrip('\n')
GM = '''; ---- entry n_gm: GAME.BIN's own money text function FUN(dst = r4, V = r5 in man): the jp text + NUL
n_gm:   sts.l pr,@-r15
        mov.l r8,@-r15
        mov   r4,r8
        mov   #0,r6
        mov.l @(n_mny,pc),r0
        jsr   @r0
        nop
        add   r0,r8
        mov   #0,r0
        mov.b r0,@r8
        mov.l @r15+,r8
        lds.l @r15+,pr
        rts
        nop
'''
marker = '; ---- n_core:'
assert src.count(marker) == 1
src = src.replace(marker, GM + marker)
py = open(os.path.join(HERE, 'mn6_libn_py.txt'), encoding='utf-8').read().replace('@SRC@', src)
anchor = '\n# ------------------------------------------------------------------------------------------------ sites\nFN_LEN = 206'
assert s.count(anchor) == 1
s = s.replace(anchor, py + anchor)

EDITS = [
    ("                  lib=True):\n    \"\"\"add the hook",
     "                  lib=True, libn=True):\n    \"\"\"add the hook"),
    ("    if lib and style == 'jp' and addr == CAVE_ADDR and name in LIB_SITES:\n        lib_edits(es, d, name, sites)\n",
     "    if lib and style == 'jp' and addr == CAVE_ADDR and name in LIB_SITES:\n        lib_edits(es, d, name, sites)\n"
     "    if libn and style == 'jp' and addr == CAVE_ADDR and (name in LIBN_SITES or name in LIBN_GAME):\n        libn_edits(es, d, name, sites)\n"),
    ("                  lib=True):\n    \"\"\"returns (new bytes, sites).",
     "                  lib=True, libn=True):\n    \"\"\"returns (new bytes, sites)."),
    ("    sites = overlay_edits(es, d, name, addr, variants, decimal_d, style, compact_token, panel_compact, lib)\n",
     "    sites = overlay_edits(es, d, name, addr, variants, decimal_d, style, compact_token, panel_compact, lib, libn)\n"),
    ("def patch_1st_read(k, addr=CAVE_ADDR, style=DEFAULT_STYLE, lib=True):",
     "def patch_1st_read(k, addr=CAVE_ADDR, style=DEFAULT_STYLE, lib=True, libn=True):"),
    ("    try:\n        return es.apply({PE.IMG_NAME: k})[PE.IMG_NAME]\n    except PE.EngineError as e:\n        raise MoneyPatchError(str(e))\n\n\n# ----",
     "    if libn and style == 'jp' and addr == CAVE_ADDR:\n"
     "        ln = libn_bytes(LIBN_ADDR, addr)\n"
     "        es.add('money.libn', PE.IMG_NAME, LIBN_ADDR - IMG_BASE, ln + bytes(LIBN_RESERVE - len(ln)), expect=PE.ZERO)\n"
     "    try:\n        return es.apply({PE.IMG_NAME: k})[PE.IMG_NAME]\n    except PE.EngineError as e:\n        raise MoneyPatchError(str(e))\n\n\n# ----"),
    ("                 compact_token=False, panel_compact=True, lib=True):", "                 compact_token=False, panel_compact=True, lib=True, libn=True):"),
    ("    out['/1ST_READ.BIN'] = patch_1st_read(cur('1ST_READ.BIN'), addr, style, lib)",
     "    out['/1ST_READ.BIN'] = patch_1st_read(cur('1ST_READ.BIN'), addr, style, lib, libn)"),
    ("        nd, sites = patch_overlay(d, rel, addr, variants, decimal_d, style, compact_token, panel_compact, lib)",
     "        nd, sites = patch_overlay(d, rel, addr, variants, decimal_d, style, compact_token, panel_compact, lib, libn)"),
]
for old, new in EDITS:
    if s.count(old) != 1:
        sys.exit('edit not applicable (%d matches): %r' % (s.count(old), old[:80]))
    s = s.replace(old, new)
open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
