import modules.state as state
from datetime import datetime, timedelta
from asyncio import sleep as asleep, CancelledError
from time import perf_counter
from logging import getLogger
from tkinter import Button, Label, Frame, TclError, Tk, Toplevel
from tksvg import SvgImage
from ctypes import windll, c_byte, byref, Structure
from modules.schedule import Schedule
from modules.settings.schedule import UnifiedClassData, _classData

init_data:dict[str, int|str] = {}
class classFrame(Frame):
	_data:dict[str, int|str|_classData|None]
	def __init__(self, master, _class:_classData|None):
		self._data = {
			"wraplength": 0,
			"bg":init_data["bg"],
			"fg":init_data["fg"],
			"class":_class
		}
		self._logger = getLogger(__name__)
		super().__init__(master, bg=init_data["bg"])
		self.nameLabel = Label(self, cnf=init_data, padx=5, anchor="n", justify="center")
		self.roomLabel = Label(self, cnf=init_data, padx=5, anchor="n", justify="center")
		self.teacherLabel = Label(self, cnf=init_data, padx=5, anchor="n", justify="center")
		self._class = _class
	# region Class
	@property
	def _class(self) -> _classData|None:
		return self._data["class"]
	@_class.setter
	def _class(self, value:_classData|None):
		self._data["class"] = value
		if value is not None:
			self.nameLabel.config(text=value.name)
			self.nameLabel.grid(row=0)
			self.roomLabel.config(text=value.room)
			self.roomLabel.grid(row=1)
			self.teacherLabel.config(text=value.teacher)
			if state.settings.config.showTeacher:
				self.teacherLabel.grid(row=2)
			else:
				self.teacherLabel.grid_forget()
		else:
			self.nameLabel.config(text=state.settings.localization.noneClass)
			self.nameLabel.grid(row=0)
			self.roomLabel.grid_forget()
			self.teacherLabel.grid_forget()
	# endregion
	# region Background
	@property
	def bg(self) -> str:
		return self._data["bg"]
	@bg.setter
	def bg(self, value:str):
		self._data["bg"] = value
		self.nameLabel.config(bg=value)
		self.roomLabel.config(bg=value)
		self.teacherLabel.config(bg=value)
		self.config(bg=value)
	# endregion
	# region Foreground
	@property
	def fg(self) -> str:
		return self._data["fg"]
	@fg.setter
	def fg(self, value:str):
		self._data["fg"] = value
		self.nameLabel.config(fg=value)
		self.roomLabel.config(fg=value)
		self.teacherLabel.config(fg=value)
	# endregion
	# region Wraplength
	@property
	def wraplength(self) -> int:
		return self._data["wraplength"]
	@wraplength.setter
	def wraplength(self, value:int):
		self._data["wraplength"] = value
		self.nameLabel.config(wraplength=value)
		self.roomLabel.config(wraplength=value)
		self.teacherLabel.config(wraplength=value)
	# endregion
