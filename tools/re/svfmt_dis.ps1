param([string]$prog, [string]$out, [string]$aa)
$a = $aa -split ","
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-25.0.5.8-hotspot'; $env:PATH="$env:JAVA_HOME\bin;$env:PATH"
$r=(Resolve-Path "$PSScriptRoot\..\..").Path
& "$env:GHIDRA_HOME\support\analyzeHeadless.bat" "$r\build\svfmt\proj" svf -process "$prog" -noanalysis -readOnly -scriptPath "$r\tools\re\capacity\bank" -postScript Dis.java "$r\build\svfmt\$out" @a 2>&1 | Select-String 'ERROR|Exception|rror'
