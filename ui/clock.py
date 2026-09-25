import modules.state as state
from datetime import datetime, timedelta
from asyncio import sleep as asleep, CancelledError
from time import perf_counter
from logging import getLogger
from os import environ
import ctypes
import ctypes.util
from PySide6.QtWidgets import QWidget, QLabel, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QMessageBox
from PySide6.QtCore import Qt, QByteArray, QRect, QPoint, QTimer
from PySide6.QtGui import QGuiApplication, QPixmap, QPainter, QIcon, QColor, QCursor
from PySide6.QtSvg import QSvgRenderer
from modules.schedule import Schedule
from modules.settings.schedule import UnifiedClassData, _classData

init_data:dict[str, str] = {}

# X11 cursor query. QCursor.pos() can return a stale cached position on xcb when
# the pointer is over the root window or foreign windows, so we query the X
# server directly (this is what Tkinter's winfo_pointerx/y used under the hood).
_x11_lib = None
_x11_display = None
_x11_pointer_child = None
def _x11():
	global _x11_lib, _x11_display
	if _x11_lib is None:
		lib_name = ctypes.util.find_library("X11")
		if not lib_name:
			return None, None
		try:
			lib = ctypes.CDLL(lib_name)
			lib.XOpenDisplay.restype = ctypes.c_void_p
			lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
			lib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
			lib.XDefaultRootWindow.restype = ctypes.c_ulong
			lib.XQueryPointer.argtypes = [
				ctypes.c_void_p, ctypes.c_ulong,
				ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
				ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
				ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
				ctypes.POINTER(ctypes.c_uint),
			]
			lib.XQueryPointer.restype = ctypes.c_int
			display = lib.XOpenDisplay(None)
			_x11_lib = lib
			_x11_display = display
		except Exception:
			_x11_lib = None
			_x11_display = None
	return _x11_lib, _x11_display
def getGlobalCursorPos() -> QPoint:
	"""Return the current global cursor position, fresh from the X server."""
	global _x11_pointer_child
	lib, display = _x11()
	if lib is not None and display:
		try:
			root = lib.XDefaultRootWindow(display)
			root_ret = ctypes.c_ulong()
			child_ret = ctypes.c_ulong()
			root_x = ctypes.c_int()
			root_y = ctypes.c_int()
			win_x = ctypes.c_int()
			win_y = ctypes.c_int()
			mask = ctypes.c_uint()
			lib.XQueryPointer(
				display, root,
				ctypes.byref(root_ret), ctypes.byref(child_ret),
				ctypes.byref(root_x), ctypes.byref(root_y),
				ctypes.byref(win_x), ctypes.byref(win_y),
				ctypes.byref(mask),
			)
			_x11_pointer_child = child_ret.value
			# XQueryPointer reports native pixels; Qt uses logical pixels.
			dpr = 1.0
			screen = QGuiApplication.primaryScreen()
			if screen is not None:
				dpr = screen.devicePixelRatio()
			return QPoint(round(root_x.value / dpr), round(root_y.value / dpr))
		except Exception:
			pass
	_x11_pointer_child = None
	return QCursor.pos()
class classFrame(QWidget):
	_data:dict[str, str|_classData|None]
	def __init__(self, master, _class:_classData|None):
		self._data = {
			"wraplength": 0,
			"bg": init_data["bg"],
			"fg": init_data["fg"],
			"class": _class
		}
		self._logger = getLogger(__name__)
		super().__init__(master)
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(2)
		self.nameLabel = QLabel(self)
		self.roomLabel = QLabel(self)
		self.teacherLabel = QLabel(self)
		for label in (self.nameLabel, self.roomLabel, self.teacherLabel):
			label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
			label.setWordWrap(True)
			layout.addWidget(label)
		self._class = _class
	# region Class
	@property
	def _class(self) -> _classData|None:
		return self._data["class"]
	@_class.setter
	def _class(self, value:_classData|None):
		self._data["class"] = value
		if value is not None:
			self.nameLabel.setText(value.name)
			self.nameLabel.setVisible(True)
			self.roomLabel.setText(value.room)
			self.roomLabel.setVisible(True)
			self.teacherLabel.setText(value.teacher)
			self.teacherLabel.setVisible(state.settings.config.showTeacher)
		else:
			self.nameLabel.setText(state.settings.localization.noneClass)
			self.nameLabel.setVisible(True)
			self.roomLabel.setVisible(False)
			self.teacherLabel.setVisible(False)
	# endregion
	# region Background
	@property
	def bg(self) -> str:
		return self._data["bg"]
	@bg.setter
	def bg(self, value:str):
		self._data["bg"] = value
	# endregion
	# region Foreground
	@property
	def fg(self) -> str:
		return self._data["fg"]
	@fg.setter
	def fg(self, value:str):
		self._data["fg"] = value
	# endregion
	# region Wraplength
	@property
	def wraplength(self) -> int:
		return self._data["wraplength"]
	@wraplength.setter
	def wraplength(self, value:int):
		self._data["wraplength"] = value
		self.nameLabel.setMaximumWidth(max(value, 20))
		self.roomLabel.setMaximumWidth(max(value, 20))
		self.teacherLabel.setMaximumWidth(max(value, 20))
	# endregion
