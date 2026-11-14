import json
clr = {'mode': 'clear'}
sc = {'font': ['segoe-ui-semibold', 'arial-bold'], 'gradient': [[0, '#fff4cc'], [0.5, '#ffc860'], [1, '#f08800']], 'outline': {'color': '#6a3800', 'width': 0.5}}
d = {'texture': '36800', 'supersample': 4, 'quantize': 'argb4444', 'styles': {'sc': sc}, 'regions': [
  {'id': 'scorer', 'ja': '得点者', 'text': 'Scorer', 'x': 100, 'y': 151, 'w': 84, 'h': 24, 'style': 'sc', 'erase': clr, 'align': 'center', 'size': 'auto', 'max_size': 18}]}
json.dump(d, open('tools/re/art6/36800.json', 'w', encoding='utf8'), indent=1, ensure_ascii=False)
wh = {'font': ['arial-bold-italic'], 'gradient': [[0, '#ffffff'], [1, '#d8d8e8']], 'outline': {'color': '#202020', 'width': 0.5},
      'shadow': {'color': '#000000', 'dx': 1.5, 'dy': 1.5, 'alpha': 1.0}}
def R(id, ja, en, x, y, w, h):
    return {'id': id, 'ja': ja, 'text': en, 'x': x, 'y': y, 'w': w, 'h': h, 'style': 'wh', 'erase': clr, 'align': 'left', 'size': 'auto',
            'max_size': 16, 'min_sx': 0.75}
d = {'texture': '03266', 'supersample': 4, 'quantize': 'argb4444', 'styles': {'wh': wh}, 'regions': [
  R('weak', '弱点', 'Weakness', 8, 139, 62, 24), R('sell', 'セールスポイント', 'Selling Point', 73, 139, 110, 24),
  R('comp', '不満', 'Complaint', 8, 169, 62, 24), R('club', 'クラブへ意見', 'Club Feedback', 75, 169, 106, 24)]}
json.dump(d, open('tools/re/art6/03266.json', 'w', encoding='utf8'), indent=1, ensure_ascii=False)
