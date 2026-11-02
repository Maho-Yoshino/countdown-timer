@echo off
cd /d "%~dp0"
if not exist ".venv" (
	echo .venv does not exist. Please run setup.bat first.
	pause
	exit
)
.\.venv\Scripts\python .\main.py
rem exit