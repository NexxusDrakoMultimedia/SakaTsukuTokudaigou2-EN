"""ar6_groups: write build/art/groups_v2.json (second art inventory): ids / copies / wording of everything repainted by ar6.
Banner ids come from tools/re/ar6_banner.py WORDS; the other groups are listed by installed file (translation/textures path)."""
import os, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import art7_lib as L

src = open(os.path.join(HERE, 'ar6_banner.py'), encoding='utf8').read()
ns = {}
exec(compile('WORDS = ' + src.split('WORDS = ', 1)[1].split('\nTEXT_STYLE')[0], 'w', 'exec'), ns)
WORDS = ns['WORDS']


def ban(i, w):
    try:
        s, t, d = L.resolve(i)
        cps = L.dups(s, t)
        return {'id': i, 'source': s, 'tid': t, 'size': '%sx%s' % (d['width'], d['height']), 'copies': len(cps), 'wording': w}
    except Exception as e:
        return {'id': i, 'wording': w, 'note': str(e)[:80]}


chg = subprocess.run([sys.executable, '-I', '-X', 'utf8', os.path.join(HERE, 'ar6_changed.py')], capture_output=True, text=True).stdout.split('\n')
files = [l.split(' ', 1)[1] for l in chg if l.strip()]


def pick(*subs):
    return [f for f in files if any(s in f for s in subs)]


groups = [
    {'name': 'A EVENT title banners (256x32 tag plates, rebuilt to the text width)', 'script': 'tools/re/ar6_banner.py',
     'ids': [ban(i, w) for i, w in sorted(WORDS.items())]},
    {'name': 'B Schedule cell words OFF / ??? / TBD / Overseas Camp (sweep id 10817)', 'script': 'tools/re/ar6_sched.py',
     'files': ['GAME/ALLLOGOS.BIN/[59]', 'GAME/BINDLOGO.BIN/[73]'], 'wording': {'未定': 'TBD', '海外キャンプ': 'Overseas Camp'}},
    {'name': 'C TV station headings (Decided / Retained / Promoted / Demoted) and TV_E1..E6 titles', 'script': 'tools/re/ar6_tvedit.py',
     'files': pick('TV_EVENT')},
    {'name': 'D Header unit cells Yr / Mo / Wk with left padding (BAR copies), 1st / 2nd', 'script': 'tools/re/ar6_hdrspec.py + art1_spec',
     'files': pick('BAR.TBD', 'LOADBAR', 'YOUTH', 'TRAINING.TBD', 'TOWNSEL')},
    {'name': 'E Money units lower case (oku, man) in sprites and plates', 'script': 'art1_gen / art1_gen2 / art5 specs',
     'files': pick('PLATE.ZAR', 'MON_INST', 'INVEST', 'LOCAL.ZAR', 'DRSSRANK', 'SPT_CLUB', 'ESTABLIS', 'TOWNSEL', 'LOADBAR')},
    {'name': 'F Office personnel / town menu / staff list / ALLJINI, TWND, STAFFLST, NEWS PARTS', 'script': 'art7 / ar6 specs',
     'files': pick('ALLJINI', 'TWND', 'STAFFLST', 'NEWS/PARTS')},
    {'name': 'G Tournament names, schedule sheet, misc', 'files': pick('CPNAMEB', 'SCHE1', 'MON_INST', 'OFFD', 'JSCEVENT', 'LOC_GAME', 'SHINJIN')},
]
out = os.path.join(ROOT, 'build', 'art', 'groups_v2.json')
json.dump({'made': '2026-11-12', 'groups': groups}, open(out, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print(out, sum(len(g.get('ids', g.get('files', []))) for g in groups))
