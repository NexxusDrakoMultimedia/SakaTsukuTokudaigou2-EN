"""l10 non-ascii: count non-ASCII characters per file (read-only). usage: l10_nonascii.py FILE.."""
import sys

for f in sys.argv[1:]:
    t = open(f, encoding='utf-8').read()
    n = sum(1 for c in t if ord(c) > 0x7f)
    first = next((i for i, c in enumerate(t) if ord(c) > 0x7f), None)
    ln = t[:first].count('\n') + 1 if first is not None else None
    print('%-40s non-ascii=%d first-line=%s' % (f, n, ln))
