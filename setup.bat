cls
@echo off
echo [Setup] Beginning setup
cd "%~dp0"
if not exist ".venv" (
	echo [Setup] Creating virtual environment
	python -m venv .venv
)
call ./.venv/Scripts/activate
echo [Setup] Upgrading pip
python.exe -m pip install --upgrade pip -q -q
echo [Setup] Installing requirements
pip install -r requirements.txt -q -q
call deactivate
echo [Setup] Setup complete
pause
exit
