"""Per-overlay tail capacity (route d).  From survey_overlays.tsv (_end) and the slot table (1 MB slots 0x8c2d0000..0x8c9d0000, 0x8cad0000/0x90000,
0x8cb60000/0x40000, 0x8cba0000/0x1bc000).  heap_now = end of the slot containing _end-1 minus _end (the allocator arena of the overlay is
[_end, slot end); PROVEN formula in docs/text-engine.md s6, NOT checked against other simultaneously loaded overlays).
need = relocatable overflow bytes at r=1.5 after removing the strings a shared bank would hold (>=5 overlays)."""
import csv,sys,json,glob,os,math,collections
sys.path.insert(0,'tools')
import textdb
slots=[(0x8c2b0000,0x20000),(0x8c2d0000,0x100000),(0x8c3d0000,0x100000),(0x8c4d0000,0x100000),(0x8c5d0000,0x100000),(0x8c6d0000,0x100000),(0x8c7d0000,0x100000),(0x8c8d0000,0x100000),(0x8c9d0000,0x100000),(0x8cad0000,0x90000),(0x8cb60000,0x40000),(0x8cba0000,0x1bc000)]
def slotend(a):
    for b,s in slots:
        if b<=a<b+s: return b+s
    return None
rows={r['overlay']:r for r in csv.DictReader(open('tools/re/textengine/survey_overlays.tsv'),delimiter='\t')}
# need per overlay (r=1.5), shared >=5 overlays removed
g=collections.defaultdict(set)
items=[]
for p in sorted(glob.glob('translation/FLOW_PRG__*.jsonl'))+sorted(glob.glob('translation/ATFIRST__*.jsonl')):
    src=os.path.basename(p)[:-6].split('__')[1]
    for l in open(p,encoding='utf8'):
        r=json.loads(l); ctx=r.get('ctx') or ''
        if not r.get('refs') or 'stride-table' in ctx or 'interior-ptrs' in ctx: continue
        eb=len(textdb.encode_text(r['ja'])); en=math.ceil(1.5*eb)+1
        if en<=(r['max_bytes'] or 0): continue
        g[r['ja']].add(src); items.append((src,r['ja'],en))
need=collections.Counter(); need_sh=collections.Counter()
for src,ja,en in items:
    need[src]+=en
    if len(g[ja])<5: need_sh[src]+=en
print('overlay      class   file     _end        bss   heap_now  slots  need(all) need(after shared>=5)  fits_tail(no-bss: heap_now - need)')
tot_heap=0
for k in sorted(rows,key=lambda k:-need[k]):
    r=rows[k]
    if r['_end'] in ('','-') : continue
    try: end=int(r['_end'],16)
    except: continue
    size=int(r['size']); base=int(r['base'],16)
    se=slotend(end-1) 
    heap=(se-end) if se else -1
    print('%-12s %-8s %8d %08x %8s %9d  %s %9d %9d   %s'%(k[:-4],r['class'].split('(')[0],size,end,r['bss_bytes'],heap,'%x'%se if se else '?',need[k],need_sh[k],'OK' if heap>=need_sh[k] else 'TIGHT'))
