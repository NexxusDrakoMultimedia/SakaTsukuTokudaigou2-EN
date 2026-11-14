# Translation style guide (Japanese -> English)

Project: Sakatsuku Tokudaigou 2 (Dreamcast). Applies to every `en` field in `translation/*.jsonl`.
Companion docs: `text-engine.md` (why the technical limits exist), `font.md` (glyphs), `pipeline.md` (workflow).

Status words: **RULE** = follow it. **DEFAULT** = follow unless a `max_bytes` limit forces the fallback.
**OPEN** = decision needed from the project owner; a working choice is given.

**OPEN (integrator, 2026-11-11): honorifics and name order.**  The project owner decided that Japanese idiosyncrasies (honorifics, counters, ranks, `-gun` in lists, name order) stay Japanese and are explained in the translators' notes
(`doc/TRANSLATORS_NOTES.md`), not in game.  Sections 1, 7.1, 9 and 11 below, and the translation database as built (prop7 / prop7r), still do the opposite for two items: honorifics are dropped
(0 occurrences of -san, -kun, -sama, senpai in any `en` field) and people are written Given Family (`Katsuo Ozaka`).  Money (oku / man), ranks (kyu / dan), counters and `-gun` are already as decided.
Changing honorifics or name order is a translation-wide edit plus a rebuild and a width re-check; it was NOT done unattended.  The shipped guide describes what the build does.  See `docs/status-report.md`.

---

## 1. Language variant and voice

| Topic | Rule |
|---|---|
| Variant | **British/Australian English.** centre, colour, defence, programme (only for TV), organise, licence (noun), grey, travelling. `-ise`, not `-ize`. |
| Sport word | **football** in running text; **match** (not "game"), **pitch** (not "field"), **kit** (not "uniform"), **full-back**, **centre-back**, **goalkeeper**, **supporters**, **fixtures**. |
| Exception | The series/product name keeps "Soccer": *J.League Pro Soccer Club o Tsukurou!* / "Sakatsuku". Do not "correct" it. |
| Dates / numbers | Day before month if a date is ever spelled out (10 Nov). Thousands separator is a comma. Metres, not meters. |
| Register | The game talks to the **Owner** (the player). Staff (secretary, manager, scouts) are polite and warm, not stiff: "Please select a player." not "Kindly select the player." |
| Honorifics | Drop -san / -kun / -sama / -senshu. The secretary addresses the Owner by name only: `#sname#さん` -> `#sname#`. Never "Mr." (gender and name are unknown). |
| Gender | Do not add gender the source does not carry. Prefer "they"/"you"/the name over he/she when Japanese is silent. Keep gender only when the speech style makes it unmistakable. |
| Player voices | Keep the characterisation, not the grammar: `俺…知らないぞ` gruff ("Me, captain? Don't blame me if it goes wrong."), `僕…ですよ` nervous/polite, `私…よ` composed. Contractions are fine and encouraged. |
| Dialect | `だがや` (Nagoya) and similar: render as light colloquial English ("y'know"), only in jokes/dummy text. |
| Exclamation | One `!` is enough. `！？` -> `!?`. Never stack. |
| Rhetorical softeners | `ですよね`, `ますよ`, `〜かな` etc.: render as tone, do not translate literally ("Be careful, okay?"). |

## 2. Hard technical limits (non-negotiable)

These come from the engine; see `text-engine.md` sections 3-5 for evidence.

1. **ASCII only.** Bytes 0x20-0x7E. No curly quotes, en/em dashes, accents, bullets, macrons.
   (Accented letters become possible only if glyphs are added to the free half-width slots; until then, none.)
2. **0x5C draws as a yen sign and 0x7E as an overline.** Never use `\` or `~`.
3. **Never type `@`, `=`, `#` or a lone `%` in text.** They are control characters in normal windows and cannot be escaped
   (`%%` prints `%` in format windows, but raw-window behaviour is unknown). Write "at", "No.", "and"/"plus", "percent" or "pct".
4. **Keep control tokens exactly as in the source**, in the same order: `@Y/ ... @` (colour; letters W R B Y G M P K O), `=K/ ... =`
   (window style), `%s %d %D %m`, `#sname#`, `#YOU#`, `#tkNN#`, and `<XX>` raw-byte tokens. Move them only to follow the word
   they colour. The `@Y/` in `@Y/７段@のクラブです` surrounds "7 Dan" -> `@Y/7-dan@`.
5. **Byte budget.** `max_bytes` counts the string **plus its NUL**, so `chars <= max_bytes - 1`. Control tokens count as bytes
   but take no screen width. Japanese is 2 bytes/char, English is 1 byte/char, so English usually *fits*; the screen width is
   the real constraint (next point).
6. **Width.** Every ASCII character is exactly **12 px** (monospaced). The default dialogue window is **39 characters per
   line, 3 lines**. A window of W cells holds `2W-1` characters. The engine breaks **per character, never per word**, so:
   - insert `\n` yourself at word boundaries;
   - never exceed the row count of the source string (count the source `\n`s: same number of lines, or fewer);
   - leave one cell of slack at the end of a line that finishes with `. , ! ?` (ASCII punctuation cannot hang into the margin);
   - do not start a line with a space and do not end one with a space.
7. **Full-width digits/letters** in the source (`１０級`, `Ｊ２`, `ＦＷ`) become plain ASCII (`10`, `J2`, `FW`). Do not use `%D` in new
   text; call sites that use `%D` need the code patch noted in `text-engine.md` 5.3.
8. **Do not translate or touch** non-text records (e.g. garbled `廚曙(`, `HC曙`, `xF曙`; `orphan: true`; strings under 2 real
   characters that are only code bytes). Leave `en` identical to `ja` and add `"skip": true` (see section 10).

## 3. Space-saving ladder

Menu labels and table cells are often only 8-16 bytes. Apply in order and stop at the first that fits:

1. Full natural wording ("Stamina Training").
2. Standard short form from the abbreviation table (section 6).
3. Drop filler: articles, "the", "of", `-ing` forms ("Sponsor Deals" -> "Sponsors").
4. Shortest legible noun ("Training").

Never truncate a word mid-letter without a full stop. Use at most one abbreviation per label. Consistency beats elegance:
the same Japanese string gets the same English everywhere (the glossary wins over local taste).

---

## 4. Football terminology

### 4.1 Positions and roles

| Japanese | English | Short | Note |
|---|---|---|---|
| ＧＫ / ゴールキーパー | Goalkeeper | GK | |
| ＤＦ / ディフェンダー | Defender | DF | |
| ＭＦ / ミッドフィルダー | Midfielder | MF | |
| ＦＷ / フォワード | Forward | FW | |
| 攻撃的ＭＦ | Attacking Midfielder | AM / Att. MF | |
| 守備的ＭＦ | Defensive Midfielder | DM / Def. MF | |
| ボランチ | Holding Midfielder | Holding Mid | Do not write "Volante" |
| トップ下 | Playmaker (No. 10) | Support FW | "behind the strikers" in help text |
| サイドＤＦ / サイドバック | Full-back | FB | |
| センターＤＦ / センターバック | Centre-back | CB | |
| ウイングバック | Wing-back | WB | |
| ストッパー | Stopper | | |
| リベロ | Libero | | |
| スイーパー | Sweeper | | |
| ストライカー | Striker | | |
| ポストプレイヤー | Target Man | | |
| ゲームメーカー | Playmaker | | |
| アタッカー | Attacker | | |
| ユース | Youth (team) | | "Youth Team" in full |

