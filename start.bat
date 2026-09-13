@echo off
setlocal
cd /d "%~dp0"

where pythonw >nul 2>nul
if errorlevel 1 goto :no_python

start "" pythonw main.py
exit /b 0

:no_python
echo [ERROR] Python not found. Please install Python 3.8+ and check "Add Python to PATH".
pause
exit /b 1
