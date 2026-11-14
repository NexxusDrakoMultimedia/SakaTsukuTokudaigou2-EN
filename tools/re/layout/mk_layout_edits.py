"""Build the shard result files for the layout English edits of docs/layout-issues.md (task D) in build/trans/layoutD/.

    python -I -X utf8 tools/re/layout/mk_layout_edits.py [--outdir build/trans/layoutD]
    python -I -X utf8 tools/transcheck.py build/trans/layoutD/NNNN.json            (each file)
    python -I -X utf8 tools/transmerge.py merge build/trans/layoutD/*.json --overwrite

Edits (each is keyed by the Japanese text, so every record that carries it follows):
  1. person names whose English is 13 characters -> ladder step 2 `G. Family` (the Event list and the player card show 12 only);
  2. FIRE/ABROAD player-card cells `%8d得点` and `%7d.%02d点`: shortened so the cell is no wider than the Japanese (12 cells);
  3. sponsor-name suffixes over 9 characters (town token + suffix must stay within about 16 cells).
"""
import argparse
import collections
import glob
import hashlib
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
KANJI_NAME = re.compile(r'[一-鿿々ヶ]+ [一-鿿々ヶ]+')
HW_NAME = re.compile(r'[ｦ-ﾟ]+・[ｦ-ﾟ]+')
EN_NAME = re.compile(r"[A-Z][a-z'-]+ [A-Z][A-Za-z'-]+")

CELL_EDITS = {
    '%8d得点': '%8d Gls',          # 12 cells like the Japanese (the validator keeps the %Nd token identical, so the word shrinks)
    '%7d.%02d点': '%7d.%02d',      # 10 cells; the row above is the 'Avg Rating' label, the unit adds nothing
}
# 13-character names the regular rule does not cover (already abbreviated, family-first Asian names, one-word names).
# "X.Family" (no space after the initial) keeps players with the same family name apart; family-first names keep the family
# name and shorten the given name (the ladder of docs/style-guide.md 7.1, applied in the order the name is written).
EXPLICIT_NAMES = {
    'T. Ishiwatari': 'T.Ishiwatari', 'E. Takayanagi': 'E.Takayanagi', 'G. Yoichikawa': 'G.Yoichikawa',
    'Y. Matsushita': 'Y.Matsushita', 'Hi. Yamaguchi': 'Hi.Yamaguchi', 'Y. Yanagisawa': 'Y.Yanagisawa',
    'K. Hashigaito': 'K.Hashigaito', 'H. Matsushita': 'H.Matsushita', 'S. Matsuhashi': 'S.Matsuhashi',
    'Shinya Tanoue': 'S. Tanoue', 'Sunhong Hwang': 'S. Hwang', 'Jonathan Wong': 'J. Wong',
    'Lun Yongliang': 'Lun Y.', 'Huang Zhuchen': 'Huang Z.', 'Liao Xiangtao': 'Liao X.', 'Park Changsok': 'Park C.',
    'Lee Gangcheon': 'Lee G.', 'Jang Yongkyun': 'Jang Y.', 'Moon Sungwook': 'Moon S.', 'Lee Changdong': 'Lee C.',
    'Chang Donggun': 'Chang D.', 'Jeong Chanhwa': 'Jeong C.', 'Chen Songyong': 'Chen S.', 'Chin Shaolong': 'Chin S.',
    'Yang Hweishan': 'Yang H.', 'Teo Chee Hean': 'Teo Chee H.', 'Wong Kan Seng': 'Wong Kan S.',
    'Constantino F': 'Constant. F', 'Constantino S': 'Constant. S', 'Stefanovich D': 'Stefanov. D',
    'Stefanovich J': 'Stefanov. J', 'Raymond Won R': 'Raymond Won', 'Daniel Chan H': 'Daniel Chan',
    'Caranguejeira': 'Caranguej.',
}

SPONSOR_EDITS = {
    '#to#汽船': '#to# Shipping',
    '#to#市民会': '#to# Society',
    '#to#水産': '#to# Fishery',
    '#to#畜産': '#to# Farming',
}


def key_of(ja):
    return hashlib.sha1(ja.encode('utf-8')).hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--outdir', default=os.path.join(ROOT, 'build', 'trans', 'layoutD'))
    a = ap.parse_args()
    by_ja = collections.defaultdict(list)
    for f in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        with open(f, encoding='utf8') as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    by_ja[r['ja']].append(r)
    edits = {}
    for ja, rs in by_ja.items():
        ens = {r['en'] for r in rs if r.get('en')}
        if len(ens) != 1:
            continue
        en = next(iter(ens))
        if len(en) == 13 and EN_NAME.fullmatch(en) and (KANJI_NAME.fullmatch(ja) or HW_NAME.fullmatch(ja) or ja == 'セルジオ越後'):
            given, family = en.split(' ')
            edits[ja] = given[0] + '. ' + family
        elif en in EXPLICIT_NAMES:
            edits[ja] = EXPLICIT_NAMES[en]
    n_names = len(edits)
    for ja, en in list(CELL_EDITS.items()) + list(SPONSOR_EDITS.items()):
        if ja not in by_ja:
            print('MISSING ja', ja)
            continue
        edits[ja] = en
    # shards
    shard_of = {}
    for p in sorted(glob.glob(os.path.join(ROOT, 'build', 'trans', 'shards', '*.json'))):
        with open(p, encoding='utf8') as f:
            sh = json.load(f)
        for it in sh['items']:
            shard_of[it['key']] = sh['shard']
    groups = collections.defaultdict(list)
    missing = []
    for ja, en in edits.items():
        k = key_of(ja)
        if k not in shard_of:
            missing.append(ja)
            continue
        groups[shard_of[k]].append({'key': k, 'en': en, 'note': 'layout D'})
    os.makedirs(a.outdir, exist_ok=True)
    for n, items in sorted(groups.items()):
        with open(os.path.join(a.outdir, '%04d.json' % n), 'w', encoding='utf8') as f:
            json.dump({'shard': n, 'results': items}, f, ensure_ascii=False, indent=1)
    print('%d edits (%d person names, %d cells, %d sponsor suffixes) in %d result files; not in any shard: %s' % (
        len(edits), n_names, len(CELL_EDITS), len(SPONSOR_EDITS), len(groups), missing))


if __name__ == '__main__':
    main()
