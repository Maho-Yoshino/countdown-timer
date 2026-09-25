if __name__ == "__main__":
	from sys import path as sp
	from os import path
	sp.append(path.abspath(path.join(path.dirname(__file__), '..')))
import modules.state as state
from asyncio import gather, all_tasks, Task, current_task, wait_for
from logging import getLogger
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon
from ui.settings import settingsGUI
from ui.schedule import scheduleGUI
from ui.delay import delayGUI
logger = getLogger(__name__)

class Tray:
	shutting_down:bool = False
	def __init__(self):
		loc = state.settings.localization
		self.icon = QSystemTrayIcon(QIcon("assets/icon.ico"), state.app)
		self.icon.setToolTip(loc.tray.name)

		self.menu = QMenu()
		self.delayAction = self.menu.addAction("")
		self.delayAction.triggered.connect(lambda: delayGUI())
		self.fullscreenAction = self.menu.addAction(loc.tray.fullscreen_schedule)
		self.fullscreenAction.setEnabled(False)
		self.fullscreenAction.triggered.connect(lambda: scheduleGUI())
		self.settingsAction = self.menu.addAction(loc.tray.settings)
		self.settingsAction.triggered.connect(lambda: settingsGUI())
		self.menu.addSeparator()
		self.closeAction = self.menu.addAction(loc.tray.close)
		self.closeAction.triggered.connect(self.quit)

		self.icon.setContextMenu(self.menu)
		self.menu.aboutToShow.connect(self._updateDelayLabel)
		self._updateDelayLabel()

		if not QSystemTrayIcon.isSystemTrayAvailable():
			logger.warning("System tray is not available on this desktop. "
				"Use Ctrl+C in the terminal to exit.")
		self.icon.show()
		logger.info("System tray icon ready")
	def _updateDelayLabel(self):
		loc = state.settings.localization
		delay = state.settings.schedule.delay
		if delay >= 60:
			time_str = f"{delay // 60} {loc.tray.delayMinutesDisplay} {delay % 60} {loc.tray.delaySecondsDisplay}"
		else:
			time_str = f"{delay % 60} {loc.tray.delaySecondsDisplay}"
		self.delayAction.setText(loc.format(f"{loc.tray.delay}", time=time_str))
	def quit(self):
		if self.shutting_down:
			return
		self.shutting_down = True
		logger.info("Closing application")
		self.icon.hide()

		current = current_task(state.runtime)
		tasks:list[Task] = [
			t for t in all_tasks(state.runtime)
			if t is not current and not t.done()
		]

		logger.debug("Destroying Qt windows")
		for level in list(state.openGUIs.values()):
			try:
				level.close()
				level.deleteLater()
			except Exception:
				logger.exception("Failed to destroy a child Qt window")
		state.openGUIs.clear()
		try:
			state.clock.close()
		except Exception:
			logger.exception("Failed to destroy the main clock window")
		logger.debug("Qt destruction done")

		for task in tasks:
			task.cancel()
		state.runtime.create_task(self._shutdown(tasks))

	async def _shutdown(self, tasks:list[Task]):
		logger.debug("Shutdown coroutine started")
		try:
			if tasks:
				await wait_for(gather(*tasks, return_exceptions=True), timeout=2)
		except TimeoutError:
			logger.debug("Shutdown timed out; remaining tasks:")
			for task in tasks:
				logger.debug("Task alive=%s cancelled=%s done=%s repr=%r",
					not task.done(), task.cancelled(), task.done(), task)
		finally:
			state.runtime.stop()
			state.app.quit()
