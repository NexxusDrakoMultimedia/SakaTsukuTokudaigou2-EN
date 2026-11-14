"""artcoverage - which repainted textures are installed and applied.

For every texture id of build/art/groups.json (and every 5-digit id named in docs/art-group*.md that exists in the sheet
index) and for every identical copy of it (tools/texinject.py `dups` rule: same format, size and payload hash), report

  * FILE     translation/textures/<iso path>/<texture id>.pvr exists
  * APPLIED  the build log of a standard build lists the texture under that file's "textures replaced:" note

and print what is MISSING (no .pvr) or NOT APPLIED (.pvr present but the log does not list it, or no log).
With --sibling it also reports "look-alike" textures: other textures with the same width/height/format whose alpha
mask equals the repainted one's (same sprite stored in another container with a different payload hash).

    python -I -X utf8 tools/artcoverage.py [--log build/trial/prop7.log] [--groups build/art/groups.json] [-v]

Exit status 1 when anything is MISSING or NOT APPLIED.
"""
import os
import re
import sys
import json
import glob
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

SHEET = os.path.join(ROOT, 'build', 'tex', 'index.tsv')
TEXIDX = os.path.join(ROOT, 'build', 'texindex.tsv')
TEXDIR = os.path.join(ROOT, 'translation', 'textures')


def load_sheet():
    rows = {}
    with open(SHEET, encoding='utf8') as f:
        hdr = f.readline().rstrip('\n').split('\t')
        for l in f:
            p = l.rstrip('\n').split('\t')
            d = dict(zip(hdr, p))
            rows[p[0][:5]] = d
    return rows


def load_texindex():
    rows = []
    with open(TEXIDX, encoding='utf8') as f:
        f.readline()
        for l in f:
            p = l.rstrip('\n').split('\t')
            if len(p) >= 13 and p[1] != '!':
                rows.append(p)
    return rows


def resolve(id5, sheet, texidx):
    """5-digit id -> (iso file, texinject id)."""
    d = sheet[id5]
    src, member, rec, w, h = d['source'], d['member'], d['rec'], d['width'], d['height']
    cands = []
    for p in texidx:
        if p[0] != src or p[5] != w or p[6] != h:
            continue
        tid = p[1]
        if d['kind'] == 'PVR' and tid == '':
            cands.append(tid)
        elif tid.endswith('#' + rec):
            if member and not tid.startswith(member + '#'):
                continue
            cands.append(tid)
    if len(cands) != 1 and member.startswith('@'):
        # run member of a blob (GAME/GAMEETC.ZAR '@110/ktss03.pvr', ATFIRST/FACEMDUL.DAT '@cb7e0/..'): the sheet's member
        # column is the texinject id itself
        cands = [p[1] for p in texidx if p[0] == src and p[1] == member and p[5] == w and p[6] == h]
    if len(cands) != 1:
        k = _by_order(id5, sheet, texidx)
        if k is not None:
            return src, k
        raise KeyError('%s: %d candidates in %s: %r' % (id5, len(cands), src, cands))
    return src, cands[0]


_ORDER_CACHE = {}


def _by_order(id5, sheet, texidx):
    """GAME/ bind files (BINDLOGO.BIN, ALLLOGOS.BIN, ... : bind records without member names or '#rec' ids): the sheet's rows of
    one source file, in id order, and the texindex rows of that file, in file order, are the same list.  Used only when
    both lists have the same length and the width/height of the matching rows agree (as in build/art/v3/m_res.py)."""
    d = sheet[id5]
    src = d['source']
    key = (id(sheet), id(texidx))
    c = _ORDER_CACHE.get(key)
    if c is None:
        c = _ORDER_CACHE.clear() or {}
        _ORDER_CACHE[key] = c
        c['sh'] = {}
        for i in sorted(sheet):
            c['sh'].setdefault(sheet[i]['source'], []).append(i)
        c['tx'] = {}
        for r in texidx:
            c['tx'].setdefault(r[0], []).append(r)
    a, b = c['sh'].get(src, []), c['tx'].get(src, [])
    if not a or len(a) != len(b) or id5 not in a:
        return None
    r = b[a.index(id5)]
    if r[5] != d['width'] or r[6] != d['height']:
        return None
    return r[1]


