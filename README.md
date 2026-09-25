# Countdown timer  
This is a countdown program until end of class, for both students and teachers  

## Automatically starting on startup  
- Win+R > "taskschd.msc"  
- "Create Basic task"  
	- Name: "countdown timer" (or whatever you want)  
	- Trigger = "When I log on"  
	- Action = "Start a program"  
	- Action > Start a program (If using source code)  
		- Program/script = "C:\WINDOWS\System32\cmd.exe"  
		- Add arguments = "/c python path/to/main.py"  
	- Action > Start a program (If using exe file)  
		- Program/script = "path\to\countdown.exe"  
# Development  
[Trello board](https://trello.com/b/SpFVKoKa)  
## Requirements  
- Python 3.12+  
- Windows 10+ or Linux (the UI uses Qt via PySide6)  
- The system tray icon uses Qt's native tray (StatusNotifierItem), so no extra packages are needed on Linux.  
## Build from source  
- Git clone the repo  
```bat  
git clone git@github.com:Maho-Yoshino/countdown-timer.git  
```  
- Change directory to the new `countdown-timer` folder  
- Windows: run `setup.bat`, then `countdown_timer.bat`  
- Linux: run `./setup.sh`, then `./run.sh`  
- To build a Windows exe run `package.bat`