### 4.2 Skills (attack / support / defence / GK)

| Japanese | English | Note |
|---|---|---|
| シュート | Shooting / Shot | skill = "Shooting"; the act = "shot" |
| ヘディング | Heading | the act = "header" |
| オーバーヘッドキック | Overhead Kick | use "Bicycle Kick" only if the label has room to spare |
| ジャンピングボレーシュート | Jumping Volley | |
| ダイビングヘッド | Diving Header | |
| トゥリベーラ | Trivela | outside-of-the-boot strike |
| ドライブシュート | Drive Shot | keep: series staple |
| バナナシュート | Banana Shot | |
| ループシュート | Lob Shot | |
| ボレー | Volley | |
| セットプレイ | Set Piece | |
| アシスト | Assist | |
| アーリークロス | Early Cross | |
| センタリング | **Cross** | "centring" is Japanese-English; always "cross" |
| 壁パス | Wall Pass | one-two |
| キープ | Ball Retention | short: "Keep Ball" |
| キラーパス | Killer Pass | |
| くさびのパス | Wedge Pass | pass into the striker's feet |
| クライフターン | Cruyff Turn | |
| グラウンダー | Ground Pass | |
| サイドチェンジ | Switch of Play | short: "Switch" |
| スルーパス | Through Ball | |
| 縦パス | Forward Pass | |
| ダイレクト | One-Touch | |
| トライアングル | Passing Triangle | |
| トラップ | Ball Control | |
| ドリブル | Dribbling | |
| ノールックパス | No-Look Pass | |
| フェイント | Feint | |
| パス | Passing | |
| タックル | Tackling | |
| ポジショニング | Positioning | |
| ロングキック | Long Ball | |
| 決定力 | Finishing | |
| 空中戦 | Aerial Duels | |
| ナツメグ | Nutmeg | |
| ハイボール | High Ball | |
| パスアンドゴー | Pass and Go | |
| デッドスペース | Dead Space | |
| ジンガ | Ginga | keep; explain in help text |
| ルックアップ | Heads-Up Play | |
| キャッチング | Catching | GK |
| コーチング | Organising | GK shouting instructions; "Coaching" is wrong here |
| スローイング | Throwing | GK |
| セービング | Shot-Stopping | short: "Saving" |
| ディフ(ィ)レクティング | Deflecting | the source spelling is a typo |
| 飛び出し | Rushing Out | GK |
| ドロップキック | Drop Kick | |
| パンチ | Punching | |
| パントキック | Punt | |
| ラインディフェンス | Defensive Line | |
| カバーリング | Covering | |
| オーバーラップ | Overlap | |
| マンツーマン | Man-to-Man Marking | short: "Man Marking" |
| ゾーンディフェンス | Zonal Marking | |
| ゾーンプレス | Zonal Press | |
| カウンター | Counter-Attack | short: "Counter" |
| ポストプレイ | Hold-up Play | short: "Post Play" |
| オフサイドトラップ | Offside Trap | |
| システム / フォーメーション | Formation | never "System" |
| ３－５－２ etc. | 3-5-2 | hyphens, ASCII |

### 4.3 Match and competition terms

| Japanese | English | Note |
|---|---|---|
| 試合 | Match | not "game" |
| 前半 / 後半 (in a match) | First Half / Second Half | short: 1st Half / 2nd Half |
| 前半 / 後半 (in `1週前半`) | Early / Late | weeks are not halves: `1週前半` -> `Wk1 Early` |
| 延長 | Extra Time | |
| ＰＫ | Penalty Kick / Pens | `延長PKあり` -> "Extra Time + Pens" |
| ペナルティーエリア | Penalty Area | |
| 引き分け / 勝ち / 負け | Draw / Win / Loss | |
| 勝点 | Points | |
| 得失点差 | Goal Difference | GD |
| 得点 / 失点 | Goals For / Goals Against | |
| 順位 | Position (league table) / Ranking | |
| 昇格 / 降格 | Promotion / Relegation | |
| 優勝 | Champions / Title | `前回優勝` -> "Last Champions" |
| 前回優勝:%s | Last Champions: %s | |
| 大会 | Tournament | |
| リーグ形式 | League Format | |
| トーナメント形式 | Knockout Format | not "Tournament Format" |
| エキシビジョン形式 | Exhibition Format | |
| オリンピック形式 | Olympic Format | |
| Ｊリーグ | J.League | with the full stop |
| Ｊ１ / Ｊ２ | J1 / J2 | |
| ファーストステージ / セカンドステージ | First Stage / Second Stage | J1 ran two stages |
| チャンピオンシップ | Championship | |
| 天皇杯 | Emperor's Cup | |
| ナビスコカップ | J.League Cup | avoid the sponsor brand (decided) |
| ワールドカップ | World Cup | |
| 五輪 / オリンピック | Olympics | |
| アジアカップ | Asian Cup | |
| 日本代表 | Japan National Team | short: "Japan" |
| 欧州選抜 / 世界選抜 | European XI / World XI | "Select XI" if space allows |
| ホーム / アウェー | Home / Away | |
| 観客動員数 | Attendance | |
| 視聴率 | TV Ratings | |

## 5. Club management terms (game-specific)

