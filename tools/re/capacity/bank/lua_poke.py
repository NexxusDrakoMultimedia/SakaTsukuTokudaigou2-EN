"""Emit a build/emu/cmd.lua body (live.lua bridge: poke/peek/dump/say) that redirects ONE overlay string to English text stored in a bank region,
without building a disc: it pokes the text at REGION_ADDR and rewrites the pointer word(s).
    python -I -X utf8 tools/re/capacity/bank/lua_poke.py FLOW_PRG/CLUBEDIT.BIN 0xHEXOFF 0x8c299400 "English text"
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import textdb
src, off, addr, text = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0), sys.argv[4]
img = textdb.load_image(src)
strs, ptrs, _ = textdb.extract_image(img)
s = {x.off: x for x in strs}[off]
b = textdb._en_bytes(text) + b'\0'
def lit(bs): return '"' + ''.join('\\%03d' % c for c in bs) + '"'
print('-- %s string at +%#x (JP: %r) pointer words %s, base %#x' % (src, off, s.raw[:24], [hex(img.base + w) for w in s.refs], img.base))
print('poke(0x%08x, %s)' % (addr, lit(b)))
for w in s.refs:
    print('poke(0x%08x, string.pack("<I4", 0x%08x))   -- pointer word at +%#x' % (img.base + w, addr, w))
print('say("redirected %s#%x to %#x")' % (src, off, addr))
