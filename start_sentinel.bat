@echo off
REM Project Sentinel Startup Script
REM This script starts the supervised monitor for Project Sentinel

cd /d "%~dp0"
if exist "%~dp0venv\Scripts\python.exe" (
    "%~dp0venv\Scripts\python.exe" monitor.py %*
) else (
    python monitor.py %*
)

exit /b %ERRORLEVEL%
