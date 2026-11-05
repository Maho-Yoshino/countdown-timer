import asyncio
from os import environ

DEBUG: bool = environ.get('TERM_PROGRAM') == 'vscode'
if not DEBUG:
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("-d", "--debug", help="Debug mode switch", action="store_true")
    DEBUG = parser.parse_args().debug

RUNTIME: asyncio.AbstractEventLoop = asyncio.get_event_loop()
