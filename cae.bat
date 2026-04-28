@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set "PYTHONPATH=%~dp0"
if exist "%~dp0venv\Scripts\python.exe" (
  "%~dp0venv\Scripts\python.exe" "%~dp0cae\main.py" %*
) else if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0cae\main.py" %*
) else (
  python "%~dp0cae\main.py" %*
)
