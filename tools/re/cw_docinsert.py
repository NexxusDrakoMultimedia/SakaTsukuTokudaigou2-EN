"""Insert build/cw/doctable.md at the CW-TABLE marker of docs/style-guide.md (idempotent).  usage: python -I -X utf8 tools/re/cw_docinsert.py"""
p = 'docs/style-guide.md'
t = open(p, encoding='utf8', newline='').read()
tab = open('build/cw/doctable.md', encoding='utf8').read().rstrip('\n')
if '<!-- CW-TABLE -->' in t:
    open(p, 'w', encoding='utf8', newline='').write(t.replace('<!-- CW-TABLE -->', tab, 1)); print('inserted')
else:
    print('marker not found')
