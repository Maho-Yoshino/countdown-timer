import sys
sys.dont_write_bytecode = True # Prevent '__pycache__' creation
import signal
from asyncio import new_event_loop, set_event_loop, all_tasks, gather
from logging import getLogger, WARNING, DEBUG, INFO, Formatter
from logging.handlers import TimedRotatingFileHandler
from sys import executable, argv
from pathlib import Path
from datetime import datetime
from os import path, chdir, environ, _exit
from hashlib import sha1
from github import Github, Repository, GitRelease
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, QLockFile, QDir
import modules.state as state
from modules.settings import Settings
from ui.clock import Clock
from ui.tray import Tray
logger = getLogger()
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
	try:
		repo:Repository.Repository = Github().get_repo("Maho-Yoshino/countdown-timer")
		latest_release:GitRelease.GitRelease = repo.get_releases()[0]
		tag = latest_release.tag_name.lstrip("v")
		latest_version = Version(tag)
	except Exception:
		logger.exception("Failed to check for updates")
		return
	logger.debug(f"Latest version online: {latest_version}")
	logger.debug(f"Current version: {VERSION}")
	if latest_version > VERSION:
		logger.warning(f"Update available ({VERSION} -> {latest_version})")
		state.callLater(_showUpdatePrompt, latest_version)
	else:
		logger.info("Running the latest version.")
def _showUpdatePrompt(latest_version:"Version"):
	loc = state.settings.localization
	box = QMessageBox()
	box.setWindowTitle(loc.messages.updatePrompt.title)
	box.setText(loc.format(
		loc.messages.updatePrompt.message,
		current=VERSION,
		latest=latest_version
	))
	box.setIcon(QMessageBox.Warning)
	yes_btn = box.addButton(QMessageBox.Yes)
	no_btn = box.addButton(QMessageBox.No)
	cancel_btn = box.addButton(QMessageBox.Cancel)
	box.setDefaultButton(yes_btn)
	box.exec()
	clicked = box.clickedButton()
	if clicked is yes_btn:
		logger.info("User accepted automatic update")
		# TODO: Finish auto-updater
	elif clicked is cancel_btn:
		logger.info("User asked to not be reminded again")
		state.settings.config.ignoreUpdates = True
	else:
		logger.info("User denied automatic update")

# endregion
state.settings = Settings()

_lock_file:QLockFile = None
def findInstance(name:str) -> bool:
	"""Checks and returns if another instance of the application is running"""
	global _lock_file
	lock_name = sha1(name.encode("utf-8")).hexdigest()
	lock_path = path.join(QDir.tempPath(), f"countdown-timer-{lock_name}.lock")
	_lock_file = QLockFile(lock_path)
	_lock_file.setStaleLockTime(0)
	if not _lock_file.tryLock(100):
		return True
	return False
def _graceful_quit():
	"""Perform the same shutdown as the tray's Exit menu item."""
	try:
		if getattr(state, "tray", None) is not None:
			state.tray.quit()
		else:
			if getattr(state, "runtime", None) is not None:
				state.runtime.stop()
			if getattr(state, "app", None) is not None:
				state.app.quit()
	except Exception:
		logger.exception("Failed to gracefully shut down")
		_exit(1)
def _signal_handler(signum, frame):
	# Qt work must not happen directly inside a signal handler, so defer the
	# shutdown to the event loop (also prevents Ctrl+C from being swallowed
	# by the QTimer-driven asyncio pump).
	try:
		QTimer.singleShot(0, _graceful_quit)
	except Exception:
		_exit(1)
def main(dummyDate:datetime|None = None):
	# The clock overlay needs window positioning, opacity, always-on-top and
	# click-through. The native Wayland platform plugin does not support those,
	# so prefer XWayland (xcb) whenever an X display is available.
	if (
		sys.platform.startswith("linux")
		and environ.get("WAYLAND_DISPLAY")
		and environ.get("DISPLAY")
		and "QT_QPA_PLATFORM" not in environ
	):
		environ["QT_QPA_PLATFORM"] = "xcb"
	app = QApplication.instance() or QApplication(argv)
	app.setQuitOnLastWindowClosed(False)
	state.app = app
	loc = state.settings.localization
	if (findInstance(state.windowHandle)):
		logger.critical("Another instance is already running.\nClosing application.")
		QMessageBox.critical(
			None,
			loc.messages.anotherInstance.title,
			loc.messages.anotherInstance.message
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
		from threading import Thread
		Thread(target=checkUpdate, daemon=True).start()
	if dummyDate is not None:
		state.dummyDate = dummyDate
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
	state.tray = Tray()
	# QTimer drives the asyncio event loop while Qt runs its own loop.
	# Keep each asyncio slice short so Qt still gets plenty of time to process
	# repaints and input (otherwise the main thread is saturated and visual
	# updates, like window opacity changes, stall until an event wakes it up).
	pump = QTimer()
	pump.setInterval(16) # ~60 FPS
	def tick():
		state.runtime.call_later(0.002, state.runtime.stop)
		state.runtime.run_forever()
	pump.timeout.connect(tick)
	pump.start()
	state.pumpTimer = pump
	signal.signal(signal.SIGINT, _signal_handler)
	signal.signal(signal.SIGTERM, _signal_handler)
	try:
		sys.exit(app.exec())
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

try:
	if environ.get('TERM_PROGRAM') == 'vscode':
		main()
		#main(datetime(year=2026, month=4, day=1, hour=12, minute=45, second=0))
	else:
		main()
except KeyboardInterrupt:
	logger.info("Keyboard Interrupt requested")
	try:
		if getattr(state, "runtime", None) is not None and not state.runtime.is_closed() and hasattr(state.runtime, "shutdown_default_executor"):
			state.runtime.run_until_complete(state.runtime.shutdown_default_executor())
	except Exception:
		pass
except Exception as e:
	logger.exception("An error occurred during runtime", exc_info=e)
