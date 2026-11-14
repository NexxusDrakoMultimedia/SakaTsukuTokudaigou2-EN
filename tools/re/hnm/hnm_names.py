"""Decide full English municipality names for HOMETOWN (club-name / hometown work) and write the map build/hnm_names.json.

Source of truth for the spelling: the hiragana reading column of the 126-byte records (en = romanised reading, the sort key of the
game), because the current `en` of many entries was cut to the 8-byte slot of the pointer table ('Yokoha.', 'Hirats.', 'Kwzaki').
After the club-name patch (tools/layoutpatch.py) nothing truncates the name any more and the pointer-table pool is repacked
(slots are soft), so the cut is no longer needed.

    python -I -X utf8 tools/re/hnm/hnm_names.py          # writes build/hnm_names.json and prints the review table
"""
import json
import os
import re
import collections

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
MAXLEN = 12                                    # characters shown in the Hometown list / club name budget
MAXGUN = 13                                    # 'Kagoshima-gun'
MANUAL = {'八代郡': 'Yatsu-gun', '各務原市': 'Kagamigahara', '勝浦郡': 'Katsuura-gun', '勝浦市': 'Katsuura', '城崎郡': 'Kinosaki', '中島郡': 'Nakashima', '行方郡': 'Namegata', '松浦市': 'Matsuura', '山辺郡': 'Yamabe'}   # 八代郡: 'Yatsushiro-gun' = 14; the rest: the cut is not a prefix of the reading
SKIP = {'松任市', '白井市', '箕面市', '美嚢郡'}       # the game's reading differs from the real name (Matto, Shiroi) or the cut is not a truncation
rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'build', 'hnm_all.tsv'), encoding='utf-8')]
DIR = [('kita', 'N. '), ('minami', 'S. '), ('higashi', 'E. '), ('nishi', 'W. '), ('kami', 'U. '), ('shimo', 'L. ')]


def rbase(ja, rd):
    r = re.sub(r'[^a-z]', '', rd.lower())
    if ja.endswith('町'):
        for suf in ('machi', 'cho'):
            if r.endswith(suf) and len(r) > len(suf) + 1:
                return r[:-len(suf)]
    if ja.endswith('村'):
        for suf in ('mura', 'son'):
            if r.endswith(suf) and len(r) > len(suf) + 1:
                return r[:-len(suf)]
    return r


info = {}                                     # ja -> (en, reading romaji base)
conflict = set()
for r in rows:
    ja, en, rd = r[2], r[3], r[5]
    if ja == 'None' or rd in ('None', ''):
        continue
    b = rbase(ja, rd)
    if ja in info and info[ja][1] != b:
        conflict.add(ja)
    info.setdefault(ja, (en, b))
bycount = collections.defaultdict(set)
for ja, (en, b) in info.items():
    bycount[b].add(ja)
curcount = collections.defaultdict(set)
for ja, (en, b) in info.items():
    curcount[re.sub(r'[^a-z]', '', en.lower())].add(ja)


def is_subseq(a, b):
    it = iter(b)
    return all(c in it for c in a)


def rank_suffix(ja):
    return {'郡': '-gun', '町': '-cho', '村': '-mura'}.get(ja[-1], '')


def full(ja, b):
    n = b.capitalize()
    suf = rank_suffix(ja)
    coll = len(bycount[b]) > 1
    if suf == '-gun' and coll:
        return n + suf
    if suf in ('-cho', '-mura') and any(j[-1] in '市区' for j in bycount[b] if j != ja):
        return n + suf
    return n


out = {}
cats = collections.defaultdict(list)
for ja, (en, b) in sorted(info.items()):
    if ja in conflict or not b or ja in SKIP:
        continue
    if ja in MANUAL:
        out[ja] = MANUAL[ja]
        cats['manual'].append((ja, en, MANUAL[ja]))
        continue
    stem = en
    gun_marked = False
    m = re.match(r'^(.*?)-g(un)?\.?$', en)
    if m:
        stem, gun_marked = m.group(1), True
    letters = re.sub(r'[^a-z]', '', stem.lower())
    cat = None
    new = None
    if (en.endswith('.') or gun_marked) and b.startswith(letters) and (len(letters) < len(b) or (gun_marked and ja.endswith('郡') and not en.endswith('-gun'))):
        cat = 'trunc'
    elif '.' not in en and not gun_marked and en[:1].lower() == b[:1] and len(letters) < len(b) and is_subseq(letters, b) and not en.isupper():
        cat = 'vowel'
    if cat:
        new = full(ja, b)
        if gun_marked and ja.endswith('郡') and not new.endswith('-gun'):
            new += '-gun'
        if len(new) > MAXLEN and not (new.endswith('-gun') and len(new) <= MAXGUN):
            for pre, sh in DIR:
                if b.startswith(pre) and len(b) > len(pre) + 2:
                    cand = sh + b[len(pre):].capitalize() + (rank_suffix(ja) if new.endswith(rank_suffix(ja)) and rank_suffix(ja) else '')
                    if len(cand) <= MAXLEN:
                        new = cand
                        break
        if len(new) > MAXLEN and not (new.endswith('-gun') and len(new) <= MAXGUN):
            new = None                         # keep the current form (documented in the report)
            cats['toolong'].append((ja, en, b))
            continue
        if new != en:
            out[ja] = new
            cats[cat].append((ja, en, new))
# collisions that exist today: a 郡 that reads like a city / town (same en) -> -gun (style guide 8.2)
for ja, (en, b) in sorted(info.items()):
    if ja in out or ja in conflict:
        continue
    if ja.endswith('郡') and not en.lower().endswith(('-gun', '-g')):
        others = [j for j in curcount[re.sub(r'[^a-z]', '', en.lower())] if j != ja and not j.endswith('郡')]
        if others and len(en) + 4 <= MAXLEN and '.' not in en:
            out[ja] = en + '-gun'
            cats['collide'].append((ja, en, out[ja]))
json.dump(out, open(os.path.join(ROOT, 'build', 'hnm_names.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
for k, v in cats.items():
    print('==', k, len(v))
    for x in v[:400]:
        print('  ', x)
print('total changes', len(out), 'conflicts', sorted(conflict)[:10])
