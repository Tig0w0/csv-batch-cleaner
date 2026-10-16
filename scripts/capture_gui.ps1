Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Snapshot {
  [StructLayout(LayoutKind.Sequential)]
  public struct RECT { public int Left, Top, Right, Bottom; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hwnd, int command);
}
'@
$root = 'C:\automation\csv-cleaner-portfolio'
$p = Start-Process -FilePath (Get-Command pythonw.exe).Source -WorkingDirectory $root -ArgumentList 'gui.py' -PassThru
try {
  Start-Sleep -Seconds 3
  $p.Refresh()
  $hwnd = $p.MainWindowHandle
  if ($hwnd -eq [IntPtr]::Zero) { throw 'GUI window unavailable' }
  [Snapshot]::ShowWindow($hwnd, 9) | Out-Null
  $rect = New-Object Snapshot+RECT
  [Snapshot]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
  $width = $rect.Right - $rect.Left
  $height = $rect.Bottom - $rect.Top
  $bitmap = New-Object System.Drawing.Bitmap($width, $height)
  $gfx = [System.Drawing.Graphics]::FromImage($bitmap)
  try {
    $hdc = $gfx.GetHdc()
    try {
      $ok = [Snapshot]::PrintWindow($hwnd, $hdc, 2)
    } finally {
      $gfx.ReleaseHdc($hdc)
    }
    if (-not $ok) { throw 'PrintWindow failed' }
    $bitmap.Save((Join-Path $root 'assets\gui-preview.png'), [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output "Captured GUI PrintWindow ($width x $height)"
  } finally {
    $gfx.Dispose()
    $bitmap.Dispose()
  }
} finally {
  if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
}
