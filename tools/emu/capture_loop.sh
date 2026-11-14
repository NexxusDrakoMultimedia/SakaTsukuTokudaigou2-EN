#!/bin/bash
# Capture only the Flycast window every N seconds while it is running. Usage: capture_loop.sh <outdir> [interval]
out="$1"; iv="${2:-4}"; mkdir -p "$out"; rm -f "$out"/f_*.png; i=0
while powershell -NoProfile -Command "if(Get-Process flycast -ErrorAction SilentlyContinue){exit 0}else{exit 1}"; do
  powershell -NoProfile -File "$(dirname "$0")/shot.ps1" "$(cygpath -w "$out")\f_$(printf %03d $i).png" >/dev/null 2>&1
  i=$((i+1)); sleep "$iv"
done
echo frames=$i
