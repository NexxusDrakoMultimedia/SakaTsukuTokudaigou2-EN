param([string]$out, [string]$aa)
$a = $aa -split ","
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-25.0.5.8-hotspot'; $env:PATH="$env:JAVA_HOME\bin;$env:PATH"
$d=$PSScriptRoot
& "$env:GHIDRA_HOME\support\analyzeHeadless.bat" "$env:GHIDRA_PROJECTS\ghproj_bank" sakatsuku -process 1ST_READ.BIN -noanalysis -readOnly -scriptPath $d -postScript Dec.java "$d\$out" @a 2>&1 | Select-String 'ERROR|Exception|rror'
