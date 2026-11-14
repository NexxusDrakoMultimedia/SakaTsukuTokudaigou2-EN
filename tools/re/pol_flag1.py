"""pol: show the town short forms of an overlay with a space / hyphen / dot.  python -I -X utf8 tools/re/pol_flag1.py DUMPDIR OVERLAY"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ovf_sim as OVF
first = open(os.path.join(OVF.ROOT, 'extracted', '1ST_READ.BIN'), 'rb').read()
comp = OVF.Composer(open(os.path.join(sys.argv[1], 'FLOW_PRG', sys.argv[2] + '.BIN'), 'rb').read(), first)
towns, _, pool = comp.tables()
print([(i + 1, t) for i, t in enumerate(towns) if any(c in t for c in b' -.')], len(pool))