| Japanese | English | Note |
|---|---|---|
| オーナー | Owner | the player's role |
| 秘書 | Secretary | |
| 監督 | **Manager** | British usage; keeps it distinct from コーチ = Coach |
| コーチ | Coach | |
| スカウト | Scout | |
| 選手 | Player | |
| 新人 | Newcomer / Rookie | "Rookie" for draft-style lists |
| クラブ | Club | never "team" for the organisation; "team" = the playing squad |
| チーム | Team / Squad | |
| スポンサー | Sponsor | `スポンサー契約` = Sponsorship Deal |
| 契約 / 契約更新 | Contract / Contract Renewal | |
| 年俸 | Salary (annual) | |
| 移籍 | Transfer | |
| 留学 | Study Abroad | the player is sent overseas to train |
| 海外キャンプ | Overseas Camp | |
| 練習 | Training | |
| チーム練習 | Team Training | |
| 筋力強化 / 瞬発力強化 / 持久力強化 | Strength / Speed / Endurance Training | the parenthetical (パワー etc.) = Power/Speed/Stamina |
| ミニゲーム | Small-Sided Game | short: "Scrimmage" |
| 成長 | Growth / Development | |
| 能力 | Ability / Attributes | |
| コンディション | Condition | |
| スタミナ | Stamina | |
| スピード | Pace | in-match speed; "Speed" for the training label |
| パワー | Strength | |
| 地元団体 | Local Groups | |
| 本拠地 / ホームタウン | Home Town | |
| 人口 | Population | |
| 住宅投資 | Housing Investment | |
| スポーツ投資 | Sports Investment | |
| 人気 | Popularity | |
| 知名度 | Recognition | |
| 観戦料 | Ticket Price | |
| 広告費 | Advertising Budget | |
| 収支 | Income and Expenditure | short: "Finances" |
| サポーター | Supporters | not "fans" |
| サポーターズクラブ | Supporters' Club | members = "Members" |
| フーリガン | Hooligans | |
| クラブハウス | Clubhouse | |
| データ室 | Data Room | |
| ミーティングルーム | Meeting Room | |
| 年末報告 | Year-End Report | |
| 月初報告 | Monthly Report | |
| 月間指示 | Monthly Orders | |
| 週 | Week | `Wk` in tight labels |
| 段位 / 級 / 段 | Rank / Kyu / Dan | `10級` -> `10-kyu`, `7段` -> `7-dan` (dans run 1 to 9); explain once in the help text |
| キャプテン / キャプテンマーク | Captain / Captain's Armband | |
| スターティングメンバー | Starting XI | |
| 日本代表監督 | Japan National Team Manager | |
| セーブ / ロード | Save / Load | |
| データ | Data | |
| 決定 / キャンセル | Confirm / Cancel | |
| Ａボタン / Ｂボタン | A Button / B Button | |
| 上下 / 左右 | Up/Down / Left/Right | `上下で選択` -> "Up/Down: select" |

Screen-name strings (`〜画面`, e.g. `留学画面`, `試合収支画面`) are internal debug labels: translate as "<noun> Screen"
at low priority and keep them short.

## 6. Abbreviation table (for the space ladder)

Add entries here before using any abbreviation in more than one place.

| Full | Short |
|---|---|
| Stamina | STA |
| Speed / Pace | SPD |
| Strength | STR |
| Technique | TEC |
| Training | Trng |
| Attendance | Att. |
| Contract | Contr. |
| Midfielder | MF |
| Attacking / Defensive | Att. / Def. |
| Week | Wk |
| Number | No. |
| Approximately | approx. |

Stat names: use the full word wherever 12+ bytes are available; do not invent new abbreviations ad hoc.

---

## 7. Names

### 7.1 Japanese people (players, staff, the Owner)
- Output order is **Given Family**, the usual English-language order for J.League players (`河本 鬼茂` -> `Kimo Kawamoto`).
- The BPINFO name fields are 14 bytes (**13 characters** including the space), but the Event list and the player card
  show only **12** (a 13-character name is cut: `Isao Nakagak`, docs/layout-issues.md section 3), so the working limit
  for a person name is **12 characters**. Fallback ladder: `Given Family` -> `G. Family` -> `Family`.
  Truncating mid-name is not allowed.
- Hepburn romanisation, **no macrons** (`Ono`, `Yuki`, `Kyosuke`); syllabic ん before b/m/p -> `n` (`Shinbashi`);
  long vowels are not marked (`Satoh`/`Sato`: write `Sato`; `Ohno`: write `Ono`).
- Half-width katakana names (`ﾋﾟｴｰﾙ`) are foreign given names: `Pierre`.
- Puns and joke names (several fictional players carry them): translate the sound, mention the pun only in the notes column.

### 7.2 Foreign people
- Real footballers: use the **standard English spelling of the person**, not a romanisation of the katakana
  (`ジダン` -> `Zidane`, `ロナウド` -> `Ronaldo`, `マラドーナ` -> `Maradona`, `ヨハン・クライフ` -> `Johan Cruyff`).
- Fictional foreign players: transliterate the katakana as English phonetics.
- Use the name the player was known by at the time of the game (1999-2000) where it differs from later usage.

### 7.3 Characters and nicknames
Keep a `notes` entry in `translation/glossary.tsv` for every recurring named character (secretaries, rival owners,
mascots) once the first instance is decided.

---

## 8. Clubs, places and organisations

### 8.1 J.League clubs (era-correct, pre-2000s naming)
Use the English club name as the club itself used it; one canonical form everywhere (no "Yokohama F Marinos" variants).

| Japanese | English |
|---|---|
| コンサドーレ札幌 | Consadole Sapporo |
| ベガルタ仙台 | Vegalta Sendai |
| モンテディオ山形 | Montedio Yamagata |
| 鹿島アントラーズ | Kashima Antlers |
| ジェフユナイテッド市原 | JEF United Ichihara |
| 柏レイソル | Reysol (field is 12 bytes; "Kashiwa Reysol" does not fit) |
| ＦＣ東京 | F.C.Tokyo (logo art F.C.TOKYO; section 12.5) |
| 東京ヴェルディ | Tokyo Verdy |
| 横浜Ｆ・マリノス | Yokohama F Marinos (logo art, no period after F; section 12.5) |
| 横浜ＦＣ | Yokohama FC |
| 川崎フロンターレ | Kawasaki Frontale |
| 湘南ベルマーレ | Shonan Bellmare |
| ヴァンフォーレ甲府 | Ventforet Kofu |
| アルビレックス新潟 | Albirex Niigata |
| 清水エスパルス | Shimizu S-Pulse |
| ジュビロ磐田 | Jubilo Iwata |
| 名古屋グランパスエイト | Nagoya Grampus Eight |
| ガンバ大阪 | Gamba Osaka |
| 浦和レッドダイヤモンズ | Urawa Red Diamonds |
| 水戸ホーリーホック | Mito Hollyhock (logo art HOLLYHOCK) |
| 大宮アルディージャ | Omiya Ardija |
| 京都パープルサンガ | Kyoto Purple Sanga |
| 大分トリニータ | Oita Trinita |
| セレッソ大阪 | Cerezo Osaka |
| ヴィッセル神戸 | Vissel Kobe |
| サンフレッチェ広島 | Sanfrecce Hiroshima |
| アビスパ福岡 | Avispa Fukuoka |
| サガン鳥栖 | Sagan Tosu |

Clubs not yet seen in the corpus (e.g. Yokohama Flugels): add as found, using the same
pattern; the diacritic in Flugels/Jubilo is dropped. Fictional clubs: Hepburn/English phonetics, never invent a real-sounding
real club.

Short forms when space is tight: drop the city (`Marinos`, `Reysol`), never the club name. A row of 24-byte club names
(`Nagoya Grampus Eight` = 20 chars) fits the 24-byte fields without shortening.

### 8.2 Prefectures, regions, municipalities
The corpus holds ~900 pre-merger (c. 1999) municipality names, so these rules apply in bulk:

