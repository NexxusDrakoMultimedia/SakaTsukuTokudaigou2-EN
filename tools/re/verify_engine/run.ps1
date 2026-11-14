[CmdletBinding()]param([string]$prog, [string]$script, [string]$out, [Parameter(ValueFromRemainingArguments=$true)][string[]]$a)
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-25.0.5.8-hotspot'; $env:PATH="$env:JAVA_HOME\bin;$env:PATH"
$d=$PSScriptRoot
& "$env:GHIDRA_HOME\support\analyzeHeadless.bat" "$env:GHIDRA_PROJECTS\ghproj_verify_engine" sakatsuku -process $prog -noanalysis -scriptPath $d -postScript $script "$d\$out" @a 2>&1 | Select-String 'ERROR|Exception'
