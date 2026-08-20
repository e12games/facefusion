$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$pack = Join-Path (Split-Path -Parent $repo) '脸幻中文便携版'
$iss = Join-Path $repo 'installer\lianhuan.iss'
if (-not (Test-Path $iss)) { throw "missing $iss" }
attrib -h "$pack\internal" 2>$null
$iscc = @(
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw 'Inno Setup 6 ISCC.exe not found' }
& $iscc $iss
Write-Host "Done. See installer-output\"
