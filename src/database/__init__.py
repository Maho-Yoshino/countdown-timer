from datetime import date, time, datetime
from typing import Optional, Any
from dataclasses import dataclass
import database.manager as Manager
import database.schema as dbSchema

class Schedule:
	@dataclass(slots=True)
	class ClassData:
		classID: int
		name: str
		room: str
		teacher: str
		is_temporary: bool

		async def load(cls, day: int, classNum: int) -> Optional["Schedule.ClassData"]:
			"""Fetches the class data for a given day and class number from the database."""
			async with Manager.transaction() as cur:
				query = f"""
					SELECT *
					FROM {dbSchema.schedule.q(dbSchema.schedule.day)} AS s JOIN {dbSchema.classes.q(dbSchema.classes.id)} AS c
					ON s.{dbSchema.schedule.q(dbSchema.schedule.classID)} = c.{dbSchema.classes.q(dbSchema.classes.id)}
					WHERE s.{dbSchema.schedule.q(dbSchema.schedule.day)} = ?
					AND s.{dbSchema.schedule.q(dbSchema.schedule.classNum)} = ?;
				"""
				# Execute the query with the provided parameters (day, classNum)
				# This is a placeholder for actual database execution logic
				result = await cur.execute(query, (day, classNum))
				result = await result.fetchone()
				if result:
					return cls(
						classID=result[0],
						name=result[1],
						room=result[2],
						teacher=result[3],
						is_temporary=int(result[4]) == 1
					)
				return None
	async def prune(self) -> None:
		"""Removes all temporary classes that haven't happened yet from the database."""
		async with Manager.transaction() as cur:
			query = f"""
				DELETE FROM {dbSchema.classes.q(dbSchema.classes.id)}
				WHERE {dbSchema.classes.q(dbSchema.classes.is_temporary)} = 1 AND {dbSchema.classes.q(dbSchema.classes.id)} NOT IN (
					SELECT {dbSchema.schedule.q(dbSchema.schedule.classID)}
					FROM {dbSchema.schedule.q(dbSchema.schedule.day)} AS s
					WHERE s.{dbSchema.schedule.q(dbSchema.schedule.day)} >= ?
				);
			"""
			await cur.execute(query, (date.today(),))
	pass
