"""inv_groups: write build/art/groups.json (art inventory groups) and verify every id against build/tex/index.tsv.
Run: python -I -X utf8 tools/re/inv_groups.py
"""
import csv
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
rows = list(csv.DictReader(open(os.path.join(ROOT, 'build/tex/index.tsv'), encoding='utf8'), delimiter='\t'))
byid = {r['id'].split('_')[0]: r for r in rows}
copies = {}
for r in rows:
    root = r['dup_of'].split('_')[0] if r['dup_of'] else r['id'].split('_')[0]
    copies.setdefault(root, []).append(r)


def rng(a, b):
    return ['%05d' % i for i in range(a, b + 1)]


G = []
G.append(dict(
    name='1 Header bar and Yes/No box',
    scope='Top bar header (BAR.TBD tex 0, ATFIRST and ETC_DATA copies) plus its look-alikes baked into LOADBAR, YOUTH.BIN, YOUTH.ZAR and TRAINING.TBD, the YEAR_PT year plate, the Yes/No box (yesno.tbd record 1 in SHTEX0..8 plus the SHTEX.ZAR 64x64 variant), and the contract/money strips (mon.tbd, ESTABLIS.BIN unit strip). Digits are separate sprites; keep them.',
    ids=['00002', '00091', '03634', '07332', '10469', '10470', '10474', '10475', '37285', '04112', '00088', '03642', '07308'],
    wording='Header: 年目 = Yr, 月 = Mo, 週 = Wk, 前半 = 1st, 後半 = 2nd. Yes/No: はい = Yes, いいえ = No. Money units next to digit sprites: 万円 = x10k Y (short form 10k Y), 億 = x100M Y, 円 = Y (artist to match the formatter output, see docs/number-formats.md). mon.tbd: 契約年数 = Contract Yrs, 年俸 = Salary, 現在の所持金 = Funds, 年 = Yr. Other English already in the sheet (SYSTEM, TACTICS, DF TYPE, PRACTICE, YOUTH TEAM) stays.'))
G.append(dict(
    name='2 TV station card',
    scope='ETC_DATA/TV_EVENT.ZAR TV_EB / TV_E1..E6 label textures: grey row labels, the four headings, and the yellow network + programme name lines under each existing English logo. Keep the English logos (Soccer TV, Excite Soccer, Super Soccer 11, Soccer News J, Asia Soccer Today, World Soccer Weekly).',
    ids=['04080', '04081', '04082', '04084', '04085', '04087', '04089', '04091', '04093'],
    wording='Rows: 平均視聴率 = Avg Ratings, 資本金 = Capital, 地域 = Region, 従業員数 = Employees. Headings: テレビ局 決定 = TV Station Decided, 継続 = Retained, 昇格 = Promoted, 降格 = Demoted. Name lines (network / programme): ローカルネット / 速報サッカーTV = Local Net / Soccer Flash TV; 6局ネット / エキサイトサッカー = Net 6 / Excite Soccer; 12局ネット / スーパーサッカー11 = Net 12 / Super Soccer 11; 全国ネット / サッカーニュースJ = Japan Net / Soccer News J; 全アジアネット / アジアサッカートゥデイ = Asia Net / Asia Soccer Today; 全世界ネット / ワールドサッカーウィークリー = World Net / World Soccer Weekly. Match the Net 6 / Net 12 / Japan / Asia / World wording on the OFFD1 oficons TV icons.'))
