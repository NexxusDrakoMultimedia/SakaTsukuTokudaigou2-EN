"""skd_links: check that every repo path named in backticks / markdown links of README.md and docs/**/*.md exists.  Read-only."""
import glob, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
files = [os.path.join(ROOT, 'README.md')] + glob.glob(os.path.join(ROOT, 'docs', '**', '*.md'), recursive=True)
bad = {}
pat = re.compile(r'`((?:tools|docs|translation|doc)/[A-Za-z0-9_./-]+)`|\]\(((?!http)[^)#\s]+)(?:#[^)]*)?\)')
for f in files:
    base = os.path.dirname(f)
    for ln, line in enumerate(open(f, encoding='utf-8'), 1):
        for m in pat.finditer(line):
            if m.group(1):
                p = m.group(1).rstrip('.')
                if '*' in p or p.endswith('/') and os.path.isdir(os.path.join(ROOT, p)):
                    continue
                cand = [os.path.join(ROOT, p)]
            else:
                p = m.group(2)
                cand = [os.path.join(base, p), os.path.join(ROOT, p)]
            if not any(os.path.exists(c) for c in cand):
                bad.setdefault(os.path.relpath(f, ROOT), []).append((ln, p))
for f, l in sorted(bad.items()):
    print(f, len(l))
    for ln, p in l[:40]:
        print('   ', ln, p)
