"""Option 1A (inline table lookup, no cave) check: decode with capstone for all sites, execute on MEETING/COMM/CSAVE3.
python -I -X utf8 tools/re/font/test_inline.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fontpatch as FP
sites = FP.scan_all()
for s in sites:
    A, code, lst, size = FP.hook_adv_inline(s)
    for a, bb, t in lst:
        if len(bb) == 2:
            assert FP.capstone_check(a, bb)[0] == t, (s['name'], t)
print('inline decode ok for', len(sites), 'sites')
for s in sites:
    if s['name'] not in ('MEETING.BIN', 'COMM.BIN', 'CSAVE3.BIN') or 'ATFIRST' in s['iso']:
        continue
    d = open(os.path.join(FP.ROOT, 'extracted', s['iso']), 'rb').read()
    A, code, lst, size = FP.hook_adv_inline(s)
    nd = bytearray(d)
    nd[s['adv_off']:s['adv_off'] + size] = code
    for kind in ('prop', 'all12'):
        tbl = FP.table_vec(kind)
        for vec in FP.test_vectors():
            for W, Aw, fl in [(20, 24, 1), (13, 24, 0)]:
                kw = dict(W=W, A=Aw, flag=fl, x0=20, y0=240, lh=24)
                got = FP.run_layout(bytes(nd), s['base'], s, vec, extra=[(FP.TABLE, tbl)], **kw)
                exp = FP.new_model(vec, table=tbl, wrap=False, adv=True, **kw) if kind == 'prop' else FP.orig_model(vec, **kw)
                assert got == exp, (s['name'], kind, W, Aw, fl)
    print('inline sim ok', s['name'], 'bytes', code.hex())