def copies(src, tid, texidx):
    me = [r for r in texidx if r[0] == src and r[1] == tid]
    if not me:
        raise KeyError('%s %r not in the index' % (src, tid))
    key = (me[0][3], me[0][4], me[0][5], me[0][6], me[0][12])
    return [(r[0], r[1]) for r in texidx if (r[3], r[4], r[5], r[6], r[12]) == key]


def pvr_path(src, tid):
    """translation/textures path of a (file, id) pair; a whole-file PVR is '@file.pvr' per load_textures_dir."""
    return os.path.join(TEXDIR, *src.split('/'), (tid if tid else '@file') + '.pvr')


def parse_log(path):
    """{iso file (no leading slash): set(texture ids)} from the 'textures replaced:' notes of a build log."""
    applied = {}
    cur = None
    with open(path, encoding='utf8', errors='replace') as f:
        for l in f:
            m = re.match(r'\s+texture\s+/(\S+)\s+(CHANGED|unchanged)', l)
            if m:
                cur = m.group(1)
                applied.setdefault(cur, set())
                fm = re.search(r'failed=(\d+)', l)
                if fm and int(fm.group(1)):
                    applied[cur].add('!FAILED')
                continue
            m = re.match(r'\s+note: textures replaced: (.*)$', l)
            if m and cur:
                for t in m.group(1).split(','):
                    applied[cur].add(t.strip())
                cur = None
    return applied


def doc_ids(sheet):
    out = {}
    for fn in sorted(glob.glob(os.path.join(ROOT, 'docs', 'art-group*.md'))):
        with open(fn, encoding='utf8') as f:
            for m in re.finditer(r'\b(\d{5})\b', f.read()):
                if m.group(1) in sheet:
                    out.setdefault(m.group(1), os.path.basename(fn))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--log', default=os.path.join(ROOT, 'build', 'trial', 'prop7.log'))
    ap.add_argument('--groups', default=os.path.join(ROOT, 'build', 'art', 'groups.json'))
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args(argv)
    sheet = load_sheet()
    texidx = load_texindex()
    with open(a.groups, encoding='utf8') as f:
        groups = json.load(f)['groups']
    ids = {}
    for g in groups:
        for i in g['ids']:
            ids.setdefault(i, g['name'])
    for i, fn in doc_ids(sheet).items():
        ids.setdefault(i, fn)
    applied = parse_log(a.log) if os.path.isfile(a.log) else None
    if applied is None:
        print('no build log at %s: APPLIED cannot be judged' % a.log)
    missing, notapplied, expected = [], [], set()
    n_copies = 0
    for i in sorted(ids):
        try:
            src, tid = resolve(i, sheet, texidx)
            cps = copies(src, tid, texidx)
        except KeyError as e:
            print('UNRESOLVED %s (%s): %s' % (i, ids[i], e))
            missing.append((i, '?', '?', 'unresolved'))
            continue
        for csrc, ctid in cps:
            n_copies += 1
            p = pvr_path(csrc, ctid)
            expected.add(os.path.normcase(p))
            have = os.path.isfile(p)
            app = applied is not None and ctid in applied.get(csrc, ())
            if not have:
                missing.append((i, csrc, ctid, ids[i]))
            elif applied is not None and not app:
                notapplied.append((i, csrc, ctid, ids[i]))
            if a.verbose:
                print('%s %-28s %-14s file=%s applied=%s' % (i, csrc, ctid or "''", 'Y' if have else 'N',
                                                              ('Y' if app else 'N') if applied is not None else '?'))
    present = []
    for dp, _, fns in os.walk(TEXDIR):
        for fn in fns:
            present.append(os.path.join(dp, fn))
    extra = [p for p in present if os.path.normcase(p) not in expected]
    print('ids %d, physical copies %d, .pvr files present %d' % (len(ids), n_copies, len(present)))
    print('MISSING (no .pvr): %d' % len(missing))
    for m in missing:
        print('  %s  %s  %s   [%s]' % m)
    print('NOT APPLIED (.pvr present, not in build log): %d' % len(notapplied))
    for m in notapplied:
        print('  %s  %s  %s   [%s]' % m)
    print('.pvr files not tied to any listed id: %d' % len(extra))
    for p in extra:
        print('  ' + os.path.relpath(p, TEXDIR).replace(os.sep, '/'))
    if applied is not None:
        bad = {k: v for k, v in applied.items() if '!FAILED' in v}
        print('texture rows with failed>0: %d' % len(bad))
    return 1 if (missing or notapplied) else 0


if __name__ == '__main__':
    sys.exit(main())
