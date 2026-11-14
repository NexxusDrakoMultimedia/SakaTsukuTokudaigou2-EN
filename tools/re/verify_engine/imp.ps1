param([string]$file, [string]$base)
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-25.0.5.8-hotspot'; $env:PATH="$env:JAVA_HOME\bin;$env:PATH"
& "$env:GHIDRA_HOME\support\analyzeHeadless.bat" "$env:GHIDRA_PROJECTS\ghproj_verify_engine" sakatsuku -import $file -processor 'SuperH4:LE:32:default' -loader BinaryLoader -loader-baseAddr $base -noanalysis -overwrite 2>&1 | Select-String 'ERROR|Exception|Import'
