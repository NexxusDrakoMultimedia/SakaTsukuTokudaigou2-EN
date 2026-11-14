"""mn6_realcmp.py: are the `real` printf functions behind the library pool words the same code in every library overlay?  Read only."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import moneypatch as MP      # noqa: E402
import textdb                # noqa: E402

SITES = {
    'CHALMODE': [(0x78ac, 0x8c4d3cd4)], 'DRSHRANK': [(0x8b74, 0x8c4d63a4)], 'DRSISEKI': [(0x464c, 0x8c4d3740)],
    'DRSJAPAN': [(0x3adc, 0x8c4d2bd0)], 'DRSLIST': [(0xae8c, 0x8c4d9418)], 'DRSSRANK': [(0x9c94, 0x8c4d74c4)],
    'GETREP': [(0x94c0, 0x8c2e1130), (0x14468, 0x8c2e1130)], 'PL_EDIT': [(0x1175c, 0x8c4de424)], 'SELNAT': [(0xb59c, 0x8c2d9b28)],
}
ref = None
for name, lst in SITES.items():
    rel = 'FLOW_PRG/%s.BIN' % name
    d = MP.read_extracted(rel)
    base = textdb.load_image(rel).base
    sites = MP.find_sites(d, rel)
    for off, real in lst:
        got = int.from_bytes(d[off:off + 4], 'little')
        fo = real - base
        code = d[fo:fo + 0x42]
        masked = MP.PE.mask_bytes(code, 'pc+bsr')
        if ref is None:
            ref = masked
        print('%-9s pool %#x = %08x (%s) real@%#x same-as-first=%s sites=%s base=%#x' % (
            name, off, got, 'ok' if got == real else 'MISMATCH', fo, masked == ref, [(s['off'], s['variant']) for s in sites], base))
        if masked != ref:
            print('   ', code.hex())
            print('   ', ref.hex() if hasattr(ref, 'hex') else ref)
