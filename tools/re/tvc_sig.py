"""tvc_sig.py : print the TV card signature of extracted TV_EVENT.BIN and the assembled routine."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import moneypatch as M
d = M.read_extracted('FLOW_PRG/TV_EVENT.BIN')
print(M.tv_card_sig(d))
code, tail, items = M.tv_card_bytes(0x8c2d33c0)
for a, w, t in items:
    print('%08x %s %s' % (a, w.hex(), t))
print(len(code), tail.hex()[:16])
