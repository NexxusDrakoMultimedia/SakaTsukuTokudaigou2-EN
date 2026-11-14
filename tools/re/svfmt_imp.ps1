param([string]$name)
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-25.0.5.8-hotspot'; $env:PATH="$env:JAVA_HOME\bin;$env:PATH"
$r=(Resolve-Path "$PSScriptRoot\..\..").Path; $p="$r\build\svfmt\proj"; New-Item -ItemType Directory -Force $p | Out-Null
& "$env:GHIDRA_HOME\support\analyzeHeadless.bat" $p svf -import "$r\build\svfmt\$name.img" -processor 'SuperH4:LE:32:default' -loader BinaryLoader -loader-baseAddr 0x8c010000 -noanalysis -overwrite 2>&1 | Select-String 'ERROR|Exception|Import'
