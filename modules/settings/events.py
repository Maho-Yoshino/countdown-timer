from json import load as jload, dump as jdump
from pathlib import Path
from logging import getLogger
from datetime import datetime, date, time, timedelta
import modules.state as state

logger = getLogger(__name__)

_defaults = {
	"specialDays": {},
	"alerts": [],
	"exams": {},
	"homework": {}
}
class Events:
	# NOTE: Changes are not persisted until save() is called explicitly
	def __init__(self):
		self.datetime_fmt = "%Y-%m-%d"
		self.path = Path("config") / "events.json"
		self.path.parent.mkdir(parents=True, exist_ok=True)
		if (not self.path.exists()):
			logger.warning("Events file not found, creating a default one.")
			self._data = {}
			self.save()
		else:
			with open(self.path, "r", encoding="utf-8") as f:
				self._data = jload(f)
				logger.info("Events loaded")

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
	
	# region specialDays
	@property 
	def specialDays(self) -> dict[
		datetime, dict[
			str, 
			str | list[str] | bool | None | dict[str, str] | list[dict[str, str]]
		]
	]:
		today = state.getTime().date()
		new_data:dict[date, bool|dict[str, str]] = {}
		changed:bool=False
		for _date, data in self._data["specialDays"].items():
			_date = datetime.strptime(_date, "%Y-%m-%d")
			if _date.date() < today:
				changed = True
				continue
			new_data[_date] = data
		if changed:
			self._data["specialDays"] = {
				day.strftime(self.datetime_fmt): schedule
				for day, schedule in new_data.items()
			}
			self.save()
		return new_data
	def setSpecialDay(self, day:datetime, schedule:dict[str, str|list[str]|None|dict[str, str]|list[dict[str, str]]]):
		self._data["specialDays"][day.strftime(self.datetime_fmt)] = schedule
		self.save()
	# endregion
	# region alerts
	alertShownError:bool = False
	@property # alerts
	def alerts(self) -> list[dict[str, int|bool|str]]:
		try:
			change:bool = False
			newAlerts:list[dict[str, int|bool|str]] = []
			now_minute = state.getTime().replace(second=0, microsecond=0)
			for alert in self._data["alerts"]:
				alert:dict[str, int|bool|str]
				if "time" not in alert:
					change = True
					continue
				new = dict(alert)
				new["message"] = alert.get("message", "Set alert has arrived")
				new["keep"] = alert.get("keep", False)
				if (weekday := alert.get("weekday", None)) is not None:
					new.update({"weekday": weekday})
				if (_date := alert.get("date", None)) is not None:
					new.update({"date": _date})
					if new["keep"] or datetime.strptime(f"{_date} {new['time']}", f"{self.datetime_fmt} %H:%M") >= now_minute:
						newAlerts.append(new)
					else:
						change = True
				else:
					alert_time = datetime.strptime(new["time"], "%H:%M").time()
					if "weekday" in new:
						alert_dt = datetime.combine((now_minute.date() + timedelta(days=(new["weekday"] - now_minute.weekday()) % 7)), alert_time)
					else:
						alert_dt = datetime.combine(now_minute.date(), alert_time)
						if alert_dt < now_minute:
							alert_dt += timedelta(days=1)
					if alert_dt >= now_minute:
						newAlerts.append(new)
					else:
						change = True
			if change:
				self._data["alerts"] = newAlerts
				self.save()
			return newAlerts
		except Exception as e:
			if not self.alertShownError:
				logger.exception("Error loading alert times")
				self.alertShownError = True
			return []
	def setAlertTime(self, time:time, *, day:date|int=None, keep:bool=False, message:str=None):
		if message is None:
			message = state.settings.localization.alert.defaultText
		tmp = {
			"message": message,
			"keep": keep,
			"time": time.strftime("%H:%M")
		}
		if isinstance(day, datetime):
			tmp.update({"date": day.strftime(self.datetime_fmt)})
		elif isinstance(day, int):
			tmp.update({"weekday": day})
		self.alerts.append(tmp)
		self.save()
	def delAlertTime(self, time:time, *, day:date|int=None):
		keep = []
		change = False
		for alert in self.alerts:
			if datetime.strptime(alert["time"], "%H:%M").time() != time:
				keep.append(alert)
			else:
				if (isinstance(day, int) and day == alert.get("weekday", None)) or (alert.get("date", None) is not None and isinstance(day, date) and day == alert["date"]):
					change = True
		if change:
			self.alerts = keep
			self.save()
	# endregion
	# region exams
	@property
	def exams(self) -> dict[datetime, list[dict[datetime, str|int]]]:
		tmp = {}
		today:date = state.getTime().date()
		change:bool = False
		for day, items in self._data["exams"].items():
			examDay = datetime.strptime(day, self.datetime_fmt)
			if today > examDay.date():
				change = True
				continue
			tmp.update({examDay:items})
		if change:
			self._data["exams"] = tmp
			self.save()
		return tmp
	def setExam(self, _date:datetime, _class:int, topic:str):
		if (datestr := _date.strftime(self.datetime_fmt)) not in self._data["exams"].keys():
			self._data["exams"].update({datestr:[]})
		self._data["exams"][datestr].append({
			"class":_class,
			"topic":topic
		})
		self.save()
	def current_exam(self) -> bool:
		if state.currentClassIndex is None:
			return False
		today = state.getTime().date()
		exams = self.exams.get(
			datetime.combine(today, time()),
			[]
		)
		return any(e["class"] == state.currentClassIndex for e in exams)

	# endregion
	# region homework
	@property
	def homework(self) -> dict[str, list[dict[datetime, str|int]]]:
		tmp = {}
		today:date = state.getTime().date()
		change:bool = False
		for day, items in self._data["homework"].items():
			examDay = datetime.strptime(day, self.datetime_fmt)
			if today < examDay:
				change = True
				continue
			tmp.update({datetime.strptime(day, self.datetime_fmt):items})
		if change:
			self._data["homework"] = tmp
			self.save()
		return tmp
	def setHomework(self, _date:datetime, _class:int, topic:str):
		if datestr := _date.strftime(self.datetime_fmt) not in self._data["homework"].keys():
			self._data["homework"].update({datestr:[]})
		self._data["homework"][datestr].append({
			"class":_class,
			"topic":topic
		})
		self.save()
	def current_homework(self) -> bool:
		if state.currentClassIndex is None:
			return False
		today = state.getTime().date()
		homework = self.homework.get(
			datetime.combine(today, time()),
			[]
		)
		return any(e["class"] == state.currentClassIndex for e in homework)
	# endregion
	
	
