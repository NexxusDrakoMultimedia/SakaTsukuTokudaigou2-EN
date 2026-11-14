"""l10 scan: Japanese characters in every file that `git add -A` would stage (dry run only, nothing is staged).

usage: python -I -X utf8 tools/re/l10_scan.py [--top N] [--tsv FILE]
Prints one line per file with Japanese characters (count of kana / kanji / full-width characters, and distinct count), a
summary per top-level folder, and the list of staged non-text (binary) files by folder.  Files under translation/ and
l10n/ are listed but separated (translation/ is the local working form after the conversion; l10n/ must be clean).
"""
import argparse
import collections
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JP = re.compile('[' + chr(0x3040) + '-' + chr(0x30ff) + chr(0x3400) + '-' + chr(0x4dbf) + chr(0x4e00) + '-' + chr(0x9fff) + chr(0xff00) + '-' + chr(0xffef) + ']')
TEXT_EXT = {'.md', '.py', '.tsv', '.txt', '.json', '.jsonl', '.toml', '.csv', '.ini', '.lua', '.ps1', '.cfg', '.html', '.c', '.h',
            '.asm', '.s', '.yml', '.yaml', '.xml', '.sh', '.bat', '.cmd', '.rst', '.lst', '.map', '.gpr', '.java', '.js', '.css', ''}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--top', type=int, default=60)
    ap.add_argument('--tsv')
    a = ap.parse_args()
    out = subprocess.run(['git', 'add', '-n', '-A'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    files = []
    for line in out.stdout.splitlines():
        m = re.match(r"add '(.*)'$", line)
        if m:
            files.append(m.group(1))
    print('git add -n -A would stage %d files' % len(files))
    rows, binary, nontext_size = [], collections.Counter(), collections.Counter()
    for f in files:
        full = os.path.join(ROOT, f)
        ext = os.path.splitext(f)[1].lower()
        if not os.path.isfile(full):
            continue
        data = open(full, 'rb').read()
        if ext not in TEXT_EXT or b'\0' in data[:4096]:
            top = f.split('/')[0] if '/' in f else '.'
            binary[(top, ext)] += 1
            nontext_size[(top, ext)] += len(data)
            continue
        try:
            t = data.decode('utf-8')
        except UnicodeDecodeError:
            try:
                t = data.decode('cp932')
                f += '  [cp932]'
            except UnicodeDecodeError:
                binary[(f.split('/')[0], ext + '?')] += 1
                continue
        chars = JP.findall(t)
        if chars:
            lines = sum(1 for l in t.split('\n') if JP.search(l))
            rows.append((f, len(chars), len(set(chars)), lines, len(t.split('\n'))))
    rows.sort(key=lambda r: -r[1])
    print('%d text files contain Japanese characters' % len(rows))
    by_top = collections.defaultdict(lambda: [0, 0])
    for f, n, d, l, tl in rows:
        k = f.split('/')[0] if '/' in f else '.'
        if f.startswith('tools/re/'):
            k = 'tools/re'
        by_top[k][0] += 1
        by_top[k][1] += n
    print('\nby folder (files, characters):')
    for k, (nf, nc) in sorted(by_top.items(), key=lambda kv: -kv[1][1]):
        print('  %-14s %5d files %10d chars' % (k, nf, nc))
    print('\nlargest %d:' % a.top)
    for f, n, d, l, tl in rows[:a.top]:
        print('  %-70s %9d chars %6d distinct %7d/%d lines' % (f[:70], n, d, l, tl))
    print('\nstaged non-text files (folder, extension: count, bytes):')
    for (top, ext), c in sorted(binary.items(), key=lambda kv: -nontext_size[kv[0]])[:40]:
        print('  %-14s %-7s %6d %12d' % (top, ext, c, nontext_size[(top, ext)]))
    if a.tsv:
        with open(a.tsv, 'w', encoding='utf-8', newline='\n') as f:
            f.write('file\tjp_chars\tdistinct\tlines_with_jp\ttotal_lines\n')
            for r in rows:
                f.write('%s\t%d\t%d\t%d\t%d\n' % r)
        print('wrote', a.tsv)


if __name__ == '__main__':
    main()
