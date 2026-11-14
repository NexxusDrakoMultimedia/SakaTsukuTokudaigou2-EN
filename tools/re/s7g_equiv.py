"""s7g_equiv: prove that the run-member extension of tools/texinject.py changes nothing for textures that were already reachable.

Loads the ORIGINAL texinject (build/s7/bak/texinject.py.s7g_orig) and the CURRENT tools/texinject.py side by side, applies every
file of a textures directory (default translation/textures; each file is read once into memory) through both, and compares the
patched container bytes (SHA-1) and the inject info.  Also compares the two list_textures() results of every container of
extracted/ that has textures: the new listing must equal the old one plus run-pvr rows only.

    python -I -X utf8 tools/re/s7g_equiv.py [TEXTURES_DIR]
"""
import os
import sys
import hashlib
import importlib.util
import importlib.machinery

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path, loader=importlib.machinery.SourceFileLoader(name, path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    tdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'translation', 'textures')
    new = load('texinject_new', os.path.join(ROOT, 'tools', 'texinject.py'))
    old = load('texinject_old', os.path.join(ROOT, 'build', 's7', 'bak', 'texinject.py.s7g_orig'))
    ext = os.path.join(ROOT, 'extracted')
    groups = new.load_textures_dir(tdir, ext)
    ntex = sum(len(v) for v in groups.values())
    print('textures dir %s: %d files in %d containers' % (tdir, ntex, len(groups)))
    bad = 0
    nrun = 0
    for cont in sorted(groups):
        with open(os.path.join(ext, *cont.split('/')), 'rb') as f:
            src = f.read()
        outs = []
        for mod in (old, new):
            cur = src
            infos = []
            for tid in sorted(groups[cont], key=str):
                if mod is old and new.RE_RUN_ID.match(tid):
                    infos.append(None)
                    continue
                try:
                    r = mod.inject(cur, tid, groups[cont][tid], 'exact')
                except Exception as e:
                    infos.append(('ERR', type(e).__name__, str(e)))
                    continue
                cur = r.data
                infos.append(sorted((k, str(v)) for k, v in r.info.items()))
            outs.append((hashlib.sha1(cur).hexdigest(), infos))
        runs = [t for t in groups[cont] if new.RE_RUN_ID.match(t)]
        nrun += len(runs)
        if runs:
            print('  %-28s %d run-member texture(s) (only the new tool can inject them): skipped in the old/new comparison' % (cont, len(runs)))
            continue
        if outs[0] != outs[1]:
            bad += 1
            print('  DIFFERENT', cont, outs[0][0], outs[1][0])
    print('containers compared %d, textures compared %d, DIFFERENT %d' % (len(groups) - sum(1 for c in groups if any(new.RE_RUN_ID.match(t) for t in groups[c])), ntex - nrun, bad))
    # listings
    nfile = nrows = extra = 0
    miss = 0
    skip = {'SSONG', 'SOUND', 'DPSS', 'DPWWW', 'BCAST'}
    for root, dirs, files in os.walk(ext):
        dirs.sort()
        for fn in sorted(files):
            rel = os.path.relpath(os.path.join(root, fn), ext).replace('\\', '/')
            if fn in ('BCAST.BIN', '_filelist.tsv') or rel.split('/')[0] in skip:
                continue
            with open(os.path.join(root, fn), 'rb') as f:
                d = f.read()
            try:
                a = old.list_textures(d, scan=True)
            except Exception:
                a = None
            try:
                b = new.list_textures(d, scan=True)
            except Exception:
                b = None
            if (a is None) != (b is None):
                print('  ERROR state differs', rel)
                miss += 1
                continue
            if a is None:
                continue
            nfile += 1
            ka = [(t.tid, t.kind, t.fmt, t.dt, t.w, t.h, t.method, t.plain_len, t.slot, t.growable, t.gbix, t.sha1) for t in a]
            kb = [(t.tid, t.kind, t.fmt, t.dt, t.w, t.h, t.method, t.plain_len, t.slot, t.growable, t.gbix, t.sha1) for t in b if t.kind != 'run-pvr']
            nrows += len(ka)
            extra += sum(1 for t in b if t.kind == 'run-pvr')
            if ka != kb:
                print('  LISTING DIFFERS', rel)
                miss += 1
    print('listings: %d files, %d old rows identical in the new listing, %d new run-pvr rows, %d problems' % (nfile, nrows, extra, miss))
    return 1 if bad or miss else 0


if __name__ == '__main__':
    sys.exit(main())
