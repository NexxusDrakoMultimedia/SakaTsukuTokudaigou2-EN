"""Integrator: ESTABLIS %m texts that the money re-wrap left at 4 rows in a 3-row window -> 3 rows (each line <= 39 cells with %m = 15).
Checks the exact old en first; edits only the listed records; atomic write."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import translib as T
M = '@Y/%m@'
NEW = {
 '184a3': ['Discounted rebuild: ' + M, 'Monthly upkeep: ' + M, 'Thanks to a sponsor. Is that OK?'],
 '1926a': ['Upgrade the facility: ' + M, 'Monthly upkeep: ' + M, 'Both needed. All right?'],
 '192b8': ['Discounted upgrade: ' + M, 'Monthly upkeep: ' + M, 'Thanks to a sponsor. Is that OK?'],
 '19e7a': ['Adding a facility: ' + M, 'Monthly upkeep: ' + M, 'Both needed. All right?'],
 '19ece': ['Discounted addition: ' + M, 'Monthly upkeep: ' + M, 'Thanks to a sponsor. Is that OK?'],
 '19f8c': ['Removal cost cut to ' + M, 'Monthly upkeep ' + M + ' waived.', 'Sponsor deal. Is that all right?'],
 '1a1e9': ['Adding the pitch: ' + M, 'Monthly upkeep: ' + M, 'Sponsor discount applied. All right?'],
 '1a736': ['Changing to short grass discards', 'the long grass. Cost: ' + M, 'Is that all right?'],
 '1a7a0': ['Sponsor discount on short grass.', 'Discard long grass: ' + M, 'Is that all right?'],
 '1aa95': ['Changing to long grass discards', 'the short grass. Cost: ' + M, 'Is that all right?'],
 '1aaff': ['Sponsor discount on long grass.', 'Discard short grass: ' + M, 'Is that all right?'],
 '1ad36': ['Floodlights cost only ' + M, 'Monthly upkeep: ' + M, 'Thanks to a sponsor. All right?'],
 '1dd16': ['Adding a facility: ' + M, 'Monthly upkeep: ' + M, 'Both needed. All right?'],
 '1dd64': ['Discounted addition: ' + M, 'Monthly upkeep: ' + M, 'Thanks to a sponsor. Is that OK?'],
 '1df51': ['Discounted roof cost: ' + M, 'Monthly upkeep: ' + M, 'Thanks to a sponsor. All right?'],
}
path = os.path.join('translation', 'FLOW_PRG__ESTABLIS.BIN.jsonl')
out = []; n = 0
for line in open(path, encoding='utf-8', newline=''):
    nl = '\n' if line.endswith('\n') else ''
    if line.strip():
        r = json.loads(line)
        k = r['id'].rsplit('#', 1)[1]
        if r['id'].startswith('FLOW_PRG/ESTABLIS.BIN#') and k in NEW:
            assert r['en'].count('\n') == 4 and '%m' in r['en'], (k, r['en'])
            new = '\n'.join(NEW[k]) + '\n'
            for ln in NEW[k]:
                assert T.cells_of_line(ln) <= 39, (k, ln, T.cells_of_line(ln))
            assert len(new.encode('cp932')) + 1 <= r['max_bytes'], k
            r['en'] = new
            line = json.dumps(r, ensure_ascii=False, separators=(',', ':')) + nl
            n += 1
    out.append(line)
assert n == len(NEW), n
T.write_atomic(path, ''.join(out))
print('edited', n)
