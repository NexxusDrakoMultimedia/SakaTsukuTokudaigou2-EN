"""fw_chopcheck.py : verify, for every overlay that carries the two Japanese-suffix choppers, the exact bytes of the `add #-2` instruction
(read-only; the study's patch catalogue).
 (1) town short-name helper (Illegal townID): 20 copies, instruction `add #-2,r5` = bytes fe 75 at signature offset + 0x54
 (2) `#to#` expander branch: 16 copies,        instruction `add #-2,r0` = bytes fe 70 at signature offset + 0x54
The signature offsets are the first-word matches of tools/re/fw_sig.py for the HOMETOWN.BIN originals (10648 and 14e1a)."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def sig(start, length):
    out = subprocess.run([sys.executable, '-I', '-X', 'utf8', os.path.join(HERE, 'fw_sig.py'), 'extracted/FLOW_PRG/HOMETOWN.BIN', start, length],
                         capture_output=True, text=True).stdout
    res = []
    for ln in out.splitlines():
        if ln.startswith('files'):
            continue
        name, n, offs = ln.split(' ', 2)
        res.append((name, eval(offs)))
    return res


for label, start, length, delta, want in (('town-short helper', '10648', '0x60', 0x54, b'\xfe\x75'),
                                         ('#to# expander', '14e1a', '0x28', 0x54, b'\xfe\x70')):
    print('==', label)
    ok = 0
    rows = sig(start, length)
    for name, offs in rows:
        d = open(os.path.join('extracted', name), 'rb').read()
        for o in offs:
            a = int(o, 16) + delta
            good = d[a:a + 2] == want
            ok += good
            print('  %-24s sig@%s patch_file_off=%#x bytes=%s %s' % (name, o, a, d[a:a + 2].hex(), 'OK' if good else 'MISMATCH'))
    print('  ->', ok, 'of', sum(len(o) for _, o in rows), 'match', want.hex())
