from __future__ import annotations
import modules.state as state
from datetime import date, datetime
from logging import getLogger
from .settings.schedule import UnifiedClassData

logger = getLogger(__name__)

class Schedule:
	"""The schedule for a single day. Must be regenerated on day change"""
	classes:list[UnifiedClassData]
	_date:date
	specialDay:bool
	def __init__(self, other_date:datetime|None=None):
		self._date = (other_date if other_date is not None else state.getTime()).date()
		weekday = self._date.weekday()
		self.specialDay = any([day.date() == self._date for day in state.settings.events.specialDays.keys()])
		if weekday not in range(len(state.settings.schedule.default)) and not self.specialDay:
			self.classes = []
			return
		if len(tmp := state.settings.schedule.getUnifiedSchedule(week_of=other_date)) > weekday:
			self.classes = tmp[weekday]
		else:
			logger.warning("The current weekday's index is higher than the schedule has days")
			self.classes = []
		logger.debug(f"Initialized Schedule class (len {len(self.classes)})")