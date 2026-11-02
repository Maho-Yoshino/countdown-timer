import modules.state as state
from json import load as jload, dump as jdump
from pathlib import Path
from logging import getLogger
from typing import Literal

_defaults = {
	"background": "#000000",
	"foreground": "#FFFFFF",
	"lang": "en",
	"ignoreUpdates": False,
	"alpha": {"default": 0.75, "onHover":0.25},
	"showTeacher": False
}
def clamp(num:int|float, _min:int|float, _max:int|float): return max(_min, min(num, _max))
class Config:
	# NOTE: Changes are not persisted until save() is called explicitly
	def __init__(self):
		self._logger = getLogger(__name__)
		self.path = Path("config") / "config.json"
		self.path.parent.mkdir(parents=True, exist_ok=True)
		if (not self.path.exists()):
			self._logger.warning("Config file not found, creating a default one.")
			self._data = {}
			self.save()
		else:
			with open(self.path, "r", encoding="utf-8") as f:
				self._data = jload(f)
				self._logger.info("Configs loaded")

		changed = False
		for key, value in _defaults.items():
			if key not in self._data:
				self._data[key] = value
				changed = True
		if changed:
			self.save()
	def save(self):
		with self.path.open("w", encoding="utf-8") as f:
			jdump(self._data, f, indent=4, ensure_ascii=False)
	# region Update
	@property # ignoreUpdates
	def ignoreUpdates(self) -> bool:
		return self._data["ignoreUpdates"]
	@ignoreUpdates.setter
	def ignoreUpdates(self, value:bool):
		self._data["ignoreUpdates"] = value
	# endregion
	# region alpha
	@property
	def alpha(self) -> dict[str, float]:
		return self._data["alpha"]
	def setAlpha(self, _type:Literal["default", "onHover"], value:float):
		self._data["alpha"][_type] = clamp(value,0,1)
	# endregion
	# region showTeacher
	@property
	def showTeacher(self) -> bool:
		return self._data["showTeacher"]
	@showTeacher.setter
	def showTeacher(self, value:bool):
		self._data["showTeacher"] = value
		try:
			for frame in state.clock.classFrames:
				if value:
					frame.teacherLabel.grid(row=2)
				else:
					frame.teacherLabel.grid_forget()
		except (AttributeError, NameError):
			self._logger.exception("Could not find clock's class frames")
	# endregion
	# region debug
	@property
	def debug(self) -> bool:
		return self._data.get("debug", False)
	# endregion
	# region logLevel
	@property # logLevel
	def logLevel(self) -> Literal[10, 20, 30, 40, 50]:
		"""
		Logging levels:
		------------
		0 - Unset  
		10 - DEBUG  
		20 - INFO  
		30 - WARNING / WARN  
		40 - ERROR  
		50 - FATAL / CRITICAL  
		"""
		return self._data.get("logLevel", 10)	
	# endregion
	# region Background color
	@property
	def background(self) -> int:
		try:
			return int(self._data["background"].removeprefix("#"), 16)
		except ValueError:
			self._logger.error(f"Invalid background value given in settings ({self._data["background"]}), defaulting to white.")
			return int(self._defaults["background"].removeprefix("#"), 16)
	@background.setter
	def background(self, value:int):
		_ = f"#{value:06X}"
		clk = state.clock
		self._data["background"] = _
		state.clock.root.config(background=_)
		clk.mainLabel.config(background=_)
		clk.timeLabel.config(background=_)
		clk.auxLabel.config(background=_)
		clk.homeworkLabel.config(background=_)
		clk.examLabel.config(background=_)
		clk.separator.config(background=_)
		clk.vertSeparator.config(background=_)
		for frame in clk.classFrames:
			frame.bg = _
	# endregion
	# region Foreground color
	@property
	def foreground(self) -> int:
		return int(self._data["foreground"].removeprefix("#"), 16)
	@foreground.setter
	def foreground(self, value:int):
		_ = f"#{value:06X}"
		clk = state.clock
		self._data["foreground"] = _
		clk.mainLabel.config(fg=_)
		clk.timeLabel.config(fg=_)
		clk.auxLabel.config(fg=_)
		clk.homeworkLabel.config(fg=_)
		clk.examLabel.config(fg=_)
		clk.separator.config(fg=_)
		clk.vertSeparator.config(fg=_)
		for frame in clk.classFrames:
			frame.fg = _
	# endregion
	# region Language
	@property
	def lang(self) -> str:
		return self._data["lang"]
	@lang.setter
	def lang(self, value:str):
		self._data["lang"] = value
		self.save()
	# endregion