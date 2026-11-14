param([string]$name, [string]$base)
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-25.0.5.8-hotspot'; $env:PATH="$env:JAVA_HOME\bin;$env:PATH"
$r=(Resolve-Path "$PSScriptRoot\..\..").Path; $p="$r\build\svfmt\proj"
Copy-Item "$r\extracted\FLOW_PRG\$name.BIN" "$r\build\svfmt\ov_$name.bin" -Force
& "$env:GHIDRA_HOME\support\analyzeHeadless.bat" $p svf -import "$r\build\svfmt\ov_$name.bin" -processor 'SuperH4:LE:32:default' -loader BinaryLoader -loader-baseAddr $base -overwrite 2>&1 | Select-String 'ERROR|Exception|Import|Analysis|REPORT'
