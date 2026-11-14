# Launch Flycast with a Lua scenario and place its window on the vertical monitor (DISPLAY3).
# Usage (from the repository root):
#   powershell -File tools/emu/launch.ps1 -Disc <cue/gdi> [-Lua <harness .lua, repo-relative or absolute>] [-Screen DISPLAY3]
# Environment (all optional except the disc):
#   SAKATSUKU_DISC   the disc to start when -Disc is not given
#   FLYCAST_DIR      the Flycast folder that holds flycast.exe (default C:\Games\Emulators\Flycast)
# The repository root is taken from this script's location and handed to the Lua scripts as SAKATSUKU_ROOT.
param(
  [string]$Disc = $env:SAKATSUKU_DISC,
  [string]$Lua  = '',
  [string]$Screen = 'DISPLAY3'
)
if (-not $Disc) { throw 'give the disc with -Disc <.cue/.gdi> (or set SAKATSUKU_DISC)' }
$Disc = (Resolve-Path -LiteralPath $Disc).Path          # Flycast is started in its own folder: pass an absolute path
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Flycast = if ($env:FLYCAST_DIR) { $env:FLYCAST_DIR } else { 'C:\Games\Emulators\Flycast' }
if (-not $Lua) { $Lua = Join-Path $PSScriptRoot 'harness.lua' }
elseif (-not [System.IO.Path]::IsPathRooted($Lua)) { $Lua = (Resolve-Path -LiteralPath $Lua).Path }
# Flycast takes the Lua path relative to its own folder (as before); fall back to the absolute path where that is not available.
try { $LuaArg = [System.IO.Path]::GetRelativePath($Flycast, $Lua) } catch { $LuaArg = $Lua }
$env:SAKATSUKU_ROOT = $Root
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System; using System.Runtime.InteropServices;
public class P { [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int w, int hgt, uint f); }
"@
Get-Process flycast -ErrorAction SilentlyContinue | Stop-Process -Force
$p = Start-Process (Join-Path $Flycast 'flycast.exe') -ArgumentList @('-config',"config:LuaFileName=$LuaArg","`"$Disc`"") -WorkingDirectory $Flycast -PassThru
$scr = [System.Windows.Forms.Screen]::AllScreens | Where-Object { $_.DeviceName -like "*$Screen" } | Select-Object -First 1
for ($i = 0; $i -lt 60; $i++) {
  Start-Sleep -Milliseconds 500; $p.Refresh()
  if ($p.MainWindowHandle -ne 0 -and $p.MainWindowTitle -like 'Flycast*') { break }
}
if ($scr) {
  $w = 1000; $h = 800
  $x = $scr.Bounds.X + [int](($scr.Bounds.Width - $w) / 2); $y = $scr.Bounds.Y + 120
  [void][P]::SetWindowPos($p.MainWindowHandle, [IntPtr]::Zero, $x, $y, $w, $h, 0x0040)   # SWP_SHOWWINDOW
  "placed on $Screen at $x,$y ${w}x$h"
} else { "screen $Screen not found; left in place" }
"pid $($p.Id)"
