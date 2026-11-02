cls
@echo off
if not exist ".venv" (
	echo Virtual environment doesn't exist, running setup
	call setup
)
cd /d "%~dp0"
echo [Packager] Starting Packager
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
"%ROOT%\.venv\Scripts\python.exe" -m PyInstaller --log-level ERROR -y -F -w --distpath "%ROOT%" --workpath "%ROOT%\output\work" -i "%ROOT%\icon.ico" -n "csengo" --clean "%ROOT%\csengo.py"
if not exist "%ROOT%\output" (
	echo An error happened while creating package.
)
if exist "%ROOT%\output" (
	rmdir /s /q output
	del csengo.spec
	echo Package Made (it can be found in the root directory)
)
pause
exit