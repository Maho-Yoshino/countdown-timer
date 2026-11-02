from json import load as jload, dump as jdump
from pathlib import Path
from logging import getLogger
from datetime import timedelta, datetime, time, date
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from .classes import Classes
	from .events import Events
from ..state import getTime

@dataclass(slots=True)
class _classData:
	name:str|None = None
	room:str|None = None
	teacher:str|None = None
	@classmethod
	def from_dict(cls, **data):
		return cls(**data)
@dataclass(slots=True, init=True)
class UnifiedClassData:
	classIndex:int
	end:time
	start:time
	data: list[_classData|None]
	def __init__(self, classIndex:int, end:time, start:time, data:_classData|list[_classData|None]|None):
		self.classIndex = classIndex
		self.end = end
		self.start = start
		if data is None:
			self.data = []
		elif isinstance(data, list):
			self.data = data
		else:
			self.data = [data,]
	@classmethod
	def from_dict(cls, **data):
		return cls(**data)

_defaults = {
	"default": [{},{},{},{},{}],
	"secondary": {},
	"offsetSecondary": False, # Offset the secondary schedule by 1 week (A-B weeks -> B-A weeks essentially)
	"delay":0,
	"group":-1, # In case more than 1 class is given for a class, display the n-th one; If -1 then display all 
	"timeSlots": {}
}
class ScheduleSettings:
	# NOTE: Changes are not persisted until save() is called explicitly
	def __init__(self, classes:'Classes', events:'Events'):
		self._logger = getLogger(__name__)
		self.classes = classes
		self.events = events
		self.path = Path("config") / "schedule.json"
		self.path.parent.mkdir(parents=True, exist_ok=True)
		if (not self.path.exists()):
			self._logger.warning("Schedule file not found, creating a default one.")
			self._data = {}
			self.save()
		else:
			with open(self.path, "r", encoding="utf-8") as f:
				self._data = jload(f)
				self._logger.info("Schedule settings loaded")

		changed = False
		for key, value in _defaults.items():
			if key not in self._data:
				self._data[key] = value
				changed = True
		if changed:
			self.save()
	def _numeric_sort_key(self, key) -> tuple[int, int | str]:
		try:
			return (0, int(key))
		except (TypeError, ValueError):
			return (1, str(key))
	def _ordered_slot_dict(self, data:dict) -> dict:
		return {
			key: data[key]
			for key in sorted(data.keys(), key=self._numeric_sort_key)
		}
	def _normalize_key_order(self):
		if isinstance(self._data.get("default"), list):
			self._data["default"] = [
				self._ordered_slot_dict(day) if isinstance(day, dict) else day
				for day in self._data["default"]
			]
		if isinstance(self._data.get("secondary"), dict):
			self._data["secondary"] = {
				day: self._ordered_slot_dict(slots) if isinstance(slots, dict) else slots
				for day, slots in sorted(self._data["secondary"].items(), key=lambda item: self._numeric_sort_key(item[0]))
			}
		if isinstance(self._data.get("timeSlots"), dict):
			self._data["timeSlots"] = self._ordered_slot_dict(self._data["timeSlots"])
	def save(self):
		self._normalize_key_order()
		with self.path.open("w", encoding="utf-8") as f:
			jdump(self._data, f, indent=4, ensure_ascii=False)
	# region default
	@property
	def default(self) -> list[dict[str, str|None|_classData|list[_classData|None]]]:
		returnData:list[dict[str, '_classData'|None]] = []
		for ind, day in enumerate(self._data["default"]):
			returnData.append({})
			for key, value in day.items():
				returnData[ind][key] = self.convertToClassData(value) 
		return returnData
	def setDefaultSchedule(self, day:int, value:dict[str, str|None|dict[str, str]]):
		if day not in range(7):
			raise IndexError("Day must be between 0 (Monday) and 6 (Sunday).")
		tmp = self.default
		while len(self.default) < day+1:
			tmp.append({})
		tmp[day] = value
		self._data["default"] = tmp
	# endregion
	# region secondary
	@property
	def secondary(self) -> dict[str, dict[str, str|list[str]|None]]:
		return self._data["secondary"]
	def setSecondary(self, index:int, value:dict[str, str|list[str]|None]):
		self._data["secondary"][str(index)] = value
	@property
	def offsetSecondary(self) -> bool:
		return self._data["offsetSecondary"]
	@offsetSecondary.setter
	def offsetSecondary(self, value:bool):
		self._data["offsetSecondary"] = value
	def currentlySecondaryWeek(self, _date:datetime|date|None = None) -> bool:
		if _date is None: _date = getTime()
		if isinstance(_date, datetime): _date = _date.date()
		return _date.isocalendar().week % 2 == int(self.offsetSecondary)
	# endregion
	# region delay
	@property
	def delay(self) -> int:
		return self._data["delay"]
	@delay.setter
	def delay(self, value: int):
		self._data["delay"] = value
	# endregion
	# region Class group
	@property
	def group(self) -> int:
		return self._data["group"]
	@group.setter
	def group(self, value:int):
		self._data["group"] = value
		self.save()
	# endregion
	# region time slots
	@property
	def timeSlots(self) -> dict[int, str]:
		tmp:dict[int, tuple[time, time]] = {}
		for _classIndex, times in self._data["timeSlots"].items():
			_classIndex:str; times:str
			tmp[int(_classIndex)] = times
		return tmp
	@property
	def timeSlotsTime(self) -> dict[int, tuple[time, time]]:
		tmp:dict[int, tuple[time, time]] = {}
		for _classIndex, times in self._data["timeSlots"].items():
			_classIndex:str; times:str
			_ = times.split("-")
			startTime = datetime.strptime(_[0], "%H:%M").time()
			endTime = datetime.strptime(_[1], "%H:%M").time()
			tmp[int(_classIndex)] = (startTime, endTime)
		return tmp
	def setTimeSlots(self, _class:int, startTime:time, endTime:time):
		self._data["timeSlots"][str(_class)] = f"{startTime.strftime("%H:%M")}-{endTime.strftime("%H:%M")}"
	# endregion
	# region Unified schedule (Primary, Secondary and Special days combined)
	def convertToClassData(self, data:str|dict[str, str]|None|list[str|dict[str, str]]) -> list[_classData|None]|_classData|None:
		if isinstance(data, str):
			return _classData(**self.classes.get(data))
		elif isinstance(data, dict):
			return _classData(**data)
		elif isinstance(data, list):
			_ = []
			for data2 in data:
				if isinstance(data2, str):
					_.append(_classData(**self.classes.get(data2)))
				elif isinstance(data2, dict):
					_.append(_classData(**data2))
				elif data2 is None:
					_.append(None)
				elif isinstance(data2, _classData):
					_.append(data2)
				else:
					raise ValueError(f"Invalid type ({type(data2)}) given")
			return _
		elif data is None:
			return None
		elif isinstance(data, _classData):
			return data
		else:
			raise ValueError(f"Invalid type ({type(data)}) given")
	def getUnifiedSchedule(self, week_of:datetime|None=None) -> list[list[UnifiedClassData]]:
		finalSchedule:list[list[UnifiedClassData]] = []
		defaultTimeSlots = self.timeSlotsTime
		for ind, _day in enumerate(self.default):
			finalSchedule.append([])
			for classIndex, data in sorted(_day.items(), key=lambda item: int(item[0])):
				times = defaultTimeSlots[int(classIndex)]
				finalSchedule[ind].append(UnifiedClassData(data=data, classIndex=int(classIndex), start=times[0], end=times[1]))
		# region Get week constraints
		if week_of is None: _date = getTime().date() # Get current week if other week is not given
		else: _date = week_of.date()
		weekstart = _date - timedelta(days=_date.weekday()) # Get monday
		# endregion
		# region Secondary Week
		if self.currentlySecondaryWeek(_date):
			for dayInd, secondary_day in self.secondary.items():
				for classIndex, classID in sorted(secondary_day.items(), key=lambda item: int(item[0])):
					times = defaultTimeSlots[int(classIndex)]
					finalSchedule[int(dayInd)].append(UnifiedClassData(data=self.convertToClassData(classID), classIndex=int(classIndex), start=times[0], end=times[1]))
		# endregion
		# region Special days
		for _date, special_day in self.events.specialDays.items(): # Merge special days with the new schedule
			_date:datetime; special_day:dict[str, bool|dict[str, str|None|list[str]]]
			if weekstart > _date.date():
				continue
			if _date.date() >= weekstart + timedelta(days=7):
				continue
			full_schedule:bool = special_day.get("full", False)
			newTimeSlots = special_day.get("timeSlots")
			if newTimeSlots:
				tmp = newTimeSlots
				newTimeSlots = {int(k):v for k, v in defaultTimeSlots.items()}
				for ind, times in tmp.items():
					_ = times.split("-")
					start = datetime.strptime(_[0], "%H:%M").time()
					end = datetime.strptime(_[1], "%H:%M").time()
					newTimeSlots[int(ind)] = (start, end)
			else:
				newTimeSlots = {int(k):v for k, v in defaultTimeSlots.items()}
			_classes:dict[str, str|None|list[str]]|None = special_day.get("classes")
			new_timetable = [] if full_schedule else deepcopy(finalSchedule[_date.weekday()])
			if _classes is None:
				for _class in new_timetable:
					_class.start = newTimeSlots[int(_class.classIndex)][0]
					_class.end = newTimeSlots[int(_class.classIndex)][1]
			else:
				for classIndex, _class in _classes.items():
					classIndexInt = int(classIndex)
					new_timetable = [entry for entry in new_timetable if entry.classIndex != classIndexInt]
					times = newTimeSlots[classIndexInt]
					new_timetable.append(UnifiedClassData(data=self.convertToClassData(_class), classIndex=classIndexInt, start=times[0], end=times[1]))
			finalSchedule[_date.weekday()] = sorted(new_timetable, key=lambda item: item.classIndex)
		# endregion
		return finalSchedule
	# endregion