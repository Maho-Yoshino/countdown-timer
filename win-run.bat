@echo off
cd /d "%~dp0"
if not exist ".venv" (
	call .\win-setup.bat
)
.\.venv\Scripts\python .\src\main.py