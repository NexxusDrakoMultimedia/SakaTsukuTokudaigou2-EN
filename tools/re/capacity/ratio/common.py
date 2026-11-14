import sys,json,glob,os,re,collections
sys.path.insert(0,'tools')
import textdb
TOK=re.compile(r'@[A-Z]/|@|#[a-z0-9]+#|<[0-9A-F]{2}>|%[0-9]*[sdDm]|=[A-Z]/|=')
def load():
    rows=[]
    for f in sorted(glob.glob('translation/*.jsonl')):
        n=os.path.basename(f)[:-6]
        for l in open(f,encoding='utf8'):
            r=json.loads(l); r['file']=n; rows.append(r)
    return rows
def jb(s):  # JP bytes incl NUL
    return len(textdb.encode_text(s))+1
def eb(s):
    return len(textdb.encode_text(s))+1
def visible(s):
    return TOK.sub('',s)
def nchars(s):
    return len(visible(s).replace('\n',''))

KANJI=re.compile(r'^[\u4e00-\u9fff\u3005\u30f6]+$')
PLACE_SUF='市区郡町村県府道島'
def is_ov(r): return r['file'].startswith(('FLOW_PRG','ATFIRST'))
def movable(r):
    c=r['ctx']
    return (not r.get('orphan')) and 'stride-table' not in c and 'interior-ptrs' not in c
def group(r):
    f=r['file'].split('__',1)[1].replace('.BIN','')
    if f=='HELP': return 'HELP'
    if f=='MEETING': return 'MEETING'
    if f in('NEWS','NEWS_ED'): return 'NEWS'
    if f.startswith('EVENT'): return 'EVENT'
    if f=='TRAINING': return 'TRAINING'
    return 'OTHER'
NUMRE=re.compile(r'[0-9\uff10-\uff19]|%[0-9]*[dDm]')
def category(r):
    ja=r['ja']; v=visible(ja); n=len(v.replace('\n',''))
    g=group(r)
    if g=='HELP' and n>=8: return 'help'
    if n>=12 or (n>=10 and '\n' in ja):
        return {'MEETING':'prose_meeting','NEWS':'prose_news','EVENT':'prose_event','TRAINING':'prose_training'}.get(g,'prose_other' if g!='HELP' else 'help')
    # short
    vs=v.strip().replace('\u3000',' ')
    if re.match(r'^[\u4e00-\u9fff\u3005]{1,4} [\u4e00-\u9fff\u3005\u3041-\u30ff]{1,4}$',vs) and 'tbl' in (r['ctx']+'tbl') and (r.get('orphan') or len(vs)>=4):
        return 'name'
    if NUMRE.search(ja) : return 'numunit'
    if KANJI.match(vs) and 2<=len(vs)<=7 and (vs[-1] in PLACE_SUF or r.get('orphan') or 'tbl' in r['ctx']) and vs[-1] in PLACE_SUF: return 'place'
    return 'label'