G.append(dict(
    name='3 Name Entry and edit-screen labels',
    scope='N_ENTRY.DAT atlas (tabs, delete and space plates, confirm; keep the kana table and the English Club Edit / Name Entry headings), the Password utility menu atlas, the SEARCH name-input labels and the Player Edit (PL_EDIT.ZAR) label atlases.',
    ids=['03541', '03553', '07594', '03578', '03583', '03584', '03585'],
    wording='Tabs: 漢字 = Kanji, ひらがな = Hiragana, カタカナ = Katakana, 英数字 = ABC/123, 記号 = Symbols, 決定 = Confirm, 一文字削除 = Delete, スペース = Space. Password menu: パスワード登録 = Register Password, パスワード削除 = Delete Password, パスワードを見る = View Password, パスワードをコピー = Copy Password, 終了 = Exit, 進む = Next, 戻る = Back, 取消 = Cancel, 決定 = OK, 中止 = Stop. SEARCH: 名前入力 = Enter Name, 捜索先 = Search In, 捜索開始 = Start Search. PL_EDIT: 顔作成 = Face Edit, 氏名 = Name, 呼称 = Nickname, 身長 = Height, きき足 = Foot, 出身 = Origin, 能力 = Ability, おまかせ = Auto, 終了 = Exit, 特徴 = Traits, スカウト寸評 = Scout Notes, ポジション = Position, 長所 = Strengths, 性格 = Character, 特技 = Skill, 肌の色 = Skin Tone, 髪型 = Hair, 目 = Eyes, 口 = Mouth, メガネ = Glasses, 輪郭 = Face Shape, 眉毛 = Brows, 鼻 = Nose, ヒゲ = Facial Hair, その他 = Other, パーツ番号 = Part No., 位置 = Position, 大きさ = Size, 高さ = Height, 幅 = Width, 骨格 = Frame, 形状 = Shape, センス/技術/知力/フィジカル/メンタル = Flair/Technique/Intelligence/Physical/Mental, 肌の色1-8 = Skin Tone 1-8.'))
G.append(dict(
    name='4 Secretary, staff and recruiting menus',
    scope='Secretary select banner and the profile plates (labels plus the secretary names, which must follow the string-pool English names), Office icon labels (SH_ICON), recruiting / draft / contract menus (DRAFT, DRAFTK, SCDRF, RECON, NEWCON), national-team select (SELNAT), scout report, and the youth system/tactics menu sheets.',
    ids=['03833', '03834', '03835', '03836', '03837', '03838', '03839', '03840', '03841', '03842', '03798', '03801', '03804', '03807', '03810', '07589', '07592', '07304', '07305', '07306', '07334', '03620', '04148', '10471', '10472', '03629'],
    wording='秘書選択 = Secretary Select. Plates: 血液型 = Blood Type, 誕生日 = Birthday, 出身地 = Hometown, 趣味 = Hobby, the T/B/W/H height line stays; secretary names romanised as in the string pool (family name last, check the pool before painting). SH_ICON: スケジュール = Schedule, クラブ情報 = Club Info, 戦歴 = Record, 個人ランキング = Player Rankings, オフィスへ = To Office. RECON: 交渉を行う = Negotiate, 秘書に任せる = Leave to Secretary, 契約しない = Do Not Renew, 更改終了 = Finish Renewals. SCDRF: 国内 = Domestic, 海外 = Overseas, 日本新人 = Japan Rookies, 海外新人 = Overseas Rookies, スタイル = Style. DRAFT: 国内選手獲得 = Sign Domestic Player, 外国籍選手獲得 = Sign Foreign Player, ポジション指定 = By Position, 選手指定獲得 = Pick a Player, フリー選手獲得 = Sign Free Agent, 指定中 = Selected, 指定無し = No Preference, ゴールキーパー = Goalkeeper, ディフェンダー = Defender, ミッドフィルダー = Midfielder, フォワード = Forward, キャプテン候補 = Captain Candidate, 年齢 = Age, 所属 = Club. NEWCON: 条件提示終了 = Finish Offer. SELNAT: U22日本代表 = Japan U22, U23日本代表 = Japan U23, 日本代表 = Japan, 海外有力選手 = Top Overseas Players, 決定 = OK. YOUTH menus 10471/10472: システム = System, 戦術 = Tactics, 方針指示 = Policy, 中盤守備 = Midfield Defence, 指導者指定 = Pick Coach, コーチ診断 = Coach Check, 入れ替え = Swap, ユース基本方針 = Youth Policy, サテライト基本方針 = Satellite Policy; formation and instruction names as in group 6. 03629 (新人獲得) = New Recruit.'))
