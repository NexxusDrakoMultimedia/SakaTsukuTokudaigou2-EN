"""Merge sample_src.tsv (drawn by draw.py) with the hand-written translations in tr/*.txt
and write sample.jsonl.  Translation file format: 'idx|english', '|' = forced line break
(the JP text's own layout line breaks are NOT copied: the English is word-wrapped here at 39
visible characters, which only replaces spaces by newlines so the byte count is unchanged).
'SKIP' marks non-text junk (excluded from all statistics)."""
import os, sys, glob, json, re, collections
os.chdir(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, 'tools/re/capacity/ratio')
from common import *

WIDTH = 39
# assumed on-screen expansion widths of substitution tokens (UNKNOWN real values; see report)
EXPAND = [(re.compile(r'#sname#'), 10), (re.compile(r'#tk\d\d#'), 10), (re.compile(r'#(chi|ken|kyu|to)#'), 8),
          (re.compile(r'\$\d'), 6), (re.compile(r'%[0-9]*s'), 8), (re.compile(r'%[0-9]*d'), 3),
          (re.compile(r'%[0-9]*D'), 6), (re.compile(r'%[0-9]*m'), 8)]
CTRL = re.compile(r'@[A-Z]/|@|=[A-Za-z]/|=|<[0-9A-F]{2}>')


def vwidth(s, expand=True):
    """visible width of a text with no newlines (control tokens 0, substitution tokens expanded)."""
    s = CTRL.sub('', s)
    if expand:
        for rx, w in EXPAND:
            s = rx.sub('x' * w, s)
    return len(s)


def wrap(flat, width=WIDTH, expand=True):
    """flat english ('|' forced breaks) -> list of lines, greedy word wrap."""
    lines = []
    for para in flat.split('|'):
        words = para.split(' ')
        # keep leading indent (list items) as part of the first word
        cur = ''
        for w in words:
            if cur == '':
                cur = w
            elif vwidth(cur + ' ' + w, expand) <= width:
                cur += ' ' + w
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def tokens(s):
    return collections.Counter(re.findall(r'@[A-Z]/|=[A-Za-z]/|#[a-z0-9]+#|%[0-9]*[sdDm]|\$\d|<[0-9A-F]{2}>', s))


def main():
    src = {}
    for l in open('tools/re/capacity/ratio/sample_src.tsv', encoding='utf8'):
        p = l.rstrip('\n').split('\t')
        src[int(p[0])] = dict(idx=int(p[0]), cat=p[1], id=p[2], max_bytes=int(p[3]),
                              ja=p[4].replace(chr(92) + 'n', chr(10)).replace(chr(92) * 2, chr(92)))
    tr = {}
    for f in sorted(glob.glob('tools/re/capacity/ratio/tr/*.txt')):
        for l in open(f, encoding='utf8'):
            l = l.rstrip('\n')
            if not l:
                continue
            i, e = l.split('|', 1)
            assert int(i) not in tr, i
            tr[int(i)] = e
    missing = sorted(set(src) - set(tr))
    extra = sorted(set(tr) - set(src))
    print('sample', len(src), 'translations', len(tr), 'missing', missing, 'extra', extra)
    out = []
    problems = []
    for i in sorted(src):
        s = src[i]
        flat = tr[i]
        rec = dict(s)
        rec['skip'] = flat == 'SKIP'
        if rec['skip']:
            rec['en'] = s['ja']
            rec['en_flat'] = ''
        else:
            lines = wrap(flat) if s['cat'].startswith(('prose', 'help')) else flat.split('|')
            en = chr(10).join(lines)
            rec['en_flat'] = flat
            rec['en'] = en
            if not all(32 <= ord(c) < 127 or c == chr(10) for c in en):
                problems.append((i, 'non-ascii'))
            if any(c in en for c in '\\~'):
                problems.append((i, 'forbidden \\ or ~'))
            if tokens(s['ja']) != tokens(en):
                problems.append((i, 'token mismatch', dict(tokens(s['ja'])), dict(tokens(en))))
        out.append(rec)
    for p in problems:
        print('PROBLEM', p)
    with open('tools/re/capacity/ratio/sample.jsonl', 'w', encoding='utf8') as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + chr(10))
    print('wrote', len(out))


main()
