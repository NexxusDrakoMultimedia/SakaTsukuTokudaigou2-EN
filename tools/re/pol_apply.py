"""pol: give the 107 town short forms that contain a space, hyphen or dot a clean, letters-only form that survives the
club-name cut (docs/layout-issues.md section 9.3: the composer keeps short[:cap-1] + '.').
Convention = the one the table already uses for `Kamiiso`, `Shimokita`, `Nishitama`, `Higashiiwai`: direction word FUSED to the
place (Kita, Minami, Higashi, Nishi, Naka, Kami, Shimo), the place part cut on a vowel when the 12-byte slot (11 letters) is too small.
    python -I -X utf8 tools/re/pol_apply.py          dry run: prints the changes and checks
    python -I -X utf8 tools/re/pol_apply.py --write  rewrites the `en` text of those records in HOMETOWN.BIN.jsonl and in the library copies of the table in the other overlay files
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(ROOT, 'translation', 'FLOW_PRG__HOMETOWN.BIN.jsonl')
# table index -> (ja, new en)
NEW = {
    32: ('北広島市', 'Kitahiro'), 85: ('北津軽郡', 'Kitatsugaru'), 91: ('中津軽郡', 'Nakatsugaru'),
    92: ('西津軽郡', 'Nishitsuga'), 94: ('東津軽郡', 'Higashitsu'), 97: ('南津軽郡', 'Minamitsuga'),
    169: ('北村山郡', 'Kitamuraya'), 177: ('西置賜郡', 'Nishiokita'), 178: ('西田川郡', 'Nishitagawa'),
    179: ('西村山郡', 'Nishimuraya'), 180: ('東置賜郡', 'Higashioki'), 181: ('東田川郡', 'Higashitaga'),
    183: ('東村山郡', 'Higashimura'), 204: ('西白河郡', 'Nishishira'), 207: ('東白川郡', 'Higashishi'),
    210: ('南会津郡', 'Minamiaizu'), 221: ('北相馬郡', 'Kitasoma'), 236: ('西茨城郡', 'Nishiibara'),
    237: ('東茨城郡', 'Higashiiba'), 273: ('北群馬郡', 'Kitagunma'), 301: ('北足立郡', 'Kitaadachi'),
    303: ('北埼玉郡', 'Kitasaitama'), 327: ('東松山市', 'Higashimat'), 334: ('南埼玉郡', 'Minamisaita'),
    417: ('東久留米市', 'Higashikuru'), 418: ('東村山市', 'Higashimura'), 419: ('東大和市', 'Higashiyam'),
    428: ('武蔵村山市', 'Musashimura'), 431: ('足柄上郡', 'Kamiashiga'), 432: ('足柄下郡', 'Shimoashiga'),
    452: ('南足柄市', 'Minamiashi'), 460: ('利島村', 'Toshima'), 472: ('北魚沼郡', 'Kitauonuma'),
    473: ('北蒲原郡', 'Kitakanbara'), 486: ('中魚沼郡', 'Nakauonuma'), 488: ('中蒲原郡', 'Nakakanbara'),
    489: ('中頸城郡', 'Nakakubiki'), 492: ('西蒲原郡', 'Nishikanba'), 493: ('西頸城郡', 'Nishikubiki'),
    494: ('東蒲原郡', 'Higashikan'), 495: ('東頸城郡', 'Higashikubi'), 497: ('南魚沼郡', 'Minamiuonu'),
    498: ('南蒲原郡', 'Minamikanba'), 504: ('上新川郡', 'Kaminiikawa'), 506: ('下新川郡', 'Shimoniika'),
    511: ('中新川郡', 'Nakaniikawa'), 513: ('西砺波郡', 'Nishitonami'), 515: ('東砺波郡', 'Higashitona'),
    552: ('北都留郡', 'Kitatsuru'), 553: ('北巨摩郡', 'Kitakoma'), 556: ('中巨摩郡', 'Nakakoma'),
    557: ('西八代郡', 'Nishiyatsu'), 559: ('東山梨郡', 'Higashiyam'), 560: ('東八代郡', 'Higashiyat'),
    562: ('南都留郡', 'Minamitsuru'), 563: ('南巨摩郡', 'Minamikoma'), 571: ('上伊那郡', 'Kamiina'),
    572: ('上高井郡', 'Kamitakai'), 573: ('上水内郡', 'Kamiminochi'), 575: ('北安曇郡', 'Kitaazumi'),
    576: ('北佐久郡', 'Kitasaku'), 583: ('下伊那郡', 'Shimoina'), 584: ('下高井郡', 'Shimotakai'),
    585: ('下水内郡', 'Shimomino'), 594: ('東筑摩郡', 'Higashichi'), 596: ('南安曇郡', 'Minamiazumi'),
    597: ('南佐久郡', 'Minamisaku'), 689: ('北設楽郡', 'Kitashitara'), 709: ('西春日井郡', 'Nishikasuga'),
    711: ('西加茂郡', 'Nishikamo'), 720: ('南設楽郡', 'Minamishita'), 820: ('東大阪市', 'Higashiosa'),
    825: ('南河内郡', 'Minamikawa'), 876: ('北葛城郡', 'Kitakatsu'), 898: ('西牟婁郡', 'Nishimuro'),
    900: ('東牟婁郡', 'Higashimuro'), 978: ('東広島市', 'Higashihiro'), 1001: ('新南陽市', 'Shinnanyo'),
    1052: ('北宇和郡', 'Kitauwa'), 1056: ('西宇和郡', 'Nishiuwa'), 1058: ('東宇和郡', 'Higashiuwa'),
    1061: ('南宇和郡', 'Minamiuwa'), 1131: ('西松浦郡', 'Nishimatsu'), 1132: ('東松浦郡', 'Higashimat'),
    1138: ('上県郡', 'Kamiaga'), 1139: ('北高来郡', 'Kitatakaku'), 1140: ('北松浦郡', 'Kitamatsu'),
    1143: ('下県郡', 'Shimoag'), 1145: ('西彼杵郡', 'Nishisonogi'), 1146: ('東彼杵郡', 'Higashisono'),
    1150: ('南高来郡', 'Minamitaka'), 1151: ('南松浦郡', 'Minamimatsu'), 1160: ('上益城郡', 'Kamimashiki'),
    1165: ('下益城郡', 'Shimomashi'), 1181: ('北海部郡', 'Kitaamabe'), 1189: ('西国東郡', 'Nishikuni'),
    1193: ('東国東郡', 'Higashikuni'), 1196: ('南海部郡', 'Minamiamabe'), 1198: ('北諸県郡', 'Kitamoroka'),
    1203: ('西臼杵郡', 'Nishiusuki'), 1204: ('西諸県郡', 'Nishimoroka'), 1208: ('東諸県郡', 'Higashimoro'),
    1209: ('東臼杵郡', 'Higashiusu'), 1210: ('南那珂郡', 'Minaminaka'), 1234: ('種子島', 'Tane'),
    1238: ('屋久島', 'Yaku'), 1249: ('久米島', 'Kume'),
}
CTX = re.compile(r'tbl@43858\[(\d+)/1270\]')

CTX_ANY = re.compile(r'tbl@([0-9a-f]+)\[(\d+)/(12[67]\d)\]')   # 1270 slots; CSAVE3.BIN carries a 1268-slot copy
BY_JA = None


def files():
    """every translation file that carries a 1270-entry pointer table (HOMETOWN.BIN and the library copies in the other overlays)"""
    out = []
    for fn in sorted(os.listdir(os.path.join(ROOT, 'translation'))):
        if fn.endswith('.jsonl'):
            p = os.path.join(ROOT, 'translation', fn)
            with open(p, encoding='utf-8', newline='') as fh:
                if CTX_ANY.search(fh.read()):
                    out.append(p)
    return out


def process(path):
    """-> (new text, changes, errors) for one file.  A record is changed only when its ja equals the expected ja of that table index and
    its en is the recorded OLD form (or already the new one): a 1270-table that is not the town short table is never touched."""
    from pol_old import OLD
    with open(path, encoding='utf-8', newline='') as fh:
        lines = fh.read().split('\n')
    out, changes, errs = [], [], []
    per_table = {}
    for ln in lines:
        if not ln.strip():
            out.append(ln)
            continue
        r = json.loads(ln)
        m = CTX_ANY.search(r.get('ctx') or '')
        k = {v[0]: kk for kk, v in NEW.items()}.get(r['ja']) if m else None   # the table index differs per copy (CSAVE3: 30 for 32): key on the ja
        if k is not None:
            ja, new = NEW[k]
            if r['ja'] == ja and r['en'] in (OLD[k][1], new):
                if not re.fullmatch(r'[A-Z][a-z]+', new):
                    errs.append('%s %d not a plain word: %r' % (path, k, new))
                if len(new) + 1 > r['max_bytes']:
                    errs.append('%s %d %r exceeds slot %d' % (path, k, new, r['max_bytes']))
                per_table.setdefault(m.group(1), {}).setdefault(ja, set()).add(new)
                if r['en'] != new:
                    key = '"en":' + json.dumps(r['en'], ensure_ascii=False)
                    if ln.count(key) != 1:
                        errs.append('%s %d cannot find %s in line' % (path, k, key))
                    else:
                        ln = ln.replace(key, '"en":' + json.dumps(new, ensure_ascii=False))
                        changes.append((os.path.basename(path), r['id'], k, ja, r['en'], new, r['max_bytes']))
            elif r['ja'] == ja and any(c in r['en'] for c in ' -.'):
                errs.append('%s %d %s has an unexpected old form %r (not the recorded %r)' % (path, k, ja, r['en'], OLD[k][1]))
        out.append(ln)
    for t, g in per_table.items():
        for ja, s in g.items():
            if len(s) > 1:
                errs.append('%s table %s: same-ja conflict %s %s' % (path, t, ja, s))
    return '\n'.join(out), changes, errs


def main():
    write = '--write' in sys.argv
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    total, allerr, todo = 0, [], []
    for p in files():
        text, ch, errs = process(p)
        total += len(ch)
        allerr += errs
        if ch:
            todo.append((p, text))
            print('%-36s %3d records' % (os.path.basename(p), len(ch)))
    print('files with changes %d, records changed %d, errors %d' % (len(todo), total, len(allerr)))
    for e in allerr:
        print('ERROR', e)
    if allerr:
        return 1
    if write:
        for p, text in todo:
            with open(p, 'w', encoding='utf-8', newline='') as fh:
                fh.write(text)
        print('written %d files' % len(todo))
    return 0


if __name__ == '__main__':
    sys.exit(main())
