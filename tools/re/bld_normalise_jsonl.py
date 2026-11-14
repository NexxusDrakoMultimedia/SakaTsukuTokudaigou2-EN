"""bld_normalise_jsonl: heal translation/*.jsonl files whose lines mix the compact and the spaced separator style.

    python -I -X utf8 tools/re/bld_normalise_jsonl.py [--write] [FILE.jsonl ...]     (default: report every file, all of translation/)

Uses the writer's own routine (translib.normalise_styles, the one transmerge applies when it rewrites a file), so the result is
what a merge would have produced.  Without --write nothing is changed.  Records are compared before/after (must be equal).
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
import translib as T   # noqa: E402


def main(argv):
    write = '--write' in argv
    files = [a for a in argv if not a.startswith('--')]
    db = T.load_db()
    todo = []
    for f in db.files:
        if files and not any(os.path.basename(x) == os.path.basename(f.path) for x in files):
            continue
        n = sum(1 for ln in f.lines if T.line_is_compact(ln) != f.compact)
        if n:
            todo.append((f, n))
    for f, n in todo:
        print('%s: %d line(s) in the other style (file style %s)' % (f.name, n, 'compact' if f.compact else 'spaced'))
        if write:
            if not f.plain:
                print('  refused: blank lines / CRLF / no final newline')
                continue
            recs = [json.loads(ln) for ln in f.lines]
            T.normalise_styles(f)
            assert [json.loads(ln) for ln in f.lines] == recs, 'records changed'
            T.write_atomic(f.path, '\n'.join(f.lines) + '\n')
            print('  rewritten')
    if not todo:
        print('all files are style-consistent')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
