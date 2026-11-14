"""Apply the club-word art spellings (translation/clubwords_art.tsv) to the translation DB.

usage: python -I -X utf8 tools/re/cw_apply.py [--apply]        (default: dry run, prints the plan)

What it changes (only the `en` field of existing records, nothing else; untouched lines are kept byte for byte):
  1. club-word records: `ja` is one of the 54 club words (half / full width) in a club context
       - hwptr tables of 54 / 55 / 85 entries (the club-word pool, 22 + 18 + 2 overlays), the NENREP orphan pool (hwpool run=64),
         the BCAST clips yh_tm_myf / mymae / mys / mytui;
     -> the art spelling when it fits the in-place slot (hwptr: `slot`; others: `max_bytes`), else the slot-fit short form
        (FALLBACK below; the art spelling then lives in translation/refit/ for builds with --refit on).
  2. BCAST composed texts `<word> Stadium` (yh_stadi_*) and `<word> vs` (yh_tm_mytai_*): the word inside is replaced (max_bytes 75, always art).
  3. the Name&Mascot Select explanation messages (CLUBEDIT, table 0x1eb8c): word, origin language and meaning follow the art (MSG below).
Left alone (person names that happen to be spelled like a club word, same katakana): recarray / player / 'clip name' records and the
hwptr tables of any other size (Bruce, Blaze, Sie / Cielo, Leone as player names).
Backups of every file before its first change: build/cw/db_bak/<file>.orig  (only for rolling back single files).
"""
import csv, glob, json, os, re, shutil, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
APPLY = '--apply' in sys.argv
N = lambda s: unicodedata.normalize('NFKC', s)
BAK = os.path.join('build', 'cw', 'db_bak')

# slot-fit short forms for the words whose art spelling is longer than the in-place slot (8-byte slot = 7 letters, 4-byte slot = 3 letters)
FALLBACK = {3: 'Avalanc', 5: 'Monolit', 14: 'Topolin', 18: 'Cie', 19: 'Colmill', 20: 'Corrien', 24: 'Herenci', 31: 'Panther', 33: 'Ros'}

# Name&Mascot Select messages: index -> (old text that must be present, new text)
MSG = {
    2: ('@Y/Vulkan@ is German for', '@Y/Vullcan@ is Latin for'),
    15: ('@Y/Abeille@ is French for', '@Y/Ape@ is Italian for'),
    17: (('@Y/Blauwiese@ is German for', '@Y/Blau Wiese@ is German for'), '@Y/Blau Wiese@ is German:'),
    21: ('@Y/Elfschritt@', '@Y/Elf Schritt@'),
    31: ('@Y/Pantera@ is Spanish for', '@Y/Panthera@ is Latin for'),
    34: ('@Y/Unicorn@ is the mythical\n@K/"one-horned beast"@.', '@Y/Unicorn@ is English for the\n@K/"one-horned beast"@.'),
    38: ('@Y/Estrella@ is Spanish for @K/"star"@.', '@Y/Estella@ is Spanish for @K/"star"@.'),
}

words = {}
for row in csv.reader(open('translation/clubwords_art.tsv', encoding='utf8'), delimiter='\t'):
    if row[0].isdigit():
        words[int(row[0])] = row
nw = {N(r[1]): k for k, r in words.items()}
ART = {k: r[3] for k, r in words.items()}           # ascii_for_strings
OLD = {k: r[9] for k, r in words.items()}           # old pool en
clen = lambda s: len(s.encode('cp932')) + 1


def pick(k, limit):
    a = ART[k]
    if clen(a) <= limit:
        return a
    f = FALLBACK.get(k, a[:limit - 1])
    assert clen(f) <= limit, (k, f, limit)
    return f


def club_kind(r):
    """-> 'club' | 'person' | None for an exact-ja record"""
    ctx = r.get('ctx') or ''
    fmt = r.get('fmt')
    if fmt == 'hwptr':
        if 'hwpool run=64' in ctx:
            return 'club'
        m = re.search(r'tbl@[0-9a-f]+\[(\d+)/(\d+)\]', ctx)
        if m:
            return 'club' if int(m.group(2)) in (54, 55, 85) else 'person'
        return None
    if fmt == 'bcast':
        if re.search(r'clip yh\\yh_tm_(myf|mymae|mys|mytui)_', ctx) or (fmt == 'bcast' and 'yh_tm_mytai_' in ctx):
            return 'club'
        if 'clip name' in ctx:
            return 'person'
        return None
    if fmt == 'recarr' or 'player' in ctx:
        return 'person'
    return None


stats = {}
def bump(key, n=1):
    stats[key] = stats.get(key, 0) + n

