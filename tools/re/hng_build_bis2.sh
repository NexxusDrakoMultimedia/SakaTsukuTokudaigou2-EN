#!/bin/sh
# hng: second set of bisect discs (add-one-in on top of bis_e, texture subsets).  Run from the repo root: hng_build_bis2.sh SCRATCH_DIR
# SCRATCH_DIR holds empty_tex/ and t1..t4/ (copies of subsets of translation/textures; see docs/hang-investigation.md).
S="$1"
STD="--repack on --share dup --append-safe --proportional-font on --strict"
run() { name="$1"; shift
  python -I -X utf8 tools/build_patch.py $STD --out build/trial/$name --name $name "$@" > build/trial/$name.log 2>&1
  echo "$name exit $?" >> build/trial/bis_summary.txt; }
run bis_f --club-guard off --textures-dir "$S/empty_tex"
run bis_g --money-format off --textures-dir "$S/empty_tex"
run bis_h --money-format off --club-guard off
run bis_i --money-style western --club-guard off --textures-dir "$S/empty_tex"
run bis_j --money-format off --club-guard off --textures-dir "$S/t1"
run bis_k --money-format off --club-guard off --textures-dir "$S/t2"
run bis_l --money-format off --club-guard off --textures-dir "$S/t3"
run bis_m --money-format off --club-guard off --textures-dir "$S/t4"
