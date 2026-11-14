"""art4sk_draft1: re-run art4 job draft1 with the Age/Club cells rebuilt from the clean bar profile (column 95) and the labels lowered into the bar body.
python -I -X utf8 tools/re/art4sk_draft1.py SIZE Y H [--write]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import art4_run, art4_specs
SZ = int(sys.argv[1]); Y = int(sys.argv[2]); H = int(sys.argv[3]); write = '--write' in sys.argv
_orig = art4_run.rowmode
def rm(arr, rect, ink, dilate=0, exclude=(), rad=0):
    if ink == 'PROFILE':
        x, y, w, h = rect
        for j in range(y, y + h):
            arr[j, x:x + w] = arr[j, 95]
        return
    return _orig(arr, rect, ink, dilate, exclude, rad)
art4_run.rowmode = rm
job = art4_specs.JOBS['draft1']
job['pre'] = [p for p in job['pre'] if p['ink'] != art4_specs._TINK] + [
    {'rect': [24, 216, 52, 24], 'ink': 'PROFILE'}, {'rect': [79, 216, 110, 24], 'ink': 'PROFILE'}]
for r in job['spec']['regions']:
    if r['id'] in ('age', 'club'):
        r.update(y=Y, h=H, size=SZ)
art4_run.run('draft1', 3, write)
