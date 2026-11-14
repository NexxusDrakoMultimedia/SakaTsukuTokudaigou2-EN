"""skt_break: skeptic checks for tools/texdelta.py. Scratch dirs: build/l10n_skt_*  (deleted by the 'clean' phase)."""
import os, sys, shutil, hashlib, re, subprocess, random
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import texdelta as T, vcdiff as V, texinject
TEX = os.path.join(ROOT, 'translation', 'textures')
EXT = os.path.join(ROOT, 'extracted')
B = os.path.join(ROOT, 'build')
def d(n): return os.path.join(B, 'l10n_skt_' + n)
def tree(root):
    out = {}
    for dp, dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            out[os.path.relpath(p, root)] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    return out
def lg(s): print(s, flush=True)

def phase_det():
    for n in ('a', 'b'):
        shutil.rmtree(d(n), ignore_errors=True)
        T.make(TEX, EXT, d(n))
    ta, tb = tree(d('a')), tree(d('b'))
    lg('determinism: %d files, identical=%s' % (len(ta), ta == tb))
    done, probs = T.apply_all(d('a'), EXT, d('a_pvr'))
    lg('apply-all: %d done, %d problems %s' % (len(done), len(probs), probs[:3]))
    bad = 0
    for rel in done:
        if open(os.path.join(d('a_pvr'), *rel.split('/')), 'rb').read() != open(os.path.join(TEX, *rel.split('/')), 'rb').read():
            bad += 1
    lg('byte compare mismatches: %d' % bad)
    shutil.rmtree(d('p'), ignore_errors=True)
    T.make(TEX, EXT, d('p'), secondary=False)
    done, probs = T.apply_all(d('p'), EXT, d('p_pvr'))
    lg('plain apply-all: %d done, %d problems' % (len(done), len(probs)))

def phase_scan():
    jp = re.compile('[　-ヿ㐀-鿿豈-﫿＀-￯]')
    hits = 0
    for n in ('a', 'p'):
        for dp, dn, fn in os.walk(d(n)):
            for f in fn + dn:
                if jp.search(f):
                    hits += 1; lg('JP in name: ' + f)
            for f in fn:
                raw = open(os.path.join(dp, f), 'rb').read()
                for enc in ('utf-8', 'utf-16-le', 'utf-16-be', 'cp932'):
                    s = raw.decode(enc, errors='ignore')
                    if re.search('[぀-ヿ一-鿿]{3,}', s):
                        hits += 1; lg('JP-ish run (%s) in %s/%s%s' % (enc, n, os.path.relpath(dp, d(n)), f))
                        break
    lg('JP scan hits: %d' % hits)
    worst = 0; tot8 = 0; adds = 0
    orig = T.Originals(EXT)
    for rel, _, _, _ in T.read_manifest(os.path.join(d('p'), T.MANIFEST)):
        cont, tid = T.split_container(rel.split('/'), EXT)
        src = orig.texture(cont, tid[:-4])
        gset = {src[i:i + 8] for i in range(len(src) - 7)}
        delta = open(os.path.join(d('p'), *rel[:-4].split('/')) + '.vcdiff', 'rb').read()
        for kind, v in T.delta_pieces(delta):
            if kind != 'add':
                continue
            adds += len(v)
            run = 0
            for i in range(len(v) - 7):
                if v[i:i + 8] in gset:
                    run += 1; tot8 += 1
                else:
                    run = 0
                worst = max(worst, run)
    lg('8-grams of ADD data present in original: %d (ADD bytes %d); longest chain of consecutive hits=%d' % (tot8, adds, worst))

def phase_ten():
    """independent check: every 10-gram (and 9/8 for the distribution) of every ADD byte vs the original, plain deltas"""
    orig = T.Originals(EXT)
    hits = {8: 0, 9: 0, 10: 0}
    for rel, _, _, _ in T.read_manifest(os.path.join(d('p'), T.MANIFEST)):
        cont, tid = T.split_container(rel.split('/'), EXT)
        src = orig.texture(cont, tid[:-4])
        sets = {k: {src[i:i + k] for i in range(len(src) - k + 1)} for k in hits}
        delta = open(os.path.join(d('p'), *rel[:-4].split('/')) + '.vcdiff', 'rb').read()
        for kind, v in T.delta_pieces(delta):
            if kind == 'add':
                for k in hits:
                    hits[k] += sum(1 for i in range(len(v) - k + 1) if v[i:i + k] in sets[k])
    lg('ADD windows present in original, by window length: %s' % hits)

