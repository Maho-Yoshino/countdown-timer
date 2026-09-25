from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from asyncio import CancelledError, Task, AbstractEventLoop
from logging import getLogger
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget
from PySide6.QtGui import QFont
from PySide6.QtCore import QTimer

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
app:QApplication = None

windowHandle:str = u"Csengetés időzítő"
dummyDate:Optional[datetime] = None

runtime:AbstractEventLoop = None

currentClassIndex:int|None = None
openGUIs:dict[str, QWidget] = {}

def getTime(): return datetime.now() if dummyDate is None else dummyDate

def callLater(func, *args):
	"""Schedule a callback on the Qt event loop (main thread)."""
	QTimer.singleShot(0, lambda: func(*args))

def exc_handler(task: Task):
	try:
		task.result()
	except CancelledError:
		return
	except Exception as e:
		_logger.exception("Unhandled async task exception", exc_info=e)
		def showError():
			QMessageBox.critical(
				None,
				settings.localization.messages.error.title,
				settings.localization.messages.error.message,
			)
			tray.quit()
		callLater(showError)

def fontSize(size:int) -> QFont:
	font = QFont()
	font.setPointSize(size)
	return font
