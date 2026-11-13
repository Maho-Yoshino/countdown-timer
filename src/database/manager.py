from contextlib import asynccontextmanager

import aiosqlite

import const as Const

db = Const.DATA / "schedule.db"

@asynccontextmanager
async def transaction():
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
