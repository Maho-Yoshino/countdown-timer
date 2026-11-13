from enum import StrEnum
from typing import ClassVar


class _table(StrEnum):
	__table__: ClassVar[str]

	@classmethod
	def t(cls) -> str:
		return cls.__table__

	def q(self) -> str:
		return f"{self.__table__}.{self.value}"

class classes(_table):
	__table__ = "classes"
	id = "id"
	name = "name"
	room = "room"
	teacher = "teacher"
	is_temporary = "is_temporary"
class class_times(_table):
	__table__ = "class_times"
	day = "day"
	classNum = "classNum"
	start_time = "start_time"
	end_time = "end_time"
class schedule(_table):
	__table__ = "schedule"
	day = "day"
	classNum = "classNum"
	classID = "classID"
class schedule_overrides(_table):
	__table__ = "schedule_overrides"
	date = "date"
	classNum = "classNum"
	classID = "classID"