G.append(dict(
    name='5 Schedule, finance and facility screens',
    scope='Office main menu labels (OFFD1 oficons), Schedule calendar controls (SCHE1, MONTH), finance and income screens (MON_INST, INVEST, G_INCOME, G_RESULT, GROUND, ESTABLIS.BIN, facility captions), the GRICON and NRICON caption strips, sponsor and supporters-club cost screens, JSCEVENT, and the money plates.',
    ids=['07405', '03587', '03589', '03590', '03323', '03333', '02227', '02228', '02213', '02214', '02219', '02208', '07309', '02003', '02006', '02009', '02187', '02190', '02193', '02196', '02199', '02202', '02205', '03530', '03533', '03536', '03816', '03822', '03823', '02233'] + rng(3555, 3571),
    wording='OFFD1 oficons: 日程進行 = Schedule, ホームタウン = Hometown, 人事 = Personnel, 施設 = Facilities, データ室 = Data Room, 終了・設定 = Quit / Options. SCHE1: 前月 = Prev Month, 翌月 = Next Month, 終了 = Done, 前半 = 1st Half, 後半 = 2nd Half, 1週-4週 = Wk 1-4, 戻る = Back, 月 = Mo. MONTH: 延長 = ET, 前 = 1st, 後 = 2nd. MON_INST: 広告費 = Ad Cost, 観戦料 = Admission, 試合数 = Matches, ホーム数 = Home Matches, 試合 = Matches, 万円 = x10k Y. ESTABLIS: 増設 = Expand, 撤去 = Remove, 閲覧 = View, 終了 = Exit. Facility captions: クラブハウス = Clubhouse, グラウンド = Ground, スタジアム = Stadium. GRICON: 収支報告 = Finances, 試合結果 = Match Results, 観客動員数 = Attendance, 視聴率 = TV Ratings, サポーターズクラブ = Supporters Club, 人事情報 = Personnel Info, 終了 = Exit. NRICON: クラブ成績 = Club Record, クラブ人気 = Club Popularity, 代表成績 = National Team Record. G_RESULT: その他 = Other, 得点者 = Scorers, 選手評価点 = Player Ratings. Sponsor: 新規スポンサーリスト = New Sponsor List, 年間総収入 = Annual Income, 新規スポンサー = New Sponsor, 契約期間 = Term, 資本 = Capital, 従業員数 = Employees, 契約条件 = Conditions, 現在スポンサーリスト = Current Sponsors, スポンサー状況 = Sponsor Status, 終了 = Exit. SPT_CLUB: サポーターズ運営費設定 = Supporters Club Budget, 万円 = x10k Y, 億 = x100M Y. Money plates 03555-03571 (1000円 ... 1億円): 円 = Y, 万円 = x10k Y, 億 = x100M Y, keep digits. Note: 02213/02214 and some GRICON/NRICON ids were identified from contact sheets; open each PNG first and drop any with no Japanese.'))
