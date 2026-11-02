import pystray
if __name__ == "__main__":
	from sys import path as sp
	from os import path
	sp.append(path.abspath(path.join(path.dirname(__file__), '..')))
import modules.state as state
from asyncio import gather, all_tasks, Task, current_task, wait_for
from logging import getLogger
from PIL.Image import open as imgopen
from ui.settings import settingsGUI
from ui.schedule import scheduleGUI
from ui.delay import delayGUI
logger = getLogger(__name__)

class Tray:
	shutting_down:bool = False
	def __init__(self):
		loc = state.settings.localization
		self.icon = pystray.Icon(loc.tray.name, imgopen("assets/icon.ico"), menu=pystray.Menu(
			pystray.MenuItem(
				lambda item: loc.format(f"{loc.tray.delay}", time=f"{f"{state.settings.schedule.delay//60} {loc.tray.delayMinutesDisplay} " if state.settings.schedule.delay >= 60 else ""}{state.settings.schedule.delay%60} {loc.tray.delaySecondsDisplay}"), 
				lambda icon, item: state.runtime.call_soon_threadsafe(lambda: delayGUI())
			),
			pystray.MenuItem(
				loc.tray.fullscreen_schedule,
				lambda icon, item: state.runtime.call_soon_threadsafe(lambda: scheduleGUI()),
				enabled=False
			),
			pystray.MenuItem(
				loc.tray.settings,
				lambda icon, item: state.runtime.call_soon_threadsafe(lambda: settingsGUI())
			),
			pystray.MenuItem(
				loc.tray.close,
				lambda icon, item: state.runtime.call_soon_threadsafe(self.quit)
			)
		))
		self.icon.run_detached()
	def quit(self):
		if self.shutting_down:
			return
		self.shutting_down = True
		logger.info("Closing application")
		try:
			self.icon.stop()
		except Exception:
			logger.exception("Failed to stop tray icon cleanly")

		current = current_task(state.runtime)
		tasks:list[Task] = [
			t for t in all_tasks(state.runtime)
			if t is not current and not t.done()
		]

		logger.debug("Destroying Tk windows")
		for level in list(state.openGUIs.values()):
			try:
				level.destroy()
			except Exception:
				logger.exception("Failed to destroy a child Tk window")
		state.openGUIs.clear()
		try:
			state.clock.quit()
			state.clock.destroy()
		except Exception:
			logger.exception("Failed to destroy the main clock window")
		logger.debug("Tk destruction done")
		
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
