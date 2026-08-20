@echo off
setlocal EnableExtensions
set "REPO=%~dp0.."
set "PACK=c:\bak\gamesb1_soft\PC端\face\脸幻中文便携版"
set "APP=%PACK%\internal\app"
if not exist "%APP%" (
  echo missing %APP%
  exit /b 1
)
for %%F in (lianhuan_client.py lianhuan_update.py lianhuan_login.py lianhuan_version.txt lianhuan_api.txt.example) do (
  if exist "%REPO%\%%F" copy /Y "%REPO%\%%F" "%APP%\%%F" >nul
)
copy /Y "%REPO%\portable\启动换脸.bat" "%PACK%\启动换脸.bat" >nul
copy /Y "%PACK%\启动换脸.bat" "%PACK%\internal\start.bat" >nul
copy /Y "%PACK%\启动换脸.bat" "%PACK%\internal\启动换脸.bat" >nul
if exist "%REPO%\使用说明.txt" copy /Y "%REPO%\使用说明.txt" "%PACK%\" >nul
echo Synced to %PACK%