| Item | Rule | Example |
|---|---|---|
| Prefecture 県 / 府 / 都 / 道 | Romanise the name, **drop the suffix** | 青森県 -> Aomori, 東京都 -> Tokyo, 京都府 -> Kyoto, 北海道 -> Hokkaido |
| Suffix kept only to disambiguate (space permitting) | "Pref." | `Kyoto Pref.` vs `Kyoto` (city) |
| City 市 | Name only, **drop "City"** | 札幌市 -> Sapporo, 横浜市 -> Yokohama |
| Tokyo ward 区 | Name only | 新宿区 -> Shinjuku |
| District 郡 | Name + `-gun` | 阿寒郡 -> Akan-gun |
| Town 町 / Village 村 | Name + `-cho` / `-mura` | 大島町 -> Oshima-cho |
| Collisions (same name, different rank) | The rank suffix is mandatory on the *less common* one | 大島郡 `Oshima-gun`, 大島町 `Oshima-cho`, 清水市 `Shimizu`, 清水町 `Shimizu-cho` |
| Island 島 | Name + Island only if it is a standalone entry | 種子島 -> Tanegashima (the 島 is part of the name; no extra "Island") |
| Region 地方 | `Tohoku, Kanto, Chubu, Tokai, Kansai, Shikoku, Kyushu, Okinawa` | 近畿 -> Kansai (decided: the familiar English name, not Kinki) |
| Old provinces | Romanised, no suffix | 陸奥 Mutsu, 陸中 Rikuchu, 陸前 Rikuzen, 羽後 Ugo, 常陸 Hitachi |
| Foreign places | English exonym | 北ｱｲﾙﾗﾝﾄﾞ -> Northern Ireland, 北朝鮮 -> North Korea, 韓国 -> South Korea, 香港 -> Hong Kong, 台湾 -> Taiwan |
| 国未定 | Undecided | |
| Fictional (ブリタニア県, オクロー市) | Phonetic, keep the suffix rule | Britannia, Okuro |

Romanisation: Hepburn, macrons dropped (`Kyushu`, `Osaka`, `Tokyo`, `Ome`, `Kochi`), old long-vowel forms not used
(`Chuo`, not `Chuou`/`Chuuou`). Established English forms win over strict Hepburn (`Tokyo`, `Osaka`, `Kyoto`, `Kobe`).
Typos in the source (`北会津群` for `郡`, `美濃群`) are translated as the intended name, not flagged in `en`.

### 8.3 Currency and numbers
- **Money keeps the Japanese oku / man structure, written in English words, in LOWER CASE (USER DECISION, binding; lower case since the
  second playtest: the capital `O` of `Oku` reads as a zero in the half-width font, `1 Oku` looked like `1 0ku`).**  *oku* = 100 million
  yen, *man* = 10 thousand yen.  The patched money function prints `13 oku 1500 man`, `6000 man`, `1 oku`, `1 oku 300 man`, `0 Yen`
  (negative: `-1 man`).  There is **no `Y` prefix and no decimal / western form** (`Y1.315bn`, `Y150M`, `1.5 billion yen` are wrong
  in this project).  Nothing is explained in game; the translator's guide does that.  `--money-style western` still builds the old
  decimal text but is not the shipped style (docs/number-formats.md).  `Yen` keeps its capital (a plain amount below one man, `0 Yen`).
- **Compact form `13 oku 1500m`** (`man` after an oku part shrinks to `m`; flag 77 / `%M`): scout panel, TV station card capital, the 12 character
  player-info fields, any field narrower than the full text.  An amount with one part is never shortened.
- `%m` (and every `%s` the game fills with a money string) is printed by that function (tools/moneypatch.py, `--money-format on`, the
  default).  Write `%m` exactly as the Japanese does, never put `Y`, `yen` or a unit after it; budget **15 cells** for it (`13 oku 1500 man`;
  the design maximum is 17 for `9999 oku 9999 man`).  tools/translib.py `_fmt_cells`, transcheck and pixelwidth charge 15.
  Without the patch the translated `%m` texts would show Japanese amounts, so a build that ships English must use it.
- Literal amounts typed in prose are written in the same words, lower case: `2 oku`, `3 oku`, `9 oku 9000 man`, `1000 man bonus`; right-aligned
  columns use `  3 man`, ` 10 man`, `  0 Yen`.  A bare 円 is `Yen`.  The population figure is the exception: 万 beside people is `10k`, not `man`.
  Football words and names keep their capitals (`Target Man`, `Man of the Match`, the surname Oku): the rule is digit + space + `oku` / `man`.
- **Library and sprintf formats (converted by code, docs/number-formats.md s5).**  The English format of an amount keeps the Japanese tokens and names
  the unit after each one; the patch reads that format and prints the money text itself:
  `%s %s man` / `@R/%s %s man@` (hi, lo), `%s man`, `%s Yen` (the shared library of the data-room screens and the monthly report),
  `%2d oku %02d00m` and `%6d00 man` (hundreds of man: ABROAD, FIRE, PLNUMSET, SELNAT), `%d cho%04d oku%02d00m`, `    %4d oku %02d00m`,
  `          %4d man` (INVEST), `%d Yen` (G_INCOME, plain yen rounded down to whole man).  Do not "improve" these strings: the unit letter after
  each conversion (c / o / m / y) is what the patch reads, and a `%d` without a unit makes the format pass through unchanged.
- The currency sign: where a literal sign is still needed (the open sprintf formats above) it is `Y` until a glyph test confirms 0x5C.
- `%D` is the full-width-digit variant of `%d` (the Japanese uses it before `人`); the patch prints ASCII digits for it.
  Width formats (`%2d`, `%04d`, `%-13s`) only work in sprintf strings; the tsString window prints them literally (`2d`).
- Counters: `3人` -> "3" or "3 players"; `1年` -> "1 yr" / "1 year"; `10社` -> "10 companies" ("10 sponsors" if context says so).
- Numbers up to 10 are words in running prose, digits in menus and tables.

---

## 9. Japanese terms that need handling

| Item | Rule |
|---|---|
| Set phrases of politeness (お疲れ様, よろしくお願いします, おめでとうございます) | Natural English equivalent ("Well done today.", "Looking forward to working with you.", "Congratulations!"); no romaji. |
| Honorific nouns (先輩, 後輩) | Translate by function ("senior", "junior"); do not keep romaji. |
| Cultural words with no equivalent (ジンガ, サカつく) | Keep the romanisation; explain once in the help text, never in a menu label. |
| Onomatopoeia and sound words | Choose an English sound or paraphrase; no romaji. |
| Brackets `『』「」` | Straight double quotes `"..."`; quotes inside quotes: single `'...'`. `『#tk00#』` -> `"#tk00#"`. |
| `…` and `……` | `...` (three ASCII full stops); never more than three. |
| `〜` (wave dash) | `-` when it means "to"; otherwise drop. |
| `♪` `☆` and other symbols | Drop if decorative; replace with `!` or a word if functional. |
| `、` `。` | `,` `.` with English punctuation rules, not 1:1. |
| Full-width space `　` used as list indent | One or two ASCII spaces (a full-width cell is two half cells). |
| Lists in HELP (`　キャッチング`) | Keep the leading indent; alphabetical order of the English item is **not** required (the list is paged by the source order). |
| Source typos | Translate the intended meaning. |

