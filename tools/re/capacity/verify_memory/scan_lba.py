# Does any code-bearing file contain a literal equal to a file's LBA (or LBA+150)? (absolute-LBA reads would break relocation)
import struct,glob,os,collections
fl=[l.rstrip('\r\n').split('\t') for l in open('extracted/_filelist.tsv',encoding='utf8')]
fl=[(n,int(a),int(s)) for n,a,s in fl]
lbas={}
for n,a,s in fl:
    for v,k in ((a,'lba'),(a+150,'lba+150')): lbas.setdefault(v,[]).append((n,k))
code=['extracted/1ST_READ.BIN','extracted/IP.BIN']+glob.glob('extracted/FLOW_PRG/*.BIN')+glob.glob('extracted/ATFIRST/*.BIN')+glob.glob('extracted/TRAINING/*.BIN')+glob.glob('extracted/NEWS/*.BIN')+glob.glob('extracted/EVENT/*.BIN')+glob.glob('extracted/GAME/*.BIN')+glob.glob('extracted/GAME2/*.BIN')
tot=collections.Counter()
for p in code:
    if not os.path.isfile(p): continue
    b=open(p,'rb').read(); n=len(b)//4
    ws=struct.unpack_from('<%dI'%n,b,0)
    for i,w in enumerate(ws):
        if w in lbas and 40000<w<600000:
            tot[p]+=1
            if tot[p]<=3: print(p,hex(i*4),w,lbas[w])
print('files with hits:',len(tot),'total hits',sum(tot.values()),'of',len(code),'files scanned')
print('1ST_READ hits:',tot['extracted/1ST_READ.BIN'] if 'extracted/1ST_READ.BIN' in tot else 0)
