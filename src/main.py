from asyncio import new_event_loop, set_event_loop, all_tasks, gather
from logging import getLogger, WARNING, DEBUG, INFO, Formatter
from logging.handlers import TimedRotatingFileHandler
from sys import executable, argv, platform
from pathlib import Path
from datetime import datetime
from os import path, _exit
from packaging.version import Version
import shared

VERSION: Version = Version("4.0.0")
#region Logger setup
logger = getLogger()
def log_namer(default_name:str):
    dirname = path.dirname(default_name)
    filename = path.basename(default_name)
    _, _, date = filename.rpartition(".")
    return path.join(dirname, f"{date}.log")
latestLogPath = Path("logs") / "latest.log"
latestLogPath.parent.mkdir(exist_ok=True, parents=True)
if not latestLogPath.exists():
    with latestLogPath.open("x"):
        logger.warning("Could not find any 'latest.log', Created an empty one")
handler = TimedRotatingFileHandler("logs/latest.log", when="midnight", interval=1, backupCount=5)
handler.suffix = "%Y-%m-%d"
formatter = Formatter(f"%(asctime)s:%(name)-15s:%(funcName)-15s:%(lineno)-3d:%(levelname)-7s:%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
handler.namer = log_namer
logger.addHandler(handler)
logger.setLevel(DEBUG if shared.DEBUG else INFO)
logger.info(f"Application Starting up (v{VERSION})")

getLogger("PIL").setLevel(WARNING)
getLogger("pystray").setLevel(WARNING)
getLogger("asyncio").setLevel(WARNING)
#endregion

def main():
    try:
        shared.RUNTIME.run_forever()
    finally:
        pending = [task for task in all_tasks(shared.RUNTIME) if not task.done()]
        for task in pending:
            task.cancel()
        if pending:
            shared.RUNTIME.run_until_complete(gather(*pending, return_exceptions=True))
        shared.RUNTIME.run_until_complete(shared.RUNTIME.shutdown_asyncgens())
        if hasattr(shared.RUNTIME, "shutdown_default_executor"):
            shared.RUNTIME.run_until_complete(shared.RUNTIME.shutdown_default_executor())
        shared.RUNTIME.close()
        _exit(0)
    pass

try:
    main()
except KeyboardInterrupt:
    logger.info("KeyboardInterrupt received. Exiting...")
    _exit(0)
except Exception as e:
    logger.exception("An unhandled exception occurred during startup")
    _exit(1)