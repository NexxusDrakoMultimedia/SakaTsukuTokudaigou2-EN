import sys, os, struct, re, collections
sys.path.insert(0,'tools')
import bzlib
# independent CRC16/X25
T=[]
for i in range(256):
    c=i
    for _ in range(8): c=(c>>1)^0x8408 if c&1 else c>>1
    T.append(c)
def x25(d):
    c=0xFFFF
    for b in d: c=(c>>8)^T[(c^b)&0xFF]
    return c^0xFFFF
assert x25(b'123456789')==0x906E
root='extracted'
files=[]
for dp,dn,fn in os.walk(root):
    for f in fn:
        p=os.path.join(dp,f)
        if f in('_filelist.tsv',): continue
        files.append(p)
files.sort()
st=collections.Counter(); anomalies=[]
hdrlens=collections.Counter(); bypath={}
bycontent=collections.defaultdict(set)
METH=[b'-nc--',b'-bz--',b'-bzw-']
pat=re.compile(rb'-(?:nc|bz|bzw)--',re.S)
for p in files:
    if os.path.basename(p)=='BCAST.BIN': st['skipped_bcast']+=1
    d=open(p,'rb').read()
    ms,tail=bzlib.parse_archive(d)
    # independent walk: own parse of hdr at 0 only
    covered=[]
    for m in ms:
        st['members']+=1; st['m_'+m.method]+=1; hdrlens[m.hdrlen]+=1
        covered.append((m.offset,m.end_offset))
        try: out=m.extract(verify=False)
        except Exception as e:
            anomalies.append((p,m.offset,'decode err %s'%e)); continue
        if len(out)!=m.orig_size: st['len_mismatch']+=1; anomalies.append((p,m.offset,'len %d!=%d'%(len(out),m.orig_size)))
        if x25(out)!=m.crc16: st['crc_mismatch']+=1; anomalies.append((p,m.offset,'crc'))
        else: st['crc_ok']+=1
        if m.hdr_crc is None: st['no_hdrcrc']+=1
        elif not m.hdr_crc_ok: st['hdrcrc_bad']+=1
        if m.name and m.name.lower().endswith('.pvr'):
            st['pvr']+=1
            if not (out[:4] in(b'GBIX',b'PVRT')): st['pvr_badmagic']+=1; anomalies.append((p,m.offset,'pvr magic %r'%out[:8]))
        bycontent[(len(out),x25(out),hash(out))].add(m.method)
        key=(len(out),hash(out))
        bypath.setdefault(key,set()).add(m.method)
        # gaps between members
    # gaps
    prev=0
    for a,b in covered:
        gap=d[prev:a]
        if gap.strip(b'\0'): st['nonzero_gap']+=1; anomalies.append((p,prev,'nonzero gap %d bytes before member'%len(gap)))
        prev=b
    if ms:
        st['container']+=1
        rest=d[prev:]
        if rest.strip(b'\0'):
            st['tail_nonzero']+=1
            anomalies.append((p,prev,'tail %d bytes (file %d) nz=%d'%(len(rest),len(d),len(rest.lstrip(b'\0')))))
    else:
        st['noncontainer']+=1
        # check for header-looking at 0 with method string
        if d[2:7] in METH: st['noncont_with_method_at2']+=1; anomalies.append((p,0,'method at 2 but unparsed hdrlen=%d'%struct.unpack_from('<H',d,0)[0]))
    # scan for method strings anywhere not covered
    for mt in pat.finditer(d):
        o=mt.start()-2
        if o<0: continue
        if any(a<=o<b for a,b in covered): continue
        hl=struct.unpack_from('<H',d,o)[0]
        if 28<=hl<=512 and hl%2==0 and o+hl<=len(d):
            m2=bzlib.parse_member(d,o)
            st['uncovered_candidates']+=1
            anomalies.append((p,o,'uncovered cand hdrlen=%d parsed=%s'%(hl,'OK' if m2 else 'REJECTED')))
print(dict(st)); print('hdrlens',dict(hdrlens))
mixed=sum(1 for k,v in bypath.items() if len(v)>1)
print('content groups',len(bypath),'with >1 method',mixed)
# nc vs bz same name/size dupes
print('anomalies',len(anomalies))
c=collections.Counter(a[2].split()[0]+' '+a[2].split()[1] if ' ' in a[2] else a[2] for a in anomalies)
print(c.most_common(20))
import pickle; pickle.dump(anomalies,open('tools/re/verify_gt/anom.pkl','wb'))
for a in anomalies[:40]: print(a)
