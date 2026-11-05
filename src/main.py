import velopack
from asyncio import all_tasks, gather
from logging import DEBUG, INFO, WARNING, Formatter, getLogger
from logging.handlers import TimedRotatingFileHandler
from os import _exit, path

from packaging.version import Version

import const

VERSION: Version = Version("4.0.0")
#region Logger setup
logger = getLogger()
def log_namer(default_name:str):
    dirname = path.dirname(default_name)
    filename = path.basename(default_name)
    _, _, date = filename.rpartition(".")
    return path.join(dirname, f"{date}.log")
latestLogPath = const.LOGS / "latest.log"
latestLogPath.touch(exist_ok=True)
handler = TimedRotatingFileHandler("logs/latest.log", when="midnight", interval=1, backupCount=5)
handler.suffix = "%Y-%m-%d"
formatter = Formatter("%(asctime)s:%(name)-15s:%(funcName)-15s:%(lineno)-3d:%(levelname)-7s:%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
handler.namer = log_namer
logger.addHandler(handler)
logger.setLevel(DEBUG if const.DEBUG else INFO)
logger.info(f"Application Starting up (v{VERSION})")

getLogger("PIL").setLevel(WARNING)
getLogger("pystray").setLevel(WARNING)
getLogger("asyncio").setLevel(WARNING)
#endregion

def check_updates():
	manager = velopack.UpdateManager(const.REPO)

	update = manager.check_for_updates()
	if update is None:
		return False

	manager.download_updates(update)
	manager.apply_updates_and_restart(update)
	return True

def main():
    velopack.App.run()
    try:
        const.RUNTIME.run_forever()
    finally:
        pending = [task for task in all_tasks(const.RUNTIME) if not task.done()]
        for task in pending:
            task.cancel()
        if pending:
            const.RUNTIME.run_until_complete(gather(*pending, return_exceptions=True))
        const.RUNTIME.run_until_complete(const.RUNTIME.shutdown_asyncgens())
        if hasattr(const.RUNTIME, "shutdown_default_executor"):
            const.RUNTIME.run_until_complete(const.RUNTIME.shutdown_default_executor())
        const.RUNTIME.close()
        _exit(0)

try:
    main()
except KeyboardInterrupt:
    logger.info("KeyboardInterrupt received. Exiting...")
    _exit(0)
except Exception:
    logger.exception("An unhandled exception occurred during startup")
    _exit(1)