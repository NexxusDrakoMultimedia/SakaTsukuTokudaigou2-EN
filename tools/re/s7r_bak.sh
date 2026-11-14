#!/bin/sh
# s7r_bak.sh FILE... : copy translation/textures files to build/s7/bak/ (flattened names, once)
for f in "$@"; do
  n=$(echo "$f" | sed 's#translation/textures/##; s#/#__#g')
  [ -e "build/s7/bak/$n" ] || cp -p "$f" "build/s7/bak/$n"
done
