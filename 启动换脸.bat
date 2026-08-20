@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "FACEFUSION_LANGUAGE=zh"
set "CONDA_ROOT=%USERPROFILE%\miniconda3"
set "WINGET_LINKS=%LOCALAPPDATA%\Microsoft\WinGet\Links"
if exist "%WINGET_LINKS%\ffmpeg.exe" set "PATH=%WINGET_LINKS%;%PATH%"
title LianHuan Dev
echo.
echo ========================================
echo   LianHuan dev mode
echo   First run may download models. Please wait.
echo ========================================
echo.
if not exist "%CONDA_ROOT%\Scripts\activate.bat" goto FAIL
call "%CONDA_ROOT%\Scripts\activate.bat" facefusion
if errorlevel 1 goto FAIL
echo Checking updates...
python lianhuan_update.py
if errorlevel 1 goto FAIL
python lianhuan_login.py
if errorlevel 1 goto FAIL
echo Starting main program...
python facefusion.py run --open-browser --language zh
if errorlevel 1 goto FAIL
goto :eof
:FAIL
echo.
echo Start failed.
pause
