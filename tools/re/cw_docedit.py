"""One-off doc edits for the club-word art rule (idempotent: each replacement is skipped when already applied).
usage: python -I -X utf8 tools/re/cw_docedit.py"""
import io
def sub(path, old, new):
    t = open(path, encoding='utf8', newline='').read()
    if new in t:
        print('already', path, old[:40]); return
    assert old in t, (path, old[:60])
    open(path, 'w', encoding='utf8', newline='').write(t.replace(old, new, 1)); print('edited', path, old[:40])

sub('docs/style-guide.md',
    "* The club shows as `<hometown short name> <word>`: the town part is the English of the municipality cut to its short form\n  (`Aogashi`), so the pool word is the part with the budget: **<= 7 characters**.  Ladder when the phonetic spelling is longer:\n  1. standard spelling; 2. drop a doubled consonant (`Rendill` -> `Rendil`); 3. drop a final vowel that is not stressed;\n  4. replace `-ia` / `-io` with `-a` / `-o`; stop at the first that fits.  Never cut a word in the middle.\n",
    "\n* The club shows as `<hometown short name> <word>`: the town part is the English of the municipality cut to its short form\n  (`Aogashi`).  The word is the logo spelling (rule above), so it is NOT shortened by a ladder any more; only where the in-place slot is too small does the DB hold a slot-fit\n  prefix (`Avalanc`, `Topolin` ...; the art spelling is then the `--refit on` form).  Composed names: 13 characters; words of 9 to 11 letters (`Avalanche`,\n  `Corriente`, `Blau Wiese`, `Elf Schritt`) are cut by the guard to 8 letters (`Tsu. Elf Schr`, `Ton. Blau Wie`), see docs/layout-issues.md 9.10.\n")
sub('docs/style-guide.md',
    "| Club-name pool (`hwptr`, 55 names, `ﾐｭｰﾄｽ`, `ｻﾘｰﾚ`, `ﾀﾞﾐｰﾁｰﾑ` ...) | invented Latin-sounding word, 3-9 kana | **8** (a few 4 / 12) | **7** (3 / 11) | see 12.2 |",
    "| Club-name pool (`hwptr`, 55 names, `ﾐｭｰﾄｽ`, `ｻﾘｰﾚ`, `ﾀﾞﾐｰﾁｰﾑ` ...) | foreign word printed in the logo art, 3-9 kana | **8** (a few 4 / 12) | **7** (3 / 11); the art spelling is longer for 9 words | see 12.2 (logo rule) |")
sub('doc/TRANSLATORS_NOTES.md',
    "names, and invented ones are spelt by sound.",
    "names. Each word is spelt exactly as the club logo shows it (`Blues`, `Ape`, `Vullcan`, `Estella`); the logo is shown next to the text.\nIn the default build a few long words are shortened to fit their slot (`Avalanc`, `Panther`); a build with the refit option prints them in full.")
