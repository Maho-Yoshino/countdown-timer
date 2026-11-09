import aiosqlite
import const as Const
from typing import AsyncGenerator

db = Const.DATA / "schedule.db"

async def transaction() -> AsyncGenerator[aiosqlite.Connection]:
	con = await aiosqlite.connect(db)
	con.row_factory = aiosqlite.Row
	try:
		cur = await con.cursor()
		try:
			yield cur
			await con.commit()
		except Exception:
			await con.rollback()
			raise
		finally:
			await cur.close()
	finally:
		await con.close()
