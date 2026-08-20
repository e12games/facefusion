$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$pack = 'c:\bak\gamesb1_soft\PC端\face\脸幻中文便携版'
$app = Join-Path $pack 'internal\app'
if (-not (Test-Path $app)) { throw "missing portable app dir: $app" }
$files = @(
  'lianhuan_client.py','lianhuan_update.py','lianhuan_login.py',
  'lianhuan_version.txt','lianhuan_api.txt.example'
)
foreach ($f in $files) {
  $src = Join-Path $repo $f
  if (Test-Path $src) { Copy-Item -Force $src (Join-Path $app $f) }
}
Copy-Item -Force (Join-Path $repo 'portable\启动换脸.bat') (Join-Path $pack '启动换脸.bat')
Copy-Item -Force (Join-Path $pack '启动换脸.bat') (Join-Path $pack 'internal\start.bat')
Copy-Item -Force (Join-Path $pack '启动换脸.bat') (Join-Path $pack 'internal\启动换脸.bat')
$readme = Join-Path $repo '使用说明.txt'
if (Test-Path $readme) { Copy-Item -Force $readme $pack }
Write-Host "Synced to $pack"
