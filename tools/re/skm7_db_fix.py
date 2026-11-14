"""skm7_db_fix.py: the 8 'Profit of Y200M' records the first literal-amount pass missed -> 'Profit of 2 oku' (same byte length), via mn6_db (atomic, by id)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mn6_db  # noqa: E402

OLD = 'Profit of Y200M\nevery contract\nyear'
NEW = 'Profit of 2 oku\nevery contract\nyear'
IDS = ['FLOW_PRG/NEWS_ED.BIN#6dcf4', 'FLOW_PRG/OFFICE.BIN#9c880', 'FLOW_PRG/SCHE0.BIN#5d244', 'FLOW_PRG/SCHE1.BIN#5d244',
       'FLOW_PRG/SPONSOR.BIN#32cb8', 'FLOW_PRG/SPONSOR2.BIN#2e730', 'FLOW_PRG/TOWN.BIN#67120', 'FLOW_PRG/WEEKLY.BIN#52754']
print(mn6_db.apply({i: (OLD, NEW) for i in IDS}, dry='--dry' in sys.argv))
