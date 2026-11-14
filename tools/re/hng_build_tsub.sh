#!/bin/sh
# hng: texture-subset bisect discs: prop8 with money and guard OFF and only subset sN of the textures (build/int/tsub/sN).
# Usage: sh tools/re/hng_build_tsub.sh
for n in 1 2 3 4; do
  python -I -X utf8 tools/build_patch.py --repack on --share dup --append-safe --proportional-font on --strict \
    --out build/trial/bis_s$n --name bis_s$n --money-format off --club-guard off \
    --textures-dir build/int/tsub/s$n > build/trial/bis_s$n.log 2>&1
  echo "bis_s$n exit $?" >> build/trial/bis_summary.txt
done
