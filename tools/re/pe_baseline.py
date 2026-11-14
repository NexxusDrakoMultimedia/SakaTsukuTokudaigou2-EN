"""patch-engine baseline: sha256 of every output of fontpatch / moneypatch make_patches over a set of configurations.
    python -I -X utf8 tools/re/pe_baseline.py record FILE.json    # before touching the modules
    python -I -X utf8 tools/re/pe_baseline.py compare FILE.json   # after: must be identical
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
import fontpatch as FP      # noqa: E402
import moneypatch as MP     # noqa: E402


def h(b):
    return hashlib.sha256(b).hexdigest()[:16]


def collect():
    res = {}
    rd = FP.read_extracted
    for variants in ('A', 'ABC'):
        for place in ('tail', 'gap1'):
            for wrap in (True, False):
                for glyphs in (True, False):
                    out, rep = FP.make_patches(rd, variants=variants, place=place, wrap=wrap, glyphs=glyphs)
                    key = 'font/%s/%s/wrap%d/gl%d' % (variants, place, wrap, glyphs)
                    res[key] = {k: h(v) for k, v in sorted(out.items())}
                    res[key + '/rep'] = [rep['sites'], rep['cave'], rep['table_addr'], sorted(rep['files']), h(rep['table'])]
    for kw in ({}, dict(variants='AB'), dict(decimal_d=False), dict(tv_card=False)):
        out, rep = MP.make_patches(rd, expect=MP.EXPECTED_SITES if not kw.get('variants') else None, **kw)
        key = 'money/' + ','.join('%s=%s' % kv for kv in sorted(kw.items()))
        res[key] = {k: h(v) for k, v in sorted(out.items())}
        res[key + '/rep'] = [rep['sites'], rep['cave'], rep['size'], sorted(rep['files']), rep.get('tv_card')]
    # composition both orders on the current bytes (as build_patch does)
    fo, _ = FP.make_patches(rd, variants='A')
    mo, _ = MP.make_patches(rd, current=fo, variants='A')
    res['compose/font+money'] = {k: h(v) for k, v in sorted(mo.items())}
    mo2, _ = MP.make_patches(rd, variants='A')
    fo2, _ = FP.make_patches(rd, current=mo2, variants='A')
    res['compose/money+font'] = {k: h(v) for k, v in sorted(fo2.items())}
    for place in FP.PLACEMENTS:
        res['font/cave/' + place] = h(FP.cave_bytes(FP.PLACEMENTS[place]))
    for a in (0x8C299A00, 0x8C299C00):
        res['money/cave/%x' % a] = h(MP.cave_bytes(a))
        res['money/hook/%x' % a] = h(MP.hook_bytes(a))
    res['font/lua'] = h(FP.lua_source().encode('utf8'))
    return res


def main(argv):
    cur = collect()
    if argv[1] == 'record':
        with open(argv[2], 'w') as f:
            json.dump(cur, f, indent=1, sort_keys=True, default=str)
        print('recorded', len(cur), 'entries')
        return 0
    with open(argv[2]) as f:
        old = json.load(f)
    cur = json.loads(json.dumps(cur, default=str))
    bad = [k for k in sorted(set(old) | set(cur)) if old.get(k) != cur.get(k)]
    for k in bad:
        print('DIFF', k)
    print('identical' if not bad else '%d differences' % len(bad), '(%d entries)' % len(cur))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
