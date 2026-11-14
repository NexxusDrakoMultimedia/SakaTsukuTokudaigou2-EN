"""Find load base of an SH-4 image by pointer-to-string voting.
usage: python -I -X utf8 tools/re/datatext/findbase.py <file> [...]
For each aligned word w in RAM range and each sample string start s (NUL-preceded
cp932 string with kana), vote base = w - s.  Only bases that are multiples of 0x1000
are kept.  Fast version: vote using words restricted to a sorted list and bisect."""
import sys, struct, re, bisect, collections

DB = rb'[\x81-\x84\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]'
kana_start = re.compile(rb'(?<=\x00)(?:\x82[\x9f-\xf1]|\x83[\x40-\x96])(?:' + DB + rb'|[\x20-\x7e]){2,}\x00')


def run(path):
    d = open(path, 'rb').read()
    words = {}
    n = len(d) // 4
    for i, w in enumerate(struct.unpack('<%dI' % n, d[:n * 4])):
        if 0x8c000000 <= w < 0x8d000000:
            words.setdefault(w, []).append(i * 4)
    starts = [m.start() for m in kana_start.finditer(d)]
    print(path, len(d), 'words', len(words), 'strings', len(starts))
    if not starts:
        return
    # take up to 400 sample strings; for each, candidate base set = {w - s : w in words with (w-s) % 0x1000 == 0 and base<=w}
    votes = collections.Counter()
    sample = starts[::max(1, len(starts) // 400)]
    for s in sample:
        for w in words:
            b = w - s
            if b & 0xfff == 0:
                votes[b] += 1
    for b, c in votes.most_common(5):
        # exact count over all strings
        full = sum(1 for s in starts if (b + s) in words)
        print('   base %08x votes %d  pointed strings %d / %d' % (b, c, full, len(starts)))


if __name__ == '__main__':
    for p in sys.argv[1:]:
        run(p)
