import io
p = 'doc/TRANSLATORS_NOTES.md'
t = io.open(p, encoding='utf-8', newline='').read()
reps = [
 ("(`Kimo Kawamoto`, not Kawamoto Kimo)", "(`Katsuo Ozaka`, not Ozaka Katsuo)"),
 ("then the dan ranks start (`1-dan`, ..., `7-dan`)", "then the dan ranks start (`1-dan`, ..., `9-dan`)"),
 ("(`Kashima Antlers`,\n`Yokohama F. Marinos`)", "(`Kashima Antlers`,\n`F. Marinos`)"),
 ("a list of 55 invented words (Mythos, Tempest, Palentia,\nTopolino and so on), either `Town Word` or `Word Town`. The words are made-up Latin-sounding names, like real clubs'\nnames, and are spelt by sound.",
  "a list of 55 short words (Mythos, Tempest, Palentia,\nTopolino and so on), either `Town Word` or `Word Town`. They are club-style tags, like the second half of real clubs'\nnames, and invented ones are spelt by sound."),
 ("`Att.`, `Contr.`, `Wk`, `STA`, `SPD` and shortened names", "`Att.`, `Wk`, `Comm:` and shortened names"),
]
for a, b in reps:
    if a not in t:
        print('MISSING', a[:50]); continue
    t = t.replace(a, b, 1)
io.open(p, 'w', encoding='utf-8', newline='').write(t)
