from pathlib import Path
import os
import logging
import platform
import sys


DEBUG = True
if DEBUG:
    LEVEL = logging.INFO
else:
    LEVEL = logging.WARNING

APP_NAME = '行恒'

WORK_DIR = Path(os.path.expanduser("~")) / ".xingheng"

if WORK_DIR.exists() is False:
    WORK_DIR.mkdir(parents=True)

BASE_DIR = Path(os.path.dirname(__file__))

logging.basicConfig(level=LEVEL, filename=str(BASE_DIR/ "debug.log"), filemode="w", format="%(asctime)s-%(levelname)s %(filename)s:%(lineno)s:: %(message)s")

TOKEN_PATH = WORK_DIR / "token.json"

SERVER_HOST = "www.51zhi.com"

TOMATO_DONE_MP3 = BASE_DIR / "resources/mp3" / "tomato_done.mp3"
REST_DONE_MP3 = BASE_DIR / "resources/mp3" / "rest_done.mp3"

APP_BUILD = 202401
APP_PLATFORM = platform.uname().system
APP_VERSION = platform.uname().release

LOGO_PATH = str(BASE_DIR / "resources/images/logo.icns")

APP_SIZE = (800, 600)