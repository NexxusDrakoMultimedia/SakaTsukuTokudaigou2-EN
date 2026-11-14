#!/bin/sh
# hng: third bisect disc: text + minimal layout only (everything optional off, proportional font off).  hng_build_bis3.sh SCRATCH_DIR
S="$1"
python -I -X utf8 tools/build_patch.py --repack on --share dup --append-safe --proportional-font off --strict --out build/trial/bis_n --name bis_n --money-format off --club-guard off --textures-dir "$S/empty_tex" > build/trial/bis_n.log 2>&1
echo "bis_n exit $?" >> build/trial/bis_summary.txt
