"""tx5: generate result lines for the purely numeric clip groups of BCAST.BIN (minutes, kick-off times) from the frozen distinct list:
    python -I -X utf8 tools/re/tx5_gen_numbers.py
writes build/tx5/results/r_numbers.tsv  (N<TAB>en) for every distinct ja that matches one of the numeric patterns below
(full-width digits are normalised; 'N分' -> 'N min', '前半N分' -> 'First half, N min', 'あとN分' -> 'N min to go', ...).
Anything that does not match is left for the manual batches."""
import os, re, sys, unicodedata
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dist = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'build', 'tx5', 'distinct.tsv'), encoding='utf8')]
N = lambda s: unicodedata.normalize('NFKC', s)
PAT = [
    (r'^(\d+)分$', lambda m: '%s min' % m[1]),
    (r'^前半(\d+)分$', lambda m: 'First half, %s min' % m[1]),
    (r'^後半(\d+)分$', lambda m: 'Second half, %s min' % m[1]),
    (r'^延長前半(\d+)分$', lambda m: 'Extra time first half, %s min' % m[1]),
    (r'^延長後半(\d+)分$', lambda m: 'Extra time second half, %s min' % m[1]),
    (r'^あと(\d+)分$', lambda m: '%s min to go' % m[1]),
    (r'^残りあと(\d+)分$', lambda m: '%s min remaining' % m[1]),
    (r'^ロスタイムは(\d+)分です$', lambda m: 'Stoppage time is %s min.' % m[1]),
    (r'^第(\d+)節$', lambda m: 'Matchday %s' % m[1]),
    (r'^第(\d+)戦$', lambda m: 'Match %s' % m[1]),
    (r'^(\d+)位$', lambda m: 'No. %s' % m[1]),
    (r'^第(\d+)位。?$', lambda m: 'No. %s.' % m[1]),
    (r'^(\d+)番$', lambda m: 'No. %s' % m[1]),
    (r'^(\d+)勝$', lambda m: '%s wins' % m[1]),
    (r'^(\d+)敗$', lambda m: '%s losses' % m[1]),
    (r'^(\d+)引き分け$', lambda m: '%s draws' % m[1]),
    (r'^勝ち点(\d+)$', lambda m: '%s points' % m[1]),
    (r'^(\d+)点$', lambda m: '%s goals' % m[1]),
    (r'^(\d+)対$', lambda m: '%s to' % m[1]),
    (r'^(\d+)回戦$', lambda m: 'Round %s' % m[1]),
    (r'^(\d+)分け$', lambda m: '%s draws' % m[1]),
    (r'^(\d+)負$', lambda m: '%s losses' % m[1]),
    (r'^現在第(\d+)位。?$', lambda m: 'Currently No. %s.' % m[1]),
    (r'^(\d+)点目(!{1,2}|)$', lambda m: 'Goal %s%s' % (m[1], m[2])),
    (r'^(\d)(!?)$', lambda m: '%s%s' % (m[1], m[2])),
    (r'^現在首位。$', lambda m: 'Currently top.'),
    (r'^現在トップ。$', lambda m: 'Currently at the top.'),
    (r'^現在最下位。$', lambda m: 'Currently bottom.'),
    (r'^首位。$', lambda m: 'Top.'),
    (r'^トップ。$', lambda m: 'Top.'),
    (r'^最下位。$', lambda m: 'Bottom.'),
    (r'^開幕戦$', lambda m: 'Opening match'),
    (r'^最終節$', lambda m: 'Final matchday'),
    (r'^最終戦$', lambda m: 'Final match'),
    (r'^背番号$', lambda m: 'Squad number'),
    (r'^引き分けなし$', lambda m: 'No draws'),
    (r'^(\d+)分になろうというところ$', lambda m: 'Nearly %s minutes in' % m[1]),
    (r'^(\d+)分が経過しています$', lambda m: '%s minutes have passed' % m[1]),
    (r'^(\d+)分を回ったところです$', lambda m: 'Just past %s minutes' % m[1]),
]
out = []
for row in dist:
    n, tier, ja = row[0], row[1], row[2]
    s = N(ja).strip()
    for rx, f in PAT:
        m = re.match(rx, s)
        if m:
            out.append((n, f(m)))
            break
p = os.path.join(ROOT, 'build', 'tx5', 'results', 'r_numbers.tsv')
with open(p, 'w', encoding='utf8', newline='\n') as f:
    for n, en in out:
        f.write('%s\t%s\n' % (n, en))
print(len(out), 'numeric lines ->', p)
