param([string]$out, [Parameter(ValueFromRemainingArguments=$true)][string[]]$a)
# ovmem: run the existing Dec.java (tools/re/capacity/memmap) read-only on the memmap Ghidra project copy
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-25.0.5.8-hotspot'; $env:PATH="$env:JAVA_HOME\bin;$env:PATH"
$d=(Join-Path $PSScriptRoot 'capacity\memmap')
& "$env:GHIDRA_HOME\support\analyzeHeadless.bat" "$env:GHIDRA_PROJECTS\ghproj_memmap" sakatsuku -process 1ST_READ.BIN -noanalysis -readOnly -scriptPath $d -postScript Dec.java $out @a 2>&1 | Select-String 'ERROR|Exception'
