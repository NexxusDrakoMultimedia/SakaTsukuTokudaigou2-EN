"""How many extracted strings have a region [off, off+max_bytes) that overlaps an aligned pointer word that references another
extracted string (words that merely hold an in-image value do not count: 278 strings in 28 overlays overlap those)?  Such 'strings' are extraction false positives (bytes of a pointer table
read as text); writing English into them clobbers the pointer.  Found by the fullrun validation (NEWS_OP#28f21).
  python -I -X utf8 tools/re/capacity/synth/ptroverlap.py"""
import sys, os, importlib.util, collections
here = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(here, '..', '..', '..', '..'))
os.chdir(ROOT); sys.path.insert(0, 'tools')
import textdb as T, textrepack as R
spec = importlib.util.spec_from_file_location('pc', 'tools/re/capacity/pool/common.py'); pc = importlib.util.module_from_spec(spec); spec.loader.exec_module(pc)
tot = collections.Counter(); per = collections.Counter(); ex = []; ids = []
for src, img, strs, ptrs in pc.load_all('full'):
    refwords = {w for s in strs for w in s.refs}       # words that really point at an extracted string
    words = sorted(w for w in ptrs if w in refwords)   # ptrs: {word offset: target offset}
    import bisect
    for s in strs:
        own = set(s.refs)
        i = bisect.bisect_left(words, s.off - 3)
        hit = []
        while i < len(words) and words[i] < s.off + s.max_bytes:
            w = words[i]
            if w + 4 > s.off and w not in own:
                hit.append(w)
            i += 1
        tot['strings'] += 1
        if hit:
            tot['overlap'] += 1
            tot['overlap_movable'] += R.is_movable(s)
            tot['overlap_orphan'] += bool(s.orphan)
            per[src] += 1
            ids.append('%s#%x' % (src, s.off))
            if len(ex) < 8:
                ex.append((src, hex(s.off), s.max_bytes, [hex(x) for x in hit], s.raw[:16]))
print(dict(tot))
print('overlays affected', len(per), 'top', per.most_common(8))
for e in ex:
    print(e)

open(os.path.join(here, 'ptroverlap_ids.txt'), 'w').write(chr(10).join(ids) + chr(10))
print('ids written:', len(ids))
