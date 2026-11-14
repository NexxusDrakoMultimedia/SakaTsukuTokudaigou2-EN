"""Are the TBD tables embedded in FLOW_PRG overlays referenced by ABSOLUTE pointers from the image itself?

    python -I -X utf8 tools/re/texinject/ovl_tbl_ptrs.py
For each overlay with embedded tables, load address from tools/textdb.py (load_image / refine_base, text-proven) and count
aligned words equal to  base + table_offset  (pointer to the table) and base + table_offset + record offset (pointer to a
record's data).  If nothing in the image points at a table, it is addressed some other way (e.g. computed from another
pointer): the answer matters for 'is relocation possible', not for same-size replacement."""
import os
import sys
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texinject as T  # noqa: E402
import textdb         # noqa: E402

ext = os.path.join(ROOT, 'extracted', 'FLOW_PRG')
tot_t = tot_hit = 0
for fn in sorted(os.listdir(ext)):
    if not fn.upper().endswith('.BIN'):
        continue
    d = open(os.path.join(ext, fn), 'rb').read()
    tabs = T.scan_tables(d, 4, 'embedded')
    if not tabs:
        continue
    try:
        img = textdb.load_image('FLOW_PRG/' + fn)
        base = img.base if hasattr(img, 'base') else img['base']
    except Exception as e:      # noqa: BLE001
        print('%-14s no base (%s)' % (fn, e))
        continue
    n = len(d) // 4
    words = set(struct.unpack('<%dI' % n, d[:n * 4]))
    hit = 0
    for t in tabs:
        if base + t.base in words:
            hit += 1
    tot_t += len(tabs)
    tot_hit += hit
    print('%-14s base=%#x tables=%-3d pointed-to-by-an-absolute-word=%d' % (fn, base, len(tabs), hit))
print('tables', tot_t, 'with an absolute pointer to the table start', tot_hit)