## 10. Workflow and record conventions

- Edit only the `en` field. Never change `id`, `ja`, `max_bytes`, `refs`, `ctx`.
- `en` left `""` means untranslated. A string that must not be changed has `"en"` identical to `ja` plus `"skip": true`.
- Before committing a batch: `en` must contain only ASCII, must not contain `\ ~ @ = #` outside source control tokens,
  must preserve the same multiset of control tokens as `ja`, and `len(en.encode('cp932')) <= max_bytes - 1` (when
  `max_bytes` is set). `tools/textfmt_*.py` raises on overlong strings; run it.
- Line-break check: no line over `2W-1` characters (39 by default); line count not greater than the source.
- Consistency: before translating a term, search the glossary (section 4-6) and `translation/*.jsonl`; if it is new, add it
  to `translation/glossary.tsv` (`ja <TAB> en <TAB> short <TAB> notes`) in the same commit.
- Dummy, debug and test strings (`ダミー１`, `TEAM_%d そのようなクラブは…`, `ダミーのBootRomコメントだがや。`, `展開その1後`):
  lowest priority. Translate in plain English, keep format tokens, and keep within `max_bytes`; skipping is acceptable.
- Help text (HELP.BIN, ~52k Japanese characters) is the most visible long-form text: write it in clear, friendly
  instructional English, one idea per sentence, 3 lines of 39 characters per page.

## 11. Open decisions

| # | Question | Working choice |
|---|---|---|
| 1 | Game title in English UI | Keep the romanised series title; subtitle "Special Edition 2" for 特大号 |
| 2 | 0x5C yen glyph vs the letter `Y` | Use `Y` until a glyph test passes |
| 3 | `%m` money format | DONE, user decision: oku / man in English words, lower case (`13 oku 1500 man`, `6000 man`, `1 oku`, `0 Yen`), tools/moneypatch.py style jp; in-game test pending |
| 4 | `ナビスコカップ` | **Decided:** "J.League Cup" (drop the brand) |
| 5 | Region `近畿` | **Decided:** "Kansai" (not "Kinki") |
| 6 | Accented Latin letters | None until glyph slots are drawn |
| 7 | Honorifics | Dropped everywhere |

## 12. Table names that were not in the first corpus (records `fmt` = `hwptr` / `recarr`)

Added with the coverage audit (docs/uncovered-text.md).  These records are fixed in-place slots: `max_bytes` is the hard limit
(`len(en) + 1 <= max_bytes`), the same `ja` gets the same `en` everywhere (translation memory), nothing here changes sections 1-11.

### 12.1 Slot widths and the character budget

| Table | `ja` shape | slot (bytes) | max characters | notes |
|---|---|---:|---:|---|
| Municipality records (HOMETOWN.BIN, `recarray S=126`) | kanji name, e.g. 青ヶ島村 | 35 | 34 in the field, **12 on screen** | use the English of the pointer-table copy (`Aogashima`, 8 / 12-byte slots); 8.2 rules apply |
| Staff / person records (`S=56 / 112 / 28 / 30 / 60`, name column) | `Family Given`, hw foreign name, or `ﾗｺﾞｽ 武威` | 14 (13 in the one CSAVE3 array) | 13 field, **12 on screen** | 7.1 ladder |
| Person records, reading column (hw, W=16) | `ﾋﾗﾂｶ ﾛｳﾏ` | 16 | 15 | probably a sort / search key; if shown it must read exactly like the English of the kanji name next to it |
| Club-name pool (`hwptr`, 55 names, `ﾐｭｰﾄｽ`, `ｻﾘｰﾚ`, `ﾀﾞﾐｰﾁｰﾑ` ...) | foreign word printed in the logo art, 3-9 kana | **8** (a few 4 / 12) | **7** (3 / 11); the art spelling is longer for 9 words | see 12.2 (logo rule) |
| Nations, cities, leagues, cups (`ﾌﾞﾗｼﾞﾙ`, `ｿｳﾙ`, `ｱｼﾞｱｳｨﾅｰｽﾞｶｯﾌﾟ`, `J1ﾌｧｰｽﾄｽﾃｰｼﾞ`) | hw katakana | 4 ... 36 | slot - 1 | 12.3 |
| Foreign / Japanese name parts (surname and given-name pools, 4 / 8 / 12-byte slots) | hw katakana word | 4, 8, 12 | 3, 7, 11 | 12.4 |
| Sponsor industry words with `#ken#` `#to#` `#chi#` tokens | `#to#ﾌﾟﾛﾊﾟﾝ` | 16-20 | slot - 1 | keep the token, translate the rest (`#to# Propane`) |

### 12.2 Fictional club names (rival club, `<town> <suffix>`)

* **RULE (user finding, 2026-11-12, binding): the club words follow the spelling printed in the ORIGINAL LOGO ART, not a katakana transliteration.**
  The game shows the logo of the selected word (texture `GAME/ALLPNAME.BIN`, ids 10824-10877, one per pool word in pool order; the gold flags of `BINDFLAG.BIN`
  13522-13575 carry the same logos) next to the text, so the word in the pool, in the commentary (`<word> Stadium`, `<word> vs`) and in the Name&Mascot Select
  explanation (`CLUBEDIT.BIN`, message table 0x1eb8c, one message per word in pool order) must read exactly like the logo, and the **origin language and the
  meaning in that message must be true for the word as printed** (`Ape is Italian for "honeybee"`, not `Abeille ... French`).
  The art readings are in `translation/clubwords_art.tsv` (re-read at 3x-10x, 54 of 54 words have a logo; `tools/re/cw_clubwords_art.py` rebuilds it).
  Accents of the art (`Glück`, `Mégère`, `Valentía`) are folded to ASCII; capitals follow the usual Title case, the logo's lettering style is ignored;
  two-word logos (`Blau Wiese`, `Elf Schritt`, `El Toro`) keep the blank.  The old transliterations (`Bruce`, `Vulcan`, `Monoris`, `Estela`, `Palentia`,
  `Sturz`, `Arpe` ...) were wrong against the art; `Bruce` is only correct for the PLAYER named `ﾌﾞﾙｰｽ` (see "same katakana, different word" below).
