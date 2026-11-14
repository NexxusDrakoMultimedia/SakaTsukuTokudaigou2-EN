"""s8ha: compare the align cave, font cave and width table of a disc's 1ST_READ.BIN with what fontpatch generates.
usage: s8ha_cavecheck.py PATH_TO_1ST_READ"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fontpatch as FP
k = open(sys.argv[1], 'rb').read()
ct = FP.placement()
al = FP.align_address()
ab = FP.align_bytes(al, ct[1])
print('align cave equal:', k[al - FP.IMG_BASE: al - FP.IMG_BASE + len(ab)] == ab, len(ab))
cb = FP.cave_bytes(ct, False, al)
print('font cave (align form) equal:', k[ct[0] - FP.IMG_BASE: ct[0] - FP.IMG_BASE + len(cb)] == cb)
print('table first 64:', k[ct[1] - FP.IMG_BASE: ct[1] - FP.IMG_BASE + 64].hex())
print('rest of the align reserve zero:', not any(k[al - FP.IMG_BASE + len(ab): al - FP.IMG_BASE + 0x100]))
print('symbols', {a: hex(b) for a, b in FP.align_symbols(al, ct[1]).items()})
