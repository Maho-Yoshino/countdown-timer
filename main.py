import sys
sys.dont_write_bytecode = True # Prevent '__pycache__' creation
from asyncio import new_event_loop, set_event_loop, all_tasks, gather
from logging import getLogger, WARNING, DEBUG, INFO, Formatter
from logging.handlers import TimedRotatingFileHandler
from tkinter import messagebox
from sys import executable, argv, platform
from pathlib import Path
from datetime import datetime
from os import path, chdir, environ, _exit
from github import Github, Repository, GitRelease
from ctypes import windll
from ctypes.wintypes import BOOL
import modules.state as state
from modules.settings import Settings
from ui.clock import Clock
from ui.tray import Tray
from time import sleep
logger = getLogger()
getLogger("PIL").setLevel(WARNING)
getLogger("pystray").setLevel(WARNING)
getLogger("asyncio").setLevel(WARNING)

# region Setting PATH
if path.splitext(argv[0])[1].lower() != ".exe":
	current_dir = path.dirname(path.abspath(__file__))
else:
	current_dir = path.dirname(path.abspath(executable))
chdir(current_dir)
# endregion
# region update handler
class Version:
	"""Uses the principle of 'semantic versioning' (https://semver.org)"""
	major:int
	minor:int = 0
	patch:int = 0
	# 0 - Release
	# 1 - Pre-release
	# 2 - Beta
	# 3 - Alpha
	subversion:int 
	__subver_map = {
		"release": 0,
		"pre-release": 1,
		"beta": 2,
		"alpha": 3
	}
	__inv_subver_map = {v: k for k, v in __subver_map.items()}
	def __init__(self, ver:str):
		self.subversion = 0
		tmp = ver.split(".")
		if len(tmp) > 0:
			self.major = int(tmp[0])
		if len(tmp) > 1:
			self.minor = int(tmp[1])
		if len(tmp) > 2 and "-" in tmp[2]: 
			tmp2 = tmp[2].split("-")
			self.patch = int(tmp2[0])
			self.subversion = self.__subver_map.get(tmp2[1], 0)
		elif len(tmp) > 2:
			self.patch = int(tmp[2])
	def __str__(self):
		return f"{self.major}.{self.minor}.{self.patch}{f"-{self.__inv_subver_map[self.subversion]}" if self.subversion != 0 else ""}"
	def __gt__(self, version:"Version"):
		return (self.major, self.minor, self.patch, -self.subversion) > \
			   (version.major, version.minor, version.patch, -version.subversion)
	def __lt__(self, version:"Version"):
		return (self.major, self.minor, self.patch, -self.subversion) < \
			   (version.major, version.minor, version.patch, -version.subversion)
	def __eq__(self, version:"Version"):
		return (self.major, self.minor, self.patch, self.subversion) == \
			   (version.major, version.minor, version.patch, version.subversion)
VERSION:"Version" = Version("3.0.0")
def checkUpdate():
	logger.info("Checking for updates...")
	repo:Repository.Repository = Github().get_repo("Maho-Yoshino/countdown-timer")
	latest_release:GitRelease.GitRelease = repo.get_releases()[0]
	tag = latest_release.tag_name.lstrip("v")
	latest_version = Version(tag)
	logger.debug(f"Latest version online: {latest_version}")
	logger.debug(f"Current version: {VERSION}")
	if latest_version > VERSION:
		logger.warning(f"Update available ({VERSION} -> {latest_version})")
		loc = state.settings.localization
		response = messagebox.askyesnocancel(
			loc.messages.updatePrompt.title, 
			loc.format(
				loc.messages.updatePrompt.message, 
				current=VERSION, 
				latest=latest_version
			), 
			icon="warning", 
			default=messagebox.YES
		)
		if response:
			logger.info("User accepted automatic update")
			# TODO: Finish auto-updater
		elif response is None:
			logger.info("User asked to not be reminded again")
			state.settings.config.ignoreUpdates = True
		else:
			logger.info("User denied automatic update")
	else:
		logger.info("Running the latest version.")