* **Same katakana, different word.**  Four club words are also foreign player names: `ﾌﾞﾙｰｽ` (club `Blues`, player `Bruce`), `ﾌﾞﾚｲｽﾞ` (`Blaze`, player `Blaze`),
  `ｼｴﾛ` (`Cielo`, player `Sie` / `Cielo`), `ﾚｵｰﾈ` (`Leone`, also the Brazilian manager in `SPF_READ`).  Disambiguate by table, never by the Japanese:
  the club-word pool is the pointer tables of **54 / 55 / 85 entries** (one per overlay that shows club names), the NENREP orphan pool (`hwpool run=64`) and the BCAST clips
  `yh_tm_myf / mymae / mys / mytui / mytai / stadi`; recarray rows (`S=28 ... 240`), `player #n name` and BCAST `clip name\` records and every hwptr table of another size
  (6, 77, 172, 221, 326, 329, 833, 1485, 1729) are person names and keep their own English.
* The words the first corpus took for invented (`Mythos`, `Salire`, `Rendir`, `Sfida`, `Stolz`, `Tigre`, `Valentia` ...) are, per the art, real foreign words;
  their meanings are in the table below.  Special pool entries: `ﾀﾞﾐｰﾁｰﾑ` -> `Dummy Team` (index 0, a debug name, keep it plain).  Never turn one into a real club name (8.1).
* **Slots.**  The pool slot is the Japanese length + NUL: 8 bytes (7 letters) for most words, 4 bytes (3 letters) for `ｼｴﾛ` and `ﾛｯｻ`, 12 bytes for `ﾌﾞﾗｵｳﾞｨｰｾﾞ`,
  `ｴﾙﾌｼｭﾘｯﾄ`, `ｱｳﾞｧﾝﾂｧｰﾚ`, `ﾊﾟﾚﾝﾃｨｰｱ`, `ﾊﾞﾝﾃﾞｨｯﾂ`.  The art spelling is used wherever it fits the in-place slot.  Nine words are longer than their slot (`Avalanche`, `Monolith`,
  `Topolino`, `Colmillo`, `Corriente`, `Herencia`, `Panthera`: 8-9 letters in 7; `Cielo`, `Rosa`: 5 / 4 letters in 3): the DB (default build) holds the slot-fit short form
  (`Avalanc`, `Monolit`, `Topolin`, `Colmill`, `Corrien`, `Herenci`, `Panther`, `Cie`, `Ros`), and the art spelling is in `translation/refit/` + `forms.tsv`
  (class `club`, cap 9) for `--refit on` builds, where hw relocation lifts the slot.  The commentary clips (75 bytes) and the explanation messages always carry the art spelling.

* The 54 words (index = pool index = logo texture 10823 + index = message index; pool index 0 is `Dummy Team`, which makes the 55 entries of the tables):

| # | `ja` (pool) | Logo | In the DB / default build | `--refit on` | Origin and meaning (art) |
|--:|---|---|---|---|---|
| 1 | `ﾃﾝﾍﾟｽﾄ` | Tempest | `Tempest` |  | English, "great storm" |
| 2 | `ｳﾞｧﾙｶﾝ` | VULLCAN | `Vullcan` |  | English/Latin (Vulcan), "volcano (Roman god of fire)" |
| 3 | `ｱｳﾞｧﾗﾝﾁ` | Avalanche | `Avalanc` | `Avalanche` | English, "avalanche (a rush of snow)" |
| 4 | `ｽﾃｨﾝｸﾞ` | STING | `Sting` |  | English, "a sharp blow" |
| 5 | `ﾓﾉﾘｽ` | MONOLITH | `Monolit` | `Monolith` | English, "monolith / solid rock" |
| 6 | `ﾊﾞﾝﾃﾞｨｯﾂ` | Bandits | `Bandits` |  | English, "outlaws" |
| 7 | `ﾌﾞﾘｯﾂ` | BLITZ | `Blitz` |  | English (from German lightning), "to attack suddenly" |
| 8 | `ｼｭﾊﾞﾙﾂ` | SCHWARZ | `Schwarz` |  | German, "black" |
| 9 | `ﾌﾞﾚｲｽﾞ` | BLAZE | `Blaze` |  | English, "flames" |
| 10 | `ﾌﾞﾙｰｽ` | Blues | `Blues` |  | English, "blue" |
| 11 | `ｼｬﾄﾞｳｽﾞ` | SHADOWS | `Shadows` |  | English, "shadow" |
| 12 | `ﾏﾝﾃｨｽ` | Mantis | `Mantis` |  | English, "mantis" |
| 13 | `ｶﾞｲｽﾄ` | GEIST | `Geist` |  | German, "spirit" |
| 14 | `ﾄｯﾎﾟﾘｰﾉ` | Topolino | `Topolin` | `Topolino` | Italian, "little mouse" |
| 15 | `ｱｰﾍﾟ` | APE | `Ape` |  | Italian, "bee" |
| 16 | `ﾊﾞｼﾞｪｰﾅ` | BALLENA | `Ballena` |  | Spanish, "whale" |
| 17 | `ﾌﾞﾗｵｳﾞｨｰｾﾞ` | Blau Wiese | `Blau Wiese` |  | German, "blue meadow" |
| 18 | `ｼｴﾛ` | CIELO | `Cie` | `Cielo` | Spanish, "sky" |
| 19 | `ｺﾙﾐｰｼﾞｮ` | COLMILLO | `Colmill` | `Colmillo` | Spanish, "fang" |
| 20 | `ｺﾘｴﾝﾃ` | Corriente | `Corrien` | `Corriente` | Spanish, "current (of water)" |
| 21 | `ｴﾙﾌｼｭﾘｯﾄ` | ELF SCHRITT | `Elf Schritt` |  | German, "eleven steps / 11 footsteps" |
| 22 | `ｴｽﾊﾟｰﾀﾞ` | Espada | `Espada` |  | Spanish, "sword" |
| 23 | `ｸﾞﾘｭｯｸ` | GLÜCK | `Gluck` |  | German, "luck / good fortune" |
| 24 | `ｴﾚﾝｼｱ` | HERENCIA | `Herenci` | `Herencia` | Spanish, "legacy / inheritance" |
| 25 | `ｱﾝﾌｨﾆ` | infini | `Infini` |  | French, "infinity" |
| 26 | `ﾗﾝﾎﾟ` | LAMPO | `Lampo` |  | Italian, "lightning / flash" |
| 27 | `ﾚｵｰﾈ` | Leone | `Leone` |  | Italian, "lion" |
| 28 | `ﾗﾝｸｽ` | LYNX | `Lynx` |  | French/English (same spelling), "lynx" |
| 29 | `ﾒｼﾞｪｰﾙ` | MÉGÈRE | `Megere` |  | French, "shrew / termagant" |
| 30 | `ﾐｽﾄﾗﾙ` | MISTRAL | `Mistral` |  | French (Provencal), "mistral (cold strong wind)" |
| 31 | `ﾊﾟﾝﾃｰﾗ` | Panthera | `Panther` | `Panthera` | Latin (genus Panthera), "panther" |
| 32 | `ﾘｯﾁｮ` | RICCIO | `Riccio` |  | Italian, "hedgehog" |
| 33 | `ﾛｯｻ` | ROSA | `Ros` | `Rosa` | Spanish, "rose" |
| 34 | `ﾕﾆｺｰﾝ` | UNICORN | `Unicorn` |  | English, "unicorn (one-horned mythical beast)" |
| 35 | `ｱｳﾛｰﾗ` | Aurora | `Aurora` |  | Italian, "dawn" |
| 36 | `ｱｳﾞｧﾝﾂｧｰﾚ` | AVANZARE | `Avanzare` |  | Italian, "to advance" |
| 37 | `ｴﾙﾄｰﾛ` | EL TORO | `El Toro` |  | Spanish, "the bull" |
| 38 | `ｴｽﾃｰﾗ` | ESTELLA | `Estella` |  | Spanish (name from Latin stella), "star" |
| 39 | `ﾌｪﾘｽ` | FELIZ | `Feliz` |  | Spanish, "happy / fortunate" |
| 40 | `ﾌｫﾙﾃ` | FORTE | `Forte` |  | Italian, "strong" |
| 41 | `ｶﾞｰﾍﾞ` | GABE | `Gabe` |  | German, "gift / talent" |
| 42 | `ｶﾞﾚｵｽ` | Galeos | `Galeos` |  | Greek, "shark" |
| 43 | `ｼﾞｭﾗｰﾚ` | GIURARE | `Giurare` |  | Italian, "to swear" |
| 44 | `ｲｰﾘｽ` | IRIS | `Iris` |  | Greek, "rainbow" |
| 45 | `ﾘｭﾐｴｰﾙ` | LUMIERE | `Lumiere` |  | French, "light" |
| 46 | `ﾐｭｰﾄｽ` | mythos | `Mythos` |  | German/Greek, "myth" |
| 47 | `ﾌﾟﾚｼﾞｰﾙ` | PLAISIR | `Plaisir` |  | French, "pleasure" |
| 48 | `ﾗﾌｧｰﾙ` | RAFALE | `Rafale` |  | French, "gust (of wind)" |
| 49 | `ﾚﾝﾃﾞｨﾙ` | RENDIR | `Rendir` |  | Spanish, "to defeat / subdue" |
| 50 | `ｻﾘｰﾚ` | Salire | `Salire` |  | Italian, "to climb" |
| 51 | `ｽﾌｨｰﾀﾞ` | SFIDA | `Sfida` |  | Italian, "challenge" |
| 52 | `ｼｭﾄﾙﾂ` | STOLZ | `Stolz` |  | German, "pride" |
| 53 | `ﾃｨｸﾞﾚ` | TIGRE | `Tigre` |  | Italian, "tiger" |
| 54 | `ﾊﾟﾚﾝﾃｨｰｱ` | VALENTÍA | `Valentia` |  | Spanish, "courage / bravery" |

* The club shows as `<hometown short name> <word>`: the town part is the English of the municipality cut to its short form
  (`Aogashi`).  The word is the logo spelling (rule above), so it is NOT shortened by a ladder any more; only where the in-place slot is too small does the DB hold a slot-fit
  prefix (`Avalanc`, `Topolin` ...; the art spelling is then the `--refit on` form).  Composed names: 13 characters; words of 9 to 11 letters (`Avalanche`,
  `Corriente`, `Blau Wiese`, `Elf Schritt`) are cut by the guard to 8 letters (`Tsu. Elf Schr`, `Ton. Blau Wie`), see docs/layout-issues.md 9.10.
* **The composer is bounded (stage 3, docs/layout-issues.md section 9):** the club name buffer holds 13 characters + NUL, so the game cuts the
  TOWN, never the word: `town + ' ' + word` over 13 characters becomes `town[:cap-1] + '.' + ' ' + word` with `cap = max(12 - len(word), 4)`
  (`Akabira` + `Tempest` -> `Akab. Tempest`, `Tsurugashima` + `Palentia` -> `Tsu. Palentia`).  A word of up to 8 letters is never cut (the pool has
  words of 3 to 8 letters).  Measured on the real prop6 / prop6r overlays (all 1,248 x 55 pairs): 46.7 % / 48.6 % of the town + word pairs are
  cut (word of 4 letters 17.9 %, 5: 31.3 %, 6: 46.8 %, 7: 65.7 %, 8: 80.9 %), the longest result is 13 characters.  So a SHORTER pool word
  directly keeps more of the town; prefer the shortest form of the ladder above, and give long town short forms a vowel-clean prefix (the cut keeps
  the first `cap - 1` letters).  The former cosmetic shapes (a cut right after a space, dot or hyphen of a town short form: `N. . Topolino`, `Minami-. Arpe`, 916 of 69,298 cut results)
  are FIXED: the 107 town short forms are now letters-only words fused with their direction (`Kitahiro`, `Nishitsuga`, `Minamiaizu`; layout-issues.md 9.9).  Cut shares after the fix: 49.0 % (refit build), 47.1 % (plain build) of the 68,640 town + word pairs; odd shapes in the real composers of prop7 / prop7r: 0.
* Special pool entries keep their meaning: `ﾁｰﾑNOT` -> `No Team`, `ﾏｲﾁｰﾑ` -> `My Team`, `ﾗｲﾊﾞﾙﾁｰﾑ` -> `Rival Team` (12 bytes: `Rival Team`).

### 12.3 Nations, cities, leagues, cups (hw)

* Use the English exonym of section 8.2 (`ﾌﾞﾗｼﾞﾙ` -> `Brazil`, `ｲﾝｸﾞﾗﾝﾄﾞ` -> `England`, `ｿｳﾙ` -> `Seoul`, `ｱﾌﾞﾀﾞﾋﾞ` -> `Abu Dhabi`).
* Competitions: the glossary form (`J1ﾌｧｰｽﾄｽﾃｰｼﾞ` -> `J1 1st Stage`, `Jﾘｰｸﾞｶｯﾌﾟ` -> `J.League Cup`); abbreviations from section 6 when the slot is short
  (8 bytes: `Intl.`, `Cup`).  Fixed-width digits stay ASCII.

### 12.4 Person-name pools and records

* Japanese names from hw readings (`ｱｷﾗ`, `ｲﾜｲ`): Hepburn, no macrons, capitalised (`Akira`, `Iwai`); the order inside a pool entry that holds both
  (`ｶﾜﾓﾄ ｵﾆｼｹﾞ`) is **Given Family** like everywhere (`Onishige Kawamoto`) and follows the ladder of 7.1 (`O. Kawamoto`, `Kawamoto`) in 14-16 byte slots.
* Foreign names written as hw katakana (`ｱﾚｯｻﾝﾄﾞﾛ ﾛｯｼ`): the standard spelling of the person when it is a known player (7.2), else English phonetics; Given Family; same ladder.
* Mixed entries `ﾗｺﾞｽ 武威` (hw family name, kanji given name, naturalised players): `Given Family` = `Takei Lagos`, same ladder.
* Managers and coaches (56 / 112-byte staff records, the Event list): plain person names, no `Mr.` / `Coach`; 12 characters on screen.

### 12.5 Fixed J.League clubs, select / special teams and competitions: the spelling of the logo and banner art (names2, 2026-11-12)

**RULE (user finding, binding, same as the club-word rule of 12.2):** every name that has a picture beside it follows the spelling of that picture.  The readings are
the `F01`-`F33` / `S01`-`S21` rows of `translation/clubwords_art.tsv` (flags `GAME/ALLFLAGS` 10481-10514, club logos `GAME/ALLPNAME` 10730-10757, special teams
`GAME/BINDNAME` 14024-14044, each re-read against the PNGs on 2026-11-12) and, for competitions, the banners `GAME/BINDMTCH` 13905-13941 and the small plates
`ETC_DATA/CPNAMES.TBD` 296-300 (English original art, abbreviated: `ASIA WIN CUP`, `WORLD VS EURO`, `THANKS GIVING`).  Not part of this rule: person names with the same
katakana, sponsor logos, stadium / advert signage and the J.League logo art (never repainted, never copied).

Where a name appears the pass changed it by Japanese source and context:

* **Prose, commentary clips, news / schedule / event strings** (`tools/re/s7n_rules.py`, run by `s7n_plan.py` / `s7n_apply.py`; 779 records, list in `build/s7n_changed_ids.tsv`):
  the art form where it fits (`Red Diamonds`, `JEF United`, `Vissel Kobe`, `Sagan Tosu`, `F.C.Tokyo`, `Yokohama F Marinos`, `Bellmare`, `Sanfrecce`, `Consadole`, `Montedio`,
  `Frontale`, `Hollyhock`).  Only records whose Japanese contains the club / team / competition are touched, so a player with the same letters never changes.
* **Pointer tables of club names** (the team menus; hw pool): the DB keeps the slot-fit form (default build), `translation/refit/` (class `jclub`) carries the art form for
  `--refit on`: `JEF United`, `Vissel Kobe`, `Hollyhock`, `Bellmare`, `Sanfrecce`, `Consadole`, `Montedio`, `Purple Sanga`.  The generator also checks the pixel width of the new
  form against the widest Japanese string of the same table (+1 cell): `Red Diamonds` (139 px against 96 px), `Sagan Tosu`, `F.C.Tokyo` and `Yokohama FC` do not fit those columns and keep
  the short form (`Reds`, `Sagan`, `FCTokyo`, `Yoko.FC`) there, while the commentary clips, the news and the schedule texts have the full art name.  The 8-byte in-place pool of the
  year report (`hwpool`, one record per club in NENREP, 67 for `Marinos`) cannot move and keeps its short form too.
* **East / West / Dream / Euro / World** (flags `EAST`, `WEST`, `DREAM`, `EURO`, `WORLD`): in the team menus the labels are `East`, `West`, `Dream`, `Euro`, `World` (the mode name
  `Dream Club` keeps its English).  In prose the teams are `the Euro team` / `the World team`; the match is `World vs Europe` (banner `WORLD VS EUROPE`, 13912), not `World XI vs European XI`.
* **Special teams** (`BINDNAME` art): `Japanese Stars`, `Asian Stars`, `African Stars`, `N.Euro Stars`, `Balkan Stars`, `Sakatsuku Stars`, `Spanish / French / English / Hollander / Argentine /
  Italian / German / Brazilian Legends`, `Euro Super Stars`, `S.Am. Super Stars`, `Euro Old Stars`, `S.Am. Old Stars`, `The World Stars`, `Dream Stars`, `Wing Farms` (the art `HÖLLANDER`
  is written `Hollander`; accents of the art are folded like in 12.2).
* **Competitions** (banner wording wins where it is a different word, not a different way of writing the same word):

| Japanese | Banner / plate | Was | Now |
|---|---|---|---|
| `ﾌｧﾝ感謝ﾏｯﾁ` | THANKSGIVING MATCH (13924), THANKS GIVING | Fan Appreciation Match / Fan Thanks Match / Thank-You Match | `Thanksgiving Match` (label `Thanksgiving`) |
| `ｱｼﾞｱｳｨﾅｰｽﾞｶｯﾌﾟ` | ASIA WINNERS CUP (13913) | Asian Winners Cup / Asian Winners' Cup / Asia Champ Cup | `Asia Winners Cup` |
| `ﾜｰﾙﾄﾞｳｨﾅｰｽﾞｶｯﾌﾟ` | WORLD WINNERS CUP (13914) | World Winners' Cup / World Champ Cup | `World Winners Cup` |
| `ｱｼﾞｱﾁｬﾚﾝｼﾞｶｯﾌﾟ` | ASIA CHALLENGE CUP (13927) | Asian Challenge Cup | `Asia Challenge Cup` |
| `ｱｼﾞｱﾄｰﾅﾒﾝﾄ` | ASIA TOURNAMENT (13918) | Asian Tournament | `Asia Tournament` |
| `U21 / U22 ｱｼﾞｱﾄｰﾅﾒﾝﾄ` | UNDER22 ASIA TOURNAMENT (13935) | U21 / U22 Asian Tournament | `U22 Asia Tournament` (the art says 22; one clip said 21) |
| `U21 ｲﾝﾀｰﾘｰｸﾞ` | UNDER23 INTER LEAGUE (13936) | U21 Inter-League | `U23 Inter League` |
| `ﾖｰﾛｯﾊﾟｶｯﾌﾟ` | EUROPE CUP (13920) | European Cup | `Europe Cup` |
| `欧州ﾁｬﾚﾝｼﾞﾘｰｸﾞ` | EUROPE CHALLENGE LEAGUE (13930) | European Challenge League | `Europe Challenge League` |
| `南米ﾁｬﾚﾝｼﾞﾘｰｸﾞ` | SOUTH AMERICA CHALLENGE LEAGUE (13931) | South American Challenge League | `South America Challenge League` |
| `ｻｳｽｱﾒﾘｶｶｯﾌﾟ` | SOUTH AMERICA CUP (13921) | South American Cup (prose) | `South America Cup` |
| `ﾌﾟﾚｼｰｽﾞﾝﾏｯﾁ` | PRESEASON MATCH (13938) | Pre-Season / Pre-season Match | `Preseason Match` |
| `世界ｽﾎﾟｰﾂ大会` | WORLD SPORTS FESTIVAL, U23 (13933 / 13934) | World Sports Games / World Games | `World Sports Festival` (table labels: `Sports Festival`, `Sports Fest. Qual.`, `Sports Festival Finals` where the column is short) |
| `世界選抜対欧州選抜` | WORLD VS EUROPE (13912), WORLD VS EURO | World XI vs European XI | `World vs Europe` |
| `世界選抜戦` | - | World XI Match | `World Team Match` |

  Kept as they were, because the art differs only in the way the same word is written: `J.League` (art `J LEAGUE`), `First Stage` / `Second Stage` (art `1st STAGE` / `2nd STAGE`),
  `J.League All-Stars` (art `ALL STAR`), `Qualifiers` (art `QUALIFY`), `Inter-Champ Cup` (the Japanese itself abbreviates; art `INTERNATIONAL CHAMPIONS CUP`), `Net Cup` / `Sega Cup`
  (no art), `Great Club Cup`, `International Cup`, `Golden Cup`, `New Year Cup`, `Platinum League`, `Friendly Match`, `Best Players Match`, `World Champions League`, `World Club Tournament`
  (same as the art).

The 54 + 33 + 21 names of the art, the form in the DB / default build and the form of `--refit on` are listed by `python -I -X utf8 tools/re/s7n_state2.py out.md` (rows: key, art, kind of
record, DB form, effective form with the overlay, record count).
