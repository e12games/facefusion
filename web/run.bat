@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PY=%USERPROFILE%\miniconda3\envs\facefusion\python.exe"
if not exist "%PY%" goto FAIL
echo Open http://127.0.0.1:8080
echo Admin: admin@local.test / admin123
"%PY%" -m uvicorn app:app --host 127.0.0.1 --port 8080
goto :eof
:FAIL
echo missing conda env python
pause
