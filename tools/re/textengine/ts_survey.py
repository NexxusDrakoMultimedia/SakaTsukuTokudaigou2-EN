"""Survey of FLOW_PRG overlays (textengine agent).
For each overlay: load base, file size, whether it contains the tsString library
(string "malloc error.tsString.init"), whether the layout function bytes are identical to
MEETING.BIN's FUN_8c2de294 head/loop (=> patchable by signature), and where the stub's
"_end" word lives and its value (heap start = _end rounded; BSS = _end - file end).
Usage: python -I -X utf8 tools/re/textengine/ts_survey.py > tools/re/textengine/survey_overlays.tsv
"""
import glob, os, struct, sys
sys.path.insert(0, 'tools')
import overlay

M = open('extracted/FLOW_PRG/MEETING.BIN', 'rb').read()
MB = 0x8c2d0000
SIG_HEAD = M[0x8c2de294 - MB:0x8c2de30c - MB]      # FUN_8c2de294 first 120 bytes
SIG_LOOP = M[0x8c2de334 - MB:0x8c2de420 - MB]      # layout loop 236 bytes
SIG_INIT = M[0x8c2de988 - MB:0x8c2de9f0 - MB]      # default window creator FUN_8c2de988
print('overlay\tbase\tsize\thas_tsString\tlayout_sig\tlayout_off\tend_var_off\t_end\tbss_bytes\tclass')
for f in sorted(glob.glob('extracted/FLOW_PRG/*.BIN')):
    d = open(f, 'rb').read()
    name = os.path.basename(f)
    try:
        o = overlay.unpack_overlay(d); base = o['load_addr']
    except Exception:
        print('%s\t?\t%d\t?\t?\t?\t?\t?\t?\tunparsed' % (name, len(d))); continue
    has = d.find(b'malloc error.tsString.init') >= 0
    i = d.find(SIG_HEAD)
    sig = i >= 0 and d.find(SIG_LOOP) >= 0 and d.find(SIG_INIT) >= 0
    end = base + len(d)
    cand = None
    for k in range(0, 0x60, 4):                       # stub literal pool
        w = struct.unpack_from('<I', d, k)[0]
        if base <= w < end - 4:
            v = struct.unpack_from('<I', d, w - base)[0]
            if end - 0x10000 <= v < end + 0x2000000:
                cand = (w - base, v)
    if cand is None:
        cls = 'end-var-not-found'
        print('%s\t0x%x\t%d\t%d\t%d\t%s\t-\t-\t-\t%s' % (name, base, len(d), has, sig, i if sig else '-', cls))
        continue
    bss = cand[1] - end
    cls = 'no-bss(_end==file end)' if bss == 0 else ('bss' if bss > 0 else 'end<file')
    print('%s\t0x%x\t%d\t%d\t%d\t%s\t0x%x\t0x%x\t%d\t%s' % (name, base, len(d), has, sig, i if sig else '-', cand[0], cand[1], bss, cls))