class Clock(QWidget):
	def __init__(self):
		global init_data
		init_data = {
			"bg": f"#{state.settings.config.background:06x}",
			"fg": f"#{state.settings.config.foreground:06x}"
		}
		state.schedule = Schedule()
		super().__init__()
		self.logger = getLogger(__name__)

		# region Main config
		self.setWindowTitle(state.windowHandle)
		self.setWindowIcon(QIcon("assets/icon.ico"))
		self.setWindowFlags(
			Qt.FramelessWindowHint |
			Qt.WindowStaysOnTopHint |
			Qt.Tool |
			Qt.WindowTransparentForInput
		)
		self.setAttribute(Qt.WA_TransparentForMouseEvents, True) # Click-through
		self.setWindowOpacity(state.settings.config.alpha["default"])
		self.hoverTransparencyEnabled = not (
			environ.get("WAYLAND_DISPLAY") or
			environ.get("XDG_SESSION_TYPE") == "wayland"
		)
		self.setStyleSheet(f"background-color: {init_data['bg']}; color: {init_data['fg']};")
		screen = QGuiApplication.primaryScreen().availableGeometry()
		width = screen.width() // 6
		height = screen.height() // 4
		self.setGeometry(screen.x() + screen.width() - width, screen.y(), width, height)
		# endregion

		rootLayout = QVBoxLayout(self)
		rootLayout.setContentsMargins(15, 15, 15, 15)
		rootLayout.setSpacing(4)

		# region Main text and time config
		self.mainLabel = QLabel(self)
		self.mainLabel.setFont(state.fontSize(20))
		self.mainLabel.setAlignment(Qt.AlignCenter)
		rootLayout.addWidget(self.mainLabel, stretch=1)

		self.timeFrame = QWidget(self)
		timeLayout = QGridLayout(self.timeFrame)
		timeLayout.setContentsMargins(0, 0, 0, 0)
		self.timeLabel = QLabel(self.timeFrame)
		self.timeLabel.setFont(state.fontSize(30))
		self.timeLabel.setAlignment(Qt.AlignCenter)
		timeLayout.addWidget(self.timeLabel, 0, 1, 2, 1)
		timeLayout.setColumnStretch(1, 1)
		self.homeworkIcon = self.loadSvg("homework")
		self.homeworkLabel = QLabel(self.timeFrame)
		self.homeworkLabel.setPixmap(self.homeworkIcon)
		self.examIcon = self.loadSvg("exam")
		self.examLabel = QLabel(self.timeFrame)
		self.examLabel.setPixmap(self.examIcon)
		timeLayout.addWidget(self.homeworkLabel, 1, 3)
		timeLayout.addWidget(self.examLabel, 1, 3)
		self.homeworkLabel.hide()
		self.examLabel.hide()
		rootLayout.addWidget(self.timeFrame, stretch=1)
		# endregion

		# region Classes setup
		self.separator = QFrame(self)
		self.separator.setFrameShape(QFrame.HLine)
		self.separator.setFixedHeight(1)
		self.separator.setStyleSheet(f"background-color: {init_data['fg']};")
		rootLayout.addWidget(self.separator)

		self.classesContainer = QWidget(self)
		self.classesLayout = QHBoxLayout(self.classesContainer)
		self.classesLayout.setContentsMargins(0, 0, 0, 0)
		self.classesLayout.setSpacing(6)
		rootLayout.addWidget(self.classesContainer, stretch=1)

		self.classFrames:list[classFrame] = []
		self.vertSeparators:list[QFrame] = []
		unified = state.settings.schedule.getUnifiedSchedule()
		max_groups = 1
		for day in unified:
			for entry in day:
				if entry.data is not None:
					max_groups = max(max_groups, len(entry.data))
		for _ in range(max_groups):
			self.classFrames.append(classFrame(self.classesContainer, None))
		# endregion

		# region Misc setup
		self.auxLabel = QLabel(self)
		self.auxLabel.setFont(state.fontSize(10))
		self.auxLabel.setAlignment(Qt.AlignCenter)
		self.auxLabel.setWordWrap(True)
		self.auxLabel.setText(state.settings.localization.nextClass)
		rootLayout.addWidget(self.auxLabel)
		# endregion

		# region Asyncio loops
		self.mainloopTask = state.runtime.create_task(self.mainloop())
		self.mainloopTask.add_done_callback(state.exc_handler)
		self.transparencyTarget = None
		self.transparencyTimer = QTimer(self)
		self.transparencyTimer.setInterval(100)
		self.transparencyTimer.timeout.connect(self.updateTransparency)
		if self.hoverTransparencyEnabled:
			self.transparencyTimer.start()
		# endregion
		self.show()
		self.logger.info("Clock setup complete")
	def refreshFromSettings(self):
		bg = f"#{state.settings.config.background:06x}"
		fg = f"#{state.settings.config.foreground:06x}"
		init_data["bg"] = bg
		init_data["fg"] = fg
		self.setStyleSheet(f"background-color: {bg}; color: {fg};")
		self.separator.setStyleSheet(f"background-color: {fg};")
		self.setWindowOpacity(state.settings.config.alpha["default"])

		self.homeworkIcon = self.loadSvg("homework")
		self.homeworkLabel.setPixmap(self.homeworkIcon)
		self.examIcon = self.loadSvg("exam")
		self.examLabel.setPixmap(self.examIcon)

		state.schedule = Schedule()
		self.rebuildClassFrames()
	def rebuildClassFrames(self):
		for frame in self.classFrames:
			frame.deleteLater()
		self.classFrames.clear()
		for sep in self.vertSeparators:
			sep.deleteLater()
		self.vertSeparators.clear()

		unified = state.settings.schedule.getUnifiedSchedule()
		max_groups = 1
		for day in unified:
			for entry in day:
				if entry.data is not None:
					max_groups = max(max_groups, len(entry.data))
		for _ in range(max_groups):
			self.classFrames.append(classFrame(self.classesContainer, None))
	def loadSvg(self, filename:str) -> QPixmap:
		try:
			with open(f"assets/{filename}.svg", "r") as file:
				svg_text = file.read().replace("<svg ", f"<svg fill='#{state.settings.config.foreground:06x}' ")
		except FileNotFoundError:
			self.logger.exception(f"File \"assets/{filename}.svg\" could not be found")
			raise
		renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
		pixmap = QPixmap(25, 25)
		pixmap.fill(Qt.transparent)
		painter = QPainter(pixmap)
		renderer.render(painter)
		painter.end()
		return pixmap
	def batterySaverEnabled(self, on_val, off_val):
		# Windows-specific battery saver detection is not available on Linux.
		return off_val
	def updateTransparency(self):
		if not self.hoverTransparencyEnabled:
			return
		cursor = getGlobalCursorPos()
		over = (
			_x11_pointer_child not in (None, 0)
			and self.frameGeometry().contains(cursor)
		)
		target = state.settings.config.alpha["onHover"] if over else state.settings.config.alpha["default"]
		if target != self.transparencyTarget:
			self.logger.debug(
				f"transparencyCheck: over={over} target={target} "
				f"cursor={cursor} frame={self.frameGeometry()}"
			)
			self.setWindowOpacity(target)
			self.transparencyTarget = target
	def setClassLabels(self, classes:UnifiedClassData, aux:bool = False):
		self.mainLabel.show()
		self.timeFrame.show()
		self.separator.show()
		self.classesContainer.show()

		# Detach and hide everything currently in the classes layout
		while self.classesLayout.count():
			item = self.classesLayout.takeAt(0)
			widget = item.widget()
			if widget is not None:
				self.classesLayout.removeWidget(widget)
				widget.hide()
		for sep in self.vertSeparators:
			sep.deleteLater()
		self.vertSeparators.clear()

		data = classes.data or []
		group = state.settings.schedule.group
		for frame in self.classFrames:
			frame.hide()
		if group != -1:
			visible_data = [data[group]] if group in range(len(data)) and data[group] is not None else []
		else:
			visible_data = [item for item in data if item is not None]

		for col, class_data in enumerate(visible_data):
			if col > 0:
				sep = QFrame(self.classesContainer)
				sep.setFrameShape(QFrame.VLine)
				sep.setFixedWidth(1)
				sep.setStyleSheet(f"background-color: {init_data['fg']};")
				self.classesLayout.addWidget(sep)
				self.vertSeparators.append(sep)
			if col < len(self.classFrames):
				frame = self.classFrames[col]
				frame.show()
				frame._class = class_data
				self.classesLayout.addWidget(frame)

		if len(visible_data) > 1:
			for frame in self.classFrames:
				frame.wraplength = max(self.width() // len(visible_data), 40)
		elif len(visible_data) == 1:
			for frame in self.classFrames:
				frame.wraplength = self.width()

		# region Exam and Homework icons
		if state.settings.events.current_exam():
			self.homeworkLabel.hide()
			self.examLabel.show()
		elif state.settings.events.current_homework():
			self.examLabel.hide()
			self.homeworkLabel.show()
		else:
			self.examLabel.hide()
			self.homeworkLabel.hide()
		# endregion
		# region Aux label
		self.auxLabel.setVisible(aux)
	# endregion
	alerted:datetime = datetime.fromtimestamp(0)
	def showAlertPopup(self, alert:dict[str, str]):
		loc = state.settings.localization
		box = QMessageBox(self)
		box.setWindowTitle(loc.alert.title)
		box.setText(alert.get("message", loc.alert.defaultText))
		box.setIcon(QMessageBox.Information)
		box.setStandardButtons(QMessageBox.Ok)
		box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
		box.exec()
	def sendAlert(self):
		if len(state.settings.events.alerts) == 0:
			return
		for alert in state.settings.events.alerts:
			date = None
			if (tmp := alert.get("date", None)) is not None:
				date = datetime.strptime(tmp, "%Y-%m-%d")
			time = datetime.combine(state.getTime().date(), datetime.strptime(alert["time"], "%H:%M").time())
			if (
				self.alerted < (rn := state.getTime().replace(second=0, microsecond=0)) and 
				time.replace(second=0, microsecond=0) == rn and 
				(
					(date is not None and date.date() == rn.date()) or 
					date is None
				)
			):
				self.showAlertPopup(alert)
				self.logger.debug(f"Sent alert")
				self.alerted = state.getTime().replace(second=0, microsecond=0)
				if not alert.get("keep", False):
					state.settings.events._data["alerts"] = [
						item
						for item in state.settings.events._data["alerts"]
						if not (
							item.get("time") == alert.get("time") and
							item.get("date") == alert.get("date") and
							item.get("weekday") == alert.get("weekday") and
							item.get("class") == alert.get("class") and
							item.get("message", state.settings.localization.alert.defaultText) == alert.get("message", state.settings.localization.alert.defaultText)
						)
					]
					state.settings.events.save()
	async def mainloop(self):
		while True:
			_start = perf_counter()
			delay = state.settings.schedule.delay
			if state.schedule._date != state.getTime().date():
				self.logger.debug("Day changed since last loop")
				state.schedule = Schedule()
				if len(state.schedule.classes) == 0:
					await asleep(60*30) # 30 min delay
				continue
			now = state.getTime()
			now_time = now.time()
			self.sendAlert()
			loc = state.settings.localization
			for num, _class in enumerate(state.schedule.classes):
				if _class.data is None:
					continue
				if ((_ := datetime.combine(now, _class.start) + timedelta(seconds=delay)).time() > now_time): # Break time
					tmp = _ - now
					self.mainLabel.setText(loc.format(loc.mainlabel.onBreak, num=f"{_class.classIndex}{loc.classNumbering.getSuffix(num+1)}"))
					self.timeLabel.setText(f"{f"{tmp.seconds//3600:02}:" if tmp.seconds//3600 != 0 else ""}{(tmp.seconds//60)%60:02}:{tmp.seconds%60:02}")
					self.setClassLabels(_class)
					break
				elif ((_ := datetime.combine(now, _class.end) + timedelta(seconds=delay)).time() > now_time): # In class
					tmp = _ - now
					self.mainLabel.setText(loc.format(loc.mainlabel.inClass, num=f"{_class.classIndex}{loc.classNumbering.getSuffix(num+1)}"))
					self.timeLabel.setText(f"{f"{tmp.seconds//3600:02}:" if tmp.seconds//3600 != 0 else ""}{(tmp.seconds//60)%60:02}:{tmp.seconds%60:02}")
					if (
						tmp.seconds > 60*10 or # More than 10 minutes left
						num == len(state.schedule.classes)-1 # Last class of the day
					):
						state.currentClassIndex = num + 1
						self.setClassLabels(_class)
					else: # Less than 10 mins left
						state.currentClassIndex = num + 2
						next_classes = state.schedule.classes[num+1]
						self.setClassLabels(next_classes, aux=True)
					break
			else: # No class ends after now (No If branch broke the loop)
				self.mainLabel.setText(loc.mainlabel.dayOver)
				state.currentClassIndex = -1
				for frame in self.classFrames:
					frame.hide()
				self.auxLabel.hide()
				self.separator.hide()
				self.timeFrame.hide()
				self.classesContainer.hide()
				try:
					await asleep(10)
				except KeyboardInterrupt:
					return
				continue
			update_delay = self.batterySaverEnabled(5, 1)
			if state.dummyDate is not None:
				state.dummyDate = state.dummyDate + timedelta(seconds=1)
			delay = min(max(0.01, update_delay - (perf_counter() - _start)), 10)
			try:
				await asleep(delay)
			except KeyboardInterrupt:
				return
