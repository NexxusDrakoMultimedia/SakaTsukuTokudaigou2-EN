"""s7n: list BCAST yh_gm_name clips (competition names).  usage: s7n_gm.py"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for ln in open(os.path.join(ROOT, 'translation', 'BCAST__BCAST.BIN.jsonl'), encoding='utf8'):
    if 'yh_gm_name' in ln:
        r = json.loads(ln)
        print(r['id'], '|', r['ja'], '|', r['en'], '|', r['ctx'][:40])
