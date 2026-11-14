# Capture ONLY the Flycast window (never the full desktop). Usage: shot.ps1 <out.png>
param([string]$Out)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class W { [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
 [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
 public struct RECT { public int L,T,R,B; } }
"@
$p = Get-Process flycast -ErrorAction Stop | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
$r = New-Object W+RECT; [void][W]::GetWindowRect($p.MainWindowHandle, [ref]$r)
$w = $r.R - $r.L; $h = $r.B - $r.T
$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp); $dc = $g.GetHdc()
[void][W]::PrintWindow($p.MainWindowHandle, $dc, 2); $g.ReleaseHdc($dc)
$bmp.Save($Out); "saved ${w}x${h}"
