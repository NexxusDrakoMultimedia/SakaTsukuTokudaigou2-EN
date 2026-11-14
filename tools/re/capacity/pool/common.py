"""Shared loader for the pool survey: extracts every overlay once and caches the result."""
import os, pickle, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import textdb as T


def load_all(pad_mode='full'):
    """-> list of (source, Image, strs, ptrs) for every source with >=1 accepted string (no 1ST_READ)."""
    out = []
    for source, path in T.list_sources():
        if source == '1ST_READ.BIN':
            continue
        try:
            img = T.load_image(source, path)
        except ValueError:
            continue
        strs, ptrs, _ = T.extract_image(img, pad_mode=pad_mode)
        if strs:
            out.append((source, img, strs, ptrs))
    return out

if __name__ == '__main__':
    t = time.time()
    a = load_all()
    print(len(a), 'images', time.time() - t, 's')