# endregion
state.settings = Settings()

def findInstance(name:str) -> bool:
	"""Checks and returns if another instance of the application is running"""
	k32 = windll.kernel32
	mutex = k32.CreateMutexW(None, BOOL(True), name)
	if k32.GetLastError() == 183:
		return True
	return False
def main(dummyDate:datetime|None = None):
	loc = state.settings.localization
	if (platform != "win32"):
		logger.critical(f"User is not using windows (platform: {platform})")
		messagebox.showerror(
			loc.messages.windowsOnly.title, 
			loc.messages.windowsOnly.message, 
			icon="error"
		)
		return
	if (findInstance(state.windowHandle)):
		logger.critical("Another instance is already running.\nClosing application.")
		messagebox.showerror(
			loc.messages.anotherInstance.title, 
			loc.messages.anotherInstance.message, 
			icon="error"
		)
		return
	debug:bool
	# region Debug mode setup
	if __name__ == "__main__":
		debug = environ.get('TERM_PROGRAM') == 'vscode'
		if not debug:
			from argparse import ArgumentParser
			parser = ArgumentParser()
			parser.add_argument("-d", "--debug", help="Debug mode switch", action="store_true")
			debug = parser.parse_args().debug
	else:
		debug = True # Not ran from this file directly, a.k.a. testing another module, Always True
	# endregion
	if not state.settings.config.ignoreUpdates:
		checkUpdate()
	if dummyDate is not None:
		state.dummyDate = dummyDate
		del dummyDate
	def log_namer(default_name:str):
		dirname = path.dirname(default_name)
		filename = path.basename(default_name)
		_, _, date = filename.rpartition(".")
		return path.join(dirname, f"{date}.log")
	latestLogPath = Path("logs") / "latest.log"
	latestLogPath.parent.mkdir(exist_ok=True, parents=True)
	if not latestLogPath.exists():
		with latestLogPath.open("x"):
			logger.warning("Could not find any 'latest.log', Created an empty one")
	handler = TimedRotatingFileHandler("logs/latest.log", when="midnight", interval=1, backupCount=5)
	handler.suffix = "%Y-%m-%d"
	formatter = Formatter(f"%(asctime)s:%(name)-15s:%(funcName)-15s:%(lineno)-3d:%(levelname)-7s:%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
	handler.setFormatter(formatter)
	handler.namer = log_namer
	logger.addHandler(handler)
	logger.setLevel(DEBUG if debug else INFO)
	logger.info(f"Application Starting up (v{VERSION})")
	state.runtime = new_event_loop()
	set_event_loop(state.runtime)
	state.clock = Clock()
	state.tkPumpTask = state.runtime.create_task(state.tkPump(state.clock))
	state.tkPumpTask.add_done_callback(state.exc_handler)
	state.tray = Tray()
	try:
		state.runtime.run_forever()
	finally:
		pending = [task for task in all_tasks(state.runtime) if not task.done()]
		for task in pending:
			task.cancel()
		if pending:
			state.runtime.run_until_complete(gather(*pending, return_exceptions=True))
		state.runtime.run_until_complete(state.runtime.shutdown_asyncgens())
		if hasattr(state.runtime, "shutdown_default_executor"):
			state.runtime.run_until_complete(state.runtime.shutdown_default_executor())
		state.runtime.close()
		_exit(0)

try:
	if environ.get('TERM_PROGRAM') == 'vscode':
		main()
		#main(datetime(year=2026, month=4, day=1, hour=12, minute=45, second=0))
	else:
		main()
except KeyboardInterrupt: 
	logger.info("Keyboard Interrupt requested")
	if hasattr(state.runtime, "shutdown_default_executor"):
		state.runtime.run_until_complete(state.runtime.shutdown_default_executor())
except Exception as e:
	logger.exception("An error occurred during runtime", exc_info=e)
	messagebox.showerror(
		state.settings.localization.messages.error.title, 
		state.settings.localization.messages.error.message, 
		icon="error"
	)
finally:
	_exit(0)
