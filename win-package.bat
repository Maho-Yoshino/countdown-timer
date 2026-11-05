@echo off
cls
setlocal

pushd "%~dp0" || (
	echo Failed to access project directory.
	pause
	exit /b 1
)

set "ROOT=%CD%"

if not exist ".venv\Scripts\python.exe" (
	echo Virtual environment doesn't exist, running setup
	call win-setup.bat
	if errorlevel 1 goto :error
)

echo [Packager] Starting Packager

"%ROOT%\.venv\Scripts\python.exe" -m PyInstaller ^
	--log-level ERROR ^
	-y -F -w ^
	--distpath "%ROOT%" ^
	--workpath "%ROOT%\output\work" ^
	-i "%ROOT%\assets\icon.ico" ^
	-n "Countdown Timer" ^
	--clean "%ROOT%\src\main.py"

if errorlevel 1 goto :error

if exist "%ROOT%\output" rmdir /s /q "%ROOT%\output"
if exist "%ROOT%\Countdown Timer.spec" del "%ROOT%\Countdown Timer.spec"

echo [Packager] Package Made (it can be found in the root directory)
goto :end

:error
echo An error happened while creating package.

:end
popd
pause
endlocal