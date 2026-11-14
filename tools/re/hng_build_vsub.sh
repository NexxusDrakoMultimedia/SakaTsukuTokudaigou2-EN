#!/bin/sh
# hng: third-level texture bisect discs bis_v1..v3 (one texture file each; money and guard OFF).  Usage: sh tools/re/hng_build_vsub.sh
for n in 1 2 3; do
  python -I -X utf8 tools/build_patch.py --repack on --share dup --append-safe --proportional-font on --strict \
    --out build/trial/bis_v$n --name bis_v$n --money-format off --club-guard off \
    --textures-dir build/int/tsub/v$n > build/trial/bis_v$n.log 2>&1
  echo "bis_v$n exit $?" >> build/trial/bis_summary.txt
done
