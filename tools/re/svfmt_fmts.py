"""svfmt_fmts.py REGEX : distinct ASCII strings matching REGEX over all overlays, with the files holding them."""
import sys, re, os, glob, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rx = re.compile(sys.argv[1]); c = collections.defaultdict(list)
for f in [os.path.join(ROOT, 'extracted', '1ST_READ.BIN')] + sorted(glob.glob(os.path.join(ROOT, 'extracted', 'FLOW_PRG', '*.BIN'))):
    d = open(f, 'rb').read()
    for m in re.finditer(rb'[\x20-\x7e]{3,}', d):
        s = m.group().decode()
        if rx.search(s): c[s].append(os.path.basename(f)[:-4])
for s, fl in sorted(c.items(), key=lambda x: -len(x[1])): print(len(fl), repr(s), ' '.join(fl[:6]))