G.append(dict(
    name='6 Training, match setup and cheer editor',
    scope='Training menus and instruction tables (TRAINING.TBD, PLSEL, TUTO_BF tutorial), Match Regulations menu atlases (BMMAIN, BPMATCH; keep English MATCH REGULATIONS / ENTRY CLUB), Cheer Song editor (SS_EDIT), match overlay GOAL sheet (GM_SHORT), Meeting-room icons, and the FACEMDUL face-tile kanji.',
    ids=['37289', '37292', '37293', '37277', '37281', '37300', '00165', '00167', '00169', '00170', '36802', '36805', '36800', '03266', '00056', '00062', '00065'],
    wording='Training: 練習指示 = Practice Orders, 基本方針変更 = Change Policy, 練習実行 = Run Practice, 特別調整 = Special Prep, 連携を見る = View Teamwork, 監督チーム診断 = Manager Team Check, 臨時休養 = Extra Rest, 選手配置 = Positions, システム = System, 戦術 = Tactics, 中盤守備 = Midfield Defence, DFタイプ = DF Type, キッカー指定 = Set Takers, チーム練習 = Team Training, 個人練習 = Individual Training, チーム練習指示 = Team Practice Orders, 個人練習予定 = Individual Plan, 休養 = Rest, 監督に任せる = Leave to Manager, 決定 = OK, 総合評価 = Overall, チーム戦術 = Team Tactics, 前半/後半 = 1st/2nd, 1週-4週 = Wk 1-4. Formation and instruction names (ポストプレイ = Post Play, ストライカー = Striker, ドリブラー = Dribbler, ゲームメーカー = Playmaker, ボランチ = Holding Mid, サイドバック = Full-back, ストッパー = Stopper, リベロ = Sweeper, ゾーンプレス = Zone Press, ヘディング = Heading, シュート = Shooting, ドリブル = Dribbling, パス = Passing, タックル = Tackling, パスカット = Interception, GK飛び出し = GK Rush, GKセービング = GK Saving, プレイスキック = Set Kicks, 持久力強化 = Stamina Training, 瞬発力強化 = Speed Training, 筋力強化 = Strength Training, オフサイドトラップ = Offside Trap, 左/右サイドアタック = Left/Right Wing Attack, 中央突破 = Central Attack, カウンター = Counter, ライン = Line, ノーマル = Normal) follow glossary.tsv; the in-game English icons already say STRIKER, LIBERO, STOPPER etc., so reuse those words. PLSEL: チーム総合力 = Team Rating, オフェンス = Offence, タクティクス = Tactics, ディフェンス = Defence, システム = System, スタミナ = Stamina, FWタイプ = FW Type, MFタイプ = MF Type. TUTO_BF: スタミナ = Stamina, 攻撃力 = Attack, 守備力 = Defence, 疲れ = Fatigue (English subtitles are already printed behind them). Match Regulations: 簡易選択 = Quick Pick, 大会形式 = Format, 試合形式 = Match Type, 参加チーム = Teams, スタジアム = Stadium, 選手規定 = Player Rules, 決定 = OK, 試合開始 = Start Match, 再ドロー = Redraw, 終了 = Exit, 海外クラブ = Overseas Clubs, Jリーグ = J.League, 国代表 = National Teams, 自動選択 = Auto, 手動選択 = Manual, 代表A/B = National A/B, 海外A/B/C = Overseas A/B/C. SS_EDIT: 応援歌エディット = Cheer Song Edit, タイトル = Title, 作曲 = Compose, 拍子 = Time, テンポ = Tempo, ロード = Load, セーブ = Save, 終了 = Exit, サンプルデータ = Sample Data, セーブファイル = Save File, 遅 = Slow, 速 = Fast, メロディ = Melody, リズム = Rhythm, 三連符 = Triplet, 三拍子 = 3/4, 四拍子 = 4/4, 応援歌1-3 = Chant 1-3, ピンチ = Danger, ランダム = Random, ノーマル = Normal, 好調 = Hot Streak. GM_SHORT: 得点者 = Scorer. Meeting 03266: 弱点 = Weakness, セールスポイント = Selling Point, 弱 = Weak, 強 = Strong, 不満 = Complaint, クラブへ意見 = Club Feedback. FACEMDUL tiles 大 / 特 / 号 (together 大特号, Special Issue): repaint only if the English news strings spell a matching word, otherwise leave and note.'))