changes = []        # (file, id, old, new, kind)
left = []           # person records left alone
odd = []
files_new = {}
for f in sorted(glob.glob('translation/*.jsonl')):
    raw = open(f, encoding='utf8', newline='').read().split('\n')
    out = []
    dirty = False
    for line in raw:
        if not line.strip():
            out.append(line); continue
        r = json.loads(line)
        ja = N(r['ja'])
        new = None
        kind = None
        if ja in nw:
            k = nw[ja]
            ck = club_kind(r)
            if ck == 'club':
                limit = r['slot'] if r.get('slot') else r['max_bytes']
                new = pick(k, limit); kind = 'club-' + (r.get('fmt') or '?')
            elif ck == 'person':
                left.append((f, r['id'], r['ja'], r['en'], (r.get('ctx') or '')[:30]))
            else:
                odd.append((f, r['id'], r['ja'], r['en'], r.get('ctx')))
        elif r.get('fmt') == 'bcast':
            ctx = r.get('ctx') or ''
            m = re.match(r'(.+?)(ｽﾀｼﾞｱﾑ|スタジアム)$', ja) if 'yh_stadi_' in ctx else None
            if m and m.group(1) in nw:
                k = nw[m.group(1)]
                assert r['en'].endswith(' Stadium'), (r['id'], r['en'])
                new = ART[k] + ' Stadium'; kind = 'bcast-stadium'
            elif 'yh_tm_mytai_' in ctx:
                m = re.match(r'(.+?)\s*対\s*$', ja)
                if m and m.group(1) in nw:
                    k = nw[m.group(1)]
                    assert r['en'].endswith('vs'), (r['id'], r['en'])
                    new = ART[k] + ' vs'; kind = 'bcast-vs'
        elif 'CLUBEDIT' in f and r['id'].startswith('FLOW_PRG/CLUBEDIT.BIN#'):
            pass
        if new is not None and new != r['en']:
            old = r['en']
            assert json.dumps(r, ensure_ascii=False, separators=(',', ':')) == line, ('roundtrip', f, r['id'])
            r['en'] = new
            line = json.dumps(r, ensure_ascii=False, separators=(',', ':'))
            changes.append((f, r['id'], old, new, kind)); bump(kind); dirty = True
        elif new is not None:
            bump('same-' + kind)
        out.append(line)
    files_new[f] = ('\n'.join(out), dirty)

# --- the explanation messages (CLUBEDIT)
import struct
f = os.path.join('translation', 'FLOW_PRG__CLUBEDIT.BIN.jsonl')
text, dirty = files_new[f]
lines = text.split('\n')
byid = {}
for i, line in enumerate(lines):
    if line.strip():
        byid[json.loads(line)['id']] = i
d = open(os.path.join('extracted', 'FLOW_PRG', 'CLUBEDIT.BIN'), 'rb').read()
for k, (old, newt) in MSG.items():
    v = struct.unpack_from('<I', d, 0x1eb8c + 4 * k)[0] - 0x8c2d0000
    rid = 'FLOW_PRG/CLUBEDIT.BIN#%x' % v
    r = json.loads(lines[byid[rid]])
    assert N(r['ja']).count(words[k][1] if False else N(words[k][1])) >= 1, (k, r['ja'])
    olds = old if isinstance(old, tuple) else (old,)
    if newt in r['en']:
        continue
    old = next(o for o in olds if o in r['en'])
    en = r['en'].replace(old, newt, 1)
    # the message must carry its (new) word in the @Y/ span
    assert ('@Y/%s@' % ART[k]) in en or k in (), (k, en)
    changes.append((f, rid, r['en'], en, 'message'))
    bump('message')
    r['en'] = en
    lines[byid[rid]] = json.dumps(r, ensure_ascii=False, separators=(',', ':'))
files_new[f] = ('\n'.join(lines), True)

print('plan:', stats)
print('left alone (person-name records spelled like a club word): %d records' % len(left))
import collections
c = collections.Counter((os.path.basename(x[0])[:-6], x[2], x[3]) for x in left)
words_left = collections.Counter((x[2], x[3]) for x in left)
print('  by word/en:', dict(words_left))
print('unclassified exact records:', len(odd))
for x in odd[:10]:
    print('   ', x)
msgs = [c for c in changes if c[4] == 'message']
for c in msgs:
    print('MSG', c[1]); print('   -', c[2].replace('\n', ' / ')); print('   +', c[3].replace('\n', ' / '))
kinds = collections.Counter((c[2], c[3]) for c in changes if c[4].startswith('club'))
for (o, n), v in sorted(kinds.items(), key=lambda x: x[0][1]):
    if o != n: print('  %-9s -> %-12s %d' % (o, n, v))

if APPLY:
    os.makedirs(BAK, exist_ok=True)
    nf = 0
    for f, (text, dirty) in files_new.items():
        if not dirty:
            continue
        bk = os.path.join(BAK, os.path.basename(f) + '.orig')
        if not os.path.exists(bk):
            shutil.copy2(f, bk)
        tmp = f + '.cwtmp'
        with open(tmp, 'w', encoding='utf8', newline='') as fh:
            fh.write(text)
        os.replace(tmp, f)
        nf += 1
    print('written', nf, 'files')
