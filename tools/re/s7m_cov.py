import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7m_lib as L
M = [('FLOW_PRG/ALLJINI.ZAR', t) for t in ('jini11.tbd#1', 'jini7.tbd#1', 'jini10.tbd#1', 'jini8.tbd#1', 'jini9.tbd#1', 'scsitei.tbd#0')]
M += [('FLOW_PRG/TWND1.ZAR', 'selb.tbd#0'), ('FLOW_PRG/TWND1F.ZAR', 'selb.tbd#0'), ('FLOW_PRG/TWND1.ZAR', 'glv.tbd#5'), ('ETC_DATA/CLUBHOUS.DAT', '#22')]
for s, t in M:
    cs = L.copies(s, t)
    miss = [c for c in cs if not os.path.exists(L.tex_path(*c))]
    print(s, t, len(cs), 'missing', miss)
