@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ROOT=%~dp0"
set "RT=%ROOT%internal\runtime"
set "APP=%ROOT%internal\app"
set "FF=%ROOT%internal\ffmpeg"
set "FACEFUSION_LANGUAGE=zh"
set "PYTHONNOUSERSITE=1"
set "PATH=%RT%;%RT%\Scripts;%FF%;%PATH%"
title LianHuan
echo.
echo ========================================
echo   LianHuan is starting...
echo   First run may unpack and download models.
echo   Please wait. Do NOT close this window.
echo ========================================
echo.
if not exist "%RT%\python.exe" goto FAIL
if exist "%RT%\Scripts\conda-unpack.exe" if not exist "%RT%\.unpacked" (
  echo Unpacking runtime, first time only...
  "%RT%\Scripts\conda-unpack.exe"
  echo 1>"%RT%\.unpacked"
)
cd /d "%APP%"
echo Checking updates...
python lianhuan_update.py
if errorlevel 1 goto FAIL
python lianhuan_login.py
if errorlevel 1 goto FAIL
echo.
echo Starting main program...
python facefusion.py run --open-browser --language zh
if errorlevel 1 goto FAIL
goto :eof
:FAIL
echo.
echo Start failed.
pause
