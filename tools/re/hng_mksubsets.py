"""hng: split translation/textures into 4 subsets under build/int/tsub/s1..s4 for texture bisecting.

s1 = everything outside ETC_DATA (FLOW_PRG, TRAINING, GAME2, EVENT, ...);
s2..s4 = the ETC_DATA containers split by sorted order into three roughly equal file counts.
Usage: python -I -X utf8 tools/re/hng_mksubsets.py
"""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'translation', 'textures')
OUT = os.path.join(ROOT, 'build', 'int', 'tsub')


def main():
    files = []
    for dp, _dn, fn in os.walk(SRC):
        for f in fn:
            full = os.path.join(dp, f)
            files.append(os.path.relpath(full, SRC).replace('\\', '/'))
    files.sort()
    etc = [f for f in files if f.startswith('ETC_DATA/')]
    other = [f for f in files if not f.startswith('ETC_DATA/')]
    # split ETC_DATA by whole containers so that duplicate copies stay together
    cont = {}
    for f in etc:
        cont.setdefault(f.split('/')[1], []).append(f)
    keys = sorted(cont)
    third = max(1, len(etc) // 3)
    groups = [other, [], [], []]
    gi = 1
    for k in keys:
        if gi < 3 and len(groups[gi]) >= third:
            gi += 1
        groups[gi].extend(cont[k])
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    for i, g in enumerate(groups, 1):
        for f in g:
            d = os.path.join(OUT, 's%d' % i, f)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(os.path.join(SRC, f), d)
        print('s%d: %d files' % (i, len(g)))
        if i > 1:
            print('   containers: %s' % ', '.join(sorted({x.split('/')[1] for x in g})))


if __name__ == '__main__':
    main()
