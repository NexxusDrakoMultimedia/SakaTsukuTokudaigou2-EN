"""ar5_dupcmp: compare the copy count of groups.json with the copies the injector knows (texindex sha1 rule) and with the
pixel-identical rows of build/tex/index.tsv (dup_of).  Prints every id where the numbers differ."""
import os, sys, json
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import artcoverage as A  # noqa

sheet = A.load_sheet()
texidx = A.load_texindex()
g = json.load(open(os.path.join(ROOT, 'build', 'art', 'groups.json'), encoding='utf8'))['groups']
# sheet rows: id5 -> row; dup_of -> id (full id string)
root_of = {}
for i5, d in sheet.items():
    root_of[d['id']] = d['dup_of'] or d['id']
members = {}
for fid, r in root_of.items():
    members.setdefault(r, []).append(fid)
for grp in g:
    for t in grp['textures']:
        i5 = t['id']
        try:
            src, tid = A.resolve(i5, sheet, texidx)
            cps = A.copies(src, tid, texidx)
        except KeyError:
            continue
        full = sheet[i5]['id']
        mem = members.get(root_of[full], [full])
        if len(mem) != len(cps) or t['copies'] != len(cps):
            print('%s %s %s: groups.json copies=%s injector copies=%d sheet identical rows=%d' % (
                i5, src, tid, t['copies'], len(cps), len(mem)))
            for m in mem:
                d = sheet[m[:5]]
                print('      sheet', m, d['source'], d['member'], d['rec'])
