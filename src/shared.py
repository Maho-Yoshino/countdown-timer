import asyncio
from os import environ
from platformdirs import user_data_path, user_config_path, user_log_path, user_cache_path

APP_NAME = "countdown-timer"
APP_AUTHOR = "MahoYoshino"

DEBUG: bool = environ.get('TERM_PROGRAM') == 'vscode'
if not DEBUG:
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("-d", "--debug", help="Debug mode switch", action="store_true")
    DEBUG = parser.parse_args().debug

LOGS = user_log_path(APP_NAME, APP_AUTHOR, ensure_exists=True)
CONFIG = user_config_path(APP_NAME, APP_AUTHOR, ensure_exists=True)
DATA = user_data_path(APP_NAME, APP_AUTHOR, ensure_exists=True)
CACHE = user_cache_path(APP_NAME, APP_AUTHOR, ensure_exists=True)

RUNTIME: asyncio.AbstractEventLoop = asyncio.get_event_loop()
