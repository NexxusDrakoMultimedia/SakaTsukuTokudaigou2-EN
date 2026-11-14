"""tx5: systematic audit of visible Japanese left in the translation DB.

    python -I -X utf8 tools/re/tx5_audit.py [--out build/tx5/audit.tsv]

Per source file (translation/*.jsonl) and visibility tier: records, with English, ja-only (en empty), skip-flagged, en == ja (identity),
and how many of the ja-only / identity ones contain real Japanese (kana or kanji; pure ASCII / numbers / symbols do not count).
Tiers (player-visible first): T1 match HUD / commentary / attract demo, T2 title / intro / options / help, T3 ending / credits,
T4 memory card (save / load), T5 error / system dialogs, T6 everything else (menus, reports, data tables).
Table records (fmt hwptr / recarr: person names, hw pools) are counted separately as 'table' because their ja-only share is
policy (docs/uncovered-text.md), not a gap.
"""
import collections, glob, json, os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
JP = re.compile(r'[぀-ヿ一-鿿ｦ-ﾟ]')
TIERS = [
    ('T1 match / commentary / attract', r'(BCAST|FLOW_PRG/(GAME|BPMATCH|BPMWEEK|GMSHOW\d+|G_RESULT|GAMEOVER|MOVIE|MOVIE_BG|SPF_READ|CE_VS)\.BIN)'),
    ('T2 title / intro / options / help', r'(ATFIRST/|FLOW_PRG/(TITLE|LOGO|OPTION|HELP|HEREWEGO|N_ENTRY|NEWCON|INITCON|LOADBAR)\.BIN)'),
    ('T3 ending / credits', r'FLOW_PRG/(ENDING|ENDOPT|NENREP|J1_REP)\.BIN'),
    ('T4 memory card', r'FLOW_PRG/(LOAD|AUTOSAVE|CSAVE\d*|BACKUP|VTRLOAD|SONGSAVE|SAVE)\.BIN'),
    ('T5 error / system dialogs', r'(DPETC/|FLOW_PRG/(PASS_PL|FREELOAD)\.BIN|ROOT__)'),
]


def tier(src):
    for name, rx in TIERS:
        if re.search(rx, src):
            return name
    return 'T6 everything else'


def main():
    rows = collections.defaultdict(lambda: collections.Counter())
    per_src = collections.defaultdict(lambda: collections.Counter())
    for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        for ln in open(p, encoding='utf8'):
            if not ln.strip():
                continue
            r = json.loads(ln)
            src = r['id'].rsplit('#', 1)[0]
            t = tier(src)
            kind = 'table' if r.get('fmt') in ('hwptr', 'recarr') else 'text'
            for d in (rows[(t, kind)], per_src[src]):
                d['records'] += 1
                en = r.get('en', '')
                has_jp = bool(JP.search(r['ja']))
                if en:
                    d['with_en'] += 1
                    if en == r['ja'] and has_jp:
                        d['identity_jp'] += 1
                else:
                    if has_jp:
                        d['ja_only_jp'] += 1
                        if r.get('skip'):
                            d['skip_flagged'] += 1
                    else:
                        d['ja_only_nonjp'] += 1
    print('%-34s %-6s %8s %8s %9s %9s %8s' % ('tier', 'kind', 'records', 'with_en', 'ja_only_jp', 'skip_flag', 'identity'))
    tot = collections.Counter()
    for (t, kind), d in sorted(rows.items()):
        print('%-34s %-6s %8d %8d %9d %9d %8d' % (t, kind, d['records'], d['with_en'], d['ja_only_jp'], d['skip_flagged'], d['identity_jp']))
        tot.update(d)
    print('%-34s %-6s %8d %8d %9d %9d %8d' % ('TOTAL', '', tot['records'], tot['with_en'], tot['ja_only_jp'], tot['skip_flagged'], tot['identity_jp']))
    print()
    worst = sorted(((d['ja_only_jp'], s) for s, d in per_src.items() if d['ja_only_jp']), reverse=True)[:30]
    print('sources with the most ja-only records that contain Japanese:')
    for n, s in worst:
        d = per_src[s]
        print('  %6d / %6d  %-42s %s' % (n, d['records'], s, tier(s)))
    out = os.path.join(ROOT, 'build', 'tx5', 'audit.tsv')
    if '--out' in sys.argv:
        out = sys.argv[sys.argv.index('--out') + 1]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf8', newline='\n') as f:
        f.write('source\ttier\trecords\twith_en\tja_only_jp\tskip_flagged\tidentity_jp\n')
        for s, d in sorted(per_src.items()):
            f.write('%s\t%s\t%d\t%d\t%d\t%d\t%d\n' % (s, tier(s), d['records'], d['with_en'], d['ja_only_jp'], d['skip_flagged'], d['identity_jp']))
    print('wrote', out)


if __name__ == '__main__':
    main()
