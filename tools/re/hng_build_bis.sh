#!/bin/sh
# hng: build the five bisect trial discs (bis_a .. bis_e) sequentially.  Run from the repo root.
# Standard flags: --repack on --share dup --append-safe --proportional-font on --strict
EMPTY="$1"
STD="--repack on --share dup --append-safe --proportional-font on --strict"
run() { name="$1"; shift
  python -I -X utf8 tools/build_patch.py $STD --out build/trial/$name --name $name "$@" > build/trial/$name.log 2>&1
  echo "$name exit $?" >> build/trial/bis_summary.txt; }
: > build/trial/bis_summary.txt
run bis_e --money-format off --club-guard off --textures-dir "$EMPTY"
run bis_a --money-format off
run bis_b --club-guard off
run bis_c --textures-dir "$EMPTY"
run bis_d --proportional-font off
