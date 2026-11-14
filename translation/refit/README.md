# translation/refit: opt-in re-fit overlays

The main database (`translation/*.jsonl`) keeps one English per Japanese string.  For the half-width pools (club words, nations,
cities, name parts) that English was chosen to fit the smallest slot the string ever sat in, so it is often a rough short form
(`Sie`, `Ros`, `Rumostk`, `Arg.`, `Casab.`, `Kat`).  Since half-width strings can be relocated (`build_patch --hw-relocate on`,
docs/hw-relocation.md) a better form can be written.  These overlays carry the better forms; they are applied on top of the
loaded DB only when the build asks for it, so the default build is unchanged.

* `FLOW_PRG__X.BIN.jsonl`, `ATFIRST__X.BIN.jsonl` ... one overlay per source, one record per line:
  `{"id", "ja", "en", "why", "cls"}`.  `id` / `ja` identify the DB record (a stale `ja` is skipped), `en` replaces the DB `en`
  (nothing else of the record changes), `why` names the authority and the old form, `cls` selects the caps
  (`club` <= 8 characters, `person` <= 12, pixel width <= the widest Japanese string of the same pointer table + 1 cell).
* `forms.tsv`: the curated source forms (club words, J.League names, nations, cities, cups, places, persons).  Not read by the build.
* `_report.txt`: what was placed and what could not be (reason).  Ignored by the loader (files starting with `_` are skipped).
* API: `tools/refit.py` -> `refit.load_overlays(db_by_source, relocate=True)`.  Check: `python -I -X utf8 tools/refit.py validate --sim`,
  `python -I -X utf8 tools/test_refit.py`.  Regenerate after the DB changed: `python -I -X utf8 tools/re/rfit_gen.py` (about 15 minutes:
  it applies everything and drops the lowest-priority forms of every overlay that gains a failure in the real build code, until the pool of every overlay places every form).

The overlays never replace a record that would fail the build: with `relocate=False` (hw relocation off) forms that do not fit the
in-place slot are skipped, and every kept record was simulated with `build_patch.do_overlay / do_extra`.
