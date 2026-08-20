@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PY=%USERPROFILE%\miniconda3\envs\facefusion\python.exe"
set "REPO=%~dp0.."
set "PACK=%~dp0..\..\脸幻中文便携版"
if not exist "%PY%" goto FAIL
"%PY%" -m pip install pyinstaller -q
set "ICON="
if exist "%PACK%\internal\app\facefusion.ico" set "ICON=--icon %PACK%\internal\app\facefusion.ico"
"%PY%" -m PyInstaller --noconfirm --clean --onefile --noconsole %ICON% --name LianHuan --distpath "%REPO%\dist" --workpath "%~dp0build" --specpath "%~dp0" "%REPO%\lianhuan_launcher.py"
if errorlevel 1 goto FAIL
copy /Y "%REPO%\dist\LianHuan.exe" "%REPO%\脸幻.exe" >nul
copy /Y "%REPO%\dist\LianHuan.exe" "%PACK%\脸幻.exe" >nul
echo.
echo Built: %REPO%\脸幻.exe
echo Copied to portable pack.
goto :eof
:FAIL
echo build failed
pause