def phase_xd():
    rows = T.read_manifest(os.path.join(d('a'), T.MANIFEST))
    orig = T.Originals(EXT)
    ok = bad = 0
    for rel, want, _, _ in rows[::20]:
        cont, tid = T.split_container(rel.split('/'), EXT)
        o = os.path.join(d('a'), 'x_orig.pvr'); open(o, 'wb').write(orig.texture(cont, tid[:-4]))
        out = os.path.join(d('a'), 'x_out.pvr')
        if os.path.exists(out): os.remove(out)
        r = subprocess.run(['xdelta3', '-d', '-f', '-s', o, os.path.join(d('a'), *rel[:-4].split('/')) + '.vcdiff', out], capture_output=True)
        if r.returncode == 0 and hashlib.sha256(open(out, 'rb').read()).hexdigest() == want: ok += 1
        else: bad += 1; lg('xdelta3 FAIL %s %s' % (rel, r.stderr[:80]))
    lg('xdelta3 -d on LZMA deltas: %d ok, %d bad' % (ok, bad))

def mk_world(name, n=8):
    root = d(name); shutil.rmtree(root, ignore_errors=True)
    tex, ext = os.path.join(root, 'tex'), os.path.join(root, 'ext')
    rels = []
    for dp, dn, fn in os.walk(TEX):
        for f in sorted(fn):
            rels.append(os.path.relpath(os.path.join(dp, f), TEX).replace(os.sep, '/'))
    rels.sort(); random.Random(1).shuffle(rels)
    seen = set(); pick = []
    for r in rels:
        c, t = T.split_container(r.split('/'), EXT)
        if c not in seen:
            seen.add(c); pick.append((r, c))
        if len(pick) >= n:
            break
    for r, c in pick:
        os.makedirs(os.path.dirname(os.path.join(tex, *r.split('/'))), exist_ok=True)
        shutil.copy(os.path.join(TEX, *r.split('/')), os.path.join(tex, *r.split('/')))
        os.makedirs(os.path.dirname(os.path.join(ext, *c.split('/'))), exist_ok=True)
        shutil.copy(os.path.join(EXT, *c.split('/')), os.path.join(ext, *c.split('/')))
    T.make(tex, ext, os.path.join(root, 'delta'))
    return root, pick

