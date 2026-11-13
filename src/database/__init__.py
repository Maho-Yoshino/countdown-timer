import aiosqlite
from datetime import date, time
import database.manager as Manager
import database.schema as dbSchema

class Schedule:
	class ClassData:
		start: time
		end: time
		name: str | None
		room: str | None
		teacher: str | None
		temporary: bool

		def __init__(self, data: aiosqlite.Row):
			self.start = time.strptime(data[dbSchema.class_times.start_time], "%H:%M")
			self.end = time.strptime(data[dbSchema.class_times.end_time], "%H:%M")
			self.name = data[dbSchema.classes.name]
			self.room = data[dbSchema.classes.room]
			self.teacher = data[dbSchema.classes.teacher]
			self.temporary = int(data[dbSchema.classes.is_temporary]) == 1

	@staticmethod
	async def prune():
		"""Removes all temporary classes that have happened already and won't happen again from the database."""
		async with Manager.transaction() as cur:
			await cur.execute(
				f"""
				DELETE FROM {dbSchema.classes.t()}
				WHERE {dbSchema.classes.is_temporary.q()} = 1 AND {dbSchema.classes.id.q()} NOT IN (
					SELECT {dbSchema.schedule.classID}
					FROM {dbSchema.schedule.t()} AS s
					WHERE s.{dbSchema.schedule.day} >= ?
				);
				""",
				(date.today(),)
			)
	@staticmethod
	async def get_schedule() -> dict[int, ClassData]:
		async with Manager.transaction() as cur:
			_ = await cur.execute(f"""
				SELECT *
					FROM {dbSchema.schedule.t()}
					INNER JOIN {dbSchema.classes} ON ({dbSchema.schedule.classID} = {dbSchema.classes.id})
					INNER JOIN {dbSchema.class_times} ON ({dbSchema.schedule.classNum} = {dbSchema.class_times.classNum} AND {dbSchema.class_times} = ?)
					WHERE {dbSchema.schedule.day} = ?;
				""",
				(date.today().weekday(),date.today().weekday())
			)
			regular_schedule = await _.fetchall()

			_ = await cur.execute(f"""
				SELECT *
					FROM {dbSchema.schedule_overrides.t()}
					INNER JOIN {dbSchema.classes.t()} ON ({dbSchema.schedule_overrides.classID.q()} = {dbSchema.classes.id.q()})
					INNER JOIN {dbSchema.class_times.t()} ON ({dbSchema.schedule_overrides.classNum.q()} = {dbSchema.class_times.classNum.q()} AND {dbSchema.class_times.day.q()} = ?)
					WHERE {dbSchema.schedule_overrides.date} = ?;
				""",
				(date.today().weekday(),date.today())
			)
			overrides = await _.fetchall()

		classes: dict[int, Schedule.ClassData] = {}
		for row in overrides:
			classNum = int(row[dbSchema.schedule_overrides.classNum])
			classes[classNum] = Schedule.ClassData(row)

		for row in regular_schedule:
			classNum = int(row[dbSchema.schedule.classNum])
			if classNum in classes:
				continue
			classes[classNum] = Schedule.ClassData(row)

		return classes
