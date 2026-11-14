#!/bin/sh
# hng: second-level texture bisect discs bis_u1..u3 (money and guard OFF, subset of the s1 textures).  Usage: sh tools/re/hng_build_usub.sh
for n in 1 2 3; do
  python -I -X utf8 tools/build_patch.py --repack on --share dup --append-safe --proportional-font on --strict \
    --out build/trial/bis_u$n --name bis_u$n --money-format off --club-guard off \
    --textures-dir build/int/tsub/u$n > build/trial/bis_u$n.log 2>&1
  echo "bis_u$n exit $?" >> build/trial/bis_summary.txt
done
