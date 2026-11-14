"""mn6_edit_sim.py: one-off edit of tools/re/mn6_libsim.py: DISC hook (read the overlays and 1ST_READ.BIN of a BUILT disc instead of patching extracted/)."""
import os
import sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mn6_libsim.py')
s = open(P, encoding='utf-8').read()
if 'DISC = None' in s:
    sys.exit('already applied')
s = s.replace("TOKEN = 0x12345678\n", "TOKEN = 0x12345678\nDISC = None            # callable rel -> bytes of a BUILT disc (mn6_discsim.py): the overlays and 1ST_READ.BIN are read from it instead of patching extracted/\n", 1)
old1 = "        d = MP.read_extracted(rel)\n        self.nd, sites = MP.patch_overlay(d, rel)\n        self.site = sites[0]\n"
new1 = ("        d = MP.read_extracted(rel)\n        if DISC:\n            self.nd, sites = DISC(rel), [dict(off=MP.find_sites(d, rel)[0]['off'])]\n"
        "        else:\n            self.nd, sites = MP.patch_overlay(d, rel)\n        self.site = sites[0]\n")
assert s.count(old1) == 2, s.count(old1)
s = s.replace(old1, new1)
old2 = "        k = MP.read_extracted('1ST_READ.BIN')\n        k1 = MP.patch_1st_read(k)\n"
new2 = "        k1 = DISC('1ST_READ.BIN') if DISC else MP.patch_1st_read(MP.read_extracted('1ST_READ.BIN'))\n"
assert s.count(old2) == 1
s = s.replace(old2, new2)
old3 = "        k1 = MP.patch_1st_read(MP.read_extracted('1ST_READ.BIN'))\n        self.m = FMach()\n"
new3 = "        k1 = DISC('1ST_READ.BIN') if DISC else MP.patch_1st_read(MP.read_extracted('1ST_READ.BIN'))\n        self.m = FMach()\n"
assert s.count(old3) == 1
s = s.replace(old3, new3)
s = s.replace("        if english:\n            import mn6_db", "        if english and not DISC:\n            import mn6_db", 1)
open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
