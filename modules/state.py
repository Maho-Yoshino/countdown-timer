from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from asyncio import CancelledError, Task, AbstractEventLoop, sleep as asleep
from tkinter import Tk, TclError, messagebox, Toplevel
from tkinter.font import Font
from logging import getLogger
_logger = getLogger(__name__)

if TYPE_CHECKING:
	from ui.tray import Tray
	from ui.clock import Clock
	from modules.settings import Settings
	from modules.schedule import Schedule

settings:Settings = None
schedule:Schedule = None
tray:Tray = None
clock:Clock

windowHandle:str = u"Csengetés időzítő"
dummyDate:Optional[datetime] = None

runtime:AbstractEventLoop = None
tkPumpTask: Task = None

currentClassIndex:int|None = None
openGUIs:dict[str, Toplevel] = {}

async def tkPump(root: Tk):
	_logger.debug("tkPump started")
	try:
		while True:
			try:
				root.update_idletasks()
				root.update()
			except TclError:
				break
			await asleep(1/60) # 60 FPS
	except CancelledError:
		pass
def getTime(): return datetime.now() if dummyDate is None else dummyDate
def exc_handler(task: Task):
	try:
		task.result()
	except CancelledError: return
	except Exception as e:
		_logger.exception("Unhandled async task exception", exc_info=e)
		def showError(): # Needs a seperate def apparently due to threading
			messagebox.showerror(
				settings.localization.messages.error.title,
				settings.localization.messages.error.message,
				icon="error"
			)
			tray.quit()
		try:
			clock.after(0, showError)
		except Exception:
			_logger.exception("Failed to schedule Tk error dialog")
			tray.quit()
def fontSize(size:int): return Font(size=size)