def phase_fail():
    root, pick = mk_world('w')
    ext, delta = os.path.join(root, 'ext'), os.path.join(root, 'delta')
    ok, pr = T.apply_all(delta, ext, os.path.join(root, 'o0'))
    lg('baseline: %d ok %d problems; picks %s' % (len(ok), len(pr), [p[0] for p in pick]))
    r0, c0 = pick[0]
    cp = os.path.join(ext, *c0.split('/')); raw = bytearray(open(cp, 'rb').read())
    for off in (len(raw) // 2, 100, len(raw) - 1):
        b2 = bytearray(raw); b2[off] ^= 0xFF
        open(cp, 'wb').write(b2)
        ok, pr = T.apply_all(delta, ext, os.path.join(root, 'o1'))
        lg('flip @%d of %s: %d ok, problems: %s' % (off, c0, len(ok), [p[:90] for p in pr]))
    open(cp, 'wb').write(raw)
    for r, c in pick:
        p = os.path.join(ext, *c.split('/')); b2 = bytearray(open(p, 'rb').read())
        for i in range(0, len(b2), 4096):
            b2[i] ^= 1
        open(p, 'wb').write(b2)
    ok, pr = T.apply_all(delta, ext, os.path.join(root, 'o2'))
    lg('wrong revision: %d ok, %d problems; sample: %s' % (len(ok), len(pr), pr[:1]))
    r1, c1 = pick[1]
    p = os.path.join(ext, *c1.split('/')); open(p, 'wb').write(open(p, 'rb').read()[:1000])
    ok, pr = T.apply_all(delta, ext, os.path.join(root, 'o3'))
    lg('truncated container: %s' % [x[:140] for x in pr if r1 in x])
    os.remove(p)
    ok, pr = T.apply_all(delta, ext, os.path.join(root, 'o4'))
    lg('missing container: %s' % [x[:140] for x in pr if r1 in x])
    cp_ = subprocess.run([sys.executable, '-I', '-X', 'utf8', os.path.join(ROOT, 'tools', 'texdelta.py'), 'apply-all', '--delta-dir', delta, '--extracted', ext, '--out', os.path.join(root, 'o5')], capture_output=True, text=True)
    lg('CLI exit %d, last line: %s' % (cp_.returncode, cp_.stdout.strip().splitlines()[-1]))

def phase_hostile():
    root = d('w')
    delta = os.path.join(root, 'delta'); ext = os.path.join(root, 'ext')
    # restore pristine extracted for the picked containers
    for dp, dn, fn in os.walk(ext):
        for f in fn:
            os.remove(os.path.join(dp, f))
    for dp, dn, fn in os.walk(os.path.join(root, 'tex')):
        for f in fn:
            rel = os.path.relpath(os.path.join(dp, f), os.path.join(root, 'tex')).replace(os.sep, '/')
            c, t = T.split_container(rel.split('/'), EXT)
            os.makedirs(os.path.dirname(os.path.join(ext, *c.split('/'))), exist_ok=True)
            shutil.copy(os.path.join(EXT, *c.split('/')), os.path.join(ext, *c.split('/')))
    m = os.path.join(delta, T.MANIFEST)
    lines = open(m, encoding='utf-8').read().splitlines()
    first = [l for l in lines if l and not l.startswith('#')][0].split('\t')
    evil = '../../escape_%s' % os.path.basename(first[0])
    open(m, 'a', encoding='utf-8').write('\t'.join([evil, first[1], first[2], first[3]]) + '\n')
    out = os.path.join(root, 'o6')
    try:
        ok, pr = T.apply_all(delta, ext, out)
        lg('traversal manifest: ok=%d problems=%s' % (len(ok), [p[:100] for p in pr]))
    except Exception as e:
        lg('traversal manifest raised %s: %s' % (type(e).__name__, str(e)[:120]))
    lg('files escaped out_dir: %s' % [f for f in os.listdir(root) if f.startswith('escape_')])
    rel = first[0]
    dp = os.path.join(delta, *rel[:-4].split('/')) + '.vcdiff'
    good = open(dp, 'rb').read()
    cont, tid = T.split_container(rel.split('/'), ext)
    src = T.Originals(ext).texture(cont, tid[:-4])
    exc = {}
    rnd = random.Random(3)
    for k in range(200):
        b = bytearray(good)
        mode = k % 4
        if mode == 0:
            b = b[:rnd.randrange(len(b))]
        elif mode == 1:
            b[rnd.randrange(len(b))] ^= 1 << rnd.randrange(8)
        elif mode == 2:
            b = bytearray()
        else:
            b = bytearray(rnd.randbytes(rnd.randrange(1, 200)))
        try:
            T.decode_delta(bytes(b), src)
        except T.TexDeltaError:
            exc['TexDeltaError'] = exc.get('TexDeltaError', 0) + 1
        except Exception as e:
            exc[type(e).__name__] = exc.get(type(e).__name__, 0) + 1
    lg('fuzz decode_delta exceptions: %s' % exc)
    open(dp, 'wb').write(good[:len(good) // 2])
    try:
        ok, pr = T.apply_all(delta, ext, os.path.join(root, 'o7'))
        lg('truncated delta in apply_all: %s' % [p[:150] for p in pr if rel in p])
    except Exception as e:
        lg('truncated delta in apply_all RAISED %s: %s' % (type(e).__name__, str(e)[:150]))
    open(dp, 'wb').write(good)

def phase_clean():
    for n in os.listdir(B):
        if n.startswith('l10n_skt_'):
            shutil.rmtree(os.path.join(B, n), ignore_errors=True)
    lg('cleaned')

if __name__ == '__main__':
    globals()['phase_' + sys.argv[1]]()
