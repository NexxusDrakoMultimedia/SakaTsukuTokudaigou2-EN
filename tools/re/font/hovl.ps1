# usage: hovl.ps1 <program> <outfile> <args...>   Dec.java in ghproj_fonthook
param([string]$prog, [string]$out, [Parameter(ValueFromRemainingArguments=$true)][string[]]$a)
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-25.0.5.8-hotspot'; $env:PATH="$env:JAVA_HOME\bin;$env:PATH"
$d=$PSScriptRoot
& "$env:GHIDRA_HOME\support\analyzeHeadless.bat" "$env:GHIDRA_PROJECTS\ghproj_fonthook" sakatsuku -process $prog -noanalysis -readOnly -scriptPath $d -postScript Dec.java "$d\$out" @a 2>&1 | Select-String 'ERROR|Exception'
