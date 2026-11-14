import sys,os,collections,pickle
sys.path.insert(0,'tools')
import bzlib
A=pickle.load(open('tools/re/verify_gt/anom.pkl','rb'))
print(collections.Counter(a[0] for a in A if a[2].startswith('pvr')))
# all candidates anywhere (incl. inside covered), validity by hdr crc & decode
tot=ok=badcrc=nohc=decfail=0; nested=0; perfile=collections.Counter()
mixed=[]
seen={}
for dp,dn,fn in os.walk('extracted'):
  for f in fn:
    if f=='_filelist.tsv':continue
    p=os.path.join(dp,f); d=open(p,'rb').read()
    ms,_=bzlib.parse_archive(d)
    cov=[(m.offset,m.end_offset) for m in ms]
    for m in ms:
        key=(m.orig_size,m.crc16)
        seen.setdefault(key,set()).add(m.method)
    i=0
    while True:
        i=d.find(b'-',i)
        if i<0:break
        o=i-2; i+=1
        if o<0 or d[o+2:o+7] not in (b'-nc--',b'-bz--',b'-bzw-'):continue
        m=bzlib.parse_member(d,o)
        if not m: perfile['REJ '+p]+=1; continue
        if any(a<=o<b for a,b in cov): 
            if o not in [c[0] for c in cov]: nested+=1
            continue
        tot+=1
        if m.hdr_crc is None: nohc+=1
        elif not m.hdr_crc_ok: badcrc+=1
        try:
            pl=m.extract()
            ok+=1
        except Exception as e: decfail+=1
print('uncovered valid-parse',tot,'ok',ok,'badhdrcrc',badcrc,'nohc',nohc,'decfail',decfail,'nested inside covered',nested)
print('REJECTED raw-method-string candidates:',sum(v for k,v in perfile.items()))
print(perfile.most_common(10))
print('same (size,crc) w/ different methods:',[(k,v) for k,v in seen.items() if len(v)>1][:10], 'groups',len(seen))
print('--- rejected not 3/file')
for k,v in perfile.items():
    if v!=3: print(k,v)
print(len([1 for k,v in perfile.items() if v==3]))
# nested analysis: parse OK nested members inside nc members, with valid hdr crc and decode
nn=0;nok=0;bymeth=collections.Counter();files=collections.Counter()
for dp,dn,fn in os.walk('extracted'):
  for f in fn:
    if f=='_filelist.tsv':continue
    p=os.path.join(dp,f); d=open(p,'rb').read()
    ms,_=bzlib.parse_archive(d)
    for m in ms:
        inner=m.packed
        if m.method!='-nc--': continue
        # look for members inside stored payload
        for mm in bzlib.parse_archive(inner)[0]:
            nn+=1
            try: mm.extract(); nok+=1
            except Exception: pass
            files[p]+=1
print('nested archives at offset0 of stored members: members',nn,'ok',nok,files.most_common(5))
