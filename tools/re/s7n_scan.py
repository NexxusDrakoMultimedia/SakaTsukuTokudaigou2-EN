"""s7n: scan translation/*.jsonl for J-League / special-team / competition names (NFKC match).

usage: python -I -X utf8 tools/re/s7n_scan.py <outfile> [pattern-group ...]
Writes one line per hit: key <TAB> id <TAB> ja <TAB> en <TAB> max_bytes <TAB> ctx
"""
import json, sys, glob, os, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PATS = {
    'F01': ['アントラーズ'], 'F02': ['レッズ', 'レッドダイヤモンズ'], 'F03': ['ジェフ'], 'F04': ['レイソル'],
    'F05': ['ヴェルディ'], 'F06': ['マリノス'], 'F07': ['ベルマーレ'], 'F08': ['エスパルス'],
    'F09': ['ジュビロ'], 'F10': ['グランパス'], 'F11': ['パープルサンガ', 'サンガ'], 'F12': ['ガンバ'],
    'F13': ['セレッソ'], 'F14': ['ヴィッセル'], 'F15': ['サンフレッチェ'], 'F16': ['アビスパ'],
    'F17': ['コンサドーレ'], 'F18': ['ベガルタ'], 'F19': ['モンテディオ'], 'F20': ['アルディージャ'],
    'F21': ['FC東京'], 'F22': ['フロンターレ'], 'F23': ['ヴァンフォーレ'], 'F24': ['アルビレックス'],
    'F25': ['サガン'], 'F26': ['トリニータ'], 'F27': ['ホーリーホック'], 'F28': ['横浜FC'],
    'F29': ['オールイースト'], 'F30': ['オールウエスト'], 'F31': ['ドリームクラブ', 'ドリームチーム'],
    'F32': ['欧州選抜'], 'F33': ['世界選抜'],
    'C': ['ファン感謝', 'ウィナーズカップ', 'ウィナーズ', 'プラチナ', 'クラブトーナメント', 'ヨーロッパカップ', '南アメリカカップ', 'アジアトーナメント',
          'チャンピオンズリーグ', 'ゴールデンカップ', 'チャレンジカップ', 'チャレンジリーグ', 'チャンピオンズカップ', 'インターリーグ',
          'スーパーユース', '海外キャンプ', 'フレンドリーマッチ', 'プレシーズンマッチ', 'Jリーグカップ', 'グレートクラブ', 'ニューイヤー',
          'オールスター', 'ネットワークトーナメント', 'ベストプレイヤーズ', 'チャレンジマッチ', 'スポーツフェスティバル', 'インターナショナルカップ',
          'ファーストステージ', 'セカンドステージ', 'チャンピオンシップ', 'J2リーグ', 'J1リーグ', 'コパ', 'ワールドツアー', 'ワールドカップ', 'ワールドチャレンジ',
          'ヨーロッパ', 'アジアカップ', 'ユースカップ', 'サンクスギビング'],
    'S': ['スターズ', 'レジェンズ', 'ウイングファームズ', 'ウィングファームズ', 'ワールドスターズ'],
}


def main():
    out = sys.argv[1]
    groups = sys.argv[2:] or list(PATS)
    lines = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'translation', '*.jsonl'))):
        for ln in open(p, encoding='utf8'):
            ln = ln.strip()
            if not ln:
                continue
            r = json.loads(ln)
            ja = unicodedata.normalize('NFKC', r.get('ja') or '')
            for g in groups:
                if any(unicodedata.normalize('NFKC', t) in ja for t in PATS[g]):
                    lines.append('\t'.join([g, r['id'], r['ja'].replace('\n', '\\n'), (r.get('en') or '').replace('\n', '\\n'),
                                            str(r.get('max_bytes')), (r.get('ctx') or '') + ' ' + str(r.get('fmt', ''))]))
                    break
    open(out, 'w', encoding='utf8').write('\n'.join(lines) + '\n')
    print(len(lines), 'hits')


main()
