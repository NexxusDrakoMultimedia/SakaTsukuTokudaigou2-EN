"""Survey v3: NUL-delimited cp932 strings, >=40% kana.
Counts per file: strings, jp chars. Output tools/re/datatext/survey3.tsv (path,size,strings,chars).
Run from repo root: python -I -X utf8 tools/re/datatext/survey3.py
"""
import os, re, sys
DB = rb'[\x81-\x84\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]'
pat = re.compile(rb'(?<![\x01-\xff])((?:' + DB + rb'|[\x20-\x7e\x0a\x0d]|[\xa1-\xdf]){2,})(?=\x00)')
kana = re.compile('[぀-ヿ]')
kj = re.compile('[぀-ヿ一-鿿＀-￯　-〿]')


def scan(d):
    n = 0
    ch = 0
    for m in pat.finditer(d):
        b = m.group(1)
        try:
            s = b.decode('cp932')
        except Exception:
            continue
        k = len(kj.findall(s))
        if k < 2:
            continue
        if len(kana.findall(s)) * 10 < len(s) * 4 or len(s) < 3:
            continue
        n += 1
        ch += k
    return n, ch


if __name__ == '__main__':
    rows = []
    for root in ('extracted', 'build/unpacked'):
        for dp, _, fns in os.walk(root):
            for fn in fns:
                p = os.path.join(dp, fn).replace(chr(92), '/')
                if 'BCAST' in p or fn.startswith('_'):
                    continue
                if p.startswith('extracted/GAME/') and fn.endswith('.ZAR') or p.startswith('extracted/FLOW_PRG'):
                    pass
                if os.path.getsize(p) > 80_000_000:
                    continue
                d = open(p, 'rb').read()
                n, c = scan(d)
                rows.append((p, len(d), n, c))
    with open('tools/re/datatext/survey3.tsv', 'w', encoding='utf8') as f:
        for r in rows:
            f.write('%s\t%d\t%d\t%d\n' % r)
    print(len(rows))
