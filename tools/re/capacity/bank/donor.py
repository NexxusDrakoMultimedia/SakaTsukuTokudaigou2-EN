"""Which disc files are named by 1ST_READ / overlays?  Search every ISO basename (and full path) as ASCII (case-sensitive and
case-insensitive) in 1ST_READ.BIN, all FLOW_PRG/*.BIN overlays, ATFIRST/*.BIN, 2_DP.BIN, IP.BIN, MAIGO/SG_DPLDR.
Prints for each root/DP-ish candidate the hits."""
import glob,os,re,sys,collections
files=[l.split('\t')[0] for l in open('extracted/_filelist.tsv',encoding='utf8').read().splitlines()]
srcs={}
srcs['1ST_READ.BIN']=open('extracted/1ST_READ.BIN','rb').read()
for p in sorted(glob.glob('extracted/FLOW_PRG/*.BIN')): srcs['FLOW_PRG/'+os.path.basename(p)]=open(p,'rb').read()
for n in ('HELP.BIN','TITLE.BIN','FACEMDUL.BIN'): srcs['ATFIRST/'+n]=open('extracted/ATFIRST/'+n,'rb').read()
for n in ('2_DP.BIN','IP.BIN','MAIGO.BIN','SG_DPLDR.BIN','MANATEE.DRV','NAMIHEI.DRV'): srcs[n]=open('extracted/'+n,'rb').read()
low={k:v.lower() for k,v in srcs.items()}
def hits(name):
    nl=name.lower().encode()
    return [k for k,v in low.items() if nl in v]
cands=[f for f in files if f.count('/')==1 and f.split('/')[1] in ('0GDTEX.PVR','2_DP.BIN','DP3.INI','FONT.BIN','MAIGO.BIN','MANATEE.DRV','NAMIHEI.DRV','SG_DPLDR.BIN','1ST_READ.BIN')]
for f in cands:
    b=f.split('/')[-1]
    print(f,'hits for',b,':',hits(b))
for d in ('DPETC','DPFONT','DPMODEL','DPSS','DPTEX','DPWWW','BCAST'):
    print('dir',d,'hits for dir name:',hits(d+'/')+hits('/'+d))
    fs=[f for f in files if f.startswith('/'+d+'/')]
    hh={}
    for f in fs:
        h=[x for x in hits(f.split('/')[-1]) if not x.startswith(('2_DP','MANATEE','NAMIHEI'))]
        if h: hh[f]=h
    print('  files',len(fs),'files named in the game (1ST_READ/overlays):',hh)
