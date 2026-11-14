"""s7t: find a hex byte signature in all overlays/executables. usage: sigscan HEX [HEX...]"""
import glob, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + '/extracted'
sigs = [bytes.fromhex(a) for a in sys.argv[1:]]
files = glob.glob(os.path.join(ROOT, 'FLOW_PRG', '*.BIN')) + [os.path.join(ROOT, '1ST_READ.BIN')] + glob.glob(os.path.join(ROOT, 'ATFIRST', '*.BIN'))
for f in sorted(files):
    d = open(f, 'rb').read()
    for s in sigs:
        o = d.find(s)
        while o >= 0:
            print(os.path.basename(f), hex(o), s.hex()[:16])
            o = d.find(s, o + 1)
