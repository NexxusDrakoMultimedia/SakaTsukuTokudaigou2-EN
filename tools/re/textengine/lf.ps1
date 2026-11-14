param([string]$prog, [string]$out, [string]$lo, [string]$hi)
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-25.0.5.8-hotspot'; $env:PATH="$env:JAVA_HOME\bin;$env:PATH"
$d=$PSScriptRoot
& "$env:GHIDRA_HOME\support\analyzeHeadless.bat" "$env:GHIDRA_PROJECTS\ghproj_textengine" sakatsuku -process $prog -noanalysis -readOnly -scriptPath $d -postScript ListF.java "$d\$out" $lo $hi 2>&1 | Select-String 'ERROR|Exception'
