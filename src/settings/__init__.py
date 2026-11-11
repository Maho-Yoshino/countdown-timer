from json import loads, dumps
from logging import getLogger as _getLogger
from pathlib import Path
from typing import Literal, TypedDict

from const import CONFIG, DEBUG

_logger = _getLogger(__name__)


class Alpha(TypedDict):
	default: float
	onHover: float

class FileFormat(TypedDict):
	showTeacher: bool
	ignoreUpdates: bool
	alpha: Alpha
	logLevel: int
	backgroundColor: str
	foregroundColor: str
	lang: str

_DEFAULTS: FileFormat = {
	"showTeacher": False,
	"ignoreUpdates": False,
	"alpha": {"default": 0.75, "onHover": 0.25},
	"logLevel": 10,
	"backgroundColor": "#000000",
	"foregroundColor": "#FFFFFF",
	"lang": "en",
}

class _Settings:
	"""Persistent settings stored as JSON in the platform config directory."""

	def __init__(self, file: str = "config.json") -> None:
		self.__FILE: Path = CONFIG / file
		self.__DATA: dict = self._load()
		self.__CHANGED: dict = {}

	def _load(self) -> dict:
		if not self.__FILE.exists():
			data = dict(_DEFAULTS)
			self.__FILE.write_text(dumps(data, indent=4))
			return data
		return loads(self.__FILE.read_text())

	def _set(self, key: str, value) -> None:
		self.__DATA[key] = value
		self.__CHANGED[key] = value

	@staticmethod
	def _parse_color(value) -> int | None:
		if not isinstance(value, str):
			return None
		try:
			return int(value.removeprefix("#"), 16)
		except ValueError:
			return None

	def _color(self, key: str) -> int:
		value = self.__DATA.get(key)
		color = self._parse_color(value)
		if color is None:
			_logger.error("Invalid %s value in settings (%r), defaulting.", key, value)
			color = self._parse_color(_DEFAULTS[key]) or 0
		return color

	# region Show teacher
	@property
	def showTeacher(self) -> bool:
		return self.__DATA.get("showTeacher", _DEFAULTS["showTeacher"])

	@showTeacher.setter
	def showTeacher(self, value: bool) -> None:
		self._set("showTeacher", value)
	# endregion

	# region Ignore updates
	@property
	def ignoreUpdates(self) -> bool:
		return self.__DATA.get("ignoreUpdates", _DEFAULTS["ignoreUpdates"])

	@ignoreUpdates.setter
	def ignoreUpdates(self, value: bool) -> None:
		self._set("ignoreUpdates", value)
	# endregion

	# region Alpha
	@property
	def alpha(self) -> Alpha:
		value = self.__DATA.get("alpha", _DEFAULTS["alpha"])
		return dict(value) if isinstance(value, dict) else dict(_DEFAULTS["alpha"])

	@alpha.setter
	def alpha(self, value: Alpha) -> None:
		merged = dict(_DEFAULTS["alpha"])
		merged.update(value or {})
		self._set("alpha", merged)

	@property
	def alphaDefault(self) -> float:
		return self.alpha.get("default", _DEFAULTS["alpha"]["default"])

	@alphaDefault.setter
	def alphaDefault(self, value: float) -> None:
		self.alpha = {**self.alpha, "default": value}

	@property
	def alphaOnHover(self) -> float:
		return self.alpha.get("onHover", _DEFAULTS["alpha"]["onHover"])

	@alphaOnHover.setter
	def alphaOnHover(self, value: float) -> None:
		self.alpha = {**self.alpha, "onHover": value}
	# endregion

	# region Debug mode
	@property
	def debug(self) -> bool:
		return DEBUG
	# endregion

	# region Log level
	@property
	def logLevel(self) -> Literal[10, 20, 30, 40, 50]:
		"""Logging level: 10 DEBUG, 20 INFO, 30 WARNING, 40 ERROR, 50 CRITICAL."""
		return self.__DATA.get("logLevel", _DEFAULTS["logLevel"])
	# endregion

	# region Background color
	@property
	def backgroundColor(self) -> int:
		return self._color("backgroundColor")

	@backgroundColor.setter
	def backgroundColor(self, value: int) -> None:
		self._set("backgroundColor", f"#{value:06X}")
	# endregion

	# region Foreground color
	@property
	def foregroundColor(self) -> int:
		return self._color("foregroundColor")

	@foregroundColor.setter
	def foregroundColor(self, value: int) -> None:
		self._set("foregroundColor", f"#{value:06X}")
	# endregion

	# region Language
	@property
	def lang(self) -> str:
		return self.__DATA.get("lang", _DEFAULTS["lang"])

	@lang.setter
	def lang(self, value: str) -> None:
		self._set("lang", value)
	# endregion

	def save(self) -> None:
		if not self.__CHANGED:
			return
		content = loads(self.__FILE.read_text()) if self.__FILE.exists() else dict(self.__DATA)
		content.update(self.__CHANGED)
		self.__FILE.write_text(dumps(content, indent=4))
		self.__DATA = content
		self.__CHANGED = {}


settings = _Settings()
