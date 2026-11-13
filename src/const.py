import asyncio
from os import getenv

from platformdirs import (
	user_cache_path,
	user_config_path,
	user_data_path,
	user_log_path,
)

DEBUG:bool = int(getenv("DEBUG", "0")) == 1

APP_NAME = "countdown-timer" if not DEBUG else "countdown-timer-dev"
APP_AUTHOR = "MahoYoshino"
REPO = "https://github.com/Maho-Yoshino/countdown-timer"

LOGS = user_log_path(APP_NAME, APP_AUTHOR, ensure_exists=True)
CONFIG = user_config_path(APP_NAME, APP_AUTHOR, ensure_exists=True)
DATA = user_data_path(APP_NAME, APP_AUTHOR, ensure_exists=True)
CACHE = user_cache_path(APP_NAME, APP_AUTHOR, ensure_exists=True)

RUNTIME: asyncio.AbstractEventLoop = asyncio.new_event_loop()