G.append(dict(
    name='7 Hometown, supporters, data room and system menus',
    scope='Hometown data (TOWNDATA, TOWNSEL; keep English Hometown heading), Local Info and Supporters sheets (LOCAL, SUPPORT), option/help/memory menus, Dream Club and Data Room score books (DRMENU, DRSSRANK, DRSUB*, DRSGP, DRSDENDO, DCEMAIN), Challenge Mode (CHALDANI, CHALMODE, CH_DANI) and the event result ribbons (REPORT.DAT). Lowest priority; do after groups 1-6. The Challenge kanji numerals and Data Room are optional or late-game screens.',
    ids=['04073', '04077', '02281', '02270', '02273', '02276', '02279', '03869', '03879', '03882', '03885', '03550', '00067', '04096', '04097'] + rng(6483, 6490) + ['00340', '00341', '00342', '00343', '00344', '00345', '00347', '00362', '00586', '00587', '00596', '00603', '00616', '00621', '00628', '00637', '00332', '00337', '00208', '00235', '00227', '00228', '00229'] + rng(209, 222) + rng(238, 258) + ['00290', '00291', '00292', '00293', '00294', '00295'],
    wording='TOWNDATA: 人口 = Population, 前月比 = vs Last Month, 地価 = Land Price, 交通 = Transport, サッカー人気 = Soccer Popularity, 年間降雨量/気温 = Annual Rainfall / Temp, 住宅 = Housing, 商業 = Commerce, スポーツ = Sports, 自然 = Nature, その他 = Other, 万人 = x10k, 万円 = x10k Y, 億 = x100M Y. TOWNSEL: 地方別 = By Region, 五十音別 = By Kana Order. LOCAL menus: 本拠地データ = Home Data, 経営 = Management, 地元住民の声 = Local Voices, 資本投資 = Capital Investment (verify each 128x32 strip). SUPPORT: 応援歌エディット = Chant Edit, クラブ応援歌割り付け = Club Chant Setup, 代表応援歌割り付け = National Chant Setup, 人気 = Popularity, 得点力 = Scoring, 荒っぽさ = Roughness, セットプレイ = Set Pieces, 精神力 = Mental, 人脈ありそう = Well Connected, 後半強そう = Strong Late, 足の速さ = Speed, 守備の要 = Defensive Key, 統率力 = Leadership, 不満の多さ = Discontent, 体力 = Stamina, 指導力ありそう = Good Coach Potential, 大物になりそう = Rising Star, サポーターランキング = Supporter Rankings, 意見を聞く = Hear Opinions, 応援歌 = Chants. OPTION menu: 選手名 = Player Names, 実況音声 = Commentary Voice, 実況メッセージ = Commentary Text, 視点 = Camera, 大会結果 = Tournament Results, 試合結果 = Match Results, 順位変動 = Standings Changes, ゴールランキング = Goal Rankings, 評価ランキング = Rating Rankings, インデックス = Index, スクリーンセーバー = Screen Saver, 近景/中景/遠景 = Near/Mid/Far, 分 = min; ON/OFF/STEREO/MONO stay. HELP: つくろう博士 = Dr. Tsukuro, コマンド解説 = Command Guide, 育成指南 = Training Guide, サッカー用語集 = Soccer Glossary. VMCOM (Dreamcast VMU file list): ファイル名 日付 容量 = File Name / Date / Size, 記録数 = Records, 空き容量 = Free Space, 表示切り替え = Switch View, 並べ替え = Sort, コピー = Copy, 消去 = Delete, コメント = Comment, 新しい順 = Newest, 記録名順 = By Name, 終了 = Exit, VM専用ゲームブロック数 = VM Game Blocks. REPORT: 位 = th, 優勝 = Champions, 準優勝 = Runners-up, 予選突破 = Qualified, 予選敗退 = Out in Qualifiers, J1昇格 = Promoted to J1, J2降格 = Relegated to J2, 回戦敗退 = Knocked Out. Data Room: 自クラブ情報 = Own Club Info, 他クラブ情報 = Other Clubs, 選手移籍状況 = Transfer Status, グレイトプレイヤーズ = Great Players, 代表情報 = National Team Info, 選手一覧 = Player List, 殿堂入り選手 = Hall of Fame, クラブ代表の規約 = Club Rep Rules, 日本代表監督の目標 = Japan Manager Goals, Jリーグ戦歴 = J.League Record, 代表戦歴 = National Team Record, 大会成績 = Tournament Record, Jリーグレコード = J.League Records, クラブ世界成績 = Club World Record, パーソナルレコード = Personal Records, ベストレコード = Best Records, ワーストレコード = Worst Records, Jリーグ現在順位 = Current J.League Table, Jリーグ年度別成績 = J.League Season Record, Jリーグ他クラブ情報 = J.League Club Info, スケジュール = Schedule, 収支の推移 = Finance Trend, 本拠地発展状況 = Home Development, 地元投資の傾向 = Local Investment, スポンサー状況 = Sponsors, 金額(億円) = Amount (x100M Y), 収入/支出/人口 = Income/Expenses/Population, 観客動員数 = Attendance, 本拠地の歩み = Home History, ゲームオーバー条件 = Game Over Conditions, 公式戦出場不可 = Banned, クラブ経営悪化 = Finances Poor, 破産 = Bankrupt, 契約年数 = Contract Yrs, ケガ = Injury, 年俸 = Salary, 年齢 = Age, 得点 = Goals, 出場数 = Apps, カード = Cards, 留学 = Abroad, 個人パスワード選手 = Password Players, 参加メンバー確認 = Check Members, クラブメンバー決定終了 = Finish Selection, 国内選手 = Domestic, 海外選手 = Overseas, 有力選手 = Top Players, フリー選手選択 = Free Players, ランキング = Rankings. Challenge Mode: 免許皆伝 = Master, 初段 = 1st Dan, 初級 = Novice, 段 = Dan, 敗退 = Defeat, 完全制覇 = Clean Sweep, 一-十 = 1-10; CH_DANI plates use the same rank names. CHALMODE team names: 欧州オールドスターズ = Euro Old Stars, 欧州スーパースターズ = Euro Super Stars, 南米オールドスターズ = South American Old Stars, 南米スーパースターズ = South American Super Stars, アジア・スターズ = Asia Stars, ジャパン・スターズ = Japan Stars, 北欧・スターズ = Nordic Stars, バルカン・スターズ = Balkan Stars, さかつく・スターズ = Sakatsuku Stars, ワールド・スターズ = World Stars, アフリカ・スターズ = Africa Stars, スペイン・レジェンズ = Spain Legends, フランス・レジェンズ = France Legends, U.K.レジェンズ = UK Legends, ドイツ・レジェンズ = Germany Legends, オランダ・レジェンズ = Netherlands Legends, イタリア・レジェンズ = Italy Legends, ブラジル・レジェンズ = Brazil Legends, アルゼンチン・レジェンズ = Argentina Legends, ウィング・ファームズ = Wing Farms, ドリーム・スターズ = Dream Stars (check glossary and string pools for these team names). CPNAMEB 00290-00295 competition banners: check each PNG first; some may already be English.'))

out = []
bad = []
for g in G:
    ids = []
    for i in g['ids']:
        if i not in byid:
            bad.append(i)
            continue
        if i not in ids:
            ids.append(i)
    g['ids'] = ids
    cp = []
    for i in ids:
        r = byid[i]
        root = r['dup_of'].split('_')[0] if r['dup_of'] else i
        n = len(copies.get(root, []))
        cp.append({'id': i, 'source': r['source'], 'member': r['member'], 'size': '%sx%s' % (r['width'], r['height']),
                   'format': r['format'], 'copies': n, 'dup_of': root if root != i else ''})
    g['textures'] = cp
    g['copies_total'] = sum(c['copies'] for c in cp if not c['dup_of'])
    out.append(g)
if bad:
    print('MISSING ids:', bad)
dest = os.path.join(ROOT, 'build/art/groups.json')
os.makedirs(os.path.dirname(dest), exist_ok=True)
json.dump({'groups': out}, open(dest, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
for g in out:
    print(g['name'], len(g['ids']), 'ids', g['copies_total'], 'copies')
