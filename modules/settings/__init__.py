from .classes import Classes
from .config import Config
from .events import Events
from .schedule import ScheduleSettings
from .localization import Localization
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config"
class Settings:
	def __init__(self):
		self.reload()
	def reload(self):
		self.classes = Classes(CONFIG_PATH)
		self.config = Config(CONFIG_PATH)
		self.events = Events(CONFIG_PATH)
		self.schedule = ScheduleSettings(CONFIG_PATH, self.classes, self.events)
		self.localization = Localization(CONFIG_PATH, self.config.lang)