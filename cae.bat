@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set "PATH=%PATH%;D:\Apps\tools\msys\ucrt64\bin"
set "PYTHONPATH=%~dp0"
"%~dp0venv\Scripts\python.exe" "%~dp0cae\main.py" %*