class Clock(Tk):
	def __init__(self):
		# Rows setup:
		# 0 - Mainlabel
		# 1 - TimeFrame (timeLabel, homeworkLabel, examLabel)
		# 2 - Horizontal separator
		# 3 - classesFrame
		# 4 - auxLabel
		global init_data
		init_data = {
			"text":"",
			"bg":f"#{state.settings.config.background:06x}",
			"fg":f"#{state.settings.config.foreground:06x}"
		}
		state.schedule = Schedule()
		# region Misc config
		super().__init__()
		self.logger = getLogger(__name__)
		# endregion
		# region Main config
		self.iconbitmap(default="assets/icon.ico")
		self.configure(bg=f"#{state.settings.config.background:06x}")
		self.attributes("-topmost", True)
		self.title(state.windowHandle)
		self.resizable(False, False)
		self.overrideredirect(True)
		self.wm_attributes("-alpha", state.settings.config.alpha["default"])
		width = self.winfo_screenwidth()//6
		height = self.winfo_screenheight()//4
		self.geometry(f"{width}x{height}+{self.winfo_screenwidth()-width}+0")
		self.config(padx=15, pady=15)
		self.grid_columnconfigure(0, weight=1)
		# endregion
		# region Main text and time config
		self.mainLabel = Label(self, init_data, font=state.fontSize(20))
		self.mainLabel.grid(row=0, column=0, sticky="nsew")
		self.mainLabel.grid_rowconfigure(0, weight=1)

		self.timeFrame = Frame(self, bg=init_data["bg"]) # Frame so the exam and homework icons can happen
		self.timeFrame.grid_rowconfigure(0, weight=1)
		self.timeFrame.grid_rowconfigure(1, weight=1)
		self.timeLabel = Label(self.timeFrame, init_data, font=state.fontSize(30), anchor="center")
		self.timeLabel.grid(column=1)
		self.timeLabel.grid_columnconfigure(1, weight=1)
		self.homeworkIcon = self.loadSvg("homework")
		self.homeworkLabel = Label(self.timeFrame, image=self.homeworkIcon, bg=init_data["bg"], fg=init_data["fg"])
		self.homeworkLabel.image = self.homeworkIcon
		self.examIcon = self.loadSvg("exam")
		self.examLabel = Label(self.timeFrame, image=self.examIcon, bg=init_data["bg"], fg=init_data["fg"])
		self.examLabel.image = self.examIcon
		# endregion
		# region Classes setup
		self.separator = Frame(self, bg=init_data["fg"], height=1, width=self.winfo_screenwidth())
		
		self.classesContainer = Frame(self, bg=init_data["bg"])
		self.classFrames:list[classFrame] = []
		highestClassesAtOnce = 0
		unified = state.settings.schedule.getUnifiedSchedule()
		for ind, day in enumerate(unified):
			if len(unified[highestClassesAtOnce]) < len(day):
				highestClassesAtOnce = ind
		for _ in range(len(unified[highestClassesAtOnce])):
			_ = unified[highestClassesAtOnce][_].data
			for _ in [classFrame(self.classesContainer, _[i]) for i in range(len(_))]:
				self.classFrames.append(_)
		self.vertSeparators:list[Frame] = []

		self.grid_rowconfigure(3, weight=1)
		# endregion
		# region Misc setup
		self.auxLabel = Label(self, init_data, font=state.fontSize(10), anchor="center", justify="center", text=state.settings.localization.nextClass)
		self.grid_rowconfigure(4, weight=0)

		self.protocol("WM_DELETE_WINDOW", self.withdraw)
		# endregion
		# region Asyncio loops
		self.mainloopTask = state.runtime.create_task(self.mainloop())
		self.mainloopTask.add_done_callback(state.exc_handler)
		self.setClickThroughTask = state.runtime.create_task(self.setClickThrough())
		self.setClickThroughTask.add_done_callback(state.exc_handler)
		self.transparencyTask = state.runtime.create_task(self.transparencyCheck())
		self.transparencyTask.add_done_callback(state.exc_handler)
		# endregion
		self.logger.info("Clock setup complete")
	def refreshFromSettings(self):
		bg = f"#{state.settings.config.background:06x}"
		fg = f"#{state.settings.config.foreground:06x}"
		self.configure(bg=bg)
		self.mainLabel.config(bg=bg, fg=fg)
		self.timeFrame.config(bg=bg)
		self.timeLabel.config(bg=bg, fg=fg)
		self.auxLabel.config(bg=bg, fg=fg)
		self.separator.config(bg=fg)
	
		self.homeworkIcon = self.loadSvg("homework")
		self.homeworkLabel.config(image=self.homeworkIcon, bg=bg, fg=fg)
		self.homeworkLabel.image = self.homeworkIcon
	
		self.examIcon = self.loadSvg("exam")
		self.examLabel.config(image=self.examIcon, bg=bg, fg=fg)
		self.examLabel.image = self.examIcon
	
		state.schedule = Schedule()
		self.rebuildClassFrames()
	def rebuildClassFrames(self):
		for frame in self.classFrames:
			frame.destroy()
		self.classFrames.clear()
	
		for sep in self.vertSeparators:
			sep.destroy()
		self.vertSeparators.clear()
	
		unified = state.settings.schedule.getUnifiedSchedule()
		max_groups = 1
		for day in unified:
			for entry in day:
				if entry.data is not None:
					max_groups = max(max_groups, len(entry.data))
	
		for _ in range(max_groups):
			self.classFrames.append(classFrame(self.classesContainer, None))
	def loadSvg(self, filename:str) -> SvgImage:
		try:
			with open(f"assets/{filename}.svg", "r") as file:
				svg_text = file.read().replace("<svg ", f"<svg fill='#{state.settings.config.foreground:06x}' ")
		except FileNotFoundError:
			self.logger.exception(f"File \"assets/{filename}.png\" could not be found")
			raise
		return SvgImage(filename, master=self.timeFrame, data=svg_text, scaletoheight=25)
	lastWidth:int = 0
	async def setClickThrough(self):
		self.logger.debug("Setting click-through window")
		while not self.winfo_viewable():
			await asleep(0.05)
		self.logger.debug("Window found")
		try:
			while True:
				hwnd = windll.user32.FindWindowW(None, self.title())
				styles = windll.user32.GetWindowLongW(hwnd, -20)
				styles |= 0x00000020  # WS_EX_LAYERED (Allows transparency)	
				styles |= 0x00000080  # WS_EX_TRANSPARENT (Click-through)
				windll.user32.SetWindowLongW(hwnd, -20, styles)
				if (windll.user32.GetWindowLongW(hwnd, -20)) & 0x00000080 == 0x00000080:
					self.logger.debug("Click-through successfully set")
					break
				await asleep(0.5)
		except CancelledError: pass
		except Exception:
			self.logger.exception(f"An error occured while setting transparency setting")
	def batterySaverEnabled(self, on_val, off_val):
		try:
			class SYSTEM_POWER_STATUS(Structure):
				_fields_ = [
					("ACLineStatus", c_byte),
					("BatteryFlag", c_byte),
					("BatteryLifePercent", c_byte),
					("SystemStatusFlag", c_byte)
				]
			status = SYSTEM_POWER_STATUS()
			if windll.kernel32.GetSystemPowerStatus(byref(status)) == 0:
				return off_val # Failed to get status, assume OFF
			return on_val if bool(status.SystemStatusFlag & 1) else off_val  # 1 means Battery Saver is ON
		except (ImportError, CancelledError):
			return
		except Exception:
			self.logger.exception("An error occurred while checking battery saver status.") 
	async def transparencyCheck(self):
		async def isCursorOverWindow():
			win_x = self.winfo_rootx()
			win_y = self.winfo_rooty()
			return (win_x <= self.winfo_pointerx() <= win_x + self.winfo_width() and 
					win_y <= self.winfo_pointery() <= win_y + self.winfo_height())
		while True:
			try:
				if not await isCursorOverWindow() and self.wm_attributes("-alpha") != state.settings.config.alpha["default"]: 
					self.wm_attributes("-alpha", state.settings.config.alpha["default"])
				elif await isCursorOverWindow() and self.wm_attributes("-alpha") != state.settings.config.alpha["onHover"]: 
					self.wm_attributes("-alpha", state.settings.config.alpha["onHover"])
				await asleep(self.batterySaverEnabled(1, 0.1))
			except CancelledError:
				break
			except TclError:
				if state.tray is not None and state.tray.shutting_down:
					break
				await asleep(0.1)
			except Exception:
				self.logger.exception("An error happened during transparency check")
	def setClassLabels(self, classes:UnifiedClassData, aux:bool = False):
		self.mainLabel.grid(row=0, column=0)
		self.timeFrame.grid(row=1, column=0)
		self.separator.grid(row=2, column=0, sticky="ns")

		self.classesContainer.grid(row=3, column=0)
		# region Add Vertical Separators
		if state.settings.schedule.group == -1:
			if classes.data is None: needed = 0
			else: needed = max(0, len(classes.data)-1)
			while len(self.vertSeparators) < needed:
				sep = Frame(self.classesContainer, bg=init_data["fg"], width=1)
				self.vertSeparators.append(sep)
			for idx, sep in enumerate(self.vertSeparators):
				if idx < needed:
					sep.grid(column=idx*2+1, row=0, sticky="ns")
				else:
					sep.grid_forget()
		# endregion
		# region Add Classes
		self.update_idletasks() # to fix wraplength being 1 on startup
		for i in range(len(classes.data)):
			obj = self.classFrames[i]

			if state.settings.schedule.group == -1 or state.settings.schedule.group == i:
				obj.grid(row=0, column=i*2, sticky="nsew")
			
			if len(classes.data) > 1:
				obj.wraplength = self.winfo_width()//len(classes.data)
			elif len(classes.data) == 1:
				for _ in range(len(self.vertSeparators)):
					self.vertSeparators.pop().grid_forget()
				for j in self.classFrames:
					j.grid_forget()
				obj.wraplength = self.winfo_width()
				obj.grid(row=0, column=0, sticky="nsew")
			else:
				obj.grid_forget()
			
			if state.settings.config.showTeacher:
				obj.teacherLabel.grid(row=2)
				obj.grid_rowconfigure(2, weight=1, minsize=20)
			else:
				obj.teacherLabel.grid_forget()
			obj._class = classes.data[i]
		# endregion
		# region Exam and Homework icons
		if state.settings.events.current_exam():
			self.homeworkLabel.grid_forget()
			self.examLabel.grid(row=1, column=3)
		elif state.settings.events.current_homework():
			self.examLabel.grid_forget()
			self.homeworkLabel.grid(row=1, column=3)
		else:
			self.examLabel.grid_forget()
			self.homeworkLabel.grid_forget()
		# endregion
		# region Aux label
		if not aux:
			self.auxLabel.grid_forget()
		else:
			self.auxLabel.grid(row=4, column=0, sticky="ns", columnspan=3)
	# endregion
	alerted:datetime = datetime.fromtimestamp(0)
	def showAlertPopup(self, alert:dict[str, str]):
		loc = state.settings.localization
		bg = f"#{state.settings.config.background:06x}"
		fg = f"#{state.settings.config.foreground:06x}"
		popup = Toplevel(self)
		popup.title(loc.alert.title)
		popup.configure(bg=bg, padx=14, pady=12)
		popup.attributes("-topmost", True)
		popup.resizable(False, False)
		Label(
			popup,
			text=alert.get("message", loc.alert.defaultText),
			bg=bg,
			fg=fg,
			justify="center",
			wraplength=280,
		).pack(fill="both", expand=True, pady=(0, 10))
		Button(popup, text="OK", command=popup.destroy).pack()
		popup.update_idletasks()
		x = self.winfo_screenwidth() // 2 - popup.winfo_width() // 2
		y = self.winfo_screenheight() // 2 - popup.winfo_height() // 2
		popup.geometry(f"+{x}+{y}")

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
				if len(state.schedule.classes) == 0: await asleep(60*30) # 30 min delay
				continue
			now = state.getTime()
			now_time = now.time()
			self.sendAlert()
			loc = state.settings.localization
			self.grid_rowconfigure(0, weight=0)
			for num, _class in enumerate(state.schedule.classes):
				if _class.data is None:
					continue
				if ((_ := datetime.combine(now, _class.start) + timedelta(seconds=delay)).time() > now_time): # Break time
					tmp = _ - now
					self.mainLabel.config(text=loc.format(loc.mainlabel.onBreak, num=f"{_class.classIndex}{loc.classNumbering.getSuffix(num+1)}"))
					self.timeLabel.config(text=f"{f"{tmp.seconds//3600:02}:" if tmp.seconds//3600 != 0 else ""}{(tmp.seconds//60)%60:02}:{tmp.seconds%60:02}")
					self.setClassLabels(_class)
					break
				elif ((_ := datetime.combine(now, _class.end) + timedelta(seconds=delay)).time() > now_time): # In class
					tmp = _ - now
					self.mainLabel.config(text=loc.format(loc.mainlabel.inClass, num=f"{_class.classIndex}{loc.classNumbering.getSuffix(num+1)}"))
					self.timeLabel.config(text=f"{f"{tmp.seconds//3600:02}:" if tmp.seconds//3600 != 0 else ""}{(tmp.seconds//60)%60:02}:{tmp.seconds%60:02}")
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
				self.mainLabel.config(text=loc.mainlabel.dayOver)
				self.grid_rowconfigure(0, weight=100)
				state.currentClassIndex = -1
				for frame in self.classFrames: 
					if frame.winfo_ismapped(): frame.grid_forget()
				self.auxLabel.grid_forget()
				self.separator.grid_forget()
				[i.grid_forget() for i in self.vertSeparators]
				self.timeFrame.grid_forget()
				try:
					await asleep(10)
				except KeyboardInterrupt: return
				continue
			update_delay = self.batterySaverEnabled(5, 1)
			if state.dummyDate is not None:
				state.dummyDate = state.dummyDate + timedelta(seconds=1)
			delay = min(max(0.01, update_delay - (perf_counter() - _start)), 10)
			try:
				await asleep(delay)
			except KeyboardInterrupt: return
